"""
CrustData API Client
====================
A clean, robust wrapper around all CrustData REST endpoints.
Handles auth, rate limiting, retries, and error reporting.

Endpoints covered:
  - Company Search   POST /screener/company/search
  - Company Enrich   GET  /screener/company
  - People Search    POST /screener/person/search
  - People Enrich    GET  /screener/person/enrich
  - Social Posts     GET  /screener/social_posts
  - Jobs (via enrich, field: job_openings)

Auth note:
  The public docs show two formats — "Token <key>" and "Bearer <key>".
  We default to "Token" which works for all enrichment endpoints.
  If a search endpoint returns 401, flip USE_BEARER to True.
"""

import os
import time
import logging
from typing import Optional

import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ─── Constants ───────────────────────────────────────────────────────────────

BASE_URL = "https://api.crustdata.com"
DEFAULT_TIMEOUT = 30  # seconds
MAX_RETRIES = 3
RATE_LIMIT_PAUSE = 1.2  # seconds between calls (be a good API citizen)


# ─── Exceptions ──────────────────────────────────────────────────────────────

class CrustDataError(Exception):
    """Base exception for CrustData API errors."""


class CrustDataAuthError(CrustDataError):
    """Raised when the API key is missing or invalid."""


class CrustDataRateLimitError(CrustDataError):
    """Raised when we hit a rate limit (429)."""


class CrustDataNotFoundError(CrustDataError):
    """Raised when a resource is not found (404)."""


# ─── Client ──────────────────────────────────────────────────────────────────

class CrustDataClient:
    """
    Main client for the CrustData API.

    Usage:
        from src.crustdata.client import CrustDataClient
        client = CrustDataClient()

        # Enrich a company
        data = client.enrich_company("hubspot.com")

        # Search for companies
        companies = client.search_companies(filters=[...])
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("CRUSTDATA_API_KEY")
        if not self.api_key:
            raise CrustDataAuthError(
                "No API key found. Set CRUSTDATA_API_KEY in your .env file.\n"
                "Get a key at: crustdata.com → sign up → API settings"
            )
        self._last_call_time = 0.0

    # ─── Internal Helpers ────────────────────────────────────────────────────

    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _rate_limit(self):
        """Enforce minimum gap between requests."""
        elapsed = time.time() - self._last_call_time
        if elapsed < RATE_LIMIT_PAUSE:
            time.sleep(RATE_LIMIT_PAUSE - elapsed)
        self._last_call_time = time.time()

    def _handle_response(self, response: requests.Response) -> dict:
        """Parse response and raise typed exceptions on errors."""
        if response.status_code == 401:
            raise CrustDataAuthError(
                f"Authentication failed (401). Check your CRUSTDATA_API_KEY.\n"
                f"Response: {response.text[:200]}"
            )
        if response.status_code == 404:
            raise CrustDataNotFoundError(
                f"Resource not found (404). URL: {response.url}"
            )
        if response.status_code == 429:
            raise CrustDataRateLimitError(
                "Rate limit hit (429). The retry logic will handle this."
            )
        if response.status_code >= 400:
            raise CrustDataError(
                f"API error {response.status_code}: {response.text[:300]}"
            )
        try:
            return response.json()
        except Exception:
            raise CrustDataError(
                f"Could not parse JSON response: {response.text[:200]}"
            )

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((CrustDataRateLimitError, requests.ConnectionError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def _get(self, path: str, params: dict = None) -> dict:
        self._rate_limit()
        url = f"{BASE_URL}{path}"
        logger.debug(f"GET {url} params={params}")
        resp = requests.get(
            url,
            headers=self._get_headers(),
            params=params,
            timeout=DEFAULT_TIMEOUT,
        )
        return self._handle_response(resp)

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((CrustDataRateLimitError, requests.ConnectionError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def _post(self, path: str, payload: dict) -> dict:
        self._rate_limit()
        url = f"{BASE_URL}{path}"
        logger.debug(f"POST {url} payload={payload}")
        resp = requests.post(
            url,
            headers=self._get_headers(),
            json=payload,
            timeout=DEFAULT_TIMEOUT,
        )
        return self._handle_response(resp)

    # ─── Company APIs ────────────────────────────────────────────────────────

    def enrich_company(
        self,
        domain: str,
        fields: str = "company_name,headcount,funding_and_investment,web_traffic,decision_makers,job_openings",
        realtime: bool = False,
    ) -> dict:
        """
        Enrich a single company by domain.

        Args:
            domain: Company website domain, e.g. "hubspot.com"
            fields: Comma-separated list of fields to return
            realtime: If True, force a fresh crawl (uses 5x credits). Use sparingly.

        Returns:
            Dict with company data, or empty dict if not found.

        Credit cost:
            - realtime=False: 1 credit
            - realtime=True:  5 credits (only use for companies not in DB)
        """
        params = {
            "company_domain": domain,
            "fields": fields,
        }
        if realtime:
            params["enrich_realtime"] = "True"

        logger.info(f"Enriching company: {domain}")
        data = self._get("/screener/company", params=params)

        # API returns a list; we want the first item
        if isinstance(data, list) and len(data) > 0:
            return data[0]
        return {}

    def enrich_companies_batch(
        self,
        domains: list[str],
        fields: str = "company_name,headcount,funding_and_investment,web_traffic,decision_makers",
    ) -> list[dict]:
        """
        Enrich multiple companies at once (comma-separated domains).
        Max ~10 domains per call recommended.

        Returns:
            List of company dicts (same order as input).
        """
        domains_str = ",".join(domains)
        params = {
            "company_domain": domains_str,
            "fields": fields,
        }
        logger.info(f"Batch enriching {len(domains)} companies")
        data = self._get("/screener/company", params=params)
        return data if isinstance(data, list) else []

    def search_companies(
        self,
        filters: list[dict],
        page: int = 1,
    ) -> dict:
        """
        Search for companies using structured filters.

        Args:
            filters: List of filter objects. Each must have:
                     - filter_type: e.g. "COMPANY_HEADCOUNT"
                     - type: "in" | "not in" | "between"
                     - value: list or range dict
            page: Page number (25 results per page)

        Returns:
            {
                "companies": [...],
                "total_display_count": int
            }

        Example filter:
            {
                "filter_type": "COMPANY_HEADCOUNT",
                "type": "in",
                "value": ["11-50", "51-200"]
            }
        """
        payload = {"filters": filters, "page": page}
        logger.info(f"Searching companies (page {page}) with {len(filters)} filters")
        return self._post("/screener/company/search", payload=payload)

    def screen_companies(
        self,
        conditions: list[dict],
        offset: int = 0,
        count: int = 100,
    ) -> dict:
        """
        Screen companies using the older /screener/screen/ endpoint.
        Useful for numeric filters like exact headcount ranges, funding amounts.

        Args:
            conditions: List of conditions. Each must have:
                        - column: field name (e.g. "headcount")
                        - type: operator ("=>", "<=", "=", "()")
                        - value: the filter value
                        - allow_null: boolean
            offset: Pagination offset
            count: Results per page (max 100)

        Returns:
            {
                "records": [...],
                "count": int
            }

        Example condition:
            {"column": "headcount", "type": "=>", "value": 10, "allow_null": False}
        """
        payload = {
            "filters": {
                "op": "and",
                "conditions": conditions,
            },
            "offset": offset,
            "count": count,
            "sorts": [],
        }
        logger.info(f"Screening companies with {len(conditions)} conditions")
        return self._post("/screener/screen/", payload=payload)

    # ─── People APIs ─────────────────────────────────────────────────────────

    def enrich_person(self, linkedin_url: str) -> dict:
        """
        Get full profile for a LinkedIn user.

        Args:
            linkedin_url: Full LinkedIn profile URL
                          e.g. "https://www.linkedin.com/in/dtpow/"

        Returns:
            Person profile dict with employer history, skills, etc.

        Note:
            If the profile isn't in the DB yet, data returns within 60 minutes.
        """
        params = {"linkedin_profile_url": linkedin_url}
        logger.info(f"Enriching person: {linkedin_url}")
        data = self._get("/screener/person/enrich", params=params)
        if isinstance(data, list) and len(data) > 0:
            return data[0]
        return {}

    def search_people(
        self,
        filters: list[dict],
        page: int = 1,
    ) -> dict:
        """
        Search for people using structured filters.

        Args:
            filters: List of filter objects. Each must have:
                     - filter_type: e.g. "SENIORITY_LEVEL"
                     - type: "in" | "not in"
                     - value: list of valid values
            page: Page number (25 results per page)

        Returns:
            {
                "profiles": [...],
                "total_display_count": str (e.g. "78K+")
            }

        Valid SENIORITY_LEVEL values:
            "CXO", "Vice President", "Director",
            "Experienced Manager", "Entry Level Manager",
            "Strategic", "Senior", "Entry Level", "In Training"
        """
        payload = {"filters": filters, "page": page}
        logger.info(f"Searching people (page {page}) with {len(filters)} filters")
        return self._post("/screener/person/search", payload=payload)

    def get_social_posts(
        self,
        linkedin_url: str,
        page: int = 1,
    ) -> list[dict]:
        """
        Get recent LinkedIn posts from a person.

        Args:
            linkedin_url: LinkedIn profile URL
            page: Page number (20 posts per page)

        Returns:
            List of post objects with: text, engagement, date

        Warning:
            This endpoint has high latency (30–60 seconds).
            Call it only for high-priority contacts.
        """
        params = {
            "person_linkedin_url": linkedin_url,
            "page": page,
        }
        logger.info(f"Fetching social posts for: {linkedin_url}")
        data = self._get("/screener/social_posts", params=params)

        # Response format varies — handle both list and dict
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("posts", data.get("data", []))
        return []

    # ─── Convenience methods ─────────────────────────────────────────────────

    def get_company_with_jobs(self, domain: str) -> dict:
        """
        Get company data including open job listings.
        Used to detect hiring signals.
        """
        return self.enrich_company(
            domain,
            fields="company_name,headcount,funding_and_investment,job_openings,linkedin_profile_url",
        )

    def get_decision_makers(self, domain: str) -> list[dict]:
        """
        Get founder + senior leadership at a company.
        Returns list of decision maker profiles.
        """
        company = self.enrich_company(
            domain,
            fields="decision_makers,company_name",
        )
        return company.get("decision_makers", {}).get("profiles", [])

    def ping(self) -> bool:
        """
        Quick health check — verifies the API key works.
        Uses a known company (hubspot.com) to test the enrichment endpoint.

        Returns:
            True if connection is working, False otherwise.
        """
        try:
            data = self.enrich_company("hubspot.com", fields="company_name")
            name = data.get("company_name", "")
            if name:
                logger.info(f"✅ CrustData ping success — got: {name}")
                return True
            logger.warning("⚠️  Ping returned empty data")
            return False
        except CrustDataAuthError:
            logger.error("❌ Auth failed — check your CRUSTDATA_API_KEY")
            return False
        except Exception as e:
            logger.error(f"❌ Ping failed: {e}")
            return False