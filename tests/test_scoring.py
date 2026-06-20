"""
Tests — ICP Scoring Algorithm
==============================
Run with: pytest tests/test_scoring.py -v

Tests the core scoring logic that decides which companies
qualify as CrustData ICP targets.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from src.crustdata.company_search import score_company, build_scored_company


# ── Fixtures ─────────────────────────────────────────────────────────────────

def make_company(**overrides):
    """Helper — returns a base company dict with optional overrides."""
    base = {
        "name": "TestCo",
        "website": "testco.io",
        "industry": "Computer Software",
        "description": "AI-powered sales automation tool",
        "employee_count": 80,
        "employee_growth_percentages": [
            {"timespan": "SIX_MONTHS", "percentage": 20},
            {"timespan": "YEAR",       "percentage": 40},
        ],
        "days_since_last_fundraise": 30,
        "total_funding_raised_usd": 5_000_000,
        "last_round_type": "Seed",
        "specialties": ["AI", "sales automation"],
    }
    base.update(overrides)
    return base


# ── Industry scoring ─────────────────────────────────────────────────────────

class TestIndustryScoring:

    def test_ai_sdr_company_gets_full_industry_points(self):
        company = make_company(
            industry="Artificial Intelligence",
            description="AI SDR platform for outbound sales automation",
        )
        score, breakdown = score_company(company)
        assert breakdown["industry"]["points"] == 30

    def test_recruiting_platform_matches_industry(self):
        company = make_company(
            industry="Staffing and Recruiting",
            description="AI-powered applicant tracking system",
        )
        score, breakdown = score_company(company)
        assert breakdown["industry"]["points"] >= 18

    def test_unrelated_industry_scores_zero(self):
        company = make_company(
            industry="Oil and Gas",
            description="Petroleum extraction and refining",
            specialties=["energy", "oil"],
        )
        score, breakdown = score_company(company)
        assert breakdown["industry"]["points"] == 0

    def test_vc_firm_matches_industry(self):
        company = make_company(
            industry="Venture Capital & Private Equity",
            description="Early stage VC firm focused on B2B SaaS",
        )
        score, breakdown = score_company(company)
        assert breakdown["industry"]["points"] >= 18


# ── Funding recency scoring ───────────────────────────────────────────────────

class TestFundingScoring:

    def test_very_recent_funding_scores_max(self):
        company = make_company(days_since_last_fundraise=7)
        score, breakdown = score_company(company)
        assert breakdown["funding_recency"]["points"] == 25

    def test_two_week_funding_scores_high(self):
        company = make_company(days_since_last_fundraise=14)
        score, breakdown = score_company(company)
        assert breakdown["funding_recency"]["points"] >= 20

    def test_45_day_funding_still_qualifies(self):
        company = make_company(days_since_last_fundraise=45)
        score, breakdown = score_company(company)
        assert breakdown["funding_recency"]["points"] >= 15

    def test_old_funding_scores_zero(self):
        company = make_company(days_since_last_fundraise=400)
        score, breakdown = score_company(company)
        assert breakdown["funding_recency"]["points"] == 0

    def test_missing_funding_scores_zero(self):
        company = make_company(days_since_last_fundraise=None)
        score, breakdown = score_company(company)
        assert breakdown["funding_recency"]["points"] == 0


# ── Headcount growth scoring ─────────────────────────────────────────────────

class TestHeadcountGrowthScoring:

    def test_hyper_growth_scores_max(self):
        company = make_company(employee_growth_percentages=[
            {"timespan": "SIX_MONTHS", "percentage": 50},
            {"timespan": "YEAR",       "percentage": 90},
        ])
        score, breakdown = score_company(company)
        assert breakdown["headcount_growth"]["points"] == 25

    def test_moderate_growth_scores_partial(self):
        company = make_company(employee_growth_percentages=[
            {"timespan": "SIX_MONTHS", "percentage": 12},
            {"timespan": "YEAR",       "percentage": 20},
        ])
        score, breakdown = score_company(company)
        assert 8 <= breakdown["headcount_growth"]["points"] <= 20

    def test_flat_headcount_scores_zero(self):
        company = make_company(employee_growth_percentages=[
            {"timespan": "SIX_MONTHS", "percentage": 0},
            {"timespan": "YEAR",       "percentage": 2},
        ])
        score, breakdown = score_company(company)
        assert breakdown["headcount_growth"]["points"] == 0

    def test_flat_field_format_also_works(self):
        """Enrichment API uses flat fields instead of array."""
        company = make_company(
            employee_growth_percentages=[],
            headcount_qoq_pct=25,
        )
        score, breakdown = score_company(company)
        assert breakdown["headcount_growth"]["points"] >= 18


# ── Size fit scoring ──────────────────────────────────────────────────────────

class TestSizeFitScoring:

    def test_ideal_size_scores_max(self):
        company = make_company(employee_count=100)
        score, breakdown = score_company(company)
        assert breakdown["size_fit"]["points"] == 20

    def test_lower_bound_ideal(self):
        company = make_company(employee_count=10)
        score, breakdown = score_company(company)
        assert breakdown["size_fit"]["points"] == 20

    def test_upper_bound_ideal(self):
        company = make_company(employee_count=300)
        score, breakdown = score_company(company)
        assert breakdown["size_fit"]["points"] == 20

    def test_too_small_scores_partial(self):
        company = make_company(employee_count=5)
        score, breakdown = score_company(company)
        assert breakdown["size_fit"]["points"] == 12

    def test_massive_enterprise_scores_zero(self):
        company = make_company(employee_count=50_000)
        score, breakdown = score_company(company)
        assert breakdown["size_fit"]["points"] == 0


# ── End-to-end scoring ────────────────────────────────────────────────────────

class TestEndToEndScoring:

    def test_perfect_icp_scores_above_90(self):
        """A perfect ICP company should score very high."""
        company = make_company(
            industry="Artificial Intelligence",
            description="AI SDR platform for outbound sales automation and prospecting",
            employee_count=75,
            employee_growth_percentages=[
                {"timespan": "SIX_MONTHS", "percentage": 35},
                {"timespan": "YEAR",       "percentage": 65},
            ],
            days_since_last_fundraise=12,
            specialties=["AI", "sales", "sdr", "automation"],
        )
        score, _ = score_company(company)
        assert score >= 0.90, f"Expected >= 0.90, got {score:.2f}"

    def test_weak_icp_scores_below_threshold(self):
        """A poor ICP company should fail the 0.60 threshold."""
        company = make_company(
            industry="Oil and Gas",
            description="Petroleum refining and distribution",
            employee_count=5000,
            employee_growth_percentages=[
                {"timespan": "SIX_MONTHS", "percentage": 1},
            ],
            days_since_last_fundraise=500,
            specialties=["energy", "oil"],
        )
        score, _ = score_company(company)
        assert score < 0.60, f"Expected < 0.60, got {score:.2f}"

    def test_score_is_between_0_and_1(self):
        """Score must always be a valid float between 0 and 1."""
        for headcount in [0, 5, 50, 300, 5000]:
            company = make_company(employee_count=headcount)
            score, _ = score_company(company)
            assert 0.0 <= score <= 1.0, f"Score {score} out of range for headcount {headcount}"

    def test_build_scored_company_preserves_score(self):
        """build_scored_company should return object with same score as score_company."""
        raw = make_company()
        score, _ = score_company(raw)
        scored = build_scored_company(raw)
        assert abs(scored.icp_score - score) < 0.001

    def test_scored_company_qualifies_flag(self):
        """ScoredCompany.qualifies returns True above 0.60 threshold."""
        good = build_scored_company(make_company(
            days_since_last_fundraise=15,
            industry="Artificial Intelligence",
            description="AI sales automation",
            employee_count=80,
            employee_growth_percentages=[{"timespan": "SIX_MONTHS", "percentage": 25}],
        ))
        bad = build_scored_company(make_company(
            industry="Oil and Gas",
            description="Petroleum",
            employee_count=5000,
            days_since_last_fundraise=999,
            employee_growth_percentages=[],
            specialties=[],
        ))
        assert good.qualifies is True
        assert bad.qualifies is False

    def test_score_breakdown_has_all_four_dimensions(self):
        """Every score must have all 4 breakdown keys."""
        company = make_company()
        _, breakdown = score_company(company)
        assert "industry"          in breakdown
        assert "funding_recency"   in breakdown
        assert "headcount_growth"  in breakdown
        assert "size_fit"          in breakdown

    def test_total_points_never_exceed_100(self):
        """Sum of all breakdown points should never exceed 100."""
        company = make_company(
            industry="Artificial Intelligence",
            description="AI SDR automation platform sales",
            employee_count=100,
            employee_growth_percentages=[
                {"timespan": "SIX_MONTHS", "percentage": 100},
            ],
            days_since_last_fundraise=1,
            specialties=["AI", "sales", "automation", "sdr", "outbound"],
        )
        _, breakdown = score_company(company)
        total = sum(v["points"] for v in breakdown.values())
        assert total <= 100, f"Total points {total} exceeds 100"