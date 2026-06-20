"""
CrustSignal — Main Entry Point
================================
Run this to execute the full pipeline.

Usage:
    python run_pipeline.py              # mock mode (reads USE_MOCK from .env)
    python run_pipeline.py --live       # force real API (uses credits!)
    python run_pipeline.py --mock       # force mock mode (no credits)
"""

import sys
import os
import logging
from dotenv import load_dotenv

load_dotenv()

# CLI flags override .env
if "--live" in sys.argv:
    os.environ["USE_MOCK"] = "false"
elif "--mock" in sys.argv:
    os.environ["USE_MOCK"] = "true"

# Setup logging — only write to file (Rich handles terminal output)
# FileHandler uses utf-8 to avoid Windows CP1252 emoji crash
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler("pipeline.log", encoding="utf-8"),
    ],
)

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.storage.db import Database
from src.pipeline.orchestrator import run_pipeline

USE_MOCK = os.getenv("USE_MOCK", "true").lower() == "true"

if __name__ == "__main__":
    # Init DB
    db = Database()
    db.init()

    # Init API client (only needed in live mode)
    client = None
    if not USE_MOCK:
        from src.crustdata.client import CrustDataClient
        client = CrustDataClient()
        if not client.ping():
            print("❌ CrustData API ping failed. Check your key. Exiting.")
            sys.exit(1)

    # Run pipeline
    stats = run_pipeline(db, client)

    db.close()