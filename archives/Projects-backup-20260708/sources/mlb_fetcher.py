"""MLB player-projection fetcher.

Loads the latest mlb_slate file from /home/workspace/Projects/slates/.
Falls back to /home/workspace/Daily_Log/<today>/slate_MLB.json.
Returns a list of games with player projections, or {'error': ...}.
"""
import os
import json
from pathlib import Path
from datetime import datetime

WORKSPACE = Path("/home/workspace")
SLATES_DIR = WORKSPACE / "Projects" / "slates"
LOG_DIR = WORKSPACE / "Daily_Log"


def _latest_slate_file(prefix: str) -> Path | None:
    """Return the most recent file in slates/ starting with prefix, or None."""
    if not SLATES_DIR.exists():
        return None
    matches = sorted([p for p in SLATES_DIR.iterdir() if p.name.startswith(prefix) and p.suffix == ".json"])
    return matches[-1] if matches else None


def _fallback_slate_file(prefix: str) -> Path | None:
    today = LOG_DIR / datetime.now().strftime("%Y-%m-%d")
    cand = today / f"slate_{prefix}.json"
    if cand.exists():
        return cand
    return None


def get_mlb_projections() -> dict:
    """Load the latest MLB slate and return a list of games with projections.
    Returns: {'games': [...]} on success, {'error': '...'} on failure.
    """
    path = _latest_slate_file("mlb_slate_") or _fallback_slate_file("MLB")
    if not path:
        return {"error": "No MLB slate found", "games": []}
    try:
        data = json.loads(path.read_text())
    except Exception as e:
        return {"error": f"Failed to read {path}: {e}", "games": []}
    if isinstance(data, dict) and "games" in data:
        games = data["games"]
    elif isinstance(data, list):
        games = data
    else:
        return {"error": f"Unexpected slate format in {path}", "games": []}
    return {"games": games, "path": str(path)}
