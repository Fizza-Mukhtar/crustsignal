-- CrustSignal Database Schema
-- Run via: sqlite3 crustsignal.db < schema.sql
-- Or let db.py call this automatically on startup

-- ─── Leads ───────────────────────────────────────────────────────────────────
-- Companies identified as Crustdata ICP targets

CREATE TABLE IF NOT EXISTS leads (
    id               TEXT PRIMARY KEY,      -- UUID
    company_name     TEXT NOT NULL,
    company_domain   TEXT,
    linkedin_url     TEXT,
    industry         TEXT,
    headcount        INTEGER,
    headcount_growth_6m_pct  REAL,
    headcount_growth_1y_pct  REAL,
    total_funding_usd        INTEGER,
    last_round_type  TEXT,                  -- seed, series_a, series_b, etc.
    days_since_last_funding  INTEGER,
    location         TEXT,
    description      TEXT,
    icp_score        REAL,                  -- 0.0 to 1.0
    score_breakdown  TEXT,                  -- JSON string
    status           TEXT DEFAULT 'new',    -- new|enriched|drafted|approved|sent|replied
    discovered_at    TEXT,                  -- ISO timestamp
    updated_at       TEXT
);

CREATE INDEX IF NOT EXISTS idx_leads_score ON leads(icp_score DESC);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_domain ON leads(company_domain);

-- ─── Signals ─────────────────────────────────────────────────────────────────
-- Specific data points used for email personalization

CREATE TABLE IF NOT EXISTS signals (
    id            TEXT PRIMARY KEY,
    lead_id       TEXT NOT NULL REFERENCES leads(id),
    signal_type   TEXT NOT NULL,  -- funding|headcount_growth|job_posting|
                                  --  linkedin_post|web_traffic|leadership_change
    signal_value  TEXT,           -- Human readable: "raised $4.2M Series A 12 days ago"
    signal_date   TEXT,
    hook_strength REAL,           -- 0.0 to 1.0 (how good as email hook)
    raw_data      TEXT,           -- JSON of full signal data
    created_at    TEXT
);

CREATE INDEX IF NOT EXISTS idx_signals_lead ON signals(lead_id);
CREATE INDEX IF NOT EXISTS idx_signals_type ON signals(signal_type);

-- ─── Contacts ────────────────────────────────────────────────────────────────
-- Decision makers at each lead company

CREATE TABLE IF NOT EXISTS contacts (
    id            TEXT PRIMARY KEY,
    lead_id       TEXT NOT NULL REFERENCES leads(id),
    full_name     TEXT,
    title         TEXT,
    seniority     TEXT,           -- cto|ceo|founder|vp_engineering|head_of_data
    linkedin_url  TEXT,
    recent_post   TEXT,           -- Their latest LinkedIn post (for personalization)
    recent_post_date TEXT,
    created_at    TEXT
);

CREATE INDEX IF NOT EXISTS idx_contacts_lead ON contacts(lead_id);

-- ─── Outreach Drafts ─────────────────────────────────────────────────────────
-- AI-generated email drafts for each lead

CREATE TABLE IF NOT EXISTS outreach_drafts (
    id                    TEXT PRIMARY KEY,
    lead_id               TEXT NOT NULL REFERENCES leads(id),
    contact_id            TEXT REFERENCES contacts(id),
    subject_line          TEXT,
    email_body            TEXT,
    personalization_hooks TEXT,   -- JSON: which signals were used
    generation_model      TEXT,   -- e.g. "llama-3.3-70b-versatile"
    approved              INTEGER DEFAULT 0,   -- 0 or 1
    sent                  INTEGER DEFAULT 0,
    quality_score         REAL,   -- optional human rating (1-10)
    rejection_reason      TEXT,
    created_at            TEXT
);

CREATE INDEX IF NOT EXISTS idx_drafts_lead ON outreach_drafts(lead_id);
CREATE INDEX IF NOT EXISTS idx_drafts_approved ON outreach_drafts(approved);

-- ─── Pipeline Runs ───────────────────────────────────────────────────────────
-- Audit log of each pipeline execution

CREATE TABLE IF NOT EXISTS pipeline_runs (
    id                    TEXT PRIMARY KEY,
    started_at            TEXT,
    completed_at          TEXT,
    companies_discovered  INTEGER DEFAULT 0,
    companies_qualified   INTEGER DEFAULT 0,
    contacts_enriched     INTEGER DEFAULT 0,
    emails_generated      INTEGER DEFAULT 0,
    api_credits_estimated INTEGER DEFAULT 0,
    status                TEXT,   -- running|completed|failed
    error_message         TEXT
);