"""
Data freshness and validity checks.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict


def _parse_ts(ts: str) -> datetime:
    """Parse ISO timestamp; tolerate Z suffix and naive strings. Always returns aware UTC."""
    if not ts:
        return datetime.fromtimestamp(0, tz=timezone.utc)
    s = ts.replace("Z", "+00:00") if ts.endswith("Z") else ts
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return datetime.fromtimestamp(0, tz=timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def check_data_freshness() -> Dict:
    log_file = Path("/home/workspace/Daily_Log/last_run.json")
    if not log_file.exists():
        return {"status": "warning", "message": "No last_run.json"}
    try:
        data = json.loads(log_file.read_text())
        last_run = _parse_ts(data.get("timestamp", ""))
        hours_ago = (datetime.now(timezone.utc) - last_run).total_seconds() / 3600
        if hours_ago > 24:
            return {"status": "warning", "hours_ago": round(hours_ago, 1), "message": "No run in %s hours" % round(hours_ago, 1)}
        return {"status": "healthy", "hours_ago": round(hours_ago, 1)}
    except Exception as e:
        return {"status": "warning", "message": "Cannot parse last_run.json: %s" % e}


def check_projection_validity() -> Dict:
    report_dir = Path("/home/workspace/reports/daily")
    if not report_dir.exists():
        return {"status": "warning", "message": "No reports/daily directory"}
    json_files = list(report_dir.glob("*.json"))
    if not json_files:
        return {"status": "warning", "message": "No projections found"}
    latest = max(json_files, key=lambda f: f.stat().st_mtime)
    try:
        data = json.loads(latest.read_text())
        if not data:
            return {"status": "warning", "message": "Empty projections file"}
        invalid = [p for p in data if p.get("projected_points", 0) > 60 or p.get("projected_points", 0) < 0]
        if invalid:
            return {"status": "warning", "invalid_count": len(invalid), "message": "%d invalid projections" % len(invalid)}
        return {"status": "healthy", "count": len(data)}
    except Exception as e:
        return {"status": "warning", "message": "Cannot parse projections: %s" % e}
