"""
Circuit breaker and gate status checks.
"""

import json
from pathlib import Path
from typing import Dict, List


def check_circuit_breakers() -> Dict:
    breaker_dir = Path("/tmp/circuit_breakers")
    if not breaker_dir.exists():
        return {"status": "healthy", "open": []}
    open_breakers: List[str] = []
    for file in breaker_dir.glob("*.json"):
        try:
            data = json.loads(file.read_text())
            if data.get("state") == "open":
                open_breakers.append(file.stem)
        except Exception:
            pass
    if open_breakers:
        return {"status": "warning", "open": open_breakers, "message": "%d breakers open" % len(open_breakers)}
    return {"status": "healthy", "open": []}


def check_alert_deduper() -> Dict:
    try:
        from src.alert_deduper import get_deduper
        deduper = get_deduper()
        stats = deduper.get_stats() if hasattr(deduper, "get_stats") else {"ok": True}
        return {"status": "healthy", "stats": stats}
    except Exception as e:
        return {"status": "warning", "message": "Cannot load deduper: %s" % e}
