"""
Day 1 Test Script
=================
Run this FIRST to verify your CrustData API key works.

Usage:
    python scripts/test_connection.py

What it tests:
    1. Auth — does your API key work?
    2. Company Enrichment — can we get data for a known company?
    3. Company Search — can we query with filters?
    4. People Search — can we find decision makers?
    5. Social Posts — can we fetch LinkedIn posts?
    6. ICP Scoring — does our scoring algorithm work?
    7. Database — can we write and read from SQLite?

Each test prints PASS / FAIL + what it found.
"""

import sys
import json
import logging
import os
from pathlib import Path

# Add project root to Python path so imports work
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint
from dotenv import load_dotenv

load_dotenv()

# Configure logging (show warnings and errors only during tests)
logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s | %(name)s | %(message)s"
)

console = Console()

# ─── Test Runner ─────────────────────────────────────────────────────────────

results = []

def test(name: str):
    """Decorator to run a named test and track results."""
    def decorator(fn):
        def wrapper():
            console.print(f"\n[bold]Testing:[/bold] {name}...", end=" ")
            try:
                info = fn()
                results.append((name, "✅ PASS", info or ""))
                console.print("[green]✅ PASS[/green]")
                if info:
                    console.print(f"   [dim]{info}[/dim]")
            except Exception as e:
                results.append((name, "❌ FAIL", str(e)))
                console.print("[red]❌ FAIL[/red]")
                console.print(f"   [red]{e}[/red]")
        return wrapper
    return decorator


# ─── Individual Tests ─────────────────────────────────────────────────────────

@test("Environment variables")
def test_env():
    crustdata_key = os.getenv("CRUSTDATA_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")
    missing = []
    if not crustdata_key:
        missing.append("CRUSTDATA_API_KEY")
    if not groq_key:
        missing.append("GROQ_API_KEY (optional for now)")

    if "CRUSTDATA_API_KEY" in missing:
        raise ValueError(
            "CRUSTDATA_API_KEY not set!\n"
            "   Copy .env.example → .env and add your key.\n"
            "   Get a key at: crustdata.com → sign up → API settings"
        )
    groq_status = "present" if groq_key else "missing (add later)"
    return f"CRUSTDATA_API_KEY: {'*' * 8 + crustdata_key[-4:]} | GROQ: {groq_status}"


@test("CrustData client init")
def test_client_init():
    from src.crustdata.client import CrustDataClient
    client = CrustDataClient()
    return f"Client created OK"


@test("API auth + Company Enrichment (HubSpot)")
def test_enrich_hubspot():
    from src.crustdata.client import CrustDataClient
    client = CrustDataClient()

    # HubSpot is a well-known company definitely in Crustdata's DB
    data = client.enrich_company("hubspot.com", fields="company_name,headcount")

    if not data:
        raise ValueError("Empty response — company not found or API limit hit")

    name = data.get("company_name", "?")
    headcount = data.get("headcount") or {}
    if isinstance(headcount, dict):
        count = headcount.get("latest_count") or headcount.get("headcount") or "?"
    else:
        count = headcount or "?"

    return f"Found: {name}, headcount: {count}"


@test("Company Enrichment (small startup — Crustdata itself)")
def test_enrich_crustdata():
    from src.crustdata.client import CrustDataClient
    client = CrustDataClient()

    data = client.enrich_company("crustdata.com", fields="company_name,headcount,linkedin_profile_url")

    if not data:
        # This might fail if crustdata.com isn't in their own DB — that's ok
        return "Not in DB (this is acceptable)"

    name = data.get("company_name", "?")
    return f"Found: {name}"


@test("Company Search API (filter-based)")
def test_company_search():
    from src.crustdata.client import CrustDataClient
    client = CrustDataClient()

    filters = [
        {
            "filter_type": "COMPANY_HEADCOUNT",
            "type": "in",
            "value": ["51-200"],
        },
        {
            "filter_type": "INDUSTRY",
            "type": "in",
            "value": ["Computer Software", "Internet"],
        },
    ]

    result = client.search_companies(filters=filters, page=1)
    companies = result.get("companies") or []
    total = result.get("total_display_count") or 0

    if not companies and not total:
        raise ValueError(
            "Search returned nothing. This endpoint may require a paid plan.\n"
            "   Try the Screener endpoint instead (see test below)."
        )

    return f"Found {len(companies)} companies on page 1 (total: {total})"


@test("Company Screener (older endpoint — works with free tier)")
def test_company_screener():
    from src.crustdata.client import CrustDataClient
    client = CrustDataClient()

    conditions = [
        {"column": "headcount", "type": "=>", "value": 50, "allow_null": False},
        {"column": "headcount", "type": "<=", "value": 200, "allow_null": False},
        {"column": "days_since_last_fundraise", "type": "<=", "value": 90, "allow_null": False},
    ]

    result = client.screen_companies(conditions=conditions, count=10)
    records = result.get("records") or []
    count = result.get("count") or len(records)

    if not records and not count:
        raise ValueError("Screener returned nothing. This may require a paid plan too.")

    first = records[0].get("company_name", "?") if records else "?"
    return f"Found {len(records)} companies (first: {first})"


@test("People Search API")
def test_people_search():
    from src.crustdata.client import CrustDataClient
    client = CrustDataClient()

    filters = [
        {
            "filter_type": "CURRENT_TITLE",
            "type": "in",
            "value": ["Chief Technology Officer"],
        },
        {
            "filter_type": "COMPANY_HEADCOUNT",
            "type": "in",
            "value": ["51-200"],
        },
    ]

    result = client.search_people(filters=filters, page=1)
    profiles = result.get("profiles") or []
    total = result.get("total_display_count") or 0

    if not profiles and not total:
        raise ValueError("People search returned nothing. May require paid plan.")

    name = profiles[0].get("name", "?") if profiles else "?"
    return f"Found {len(profiles)} profiles (first: {name})"


@test("People Enrichment (LinkedIn profile)")
def test_people_enrich():
    from src.crustdata.client import CrustDataClient
    client = CrustDataClient()

    # Abhilash Chowdhary — Crustdata's CEO (should be in their DB)
    profile = client.enrich_person("https://www.linkedin.com/in/abhilash-chowdhary")

    if not profile:
        return "Profile not found (acceptable — may need time to crawl)"

    name = profile.get("name") or profile.get("full_name") or "?"
    return f"Found: {name}"


@test("ICP Scoring algorithm")
def test_icp_scoring():
    from src.crustdata.company_search import score_company, build_scored_company

    # Simulate a perfect ICP company
    fake_company = {
        "name": "SalesAI Inc",
        "website": "salesai.io",
        "industry": "Computer Software",
        "description": "AI-powered SDR platform for sales automation and outbound",
        "employee_count": 75,
        "employee_growth_percentages": [
            {"timespan": "SIX_MONTHS", "percentage": 35},
            {"timespan": "YEAR", "percentage": 55},
        ],
        "days_since_last_fundraise": 18,
        "total_funding_raised_usd": 4_200_000,
        "specialties": ["AI", "sales automation", "SDR", "outbound"],
    }

    score, breakdown = score_company(fake_company)
    scored = build_scored_company(fake_company)

    if score < 0.5:
        raise ValueError(f"Perfect ICP company scored only {score:.2f} — scoring bug!")

    details = " | ".join(
        f"{k}: {v['points']}/{v['max']}"
        for k, v in breakdown.items()
    )
    return f"Score: {score:.2f} ({score*100:.0f}/100) — {details}"


@test("Database init + write + read")
def test_database():
    import os
    from src.storage.db import Database
    from src.crustdata.company_search import build_scored_company

    test_db_path = "/tmp/crustsignal_test.db"

    # Clean up from previous test runs
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

    db = Database(db_path=test_db_path)
    db.init()

    # Save a fake lead
    fake = build_scored_company({
        "name": "TestCo",
        "website": "testco.io",
        "industry": "Computer Software",
        "description": "AI sales tool for testing",
        "employee_count": 50,
        "employee_growth_percentages": [{"timespan": "SIX_MONTHS", "percentage": 20}],
        "days_since_last_fundraise": 30,
        "total_funding_raised_usd": 1_000_000,
    })

    lead_id = db.save_lead(fake)
    if not lead_id:
        raise ValueError("save_lead returned empty ID")

    # Read it back
    leads = db.get_leads()
    if not leads:
        raise ValueError("get_leads returned empty after saving")

    found = leads[0]
    stats = db.get_stats()
    db.close()
    os.remove(test_db_path)

    return f"Lead saved: {found['company_name']} (score={found['icp_score']:.2f}) | DB stats: {stats}"


# ─── Summary ─────────────────────────────────────────────────────────────────

def print_summary():
    console.print("\n")
    table = Table(title="Day 1 Test Results", show_header=True)
    table.add_column("Test", style="cyan", no_wrap=True)
    table.add_column("Result", no_wrap=True)
    table.add_column("Details", style="dim")

    passed = 0
    failed = 0
    for name, result, info in results:
        if "PASS" in result:
            table.add_row(name, "[green]✅ PASS[/green]", info[:80])
            passed += 1
        else:
            table.add_row(name, "[red]❌ FAIL[/red]", info[:80])
            failed += 1

    console.print(table)

    if failed == 0:
        console.print(Panel(
            "[bold green]🎉 All tests passed! You're ready for Day 2.[/bold green]\n\n"
            "Next: python scripts/test_connection.py → all green\n"
            "Then move to Day 2 (discovery pipeline)",
            title="Status"
        ))
    else:
        console.print(Panel(
            f"[bold red]{failed} test(s) failed.[/bold red]\n\n"
            "If Company Search / People Search fail:\n"
            "  → Your free tier may only include enrichment endpoints.\n"
            "  → That's OK for now. We'll use enrichment in the MVP.\n"
            "  → Email the founders for a trial key (great reason to reach out!).\n\n"
            "If auth fails:\n"
            "  → Check .env has CRUSTDATA_API_KEY set correctly.\n"
            "  → Do NOT include 'Token' in the key itself — just the key string.",
            title="Troubleshooting"
        ))


# ─── Run all tests ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    console.print(Panel(
        "[bold]CrustSignal — Day 1 Connection Tests[/bold]\n"
        "Testing all CrustData API endpoints and local infrastructure.",
        title="🧪 Test Suite"
    ))

    test_env()
    test_client_init()
    test_enrich_hubspot()
    test_enrich_crustdata()
    test_company_search()
    test_company_screener()
    test_people_search()
    test_people_enrich()
    test_icp_scoring()
    test_database()

    print_summary()