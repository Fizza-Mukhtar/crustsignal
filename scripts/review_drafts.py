"""
Review Drafts — See all generated emails in the terminal.
Usage: python scripts/review_drafts.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from src.storage.db import Database

console = Console()
db = Database()
db.init()

leads = db.get_leads(limit=50)
if not leads:
    console.print("[yellow]No leads found. Run: python run_pipeline.py first.[/yellow]")
    sys.exit(0)

console.print(f"\n[bold]Found {len(leads)} leads in database[/bold]\n")

for lead in leads:
    drafts = db.get_drafts(lead_id=lead["id"])
    signals = db.get_signals(lead["id"])
    contacts = db.get_contacts(lead["id"])

    contact_name = contacts[0]["full_name"] if contacts else "Unknown"
    contact_title = contacts[0]["title"] if contacts else ""

    console.print(Panel(
        f"[bold cyan]{lead['company_name']}[/bold cyan] — {lead['company_domain']}\n"
        f"ICP Score: [green]{lead['icp_score']:.2f}[/green]  |  "
        f"Contact: {contact_name} ({contact_title})\n"
        f"Signals: {', '.join(s['signal_value'][:40] for s in signals[:3])}",
        title=f"🏢 Lead",
        border_style="blue"
    ))

    for draft in drafts:
        status = "[green]✅ APPROVED[/green]" if draft["approved"] else "[yellow]⏳ PENDING[/yellow]"
        console.print(Panel(
            f"[bold]Subject:[/bold] {draft['subject_line']}\n\n"
            f"{draft['email_body']}\n\n"
            f"Status: {status} | Model: {draft['generation_model']}",
            title="📧 Draft Email",
            border_style="green" if draft["approved"] else "yellow"
        ))

    console.print()

stats = db.get_stats()
console.print(f"[dim]Total: {stats['total_leads']} leads | {stats['total_drafts']} drafts | "
              f"{stats['approved_drafts']} approved[/dim]\n")
db.close()