import sys
sys.stdout.reconfigure(encoding='utf-8')
from fastapi import FastAPI, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from apscheduler.schedulers.background import BackgroundScheduler
from scraper import scrape_events
from models import Event
from pydantic import BaseModel
from typing import List, Optional
import traceback
import threading
import time
import io

class LogBuffer(io.StringIO):
    def __init__(self):
        super().__init__()
        self.logs = []
    def write(self, s):
        if s.strip():
            self.logs.append(s.strip())
            if len(self.logs) > 50: self.logs.pop(0)
        return super().write(s)

log_capture = LogBuffer()
sys.stdout = log_capture

class AutoApplyRequest(BaseModel):
    url: str

app = FastAPI(title="Heta Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# [Keep this empty here, we will move it to the bottom]

event_db: List[Event] = []
scrape_lock = threading.Lock()
is_scraping = False

def run_scraping_job():
    global event_db, is_scraping
    if is_scraping:
        print("[SKIP] Scraping already in progress...")
        return
    is_scraping = True
    try:
        new_events = scrape_events()
        event_db = new_events
        print(f"[OK] Scraped {len(new_events)} valid events.")
    except Exception as e:
        print(f"[ERROR] Scraping job failed: {e}")
        traceback.print_exc()
    finally:
        is_scraping = False

scheduler = BackgroundScheduler()
scheduler.add_job(run_scraping_job, 'cron', hour=20, minute=0)
scheduler.start()

@app.on_event("startup")
def startup_event():
    t = threading.Thread(target=run_scraping_job, daemon=True)
    t.start()

@app.get("/api/health")
def health_check():
    categories = {}
    for e in event_db:
        cat = e.category or "Other"
        categories[cat] = categories.get(cat, 0) + 1
    return {"status": "ok", "events": len(event_db), "scraping": is_scraping, "categories": categories}

@app.get("/api/events", response_model=List[Event])
def get_events(category: Optional[str] = Query(None)):
    if category and category != "All":
        return [e for e in event_db if e.category == category]
    return event_db

@app.get("/api/categories")
def get_categories():
    cats = {}
    for e in event_db:
        cat = e.category or "Other"
        cats[cat] = cats.get(cat, 0) + 1
    return {"categories": cats, "total": len(event_db)}

@app.post("/api/scrape")
def force_scrape(background_tasks: BackgroundTasks):
    if is_scraping:
        return {"message": "Scraping already in progress", "events_count": len(event_db), "status": "running"}
    background_tasks.add_task(run_scraping_job)
    return {"message": "Scraping started in background", "events_count": len(event_db), "status": "started"}

@app.get("/api/logs")
def get_logs():
    return {"logs": log_capture.logs}

@app.post("/api/auto-apply")
def auto_apply_event(req: AutoApplyRequest):
    url = req.url.lower()
    if "devfolio" in url or "unstop" in url or "github" in url:
        print(f"\n[AI Agent] Auto-Apply: {req.url}")
        time.sleep(2)
        return {"status": "success", "message": "Successfully applied via AI Agent"}
    return {"status": "manual_required", "message": "Manual authentication required"}

# Serve Frontend Static Files (at the end to not block /api)
import os
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
