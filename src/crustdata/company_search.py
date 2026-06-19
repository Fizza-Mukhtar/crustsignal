"""
ICP Discovery & Scoring
=======================
Finds companies that match CrustData's Ideal Customer Profile (ICP)
and scores them based on how likely they are to buy.

CrustData's ICP (based on their case studies and customer list):
  - AI companies building products that need live data
  - Sales tech: AI SDRs, outbound automation, sales intelligence
  - HR tech: AI recruiting, ATS, talent intelligence
  - Investment tech: VC/PE deal sourcing, portfolio monitoring
  - PLG SaaS: companies with free signups needing enrichment
  - Recently funded (they have budget and are scaling)
  - Small enough that they haven't built their own data infra
  - Actively hiring engineers/data roles (they're building)

Scoring rubric (100 points total):
  - Industry match         30 pts  (are they in a Crustdata use case?)
  - Funding recency        25 pts  (funded in past 45 days = max)
  - Headcount growth       25 pts  (growing fast = scaling = need data)
  - Size fit               20 pts  (10-300 employees is sweet spot)

ICP threshold: 0.60 (60 points out of 100)
"""

import logging
from typing import Optional
from dataclasses import dataclass, field

from src.crustdata.client import CrustDataClient

logger = logging.getLogger(__name__)


# ─── ICP Definition ──────────────────────────────────────────────────────────

# Industries / keywords that match CrustData's use cases
ICP_INDUSTRY_KEYWORDS = [
    # Core GTM / sales tech
    "sales", "sdr", "outbound", "prospecting", "sales intelligence",
    "gtm", "go-to-market", "revenue", "crm", "sales automation",

    # AI / ML broadly
    "artificial intelligence", "machine learning", "ai", "llm",
    "generative ai", "ai agent", "agentic",

    # Recruiting / HR tech
    "recruiting", "recruitment", "talent", "hr tech", "ats",
    "applicant tracking", "hiring", "talent acquisition",

    # Investment / VC
    "venture capital", "vc", "private equity", "deal sourcing",
    "investment research", "due diligence",

    # Data & analytics
    "data intelligence", "data enrichment", "b2b data",
    "business intelligence", "market intelligence",

    # SaaS / product-led
    "saas", "software", "api", "platform", "developer tools",
]

# Industries that indicate STRONG fit (get bonus points)
HIGH_FIT_INDUSTRIES = [
    "Computer Software",
    "Information Technology and Services",
    "Internet",
    "Staffing and Recruiting",
    "Financial Services",
    "Venture Capital & Private Equity",
    "Human Resources",
    "Marketing and Advertising",
]

# Company sizes (headcount) that are Crustdata's sweet spot
IDEAL_HEADCOUNT_MIN = 10
IDEAL_HEADCOUNT_MAX = 300


# ─── Data Classes ────────────────────────────────────────────────────────────

@dataclass
class ScoredCompany:
    """A company that has been discovered and scored against the ICP."""
    company_name: str
    company_domain: str
    linkedin_url: str = ""
    industry: str = ""
    headcount: int = 0
    headcount_growth_6m_pct: float = 0.0
    headcount_growth_1y_pct: float = 0.0
    total_funding_usd: int = 0
    last_round_type: str = ""
    days_since_last_funding: int = 999
    location: str = ""
    description: str = ""

    # Scoring breakdown
    icp_score: float = 0.0
    score_breakdown: dict = field(default_factory=dict)

    # Signals for email generation (populated later)
    open_jobs: list = field(default_factory=list)
    top_signals: list = field(default_factory=list)

    @property
    def qualifies(self) -> bool:
        """Returns True if this company passes the ICP threshold."""
        return self.icp_score >= 0.60

    def __repr__(self):
        return (
            f"<ScoredCompany {self.company_name!r} "
            f"score={self.icp_score:.2f} "
            f"funded={self.days_since_last_funding}d ago>"
        )


# ─── Scoring Algorithm ───────────────────────────────────────────────────────

def score_company(company_data: dict) -> tuple[float, dict]:
    """
    Score a company against CrustData's ICP.

    Args:
        company_data: Raw dict from CrustData API (company search or enrichment)

    Returns:
        Tuple of (score: float 0.0–1.0, breakdown: dict)
    """
    points = 0
    breakdown = {}

    # ── 1. Industry match (30 pts) ──────────────────────────────────────────
    industry = (company_data.get("industry") or "").lower()
    description = (company_data.get("description") or "").lower()
    specialties = " ".join(company_data.get("specialties") or []).lower()
    name = (company_data.get("name") or company_data.get("company_name") or "").lower()

    searchable_text = f"{industry} {description} {specialties} {name}"

    # Strong industry match
    strong_match = any(h.lower() in industry for h in HIGH_FIT_INDUSTRIES)
    # Keyword match anywhere in description/specialties
    keyword_matches = [kw for kw in ICP_INDUSTRY_KEYWORDS if kw in searchable_text]

    if strong_match and keyword_matches:
        industry_pts = 30
    elif keyword_matches:
        industry_pts = min(30, 10 * len(keyword_matches[:3]))
    elif strong_match:
        industry_pts = 18
    else:
        industry_pts = 0

    points += industry_pts
    breakdown["industry"] = {
        "points": industry_pts,
        "max": 30,
        "strong_match": strong_match,
        "keywords_matched": keyword_matches[:5],
    }

    # ── 2. Funding recency (25 pts) ─────────────────────────────────────────
    # Try multiple field names (API formats differ)
    days_funded = (
        company_data.get("days_since_last_fundraise")
        or company_data.get("days_since_funding")
        or 999
    )
    try:
        days_funded = int(days_funded)
    except (TypeError, ValueError):
        days_funded = 999

    if days_funded <= 15:
        funding_pts = 25   # Just raised! Perfect timing.
    elif days_funded <= 30:
        funding_pts = 22
    elif days_funded <= 45:
        funding_pts = 18
    elif days_funded <= 90:
        funding_pts = 12
    elif days_funded <= 180:
        funding_pts = 5
    else:
        funding_pts = 0

    points += funding_pts
    breakdown["funding_recency"] = {
        "points": funding_pts,
        "max": 25,
        "days_since_funding": days_funded,
    }

    # ── 3. Headcount growth (25 pts) ────────────────────────────────────────
    # Try to get growth from employee_growth_percentages array
    growth_6m = 0.0
    growth_1y = 0.0

    growth_data = company_data.get("employee_growth_percentages") or []
    for g in growth_data:
        ts = (g.get("timespan") or "").upper()
        pct = g.get("percentage") or 0
        if ts == "SIX_MONTHS":
            growth_6m = float(pct)
        elif ts == "YEAR":
            growth_1y = float(pct)

    # Also check flat field (enrichment API uses different format)
    if not growth_6m:
        growth_6m = float(company_data.get("headcount_qoq_pct") or 0)
    if not growth_1y:
        growth_1y = float(company_data.get("headcount_yoy_pct") or 0)

    # Use the most available metric
    best_growth = max(growth_6m, growth_1y)
    if best_growth >= 30:
        growth_pts = 25  # Hyper growth
    elif best_growth >= 20:
        growth_pts = 20
    elif best_growth >= 10:
        growth_pts = 14
    elif best_growth >= 5:
        growth_pts = 8
    else:
        growth_pts = 0

    points += growth_pts
    breakdown["headcount_growth"] = {
        "points": growth_pts,
        "max": 25,
        "growth_6m_pct": growth_6m,
        "growth_1y_pct": growth_1y,
    }

    # ── 4. Size fit (20 pts) ────────────────────────────────────────────────
    headcount = (
        company_data.get("employee_count")
        or company_data.get("headcount")
        or 0
    )
    try:
        headcount = int(headcount)
    except (TypeError, ValueError):
        headcount = 0

    if IDEAL_HEADCOUNT_MIN <= headcount <= IDEAL_HEADCOUNT_MAX:
        size_pts = 20  # Perfect size
    elif 5 <= headcount < IDEAL_HEADCOUNT_MIN:
        size_pts = 12  # Very small but could work
    elif IDEAL_HEADCOUNT_MAX < headcount <= 700:
        size_pts = 10  # Larger but still viable
    elif 700 < headcount <= 2000:
        size_pts = 5   # Getting big, but may still need enrichment API
    else:
        size_pts = 0   # Too small (< 5) or massive enterprise

    points += size_pts
    breakdown["size_fit"] = {
        "points": size_pts,
        "max": 20,
        "headcount": headcount,
        "ideal_range": f"{IDEAL_HEADCOUNT_MIN}–{IDEAL_HEADCOUNT_MAX}",
    }

    score = round(points / 100.0, 4)
    return score, breakdown


# ─── Company Object Builder ──────────────────────────────────────────────────

def build_scored_company(raw: dict) -> ScoredCompany:
    """
    Convert raw API data into a ScoredCompany with ICP score attached.

    Handles field name differences between search API and enrichment API.
    """
    # Field aliases: search API uses different names than enrichment API
    name = raw.get("name") or raw.get("company_name") or "Unknown"
    domain = (
        raw.get("website", "")
        or raw.get("company_website_domain", "")
        or raw.get("company_website", "")
        or ""
    ).replace("https://", "").replace("http://", "").rstrip("/")

    linkedin_url = (
        raw.get("linkedin_company_url")
        or raw.get("linkedin_profile_url")
        or ""
    )

    # Funding data
    days_funded = (
        raw.get("days_since_last_fundraise")
        or raw.get("days_since_funding")
        or 999
    )
    total_funding = (
        raw.get("total_funding_raised_usd")
        or raw.get("total_investment_usd")
        or 0
    )
    last_round = (
        raw.get("last_round_type")
        or raw.get("last_funding_round_type")
        or ""
    )

    # Growth data
    growth_data = raw.get("employee_growth_percentages") or []
    growth_6m = next(
        (g.get("percentage", 0) for g in growth_data if (g.get("timespan") or "").upper() == "SIX_MONTHS"),
        raw.get("headcount_qoq_pct") or 0,
    )
    growth_1y = next(
        (g.get("percentage", 0) for g in growth_data if (g.get("timespan") or "").upper() == "YEAR"),
        raw.get("headcount_yoy_pct") or 0,
    )

    score, breakdown = score_company(raw)

    return ScoredCompany(
        company_name=name,
        company_domain=domain,
        linkedin_url=linkedin_url,
        industry=raw.get("industry") or "",
        headcount=raw.get("employee_count") or raw.get("headcount") or 0,
        headcount_growth_6m_pct=float(growth_6m),
        headcount_growth_1y_pct=float(growth_1y),
        total_funding_usd=int(total_funding or 0),
        last_round_type=last_round,
        days_since_last_funding=int(days_funded or 999),
        location=raw.get("location") or "",
        description=(raw.get("description") or "")[:500],
        icp_score=score,
        score_breakdown=breakdown,
    )


# ─── Discovery Queries ───────────────────────────────────────────────────────

def get_icp_filters_for_search_api() -> list[dict]:
    """
    Filters for the /screener/company/search endpoint.
    This is the primary discovery method.

    Targets:
      - Companies sized 11 to 500 employees
      - Had a funding event in the past 12 months
      - In tech/software/internet/HR/finance industries
    """
    return [
        {
            "filter_type": "COMPANY_HEADCOUNT",
            "type": "in",
            "value": ["11-50", "51-200", "201-500"],
        },
        {
            "filter_type": "ACCOUNT_ACTIVITIES",
            "type": "in",
            "value": ["Funding events in past 12 months"],
        },
        {
            "filter_type": "INDUSTRY",
            "type": "in",
            "value": [
                "Computer Software",
                "Internet",
                "Information Technology and Services",
                "Staffing and Recruiting",
                "Financial Services",
                "Marketing and Advertising",
                "Human Resources",
            ],
        },
    ]


def get_icp_conditions_for_screener() -> list[dict]:
    """
    Conditions for the older /screener/screen/ endpoint.
    Useful for numeric range filters.

    Targets:
      - 10–500 employees
      - Funded in past 60 days
      - Raised at least $500K total
    """
    return [
        {
            "column": "headcount",
            "type": "=>",
            "value": 10,
            "allow_null": False,
        },
        {
            "column": "headcount",
            "type": "<=",
            "value": 500,
            "allow_null": False,
        },
        {
            "column": "days_since_last_fundraise",
            "type": "<=",
            "value": 60,
            "allow_null": False,
        },
        {
            "column": "total_investment_usd",
            "type": "=>",
            "value": 500_000,
            "allow_null": False,
        },
    ]


# ─── Main Discovery Function ─────────────────────────────────────────────────

def discover_icp_companies(
    client: CrustDataClient,
    max_pages: int = 4,
    score_threshold: float = 0.60,
    use_screen_endpoint: bool = False,
) -> list[ScoredCompany]:
    """
    Main discovery function. Runs the search and returns qualified companies.

    Args:
        client: Authenticated CrustDataClient instance
        max_pages: How many pages to pull (25 results per page)
        score_threshold: Minimum ICP score to include (0.0–1.0)
        use_screen_endpoint: If True, use /screener/screen/ instead of /screener/company/search

    Returns:
        List of ScoredCompany objects that pass the threshold, sorted by score.
    """
    all_companies = []
    qualified = []

    logger.info(f"Starting ICP discovery (max_pages={max_pages}, threshold={score_threshold})")

    if use_screen_endpoint:
        # ── Screener approach (numeric filters) ──────────────────────────────
        logger.info("Using /screener/screen/ endpoint")
        for page_offset in range(0, max_pages * 100, 100):
            try:
                result = client.screen_companies(
                    conditions=get_icp_conditions_for_screener(),
                    offset=page_offset,
                    count=100,
                )
                records = result.get("records") or []
                if not records:
                    logger.info(f"No more records at offset {page_offset}")
                    break

                logger.info(f"  Got {len(records)} records at offset {page_offset}")
                all_companies.extend(records)
            except Exception as e:
                logger.error(f"Screen endpoint error at offset {page_offset}: {e}")
                break

    else:
        # ── New Company Search API (filter-based) ─────────────────────────
        logger.info("Using /screener/company/search endpoint")
        filters = get_icp_filters_for_search_api()

        for page in range(1, max_pages + 1):
            try:
                result = client.search_companies(filters=filters, page=page)
                companies = result.get("companies") or []
                total = result.get("total_display_count") or 0

                if not companies:
                    logger.info(f"No more companies at page {page}")
                    break

                logger.info(f"  Page {page}: {len(companies)} companies (total: {total})")
                all_companies.extend(companies)
            except Exception as e:
                logger.error(f"Search error at page {page}: {e}")
                break

    logger.info(f"Total discovered: {len(all_companies)} companies")

    # Score every company
    for raw in all_companies:
        try:
            scored = build_scored_company(raw)
            if scored.icp_score >= score_threshold:
                qualified.append(scored)
        except Exception as e:
            logger.warning(f"Scoring error for {raw.get('name', 'unknown')}: {e}")

    # Sort by score, highest first
    qualified.sort(key=lambda c: c.icp_score, reverse=True)

    logger.info(
        f"Qualified: {len(qualified)}/{len(all_companies)} companies "
        f"passed threshold {score_threshold}"
    )
    return qualified