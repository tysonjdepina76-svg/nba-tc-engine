"""FastAPI app for the TC Sports pipeline.

Endpoints:
- GET /projections/{sport}  — TC projections for a sport
- GET /health                — pipeline health check
- GET /quota                 — API call budget status

Run:  uvicorn src.api.app:app --port 8510
"""
from __future__ import annotations

from pathlib import Path
import sys
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# Make repo importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.domain.projection_service import ProjectionService  # noqa: E402

app = FastAPI(title="TC Sports API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Single service instance
_service = ProjectionService()


@app.get("/")
def root():
    return {
        "service": "TC Sports API",
        "version": "1.0.0",
        "endpoints": ["/projections/{sport}", "/health", "/quota"],
    }


@app.get("/projections/{sport}")
def get_projections(sport: str):
    """Get TC projections for a sport (WNBA, NFL, MLB, NBA, NHL, SOCCER)."""
    sport = sport.upper()
    out = _service.get_projections(sport)
    if out.get("source") == "invalid":
        raise HTTPException(status_code=400, detail=out.get("errors", ["Invalid sport"])[0])
    return out


@app.get("/health")
def health():
    """Pipeline health check."""
    out = {}
    for s in ("WNBA", "NFL", "MLB", "NBA", "NHL", "SOCCER"):
        try:
            r = _service.get_projections(s)
            out[s] = {"source": r.get("source"), "count": r.get("count")}
        except Exception as e:
            out[s] = {"error": str(e)}
    return {"ok": True, "sports": out}


@app.get("/api/picks")
def get_picks(date: str, sport: Optional[str] = None):
    """Return picks from Daily_Log for a given date and optional sport.

    Reads /home/workspace/Daily_Log/{date}/picks.json (a flat list of pick dicts
    with a 'league' field). If sport is provided, filters by league.
    """
    import json

    base = Path("/home/workspace/Daily_Log") / date
    picks_file = base / "picks.json"

    if not picks_file.exists():
        return {"error": f"No data for {date}", "date": date, "count": 0, "picks": []}

    try:
        with open(picks_file) as f:
            picks = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read picks: {e}")

    if not isinstance(picks, list):
        raise HTTPException(status_code=500, detail="picks.json is not a list")

    sport_norm = sport.upper() if sport else None
    if sport_norm:
        picks = [p for p in picks if str(p.get("league", "")).upper() == sport_norm]

    return {"date": date, "sport": sport_norm, "count": len(picks), "picks": picks}


@app.get("/quota")
def quota():
    """API call budget status for all tracked services."""
    try:
        from src.monitoring.api_call_budget import report_all
        return report_all()
    except Exception as e:
        return {"error": str(e)}
