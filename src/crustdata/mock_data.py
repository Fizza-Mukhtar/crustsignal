"""
Mock Data — Realistic fake API responses for development.
USE_MOCK=true in .env → pipeline runs without hitting API.
USE_MOCK=false        → real API (only for demo recording).

Companies chosen: real AI startups that are perfect CrustData ICP.
Data is realistic but not exact — for demo purposes only.
"""

# ── 8 perfect ICP companies ────────────────────────────────────────────────
MOCK_COMPANIES = [
    {
        "company_name": "Artisan AI",
        "company_website_domain": "artisan.co",
        "linkedin_profile_url": "https://www.linkedin.com/company/artisan-ai",
        "industry": "Artificial Intelligence",
        "description": "Building the world's first AI employees — starting with Ava, the AI BDR who automates end-to-end outbound sales.",
        "headcount": {"latest_count": 52, "six_month_growth_percent": 38, "one_year_growth_percent": 91},
        "funding_and_investment": {
            "last_round_type": "Series A",
            "last_round_investment_usd": 11500000,
            "days_since_last_fundraise": 22,
            "total_investment_usd": 14200000,
        },
        "web_traffic": {"monthly_visitors": 48000, "mom_growth_percent": 18},
        "job_openings": [
            {"title": "Senior ML Engineer", "department": "Engineering", "location": "San Francisco"},
            {"title": "Data Infrastructure Engineer", "department": "Engineering", "location": "Remote"},
            {"title": "AI Research Scientist", "department": "Research", "location": "San Francisco"},
        ],
        "decision_makers": {"profiles": [
            {
                "full_name": "Jaspar Carmichael-Jack",
                "title": "CEO & Co-Founder",
                "linkedin_profile_url": "https://www.linkedin.com/in/jaspar-carmichael-jack",
                "seniority": "CXO",
            },
            {
                "full_name": "Sam Havens",
                "title": "CTO & Co-Founder",
                "linkedin_profile_url": "https://www.linkedin.com/in/sam-havens",
                "seniority": "CXO",
            },
        ]},
    },
    {
        "company_name": "Warmly",
        "company_website_domain": "warmly.ai",
        "linkedin_profile_url": "https://www.linkedin.com/company/warmlyai",
        "industry": "Sales Intelligence",
        "description": "Signal-based sales platform that reveals who's on your website and automates personalized outreach at the moment of intent.",
        "headcount": {"latest_count": 41, "six_month_growth_percent": 45, "one_year_growth_percent": 78},
        "funding_and_investment": {
            "last_round_type": "Seed",
            "last_round_investment_usd": 6000000,
            "days_since_last_fundraise": 41,
            "total_investment_usd": 9400000,
        },
        "web_traffic": {"monthly_visitors": 32000, "mom_growth_percent": 22},
        "job_openings": [
            {"title": "Senior Data Engineer", "department": "Engineering", "location": "Remote"},
            {"title": "Head of Partnerships", "department": "Business Development", "location": "New York"},
        ],
        "decision_makers": {"profiles": [
            {
                "full_name": "Alan Zhao",
                "title": "CEO & Co-Founder",
                "linkedin_profile_url": "https://www.linkedin.com/in/alan-zhao-warmly",
                "seniority": "CXO",
            },
        ]},
    },
    {
        "company_name": "Keyplay",
        "company_website_domain": "keyplay.io",
        "linkedin_profile_url": "https://www.linkedin.com/company/keyplay",
        "industry": "Computer Software",
        "description": "Account scoring and ICP fit platform that helps sales teams prioritize their best-fit accounts using AI and real-time signals.",
        "headcount": {"latest_count": 24, "six_month_growth_percent": 29, "one_year_growth_percent": 55},
        "funding_and_investment": {
            "last_round_type": "Seed",
            "last_round_investment_usd": 5200000,
            "days_since_last_fundraise": 58,
            "total_investment_usd": 5200000,
        },
        "web_traffic": {"monthly_visitors": 18000, "mom_growth_percent": 14},
        "job_openings": [
            {"title": "ML Engineer — Account Signals", "department": "Engineering", "location": "Remote"},
        ],
        "decision_makers": {"profiles": [
            {
                "full_name": "Adam Schoenfeld",
                "title": "CEO & Co-Founder",
                "linkedin_profile_url": "https://www.linkedin.com/in/adamschoenfeld",
                "seniority": "CXO",
            },
        ]},
    },
    {
        "company_name": "Default",
        "company_website_domain": "default.com",
        "linkedin_profile_url": "https://www.linkedin.com/company/default-app",
        "industry": "Sales Automation",
        "description": "Inbound lead orchestration platform — routes, enriches, and qualifies leads in real-time so reps only talk to the right people.",
        "headcount": {"latest_count": 33, "six_month_growth_percent": 32, "one_year_growth_percent": 68},
        "funding_and_investment": {
            "last_round_type": "Series A",
            "last_round_investment_usd": 12300000,
            "days_since_last_fundraise": 34,
            "total_investment_usd": 15800000,
        },
        "web_traffic": {"monthly_visitors": 22000, "mom_growth_percent": 28},
        "job_openings": [
            {"title": "Senior Backend Engineer — Data Pipelines", "department": "Engineering", "location": "San Francisco"},
            {"title": "Integrations Engineer", "department": "Engineering", "location": "Remote"},
        ],
        "decision_makers": {"profiles": [
            {
                "full_name": "Rablord Ingram",
                "title": "CEO & Co-Founder",
                "linkedin_profile_url": "https://www.linkedin.com/in/rablordingram",
                "seniority": "CXO",
            },
        ]},
    },
    {
        "company_name": "Pocus",
        "company_website_domain": "pocus.com",
        "linkedin_profile_url": "https://www.linkedin.com/company/pocus",
        "industry": "Product-Led Sales",
        "description": "Product-led sales platform that uses product usage data + external signals to surface the best accounts to target.",
        "headcount": {"latest_count": 31, "six_month_growth_percent": 22, "one_year_growth_percent": 47},
        "funding_and_investment": {
            "last_round_type": "Series A",
            "last_round_investment_usd": 23000000,
            "days_since_last_fundraise": 67,
            "total_investment_usd": 26000000,
        },
        "web_traffic": {"monthly_visitors": 29000, "mom_growth_percent": 11},
        "job_openings": [
            {"title": "Data Engineer", "department": "Engineering", "location": "New York"},
        ],
        "decision_makers": {"profiles": [
            {
                "full_name": "Alexa Grabell",
                "title": "CEO & Co-Founder",
                "linkedin_profile_url": "https://www.linkedin.com/in/alexa-grabell",
                "seniority": "CXO",
            },
        ]},
    },
    {
        "company_name": "Topo",
        "company_website_domain": "topo.io",
        "linkedin_profile_url": "https://www.linkedin.com/company/topo-io",
        "industry": "AI Sales Automation",
        "description": "AI-powered outbound platform that builds prospect lists, writes personalized emails, and automates sequences at scale.",
        "headcount": {"latest_count": 18, "six_month_growth_percent": 50, "one_year_growth_percent": 100},
        "funding_and_investment": {
            "last_round_type": "Seed",
            "last_round_investment_usd": 3800000,
            "days_since_last_fundraise": 15,
            "total_investment_usd": 3800000,
        },
        "web_traffic": {"monthly_visitors": 12000, "mom_growth_percent": 35},
        "job_openings": [
            {"title": "AI Engineer — Prospecting", "department": "Engineering", "location": "Remote"},
            {"title": "Head of Data", "department": "Data", "location": "Remote"},
        ],
        "decision_makers": {"profiles": [
            {
                "full_name": "Nicolas Vandenberghe",
                "title": "CEO & Co-Founder",
                "linkedin_profile_url": "https://www.linkedin.com/in/nvandenberghe",
                "seniority": "CXO",
            },
        ]},
    },
    {
        "company_name": "UserGems",
        "company_website_domain": "usergems.com",
        "linkedin_profile_url": "https://www.linkedin.com/company/usergems",
        "industry": "Sales Intelligence",
        "description": "Tracks job changes of past customers and champions — alerts sales teams when their buyers move to new companies.",
        "headcount": {"latest_count": 48, "six_month_growth_percent": 19, "one_year_growth_percent": 38},
        "funding_and_investment": {
            "last_round_type": "Series A",
            "last_round_investment_usd": 20000000,
            "days_since_last_fundraise": 88,
            "total_investment_usd": 23000000,
        },
        "web_traffic": {"monthly_visitors": 35000, "mom_growth_percent": 9},
        "job_openings": [
            {"title": "Data Platform Engineer", "department": "Engineering", "location": "Remote"},
        ],
        "decision_makers": {"profiles": [
            {
                "full_name": "Christian Kletzl",
                "title": "CEO & Co-Founder",
                "linkedin_profile_url": "https://www.linkedin.com/in/christiankletzl",
                "seniority": "CXO",
            },
        ]},
    },
    {
        "company_name": "Scalis",
        "company_website_domain": "scalis.ai",
        "linkedin_profile_url": "https://www.linkedin.com/company/scalisai",
        "industry": "HR Technology",
        "description": "AI-native recruiting platform that automates candidate sourcing, screening, and scheduling for high-growth companies.",
        "headcount": {"latest_count": 27, "six_month_growth_percent": 35, "one_year_growth_percent": 69},
        "funding_and_investment": {
            "last_round_type": "Seed",
            "last_round_investment_usd": 4500000,
            "days_since_last_fundraise": 29,
            "total_investment_usd": 4500000,
        },
        "web_traffic": {"monthly_visitors": 9000, "mom_growth_percent": 41},
        "job_openings": [
            {"title": "Senior Full Stack Engineer", "department": "Engineering", "location": "Remote"},
            {"title": "AI/ML Engineer", "department": "AI", "location": "Remote"},
        ],
        "decision_makers": {"profiles": [
            {
                "full_name": "Renata Leal",
                "title": "CEO & Co-Founder",
                "linkedin_profile_url": "https://www.linkedin.com/in/renata-leal-scalis",
                "seniority": "CXO",
            },
        ]},
    },
]

# ── Mock LinkedIn posts per contact ───────────────────────────────────────
MOCK_POSTS = {
    "jaspar-carmichael-jack": [
        {
            "text": "We've been using Apollo for 6 months and the data quality is honestly our biggest pain point. 30% bounce rates. Looking for something better — open to suggestions from founders who've solved this.",
            "date": "2025-06-12",
            "likes": 183,
            "comments": 47,
        },
        {
            "text": "Excited to announce Artisan AI's $11.5M Series A! We're building the AI employee stack — starting with Ava, our AI BDR. The future of work is AI employees working alongside human ones.",
            "date": "2025-05-29",
            "likes": 892,
            "comments": 134,
        },
    ],
    "alan-zhao-warmly": [
        {
            "text": "Hot take: the biggest problem in sales tech isn't the AI model. It's the data. Most outbound tools are running on data that's 3–6 months stale. That's why personalization feels fake — the info is just wrong.",
            "date": "2025-06-10",
            "likes": 241,
            "comments": 62,
        },
    ],
    "adamschoenfeld": [
        {
            "text": "We just hired a data engineer specifically to build our signal pipeline. Scraping job postings, funding data, tech stack signals. If you're not building on real-time data in 2025, you're guessing.",
            "date": "2025-06-08",
            "likes": 198,
            "comments": 38,
        },
    ],
    "rablordingram": [
        {
            "text": "Default just closed our Series A. The vision: every inbound lead gets enriched, scored, and routed in under 5 seconds — before a human even looks at it. Hiring engineers who want to build this.",
            "date": "2025-06-05",
            "likes": 445,
            "comments": 89,
        },
    ],
    "nvandenberghe": [
        {
            "text": "We seeded Topo with $3.8M last week. The bet: AI outbound that actually knows what a company is going through RIGHT NOW — not what their LinkedIn page said 4 months ago. Real-time signals are the unlock.",
            "date": "2025-06-15",
            "likes": 312,
            "comments": 71,
        },
    ],
    "christiankletzl": [
        {
            "text": "Job change data is only useful if it's fresh. We're rebuilding our tracking pipeline because 2-week-old alerts are too slow — by then, the new job honeymoon period is already over.",
            "date": "2025-06-09",
            "likes": 156,
            "comments": 29,
        },
    ],
}

def get_mock_company_list():
    """Returns all mock companies (simulates company search results)."""
    return MOCK_COMPANIES

def get_mock_company(domain: str) -> dict:
    """Returns mock data for a specific company domain."""
    for c in MOCK_COMPANIES:
        if c["company_website_domain"] == domain:
            return c
    return {}

def get_mock_posts(linkedin_handle: str) -> list:
    """Returns mock posts for a contact's LinkedIn handle."""
    # Try exact match first, then partial match
    handle = linkedin_handle.split("/in/")[-1].rstrip("/")
    return MOCK_POSTS.get(handle, [
        {
            "text": f"Excited about what we're building. Big year ahead.",
            "date": "2025-06-01",
            "likes": 45,
            "comments": 8,
        }
    ])