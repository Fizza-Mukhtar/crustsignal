"""
CrustSignal — FastAPI Backend
Serves the review UI and JSON API.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from src.storage.db import Database

app = FastAPI(title="CrustSignal")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_db = None
def get_db():
    global _db
    if _db is None:
        _db = Database()
        _db.init()
    return _db

@app.get("/")
def serve_ui():
    ui_path = Path(__file__).parent.parent.parent / "ui" / "index.html"
    return FileResponse(str(ui_path))

@app.get("/api/leads")
def api_leads():
    db = get_db()
    leads = db.get_leads(limit=50)
    result = []
    for lead in leads:
        contacts = db.get_contacts(lead["id"])
        signals  = db.get_signals(lead["id"])
        drafts   = db.get_drafts(lead_id=lead["id"])
        result.append({
            **lead,
            "contact": contacts[0] if contacts else None,
            "signals": signals,
            "draft":   drafts[0]   if drafts   else None,
        })
    return JSONResponse(result)

@app.get("/api/stats")
def api_stats():
    return JSONResponse(get_db().get_stats())

@app.post("/api/drafts/{draft_id}/approve")
def api_approve(draft_id: str):
    get_db().approve_draft(draft_id)
    return {"ok": True, "status": "approved"}

@app.post("/api/drafts/{draft_id}/reject")
def api_reject(draft_id: str):
    get_db().reject_draft(draft_id)
    return {"ok": True, "status": "rejected"}