"""
Signal Extraction — Stage 3
=============================
Takes enriched company data and extracts ranked personalization signals.

A "signal" is a specific, concrete fact that can be used as an email hook.
Each signal has a hook_strength (0.0-1.0) — how good is it as an opener?

Signal types and their hook strength:
  funding        → 0.85-0.95  (recent funding = strong hook)
  linkedin_post  → 0.80-0.90  (mentioned a pain point we solve = perfect hook)
  job_posting    → 0.70-0.80  (hiring signals = they're building)
  headcount_growth → 0.60-0.70 (growing = scaling = need data)
  web_traffic    → 0.50-0.60  (traffic growth = traction)
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def extract_signals(company, enriched: dict, contact: dict, posts: list) -> list:
    """
    Extract all available signals for a company.
    
    Returns list of signal dicts sorted by hook_strength (strongest first).
    Each signal has:
      - type: str
      - value: str (human-readable, ready to use in email)
      - hook_strength: float
      - raw: dict (full data for reference)
    """
    signals = []

    # ── 1. Funding signal ─────────────────────────────────────────────────
    days_funded = enriched.get("days_funded") or company.days_since_last_funding or 999
    funding_amount = enriched.get("funding_amount") or company.total_funding_usd or 0
    round_type = enriched.get("funding_round") or company.last_round_type or ""

    if days_funded < 90 and funding_amount > 0:
        amount_str = _format_money(funding_amount)
        recency_str = _days_to_words(days_funded)

        hook = f"raised {amount_str} {round_type} {recency_str}"
        strength = _funding_strength(days_funded)

        signals.append({
            "type": "funding",
            "value": hook,
            "hook_strength": strength,
            "raw": {
                "amount_usd": funding_amount,
                "round_type": round_type,
                "days_ago": days_funded,
            },
        })

    # ── 2. LinkedIn post signal ───────────────────────────────────────────
    PAIN_KEYWORDS = [
        "data quality", "stale data", "bounce rate", "apollo", "zoominfo",
        "enrichment", "real-time", "intent data", "signal", "data pipeline",
        "data engineer", "accurate data", "contact data", "wrong email",
        "outdated", "bad data", "data problem", "data infrastructure",
    ]

    for post in posts[:3]:
        text = (post.get("text") or "").lower()
        matched_keywords = [kw for kw in PAIN_KEYWORDS if kw in text]

        if matched_keywords:
            # This post mentions something directly relevant to CrustData
            strength = min(0.92, 0.75 + len(matched_keywords) * 0.05)
            short_text = post.get("text", "")[:120] + "..."
            signals.append({
                "type": "linkedin_post",
                "value": f"posted about {matched_keywords[0]} on LinkedIn",
                "hook_strength": strength,
                "raw": {
                    "post_text": post.get("text", ""),
                    "post_date": post.get("date", ""),
                    "keywords_matched": matched_keywords,
                    "preview": short_text,
                },
            })
            break  # One post signal is enough

    # ── 3. Job posting signals ────────────────────────────────────────────
    DATA_JOB_KEYWORDS = [
        "data engineer", "data infrastructure", "data platform", "ml engineer",
        "machine learning", "ai engineer", "data scientist", "backend engineer",
        "data pipeline", "head of data",
    ]

    relevant_jobs = []
    for job in (enriched.get("job_openings") or []):
        title_lower = (job.get("title") or "").lower()
        if any(kw in title_lower for kw in DATA_JOB_KEYWORDS):
            relevant_jobs.append(job.get("title"))

    if relevant_jobs:
        if len(relevant_jobs) == 1:
            job_str = f"hiring a {relevant_jobs[0]}"
        else:
            job_str = f"hiring {len(relevant_jobs)} data/engineering roles (incl. {relevant_jobs[0]})"

        signals.append({
            "type": "job_posting",
            "value": job_str,
            "hook_strength": 0.72,
            "raw": {"relevant_jobs": relevant_jobs},
        })

    # ── 4. Headcount growth signal ────────────────────────────────────────
    growth = enriched.get("growth_6m") or company.headcount_growth_6m_pct or 0
    headcount = enriched.get("headcount") or company.headcount or 0

    if growth >= 15:
        signals.append({
            "type": "headcount_growth",
            "value": f"grown {growth:.0f}% in 6 months (now {headcount} people)",
            "hook_strength": min(0.70, 0.45 + growth * 0.01),
            "raw": {"growth_pct": growth, "headcount": headcount},
        })

    # ── 5. Web traffic signal ─────────────────────────────────────────────
    visitor_growth = enriched.get("visitor_growth") or 0
    visitors = enriched.get("monthly_visitors") or 0

    if visitor_growth >= 20 and visitors > 0:
        signals.append({
            "type": "web_traffic",
            "value": f"web traffic up {visitor_growth:.0f}% MoM ({_format_number(visitors)}/mo)",
            "hook_strength": 0.55,
            "raw": {"growth_pct": visitor_growth, "monthly_visitors": visitors},
        })

    # Sort by hook strength (best hooks first)
    signals.sort(key=lambda s: s["hook_strength"], reverse=True)

    logger.info(
        f"Extracted {len(signals)} signals for {company.company_name}: "
        + ", ".join(s["type"] for s in signals)
    )

    return signals


def pick_top_hooks(signals: list, n: int = 3) -> list:
    """Return the top N signals to use in the email."""
    return signals[:n]


def build_signal_summary(company, enriched: dict, contact: dict, signals: list) -> str:
    """
    Build a human-readable summary of signals for the email generation prompt.
    This is what gets passed to Groq.
    """
    lines = [
        f"Company: {company.company_name}",
        f"Domain: {company.company_domain}",
        f"Industry: {company.industry}",
        f"Headcount: {enriched.get('headcount', company.headcount)} employees",
        f"Contact: {contact.get('full_name', 'Founder')}, {contact.get('title', '')}",
        "",
        "SIGNALS (use these as email hooks, strongest first):",
    ]

    for i, sig in enumerate(signals[:3], 1):
        lines.append(f"  {i}. [{sig['type'].upper()}] They {sig['value']}")
        if sig["type"] == "linkedin_post" and sig.get("raw", {}).get("post_text"):
            preview = sig["raw"]["post_text"][:150]
            lines.append(f"     Their post: \"{preview}...\"")

    return "\n".join(lines)


# ── Helpers ───────────────────────────────────────────────────────────────

def _format_money(amount_usd: int) -> str:
    if amount_usd >= 1_000_000:
        return f"${amount_usd / 1_000_000:.1f}M"
    if amount_usd >= 1_000:
        return f"${amount_usd / 1_000:.0f}K"
    return f"${amount_usd}"

def _format_number(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return str(n)

def _days_to_words(days: int) -> str:
    if days <= 7:
        return f"{days} days ago"
    if days <= 14:
        return "last week"
    if days <= 21:
        return "2 weeks ago"
    if days <= 35:
        return "3 weeks ago"
    if days <= 45:
        return "last month"
    weeks = days // 7
    return f"{weeks} weeks ago"

def _funding_strength(days: int) -> float:
    if days <= 7:   return 0.95
    if days <= 14:  return 0.92
    if days <= 21:  return 0.89
    if days <= 30:  return 0.86
    if days <= 45:  return 0.82
    if days <= 60:  return 0.77
    return 0.68