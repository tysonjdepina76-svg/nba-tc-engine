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

from fastapi import FastAPI, HTTPException
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


@app.get("/quota")
def quota():
    """API call budget status for all tracked services."""
    try:
        from src.monitoring.api_call_budget import report_all
        return report_all()
    except Exception as e:
        return {"error": str(e)}
