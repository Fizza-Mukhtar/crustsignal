# CrustSignal

> An AI-powered outbound engine built **for** CrustData, **using** CrustData.

Every morning it finds newly funded AI companies that match CrustData's ICP, pulls their live signals, and drafts personalized cold emails — automatically.


---

## The Idea

CrustData sells real-time B2B data to companies building AI SDRs, recruiting tools, and GTM automation.

They grew to $4M ARR almost entirely through inbound — zero outbound spend, one salesperson. That means the best real-time B2B data API on the market has never been turned on itself.

CrustSignal does exactly that. It uses CrustData's own APIs to:

1. Find companies that should be using CrustData
2. Pull the exact signals that make them a hot prospect right now
3. Draft a personalized email that references those specific signals
4. Surface everything in a review UI so a human can approve and send

---

## Demo

### Pipeline running (terminal)
```
Stage 1/4  Discovering ICP companies...
   Found 8 companies → 8 qualified (score ≥ 0.6)

  → Keyplay  (score: 0.87)
     Contact: Adam Schoenfeld (CEO & Co-Founder)
     Signals: linkedin_post, funding, job_posting
     Email: ✅ "Saw your post on real-time signal pipeline"

  → Topo  (score: 1.00)
     Contact: Nicolas Vandenberghe (CEO & Co-Founder)
     Signals: funding, linkedin_post, job_posting
     Email: ✅ "$3.8M for real-time AI outbound"
     
Pipeline Run Complete ✅
8 leads · 8 emails · ~38 seconds
```

### Review UI (`localhost:8000`)
- Dark two-panel interface
- Company list with ICP scores on the left
- Signal breakdown + email draft on the right
- One-click Approve / Reject

See [`examples/sample_emails.md`](examples/sample_emails.md) for real email output.

---

## How It Works

```
CRON / Manual trigger
        │
        ▼
┌───────────────────┐
│  1. DISCOVERY     │  Company Search API — filter by industry,
│                   │  headcount, recent funding, hiring signals
└────────┬──────────┘
         │  ~200 companies scanned
         ▼
┌───────────────────┐
│  2. ICP SCORING   │  Score 0–100:
│                   │  Industry match   30 pts
│                   │  Funding recency  25 pts
│                   │  Headcount growth 25 pts
│                   │  Size fit         20 pts
│                   │  Threshold: 60+
└────────┬──────────┘
         │  ~20 qualified
         ▼
┌───────────────────┐
│  3. ENRICHMENT    │  Company Enrichment API — headcount trend,
│  + SIGNALS        │  funding details, open jobs, web traffic
│                   │  People Search API — find CTO / founder
│                   │  Posts API — recent LinkedIn posts (hooks)
└────────┬──────────┘
         ▼
┌───────────────────┐
│  4. EMAIL GEN     │  Groq llama-3.3-70b writes a 5-sentence
│                   │  personalized email using top 3 signals
└────────┬──────────┘
         ▼
┌───────────────────┐
│  5. REVIEW UI     │  FastAPI + HTML — browse leads, read drafts,
│                   │  approve / reject with one click
└───────────────────┘
```

---

## APIs Used

| API | Endpoint | Purpose |
|-----|----------|---------|
| Company Search | `POST /screener/company/search` | ICP discovery |
| Company Enrichment | `GET /screener/company` | Headcount, funding, jobs |
| People Search | `POST /screener/person/search` | Find CTO / founder |
| People Enrichment | `GET /screener/person/enrich` | Full contact profile |
| Social Posts | `GET /screener/social_posts` | LinkedIn post hooks |

---

## Setup

```bash
# 1. Clone
git clone https://github.com/YOUR_USERNAME/crustsignal.git
cd crustsignal

# 2. Virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install
pip install -r requirements.txt

# 4. Environment variables
cp .env.example .env
# Add CRUSTDATA_API_KEY and GROQ_API_KEY to .env

# 5. Test connection
python scripts/test_connection.py

# 6. Run pipeline (mock mode — zero API credits)
python run_pipeline.py --mock

# 7. Open review UI
python scripts/start_server.py
```

---

## Running Modes

| Command | Mode | Credits |
|---------|------|---------|
| `python run_pipeline.py --mock` | Fake data, zero credits | 0 |
| `python run_pipeline.py --live` | Real CrustData API | ~8-20 |
| `python scripts/demo_run.py` | Real API, 8 handpicked companies | ~8 |

---

## Project Structure

```
crustsignal/
├── src/
│   ├── crustdata/
│   │   ├── client.py           ← API wrapper (5 endpoints, retry logic)
│   │   ├── company_search.py   ← ICP discovery + scoring algorithm
│   │   └── mock_data.py        ← Realistic mock data (dev/testing)
│   ├── pipeline/
│   │   ├── enrichment.py       ← Company + contact enrichment
│   │   ├── signal_extract.py   ← Signal extraction + ranking
│   │   ├── email_gen.py        ← Groq email generation
│   │   └── orchestrator.py     ← Full pipeline (all stages)
│   ├── storage/
│   │   ├── db.py               ← SQLite CRUD layer
│   │   └── schema.sql          ← DB schema
│   └── api/
│       └── main.py             ← FastAPI backend
├── ui/
│   └── index.html              ← Review UI (vanilla JS, no framework)
├── scripts/
│   ├── test_connection.py      ← API health check
│   ├── demo_run.py             ← Real API demo (8 credits)
│   ├── start_server.py         ← Launch UI server
│   └── review_drafts.py        ← Terminal email viewer
├── examples/
│   └── sample_emails.md        ← Real email output examples
├── run_pipeline.py             ← Main entry point
└── .env.example
```

---

## Tech Stack

- **Data:** [CrustData API](https://crustdata.com) — real-time B2B intelligence
- **Email AI:** [Groq](https://console.groq.com) — llama-3.3-70b (free tier)
- **Backend:** FastAPI + SQLite
- **Frontend:** Vanilla HTML/CSS/JS (no framework)
- **Terminal UI:** Rich

---

## Results

| Metric | Value |
|--------|-------|
| Pipeline runtime | ~38 seconds (8 companies) |
| ICP qualification rate | 100% (handpicked demo set) |
| Email success rate | 8/8 |
| Groq API cost | $0.00 |
| CrustData credits (demo) | ~8 |

