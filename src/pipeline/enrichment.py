"""
Enrichment Pipeline — Stage 2 & 3
===================================
Takes qualified companies and enriches them with:
  - Headcount trend details
  - Job openings (hiring signals)
  - Top decision maker (CTO / Founder / Head of Data)
  - Decision maker's recent LinkedIn posts
  
Works in mock mode (USE_MOCK=true) or real API mode (USE_MOCK=false).
"""

import os
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

USE_MOCK = os.getenv("USE_MOCK", "true").lower() == "true"

# Seniority priority order — we want the most senior technical/data person
SENIORITY_PRIORITY = [
    "CXO",           # CEO, CTO, CPO
    "Vice President", # VP Engineering, VP Data
    "Director",
    "Experienced Manager",
    "Strategic",
    "Senior",
]

TARGET_TITLES = [
    "cto", "chief technology", "co-founder", "chief executive",
    "vp engineering", "vp of engineering", "head of engineering",
    "head of data", "vp data", "director of engineering",
    "founder", "president",
]


def enrich_company(client, company) -> dict:
    """
    Pull full enrichment data for a qualified company.
    
    Args:
        client: CrustDataClient instance (ignored in mock mode)
        company: ScoredCompany object
    
    Returns:
        Dict with enriched data including jobs and headcount detail
    """
    if USE_MOCK:
        from src.crustdata.mock_data import get_mock_company
        data = get_mock_company(company.company_domain)
        if not data:
            # fallback: use data already on the ScoredCompany
            return {
                "headcount": company.headcount,
                "growth_6m": company.headcount_growth_6m_pct,
                "growth_1y": company.headcount_growth_1y_pct,
                "funding_amount": company.total_funding_usd,
                "funding_round": company.last_round_type,
                "days_funded": company.days_since_last_funding,
                "job_openings": [],
                "monthly_visitors": 0,
            }
        hc = data.get("headcount", {})
        fi = data.get("funding_and_investment", {})
        wt = data.get("web_traffic", {})
        return {
            "headcount": hc.get("latest_count", company.headcount),
            "growth_6m": hc.get("six_month_growth_percent", company.headcount_growth_6m_pct),
            "growth_1y": hc.get("one_year_growth_percent", company.headcount_growth_1y_pct),
            "funding_amount": fi.get("last_round_investment_usd", company.total_funding_usd),
            "funding_round": fi.get("last_round_type", company.last_round_type),
            "days_funded": fi.get("days_since_last_fundraise", company.days_since_last_funding),
            "job_openings": data.get("job_openings", []),
            "monthly_visitors": wt.get("monthly_visitors", 0),
            "visitor_growth": wt.get("mom_growth_percent", 0),
        }
    else:
        # Real API mode
        logger.info(f"[REAL API] Enriching: {company.company_domain}")
        data = client.get_company_with_jobs(company.company_domain)
        if not data:
            logger.warning(f"No enrichment data for {company.company_domain}")
            return {}

        hc = data.get("headcount") or {}
        fi = data.get("funding_and_investment") or {}
        wt = data.get("web_traffic") or {}

        # headcount field can be int OR dict depending on fields requested
        if isinstance(hc, dict):
            headcount_count = hc.get("latest_count") or hc.get("count") or company.headcount
        else:
            headcount_count = int(hc) if hc else company.headcount

        return {
            "headcount": headcount_count,
            "growth_6m": company.headcount_growth_6m_pct,
            "growth_1y": company.headcount_growth_1y_pct,
            "funding_amount": fi.get("last_round_investment_usd") or company.total_funding_usd,
            "funding_round": fi.get("last_round_type") or company.last_round_type,
            "days_funded": fi.get("days_since_last_fundraise") or company.days_since_last_funding,
            "job_openings": data.get("job_openings") or [],
            "monthly_visitors": wt.get("monthly_visitors") or 0,
            "visitor_growth": wt.get("mom_growth_percent") or 0,
        }


def find_best_contact(client, company, enriched: dict) -> dict:
    """
    Find the best contact to email at this company.
    Priority: CTO > Founder > VP Engineering > Head of Data > CEO

    Returns a contact dict with name, title, linkedin_url.
    """
    if USE_MOCK:
        from src.crustdata.mock_data import get_mock_company
        data = get_mock_company(company.company_domain)
        profiles = []
        if data:
            profiles = data.get("decision_makers", {}).get("profiles", [])
    else:
        # Real API: use decision_makers from enrichment or people search
        logger.info(f"[REAL API] Finding contact for: {company.company_domain}")
        profiles = client.get_decision_makers(company.company_domain)

        if not profiles:
            # Fallback: people search by company domain
            try:
                result = client.search_people(
                    filters=[
                        {
                            "filter_type": "CURRENT_COMPANY",
                            "type": "in",
                            "value": [company.company_name],
                        },
                        {
                            "filter_type": "SENIORITY_LEVEL",
                            "type": "in",
                            "value": ["CXO", "Vice President", "Director"],
                        },
                    ]
                )
                profiles = result.get("profiles", [])
            except Exception as e:
                logger.warning(f"People search failed for {company.company_name}: {e}")

    if not profiles:
        return {}

    # Score each profile and pick best
    def contact_score(profile):
        title = (profile.get("title") or "").lower()
        seniority = profile.get("seniority") or ""

        # Title match score (higher = better)
        title_score = 0
        for i, keyword in enumerate(TARGET_TITLES):
            if keyword in title:
                title_score = len(TARGET_TITLES) - i
                break

        # Seniority score
        seniority_score = 0
        for i, level in enumerate(SENIORITY_PRIORITY):
            if level == seniority:
                seniority_score = len(SENIORITY_PRIORITY) - i
                break

        return title_score * 2 + seniority_score

    profiles_sorted = sorted(profiles, key=contact_score, reverse=True)
    best = profiles_sorted[0]

    return {
        "full_name": best.get("full_name") or best.get("name") or "Founder",
        "first_name": (best.get("full_name") or best.get("name") or "Founder").split()[0],
        "title": best.get("title") or "",
        "linkedin_url": best.get("linkedin_profile_url") or best.get("linkedin_url") or "",
        "seniority": best.get("seniority") or "",
    }


def get_contact_posts(client, contact: dict) -> list:
    """
    Fetch recent LinkedIn posts from the contact.
    Used for personalization hooks in emails.

    Returns list of post dicts: {text, date, likes, comments}
    """
    if not contact.get("linkedin_url"):
        return []

    if USE_MOCK:
        from src.crustdata.mock_data import get_mock_posts
        return get_mock_posts(contact["linkedin_url"])
    else:
        logger.info(f"[REAL API] Fetching posts for: {contact.get('full_name')}")
        try:
            return client.get_social_posts(contact["linkedin_url"])
        except Exception as e:
            logger.warning(f"Posts fetch failed: {e}")
            return []