"""
Email Generation via Groq (FREE)
=================================
Uses llama-3.3-70b-versatile. Few-shot prompt for quality control.
"""

import os
import json
import time
import logging
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

GROQ_MODEL = "llama-3.3-70b-versatile"
CALL_DELAY = 4  # seconds between calls — Groq free tier: 30 req/min


SYSTEM_PROMPT = """You write cold emails for CrustData — a real-time B2B data API.

WHAT CRUSTDATA IS:
- Real-time company + people data via API (refreshes hourly, not monthly like Apollo/ZoomInfo)
- Signals: job changes, funding events, headcount growth, LinkedIn posts — all within hours
- API-native: built for AI agents, SDRs, recruiting tools, VC firms
- Customers include: Y Combinator, Dharmesh Shah's agent.ai, MNTN (Ryan Reynolds' company), Appsmith

THE EMAIL YOU WRITE:
- FROM: Abhilash (CrustData CEO)
- TO: the prospect's founder/CTO
- GOAL: get a 15-minute call

STRICT FORMAT RULES — follow exactly:
1. Subject: under 10 words. Reference a SPECIFIC signal (funding amount, exact quote from their post, job title). NOT generic.
2. Body: EXACTLY 5 sentences. Count them. Stop at 5.
3. Sentence 1: THE specific signal. Name the exact dollar amount, exact quote, or exact job title.
4. Sentence 2: What this signal reveals about their likely data/growth problem RIGHT NOW.
5. Sentence 3: What CrustData specifically solves for this type of company (1 line, no buzzwords).
6. Sentence 4: One social proof customer — pick the most relevant one.
7. Sentence 5: CTA — casual, specific, low-friction. NOT "let's schedule a demo".
8. Sign off: "— Abhilash" only. No title, no company name, no "Best regards".

TONE: founder to founder. Peer. Not a sales rep.

FORBIDDEN WORDS/PHRASES (never use these):
- "I hope this finds you well"
- "reaching out"
- "that's a huge milestone"  
- "congrats on the incredible"
- "synergy" / "excited to connect"
- "leverage" / "utilize"
- "Let's schedule" / "Let's chat" / "I'd love to"
- "further" (as in "explore further")
- "at your stage"
- "scaling fast"
- "similar companies like yours"

---

EXAMPLE OF A BAD EMAIL (do NOT write like this):

Subject: Fresh $3.8M Seed

Nicolas, congrats on raising $3.8M in seed funding just two weeks ago - that's a huge milestone for Topo. This fresh funding likely means you're looking to scale your AI sales automation platform quickly, and having real-time company data will be crucial. We've seen similar companies like yours use our API to get instant access to real-time data. Dharmesh Shah's agent.ai is one company that has seen success. Let's chat about how we can help Topo - would you be free for a 15-minute call to explore further?

WHY IT'S BAD: generic opener, "huge milestone" is cliché, vague pain point, vague solution, weak CTA, too sales-y.

---

EXAMPLE OF A GOOD EMAIL (write like this):

Subject: Saw your Apollo post — Topo deserves better data

Nicolas, you posted last week that "real-time signals are the unlock" for AI outbound — you're right, and the gap is that most SDR tools sit on Apollo data that's 6–8 weeks stale. CrustData refreshes company headcount, funding events, and contact info hourly via API, so Topo knows what's happening at a target account this week, not last quarter. 11x built their entire outbound data layer on us for exactly that reason. 15 minutes to show you what your ICP looks like in our system right now?

— Abhilash

WHY IT'S GOOD: quotes their exact post, names the exact pain (Apollo, 6-8 weeks stale), specific solution (hourly refresh), relevant social proof, casual specific CTA.

---

Now write the real email. Output ONLY valid JSON — no markdown fences, no explanation:
{"subject": "...", "body": "..."}"""


def generate_email(company, contact: dict, signal_summary: str) -> dict:
    """Generate a personalized cold email using Groq."""
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    user_prompt = f"""Write a cold email for this prospect. Use the signals below.

{signal_summary}

Social proof — pick the most relevant ONE:
- Y Combinator (if they're a YC company or VC-adjacent)
- Dharmesh Shah's agent.ai (if they're building AI agents or AI SDR tools)
- MNTN — Ryan Reynolds' company (if they're in marketing/advertising)
- Appsmith (if they're a developer tool or PLG company)
- 11x (if they're building AI sales/outbound tools)

Address email to: {contact.get('first_name', 'there')}

Output ONLY the JSON. Count to 5 sentences in the body before submitting."""

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.65,
            max_tokens=500,
        )

        raw_text = response.choices[0].message.content.strip()

        # Clean markdown fences if model adds them
        if "```" in raw_text:
            raw_text = raw_text.split("```")[-2] if raw_text.count("```") >= 2 else raw_text
            raw_text = raw_text.replace("json", "", 1).strip()
        raw_text = raw_text.strip()

        # Find JSON object in response (sometimes model adds text before/after)
        start = raw_text.find("{")
        end = raw_text.rfind("}") + 1
        if start >= 0 and end > start:
            raw_text = raw_text[start:end]

        parsed = json.loads(raw_text)
        subject = parsed.get("subject", "").strip()
        body = parsed.get("body", "").strip()

        if not subject or not body:
            raise ValueError("Empty subject or body")

        # Quality check — warn if email seems too long
        sentence_count = body.count(". ") + body.count("? ") + body.count("! ")
        if sentence_count > 7:
            print(f"     [yellow]Note: email for {company.company_name} has ~{sentence_count} sentences (should be 5)[/yellow]")

        return {"subject": subject, "body": body, "model": GROQ_MODEL, "success": True}

    except json.JSONDecodeError as e:
        print(f"     [red]JSON error for {company.company_name}: {e}[/red]")
        print(f"     [dim]Raw: {raw_text[:150] if 'raw_text' in dir() else 'N/A'}[/dim]")
        return _fallback_email(company, contact)

    except Exception as e:
        print(f"     [red]Groq error for {company.company_name}: {type(e).__name__}: {e}[/red]")
        return _fallback_email(company, contact)

    finally:
        # Always sleep after a Groq call — free tier: 30 req/min
        time.sleep(CALL_DELAY)


def _fallback_email(company, contact: dict) -> dict:
    """Fallback if Groq fails — still personalized, just not AI-generated."""
    name = contact.get("first_name", "there")
    company_name = company.company_name
    return {
        "subject": f"{company_name} — quick data question",
        "body": (
            f"{name}, saw {company_name} is building something ambitious in the "
            f"{'AI' if 'ai' in company.description.lower() else 'GTM'} space. "
            f"The pattern we see with teams like yours: Apollo and ZoomInfo data is 6–8 weeks stale "
            f"by the time it reaches your outbound. "
            f"CrustData refreshes company and contact signals hourly via API — "
            f"job changes, funding events, headcount shifts. "
            f"Dharmesh Shah's agent.ai runs their entire data layer on us. "
            f"15 minutes to show you what your ICP looks like in our system?"
            f"\n\n— Abhilash"
        ),
        "model": "fallback",
        "success": False,
    }