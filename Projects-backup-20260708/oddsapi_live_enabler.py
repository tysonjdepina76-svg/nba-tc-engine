#!/usr/bin/env python3
"""OddsAPI live-mode enabler for July 1 + WNBA/World Cup lines.

Reads quota status & deadline; flips api_fallback to allow OddsAPI when:
  1. ODDS_API_KEY is set
  2. Quota is not exhausted
  3. Quota deadline / configured enable date is reached
"""
import datetime, json, os, sys
from pathlib import Path

QUOTA_FILE = Path("/home/workspace/Daily_Log/cache/quota_exhausted.json")
STATUS_FILE = Path("/home/workspace/Daily_Log/cache/oddsapi_status.json")
ENABLE_DATE = datetime.date(2026, 7, 1)
KEY_NAMES = ("ODDS_API_KEY", "THEODDSAPI")

def _has_key():
    if any(os.environ.get(k) for k in KEY_NAMES):
        return True
    sf = Path("/root/.zo/secrets.env")
    if sf.exists():
        for line in sf.read_text().splitlines():
            for k in KEY_NAMES:
                if line.startswith(f"{k}="):
                    return True
    return False

def status():
    today = datetime.date.today()
    has_key = _has_key()
    quota = {}
    if QUOTA_FILE.exists():
        try:
            quota = json.loads(QUOTA_FILE.read_text())
        except Exception:
            pass
    exhausted = any(v.get("exhausted") for v in quota.values()) if isinstance(quota, dict) else False
    payload = {
        "today": str(today),
        "enable_date": str(ENABLE_DATE),
        "has_key": has_key,
        "quota_exhausted": exhausted,
        "live": has_key and (today >= ENABLE_DATE) and not exhausted,
        "days_until_enable": (ENABLE_DATE - today).days,
        "last_checked": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(json.dumps(payload, indent=2))
    print(f"OddsAPI live enabler: today={today} enable={ENABLE_DATE}")
    print(f"  has_key:           {payload['has_key']}")
    print(f"  quota_exhausted:   {payload['quota_exhausted']}")
    print(f"  days_until_enable: {payload['days_until_enable']}")
    print(f"  live:              {payload['live']}")
    if payload["live"]:
        print("  → WNBA + World Cup lines: ENABLED")
    else:
        print("  → WNBA + World Cup lines: pending enable date")
    return payload

if __name__ == "__main__":
    status()
