"""
Demo Pipeline — Real CrustData API
=====================================
Production-ready runner that uses real API efficiently.

Credit cost: ~8 credits (1 per company enrichment)
Strategy   : Enrich 8 handpicked ICP companies directly.
             Skips company search (not on free tier).
             Gets decision makers from enrichment response.
             Uses Groq for emails (free, unlimited).

Usage:
    python scripts/demo_run.py

Make sure .env has:
    CRUSTDATA_API_KEY = your real key
    GROQ_API_KEY      = your groq key
    USE_MOCK          = false   (set automatically by this script)
"""

import sys, os, time, webbrowser, threading
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force real API mode — override whatever is in .env
os.environ["USE_MOCK"] = "false"

from dotenv import load_dotenv
load_dotenv()

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import track

console = Console()

# ── 8 Handpicked ICP Companies ─────────────────────────────────────────────
# These are real companies in CrustData's ICP:
# AI SDRs, recruiting platforms, sales intelligence, GTM tools
DEMO_COMPANIES = [
    {"domain": "artisan.co",    "name": "Artisan AI",
     "industry": "Artificial Intelligence",
     "description": "AI-powered SDR platform for outbound sales automation"},
    {"domain": "warmly.ai",     "name": "Warmly",
     "industry": "Sales Intelligence",
     "description": "Signal-based sales platform for real-time outbound"},
    {"domain": "keyplay.io",    "name": "Keyplay",
     "industry": "Computer Software",
     "description": "AI account scoring and ICP fit platform for sales teams"},
    {"domain": "default.com",   "name": "Default",
     "industry": "Sales Automation",
     "description": "Inbound lead orchestration and qualification platform"},
    {"domain": "topo.io",       "name": "Topo",
     "industry": "Artificial Intelligence",
     "description": "AI-powered outbound platform for personalized sales automation"},
    {"domain": "usergems.com",  "name": "UserGems",
     "industry": "Sales Intelligence",
     "description": "Job change tracking platform for sales intelligence"},
    {"domain": "scalis.ai",     "name": "Scalis",
     "industry": "Human Resources",
     "description": "AI-native recruiting platform for candidate sourcing"},
    {"domain": "pocus.com",     "name": "Pocus",
     "industry": "Computer Software",
     "description": "Product-led sales platform using product usage signals"},
]

# Seniority priority for picking best contact
TITLE_PRIORITY = [
    "cto", "chief technology", "co-founder", "cofounder",
    "chief executive", "ceo", "founder", "president",
    "vp engineering", "head of engineering", "head of data",
    "vp data", "director of engineering",
]


def pick_best_contact(profiles: list) -> dict:
    """Pick the best decision maker from a list of profiles."""
    if not profiles:
        return {}

    def score(p):
        title = (p.get("title") or "").lower()
        return next(
            (len(TITLE_PRIORITY) - i for i, kw in enumerate(TITLE_PRIORITY) if kw in title),
            0
        )

    best = sorted(profiles, key=score, reverse=True)[0]
    name = best.get("full_name") or best.get("name") or "Founder"
    return {
        "full_name":   name,
        "first_name":  name.split()[0],
        "title":       best.get("title") or "",
        "linkedin_url": best.get("linkedin_profile_url") or best.get("linkedin_url") or "",
        "seniority":   best.get("seniority") or "",
    }


def extract_enrichment_dict(raw: dict) -> dict:
    """Convert raw CrustData enrichment response to standard enrichment dict."""
    hc = raw.get("headcount") or {}
    fi = raw.get("funding_and_investment") or {}
    wt = raw.get("web_traffic") or {}

    # headcount can be int or dict depending on API response
    if isinstance(hc, dict):
        headcount = hc.get("latest_count") or hc.get("count") or 0
        growth_6m = hc.get("six_month_growth_percent") or 0
        growth_1y = hc.get("one_year_growth_percent") or 0
    else:
        headcount = int(hc) if hc else 0
        growth_6m = 0
        growth_1y = 0

    # Get job openings
    jobs = raw.get("job_openings") or []
    if isinstance(jobs, dict):
        jobs = jobs.get("job_openings") or []

    return {
        "headcount":        headcount,
        "growth_6m":        float(growth_6m),
        "growth_1y":        float(growth_1y),
        "funding_amount":   fi.get("last_round_investment_usd") or 0,
        "funding_round":    fi.get("last_round_type") or "",
        "days_funded":      fi.get("days_since_last_fundraise") or 999,
        "job_openings":     jobs,
        "monthly_visitors": wt.get("monthly_visitors") or 0,
        "visitor_growth":   wt.get("mom_growth_percent") or 0,
    }


def run_demo():
    console.print(Panel(
        "[bold cyan]CrustSignal — LIVE Demo Run[/bold cyan]\n"
        f"Mode: [red]🔴 REAL API[/red] — will use ~{len(DEMO_COMPANIES)} credits\n"
        f"Companies: {len(DEMO_COMPANIES)} handpicked ICP targets",
        title="🚀 Starting Live Run"
    ))

    # Confirm before spending credits
    console.print(
        f"\n[yellow]⚠  This will use ~{len(DEMO_COMPANIES)} CrustData credits.[/yellow]"
        "\n   Press [bold]Enter[/bold] to continue, or [bold]Ctrl+C[/bold] to cancel...",
        end=""
    )
    try:
        input()
    except KeyboardInterrupt:
        console.print("\n[dim]Cancelled.[/dim]")
        return

    from src.crustdata.client import CrustDataClient
    from src.crustdata.company_search import build_scored_company
    from src.pipeline.signal_extract import (
        extract_signals, build_signal_summary, pick_top_hooks
    )
    from src.pipeline.email_gen import generate_email
    from src.storage.db import Database

    # Init
    client = CrustDataClient()
    db = Database()
    db.init()

    # Clear old data for a clean demo run
    console.print("\n[dim]Clearing previous run data...[/dim]")
    conn = db._get_conn()
    conn.execute("DELETE FROM outreach_drafts")
    conn.execute("DELETE FROM signals")
    conn.execute("DELETE FROM contacts")
    conn.execute("DELETE FROM leads")
    conn.commit()
    console.print("[dim]Done. Starting fresh.[/dim]\n")

    run_id = db.start_run()
    stats = {"discovered": 0, "qualified": 0, "contacts": 0, "emails": 0}

    for company_info in DEMO_COMPANIES:
        domain = company_info["domain"]
        name   = company_info["name"]

        console.print(f"  → [cyan]{name}[/cyan] ({domain})")

        try:
            # ── Step 1: Enrich company (1 credit) ───────────────────────
            console.print(f"     [dim]Calling Company Enrichment API...[/dim]")
            raw = client.enrich_company(
                domain=domain,
                fields=(
                    "company_name,headcount,funding_and_investment,"
                    "web_traffic,decision_makers,job_openings,"
                    "linkedin_profile_url"
                ),
            )

            if not raw:
                console.print(f"     [yellow]⚠ No data returned, skipping[/yellow]")
                continue

            stats["discovered"] += 1

            # ── Step 2: Build ScoredCompany ──────────────────────────────
            hc = raw.get("headcount") or {}

            # headcount can be int, dict, or nested — try all formats
            if isinstance(hc, dict):
                headcount_count = (
                    hc.get("latest_count")
                    or hc.get("count")
                    or hc.get("employee_count")
                    or hc.get("headcount")
                    or 0
                )
                g6 = (
                    hc.get("six_month_growth_percent")
                    or hc.get("six_month_growth")
                    or hc.get("growth_6m")
                    or 0
                )
                g1 = (
                    hc.get("one_year_growth_percent")
                    or hc.get("annual_growth")
                    or hc.get("growth_1y")
                    or 0
                )
            else:
                headcount_count = int(hc) if hc else 0
                g6 = 0
                g1 = 0

            # Also check top-level fields (some API versions return flat)
            if not headcount_count:
                headcount_count = (
                    raw.get("employee_count")
                    or raw.get("headcount_count")
                    or raw.get("total_employee_count")
                    or 0
                )

            fi = raw.get("funding_and_investment") or {}
            growth_data = [
                {"timespan": "SIX_MONTHS", "percentage": g6},
                {"timespan": "YEAR",       "percentage": g1},
            ]

            # Use hardcoded industry + description (not in enrichment API)
            adapted = {
                "name":       raw.get("company_name") or name,
                "website":    domain,
                "linkedin_company_url": raw.get("linkedin_profile_url") or "",
                "industry":   company_info["industry"],
                "description": company_info["description"],
                "specialties": company_info["description"],
                "employee_count": headcount_count,
                "employee_growth_percentages": growth_data,
                "days_since_last_fundraise": (
                    fi.get("days_since_last_fundraise")
                    or fi.get("days_since_funding")
                    or 999
                ),
                "total_funding_raised_usd": (
                    fi.get("total_investment_usd")
                    or fi.get("total_funding_usd")
                    or fi.get("last_round_investment_usd")
                    or 0
                ),
                "last_round_type": fi.get("last_round_type") or "",
            }

            # Debug — print raw keys so we can see API response structure
            console.print(
                f"     [dim]Raw keys: {list(raw.keys())}[/dim]"
            )
            if hc:
                console.print(
                    f"     [dim]Headcount raw: {hc}[/dim]"
                )
            if fi:
                console.print(
                    f"     [dim]Funding raw: {fi}[/dim]"
                )

            scored = build_scored_company(adapted)
            stats["qualified"] += 1
            console.print(
                f"     ICP Score: [green]{scored.icp_score:.2f}[/green]  "
                f"Headcount: {scored.headcount}"
            )

            # ── Step 3: Find best contact (from enrichment — no extra credits) ──
            profiles  = raw.get("decision_makers", {}).get("profiles", [])
            contact   = pick_best_contact(profiles)
            if not contact:
                contact = {"full_name": "Founder", "first_name": "there",
                           "title": "", "linkedin_url": ""}

            console.print(
                f"     Contact: [bold]{contact['full_name']}[/bold] "
                f"({contact['title']})"
            )

            # ── Step 4: Extract signals ──────────────────────────────────
            enriched = extract_enrichment_dict(raw)
            signals  = extract_signals(scored, enriched, contact, posts=[])

            console.print(
                f"     Signals: "
                + ", ".join(f"[dim]{s['type']}[/dim]" for s in signals[:3])
            )

            # ── Step 5: Save to DB ───────────────────────────────────────
            lead_id = db.save_lead(scored)
            db._get_conn().execute(
                "DELETE FROM signals WHERE lead_id = ?", (lead_id,)
            )
            db._get_conn().commit()

            for sig in signals:
                db.save_signal(
                    lead_id=lead_id,
                    signal_type=sig["type"],
                    signal_value=sig["value"],
                    hook_strength=sig["hook_strength"],
                    raw_data=sig.get("raw", {}),
                )

            contact_id = db.save_contact(
                lead_id=lead_id,
                full_name=contact["full_name"],
                title=contact["title"],
                linkedin_url=contact.get("linkedin_url", ""),
            )
            stats["contacts"] += 1

            # ── Step 6: Generate email (Groq — FREE) ─────────────────────
            top_hooks      = pick_top_hooks(signals, n=3)
            signal_summary = build_signal_summary(scored, enriched, contact, top_hooks)
            email          = generate_email(scored, contact, signal_summary)

            db.save_draft(
                lead_id=lead_id,
                contact_id=contact_id,
                subject_line=email["subject"],
                email_body=email["body"],
                personalization_hooks=[s["value"] for s in top_hooks],
                generation_model=email["model"],
            )
            db.update_lead_status(lead_id, "drafted")
            stats["emails"] += 1

            status = "✅" if email["success"] else "⚠ fallback"
            console.print(
                f"     Email: {status} [bold]\"{email['subject']}\"[/bold]\n"
            )

        except Exception as e:
            console.print(f"     [red]Error: {e}[/red]\n")
            continue

    # ── Finish ────────────────────────────────────────────────────────────
    db.finish_run(
        run_id, stats["discovered"], stats["qualified"],
        stats["contacts"], stats["emails"]
    )

    table = Table(title="Live Run Complete", show_header=True)
    table.add_column("Metric",  style="cyan")
    table.add_column("Value",   style="green", justify="right")
    table.add_row("Companies enriched",    str(stats["discovered"]))
    table.add_row("Contacts found",        str(stats["contacts"]))
    table.add_row("Email drafts generated",str(stats["emails"]))
    table.add_row("CrustData credits used",f"~{stats['discovered']}")

    console.print("\n")
    console.print(table)
    console.print(Panel(
        "[bold green]Done![/bold green] Now open the review UI:\n"
        "python scripts/start_server.py",
        title="✅ Next Step"
    ))
    db.close()


if __name__ == "__main__":
    run_demo()