# CrustSignal 🎯

> An AI-powered outbound engine that uses CrustData's own APIs to find, score, and draft personalized cold emails for CrustData's ideal customers — every morning, automatically.

Built as a project to demonstrate deep understanding of CrustData's product and data infrastructure.

---

## What it does

Every morning, CrustSignal:

1. **Discovers** newly funded AI/SaaS companies using CrustData's Company Search API
2. **Scores** each company against CrustData's ICP (funding recency, headcount growth, industry fit, size)
3. **Enriches** qualified companies — pulling hiring signals, headcount trends, funding details
4. **Finds** the right contact (CTO, Head of Data, Founder) using People Search API
5. **Reads** their recent LinkedIn posts via Posts API for personalization hooks
6. **Drafts** a hyper-personalized cold email using those exact signals (via Groq LLM)
7. **Serves** a review UI where you can approve/reject each draft + a Slack morning digest

**The twist:** This uses CrustData's own product to generate pipeline for CrustData. Maximum dogfooding.

---

## Architecture

```
CRON JOB (runs 6am daily)
       │
       ▼
┌─────────────────────┐
│  1. DISCOVERY       │   Company Search API → filter by industry, headcount, funding
│  company_search.py  │   Returns ~200 companies/run
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  2. ICP SCORING     │   Score: industry match + funding recency
│  scoring rubric     │         + headcount growth + size fit
└──────────┬──────────┘   Threshold: 0.60 → ~20-30 qualify
           │
           ▼
┌─────────────────────┐
│  3. SIGNAL PULL     │   Company Enrichment: headcount trend, funding details
│  enrichment.py      │   Jobs API: open engineering/data roles
│                     │   People Search: CTO / founder
│                     │   Posts API: what they've posted recently
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  4. EMAIL GEN       │   Groq (llama-3.3-70b) generates subject + 5-sentence email
│  email_gen.py       │   Personalized to specific signals
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  5. OUTPUT          │   SQLite DB → FastAPI → Web Review UI
│  review UI + Slack  │   Morning Slack digest with top 3 leads
└─────────────────────┘
```

---

## APIs Used

| API | Endpoint | Purpose |
|-----|----------|---------|
| Company Search | `POST /screener/company/search` | ICP discovery |
| Company Enrichment | `GET /screener/company` | Headcount, funding, jobs |
| People Search | `POST /screener/person/search` | Find CTO/founder |
| People Enrichment | `GET /screener/person/enrich` | Full profile |
| Social Posts | `GET /screener/social_posts` | LinkedIn personalization hooks |

---

## Setup (5 minutes)

```bash
# 1. Clone the repo
git clone https://github.com/yourusername/crustsignal.git
cd crustsignal

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Open .env and add your keys:
#   CRUSTDATA_API_KEY  → from crustdata.com
#   GROQ_API_KEY       → from console.groq.com (free)

# 5. Run tests to verify everything works
python scripts/test_connection.py

# 6. Run the pipeline
python run_pipeline.py
```

---

## Results (from test run)

> *(Updated after first live run)*

- Companies discovered: —
- Companies qualified: —
- Emails generated: —
- Pipeline runtime: —

---

## Project Structure

```
crustsignal/
├── src/
│   ├── crustdata/
│   │   ├── client.py           ← API wrapper (all 5 endpoints)
│   │   └── company_search.py   ← ICP discovery + scoring
│   ├── pipeline/
│   │   ├── enrichment.py       ← Signal pulling (Day 3)
│   │   └── email_gen.py        ← Groq email generation (Day 4)
│   ├── storage/
│   │   ├── db.py               ← SQLite layer
│   │   └── schema.sql          ← Database schema
│   └── output/
│       └── slack.py            ← Morning digest (Day 5)
├── scripts/
│   └── test_connection.py      ← Run first to verify setup
├── ui/                         ← Review interface (Day 5)
├── examples/                   ← Sample email outputs
├── .env.example
├── requirements.txt
└── run_pipeline.py             ← Main entry point
```

---

## Built with

- [CrustData API](https://docs.crustdata.com) — real-time B2B data
- [Groq](https://console.groq.com) — fast LLM inference (llama-3.3-70b)
- FastAPI — internal review API
- SQLite — lightweight local storage
- Rich — terminal output

---

*Built in one week as part of an internship application to CrustData.*