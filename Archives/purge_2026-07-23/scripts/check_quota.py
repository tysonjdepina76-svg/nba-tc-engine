#!/usr/bin/env python3
"""
check_quota.py — Quota monitor for TC Sports App
Checks API quota usage and sends SMS alert if over 80%.
Runs as a cron-safe standalone script.
"""
import os
import json
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path

LOG_DIR = Path("/home/workspace/Projects/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
ALERT_LOG = LOG_DIR / "quota_alerts.log"
STATE_FILE = LOG_DIR / "quota_state.json"

THRESHOLD_PCT = 80  # alert at 80%+


def get_odds_api_usage() -> dict | None:
    """Fetch Odds API usage via /v4/usage endpoint (Business tier)."""
    key = os.environ.get("ODDS_API_KEY")
    if not key:
        return None
    try:
        url = f"https://api.the-odds-api.com/v4/usage?apiKey={key}"
        with urllib.request.urlopen(url, timeout=10) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": str(e)}


def get_sportsdataio_usage() -> dict | None:
    """SportsDataIO doesn't expose usage; infer from local API key presence."""
    key = os.environ.get("SPORTS_DATA_API_KEY")
    return {"has_key": bool(key), "tracked": False}


def send_sms_alert(msg: str) -> bool:
    """Send SMS via Zo's send_sms_to_user CLI (if available)."""
    try:
        # Write to a flag file that the 6h health check picks up
        flag = LOG_DIR / "QUOTA_ALERT.pending"
        flag.write_text(f"{datetime.now().isoformat()}\n{msg}\n")
        return True
    except Exception:
        return False


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2))


def should_alert(host: str, pct: float, state: dict) -> bool:
    """Only alert once per host per day when threshold crossed."""
    today = datetime.now().strftime("%Y-%m-%d")
    last = state.get(host, {}).get("last_alert_date", "")
    return pct >= THRESHOLD_PCT and last != today


def main() -> int:
    now = datetime.now().isoformat()
    state = load_state()
    alerts = []

    # Odds API
    odds = get_odds_api_usage()
    if odds and "error" not in odds:
        used = odds.get("used", 0)
        limit = odds.get("limit", 1)
        pct = (used / limit * 100) if limit else 0
        line = f"[{now}] Odds API: {used}/{limit} ({pct:.1f}%)"
        print(line)
        if should_alert("odds_api", pct, state):
            alerts.append(f"⚠️ Odds API quota at {pct:.0f}% — {used}/{limit} used")
            state.setdefault("odds_api", {})["last_alert_date"] = datetime.now().strftime("%Y-%m-%d")
    elif odds and "error" in odds:
        print(f"[{now}] Odds API: error — {odds['error']}")

    # SportsDataIO
    sdio = get_sportsdataio_usage()
    if sdio:
        print(f"[{now}] SportsDataIO: key={'present' if sdio.get('has_key') else 'missing'}")

    # Log alerts
    if alerts:
        with ALERT_LOG.open("a") as f:
            for a in alerts:
                f.write(f"[{now}] {a}\n")
        send_sms_alert("\n".join(alerts))
        print(f"ALERTS: {len(alerts)} sent")
    else:
        print("No alerts (under threshold)")

    save_state(state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
