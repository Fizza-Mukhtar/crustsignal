"""
Pipeline Orchestrator — Ties everything together
=================================================
Runs all stages in sequence and saves results to DB.

Stages:
  1. DISCOVER   → get list of ICP companies (mock or real search)
  2. SCORE      → filter by ICP score threshold
  3. ENRICH     → pull headcount, jobs, funding details
  4. CONTACT    → find best decision maker
  5. SIGNALS    → extract personalization hooks
  6. GENERATE   → draft email via Groq
  7. SAVE       → write everything to SQLite
"""

import os
import time
import logging
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel
from rich.table import Table
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)
console = Console()

USE_MOCK = os.getenv("USE_MOCK", "true").lower() == "true"
ICP_THRESHOLD = float(os.getenv("ICP_SCORE_THRESHOLD", "0.60"))
MAX_EMAILS = int(os.getenv("MAX_EMAILS_PER_RUN", "10"))


def run_pipeline(db, client=None):
    """
    Run the full CrustSignal pipeline.
    
    Args:
        db: Database instance (already initialized)
        client: CrustDataClient (ignored in mock mode, required in real mode)
    
    Returns:
        dict with run stats
    """
    run_id = db.start_run()
    stats = {
        "discovered": 0, "qualified": 0,
        "contacts_found": 0, "emails_generated": 0,
        "run_id": run_id,
    }

    console.print(Panel(
        f"[bold cyan]CrustSignal Pipeline[/bold cyan]\n"
        f"Mode: {'🎭 MOCK (no API credits used)' if USE_MOCK else '🔴 LIVE API'}\n"
        f"ICP threshold: {ICP_THRESHOLD} | Max emails: {MAX_EMAILS}",
        title="🚀 Starting Run"
    ))

    try:
        # ── STAGE 1 & 2: Discover + Score ────────────────────────────────
        console.print("\n[bold]Stage 1/4[/bold] Discovering ICP companies...")

        if USE_MOCK:
            from src.crustdata.mock_data import get_mock_company_list
            from src.crustdata.company_search import build_scored_company, score_company

            raw_companies = get_mock_company_list()
            stats["discovered"] = len(raw_companies)

            # Build scored companies from mock data
            all_scored = []
            for raw in raw_companies:
                # Adapt mock data format to scorer format
                adapted = {
                    "name": raw["company_name"],
                    "website": raw["company_website_domain"],
                    "linkedin_company_url": raw.get("linkedin_profile_url", ""),
                    "industry": raw.get("industry", ""),
                    "description": raw.get("description", ""),
                    "employee_count": raw.get("headcount", {}).get("latest_count", 0),
                    "employee_growth_percentages": [
                        {"timespan": "SIX_MONTHS",
                         "percentage": raw.get("headcount", {}).get("six_month_growth_percent", 0)},
                        {"timespan": "YEAR",
                         "percentage": raw.get("headcount", {}).get("one_year_growth_percent", 0)},
                    ],
                    "days_since_last_fundraise": raw.get("funding_and_investment", {}).get("days_since_last_fundraise", 999),
                    "total_funding_raised_usd": raw.get("funding_and_investment", {}).get("total_investment_usd", 0),
                    "last_round_type": raw.get("funding_and_investment", {}).get("last_round_type", ""),
                }
                scored = build_scored_company(adapted)
                all_scored.append(scored)
        else:
            from src.crustdata.company_search import discover_icp_companies
            all_scored = discover_icp_companies(
                client,
                max_pages=4,
                score_threshold=ICP_THRESHOLD,
            )
            stats["discovered"] = len(all_scored)

        # Filter by threshold
        qualified = [c for c in all_scored if c.icp_score >= ICP_THRESHOLD]
        qualified.sort(key=lambda c: c.icp_score, reverse=True)
        stats["qualified"] = len(qualified)

        console.print(f"   Found [green]{stats['discovered']}[/green] companies → [green]{stats['qualified']}[/green] qualified (score ≥ {ICP_THRESHOLD})")

        # ── STAGES 3-6: Enrich, Contact, Signals, Email ──────────────────
        from src.pipeline.enrichment import enrich_company, find_best_contact, get_contact_posts
        from src.pipeline.signal_extract import extract_signals, build_signal_summary, pick_top_hooks
        from src.pipeline.email_gen import generate_email

        processed = 0
        to_process = qualified[:MAX_EMAILS]

        console.print(f"\n[bold]Stages 2-4[/bold] Enriching + generating emails for top {len(to_process)} companies...\n")

        for company in to_process:
            console.print(f"  → [cyan]{company.company_name}[/cyan] (score: {company.icp_score:.2f})")

            # Save lead first
            lead_id = db.save_lead(company)

            # Stage 3: Enrich
            enriched = enrich_company(client, company)

            # Stage 4: Find contact
            contact = find_best_contact(client, company, enriched)
            if not contact:
                console.print(f"     [yellow]⚠ No contact found, skipping[/yellow]")
                continue

            console.print(f"     Contact: {contact['full_name']} ({contact['title']})")

            # Save contact
            contact_id = db.save_contact(
                lead_id=lead_id,
                full_name=contact["full_name"],
                title=contact["title"],
                linkedin_url=contact.get("linkedin_url", ""),
                seniority=contact.get("seniority", ""),
            )
            stats["contacts_found"] += 1

            # Stage 5: Get posts + extract signals
            posts = get_contact_posts(client, contact)
            signals = extract_signals(company, enriched, contact, posts)

            # Clear old signals for this lead (handles re-runs cleanly)
            db._get_conn().execute("DELETE FROM signals WHERE lead_id = ?", (lead_id,))
            db._get_conn().commit()

            # Save fresh signals
            for sig in signals:
                db.save_signal(
                    lead_id=lead_id,
                    signal_type=sig["type"],
                    signal_value=sig["value"],
                    hook_strength=sig["hook_strength"],
                    raw_data=sig.get("raw", {}),
                )

            top_hooks = pick_top_hooks(signals, n=3)
            signal_summary = build_signal_summary(company, enriched, contact, top_hooks)

            console.print(f"     Signals: {', '.join(s['type'] for s in top_hooks)}")

            # Stage 6: Generate email
            email = generate_email(company, contact, signal_summary)

            if email["success"]:
                console.print(f"     Email: [green]✅[/green] \"{email['subject']}\"")
            else:
                console.print(f"     Email: [yellow]⚠ fallback used[/yellow]")

            # Save draft
            db.save_draft(
                lead_id=lead_id,
                contact_id=contact_id,
                subject_line=email["subject"],
                email_body=email["body"],
                personalization_hooks=[s["value"] for s in top_hooks],
                generation_model=email["model"],
            )

            # Update lead status
            db.update_lead_status(lead_id, "drafted")
            stats["emails_generated"] += 1
            processed += 1

        # ── Finish ────────────────────────────────────────────────────────
        db.finish_run(
            run_id=run_id,
            discovered=stats["discovered"],
            qualified=stats["qualified"],
            contacts=stats["contacts_found"],
            emails=stats["emails_generated"],
        )

        _print_summary(stats, db)
        return stats

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        db.finish_run(run_id, 0, 0, 0, 0, status="failed", error=str(e))
        console.print(f"\n[red]❌ Pipeline failed: {e}[/red]")
        raise


def _print_summary(stats: dict, db):
    """Print a nice summary table at the end."""
    db_stats = db.get_stats()

    table = Table(title="Pipeline Run Complete ✅", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green", justify="right")

    table.add_row("Companies discovered", str(stats["discovered"]))
    table.add_row("Companies qualified", str(stats["qualified"]))
    table.add_row("Contacts found", str(stats["contacts_found"]))
    table.add_row("Email drafts generated", str(stats["emails_generated"]))
    table.add_row("Total leads in DB", str(db_stats["total_leads"]))
    table.add_row("Total drafts in DB", str(db_stats["total_drafts"]))

    console.print("\n")
    console.print(table)
    console.print(Panel(
        "[bold green]Run complete.[/bold green]\n"
        "Next step: python scripts/review_drafts.py — review and approve emails",
        title="✅ Done"
    ))