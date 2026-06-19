"""
Database Layer
==============
All SQLite read/write operations for CrustSignal.

Usage:
    from src.storage.db import Database
    db = Database()
    db.init()
    db.save_lead(scored_company)
"""

import json
import sqlite3
import logging
import os
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DB_PATH = os.getenv("DATABASE_PATH", "crustsignal.db")
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def _now() -> str:
    """Return current UTC time as ISO string."""
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    """Generate a new UUID string."""
    return str(uuid4())


class Database:
    """
    SQLite database wrapper.

    All methods return plain Python dicts/lists for easy use elsewhere.
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row  # rows act like dicts
            self._conn.execute("PRAGMA journal_mode=WAL")  # better concurrency
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def init(self):
        """
        Create all tables if they don't exist.
        Safe to call multiple times (uses CREATE IF NOT EXISTS).
        """
        schema = SCHEMA_PATH.read_text()
        conn = self._get_conn()
        conn.executescript(schema)
        conn.commit()
        logger.info(f"✅ Database initialized at: {self.db_path}")

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    # ─── Leads ──────────────────────────────────────────────────────────────

    def save_lead(self, scored_company) -> str:
        """
        Insert or update a lead from a ScoredCompany object.
        If a company with the same domain already exists, skip it.

        Returns:
            The lead ID (new or existing).
        """
        from src.crustdata.company_search import ScoredCompany

        conn = self._get_conn()

        # Check if domain already exists
        if scored_company.company_domain:
            existing = conn.execute(
                "SELECT id FROM leads WHERE company_domain = ?",
                (scored_company.company_domain,),
            ).fetchone()
            if existing:
                logger.debug(f"Lead already exists: {scored_company.company_domain}")
                return existing["id"]

        lead_id = _new_id()
        conn.execute(
            """
            INSERT INTO leads (
                id, company_name, company_domain, linkedin_url,
                industry, headcount, headcount_growth_6m_pct, headcount_growth_1y_pct,
                total_funding_usd, last_round_type, days_since_last_funding,
                location, description, icp_score, score_breakdown,
                status, discovered_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lead_id,
                scored_company.company_name,
                scored_company.company_domain,
                scored_company.linkedin_url,
                scored_company.industry,
                scored_company.headcount,
                scored_company.headcount_growth_6m_pct,
                scored_company.headcount_growth_1y_pct,
                scored_company.total_funding_usd,
                scored_company.last_round_type,
                scored_company.days_since_last_funding,
                scored_company.location,
                scored_company.description,
                scored_company.icp_score,
                json.dumps(scored_company.score_breakdown),
                "new",
                _now(),
                _now(),
            ),
        )
        conn.commit()
        logger.debug(f"Saved lead: {scored_company.company_name} (score={scored_company.icp_score:.2f})")
        return lead_id

    def get_leads(
        self,
        status: Optional[str] = None,
        min_score: float = 0.0,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """
        Get leads, optionally filtered by status and score.

        Returns:
            List of lead dicts, sorted by icp_score descending.
        """
        conn = self._get_conn()
        query = "SELECT * FROM leads WHERE icp_score >= ?"
        params: list = [min_score]

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY icp_score DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def get_lead(self, lead_id: str) -> Optional[dict]:
        """Get a single lead by ID."""
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
        return dict(row) if row else None

    def update_lead_status(self, lead_id: str, status: str):
        """Update the status of a lead."""
        conn = self._get_conn()
        conn.execute(
            "UPDATE leads SET status = ?, updated_at = ? WHERE id = ?",
            (status, _now(), lead_id),
        )
        conn.commit()

    def lead_count(self, status: Optional[str] = None) -> int:
        """Count leads, optionally filtered by status."""
        conn = self._get_conn()
        if status:
            return conn.execute(
                "SELECT COUNT(*) FROM leads WHERE status = ?", (status,)
            ).fetchone()[0]
        return conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]

    # ─── Signals ────────────────────────────────────────────────────────────

    def save_signal(
        self,
        lead_id: str,
        signal_type: str,
        signal_value: str,
        hook_strength: float = 0.5,
        signal_date: Optional[str] = None,
        raw_data: Optional[dict] = None,
    ) -> str:
        """Save a signal for a lead. Returns signal ID."""
        conn = self._get_conn()
        signal_id = _new_id()
        conn.execute(
            """
            INSERT INTO signals (
                id, lead_id, signal_type, signal_value,
                signal_date, hook_strength, raw_data, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                signal_id,
                lead_id,
                signal_type,
                signal_value,
                signal_date or _now(),
                hook_strength,
                json.dumps(raw_data or {}),
                _now(),
            ),
        )
        conn.commit()
        return signal_id

    def get_signals(self, lead_id: str) -> list[dict]:
        """Get all signals for a lead, ordered by hook strength."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM signals WHERE lead_id = ? ORDER BY hook_strength DESC",
            (lead_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    # ─── Contacts ───────────────────────────────────────────────────────────

    def save_contact(
        self,
        lead_id: str,
        full_name: str,
        title: str,
        seniority: str = "",
        linkedin_url: str = "",
        recent_post: str = "",
        recent_post_date: str = "",
    ) -> str:
        """Save a contact (decision maker) for a lead. Returns contact ID."""
        conn = self._get_conn()
        contact_id = _new_id()
        conn.execute(
            """
            INSERT INTO contacts (
                id, lead_id, full_name, title, seniority,
                linkedin_url, recent_post, recent_post_date, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                contact_id,
                lead_id,
                full_name,
                title,
                seniority,
                linkedin_url,
                recent_post,
                recent_post_date,
                _now(),
            ),
        )
        conn.commit()
        return contact_id

    def get_contacts(self, lead_id: str) -> list[dict]:
        """Get all contacts for a lead."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM contacts WHERE lead_id = ? ORDER BY created_at",
            (lead_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    # ─── Drafts ─────────────────────────────────────────────────────────────

    def save_draft(
        self,
        lead_id: str,
        subject_line: str,
        email_body: str,
        contact_id: Optional[str] = None,
        personalization_hooks: Optional[list] = None,
        generation_model: str = "",
    ) -> str:
        """Save a generated email draft. Returns draft ID."""
        conn = self._get_conn()
        draft_id = _new_id()
        conn.execute(
            """
            INSERT INTO outreach_drafts (
                id, lead_id, contact_id, subject_line, email_body,
                personalization_hooks, generation_model, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                draft_id,
                lead_id,
                contact_id,
                subject_line,
                email_body,
                json.dumps(personalization_hooks or []),
                generation_model,
                _now(),
            ),
        )
        conn.commit()
        logger.debug(f"Saved draft for lead {lead_id}")
        return draft_id

    def get_drafts(
        self,
        approved: Optional[bool] = None,
        lead_id: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """Get email drafts, optionally filtered."""
        conn = self._get_conn()
        query = "SELECT * FROM outreach_drafts WHERE 1=1"
        params = []

        if approved is not None:
            query += " AND approved = ?"
            params.append(1 if approved else 0)

        if lead_id:
            query += " AND lead_id = ?"
            params.append(lead_id)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def approve_draft(self, draft_id: str):
        """Mark a draft as approved."""
        conn = self._get_conn()
        conn.execute(
            "UPDATE outreach_drafts SET approved = 1 WHERE id = ?",
            (draft_id,),
        )
        conn.commit()

    def reject_draft(self, draft_id: str, reason: str = ""):
        """Mark a draft as rejected."""
        conn = self._get_conn()
        conn.execute(
            "UPDATE outreach_drafts SET approved = 0, rejection_reason = ? WHERE id = ?",
            (reason, draft_id),
        )
        conn.commit()

    def draft_count(self, approved: Optional[bool] = None) -> int:
        """Count drafts."""
        conn = self._get_conn()
        if approved is not None:
            return conn.execute(
                "SELECT COUNT(*) FROM outreach_drafts WHERE approved = ?",
                (1 if approved else 0,),
            ).fetchone()[0]
        return conn.execute("SELECT COUNT(*) FROM outreach_drafts").fetchone()[0]

    # ─── Pipeline Runs ──────────────────────────────────────────────────────

    def start_run(self) -> str:
        """Log the start of a pipeline run. Returns run ID."""
        conn = self._get_conn()
        run_id = _new_id()
        conn.execute(
            """
            INSERT INTO pipeline_runs (id, started_at, status)
            VALUES (?, ?, 'running')
            """,
            (run_id, _now()),
        )
        conn.commit()
        return run_id

    def finish_run(
        self,
        run_id: str,
        discovered: int,
        qualified: int,
        contacts: int,
        emails: int,
        status: str = "completed",
        error: str = "",
    ):
        """Update a pipeline run with final stats."""
        conn = self._get_conn()
        conn.execute(
            """
            UPDATE pipeline_runs SET
                completed_at = ?,
                companies_discovered = ?,
                companies_qualified = ?,
                contacts_enriched = ?,
                emails_generated = ?,
                status = ?,
                error_message = ?
            WHERE id = ?
            """,
            (
                _now(), discovered, qualified,
                contacts, emails, status, error, run_id,
            ),
        )
        conn.commit()

    def get_recent_runs(self, limit: int = 10) -> list[dict]:
        """Get the most recent pipeline runs."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM pipeline_runs ORDER BY started_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

    # ─── Stats ──────────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        """Return a summary dict for the Slack digest."""
        return {
            "total_leads": self.lead_count(),
            "new_leads": self.lead_count(status="new"),
            "enriched_leads": self.lead_count(status="enriched"),
            "total_drafts": self.draft_count(),
            "approved_drafts": self.draft_count(approved=True),
            "pending_drafts": self.draft_count(approved=False),
        }