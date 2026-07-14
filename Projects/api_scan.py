#!/usr/bin/env python3
import json, os, time, requests
from datetime import datetime, timezone
from pathlib import Path

REG_PATH = Path("/home/workspace/Daily_Log/api_registry.json")
CACHE_DIR = Path("/home/workspace/Daily_Log/cache/api_scan")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def _key(name):
    val = os.environ.get(name, "").strip()
    if not val:
        sf = Path("/root/.zo/secrets.env")
        if sf.exists():
            for line in sf.read_text().splitlines():
                line = line.strip()
                if line.startswith(name + "="):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
    return val

SGO_KEY = _key("SPORTSGAMEODDS_API_KEY") or _key("SGO_API_KEY")
ODDS_KEY = _key("ODDS_API_KEY")
SDI_KEY = _key("SPORTS_DATA_API_KEY")
BDL_KEY = _key("BALLDONTLIE_API_KEY")
ODDS_BASE = "https://api.theoddsapi.com"

NOW = datetime.now(timezone.utc).isoformat()
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
results = {"scanned_at": NOW, "endpoints": [], "summary": {}}

def probe(name, url, params=None, headers=None, timeout=15, key_label=None, free_tier=True):
    t0 = time.time()
    entry = {"name": name, "url": url, "key_label": key_label, "free_tier": free_tier, "scanned_at": NOW}
    try:
        r = requests.get(url, params=params or {}, headers=headers or {}, timeout=timeout)
        entry["latency_ms"] = round((time.time() - t0) * 1000, 1)
        entry["status_code"] = r.status_code
        entry["ok"] = 200 <= r.status_code < 300
        body = r.text[:2000]
        try:
            data = r.json()
            if isinstance(data, dict):
                for k in ("remaining_credits", "remaining", "credits", "quota", "requests_remaining"):
                    if k in data:
                        entry[k] = data[k]
                if "message" in data:
                    entry["message"] = str(data["message"])[:200]
        except:
            pass
        if r.status_code == 401:
            entry["auth"] = "missing_or_invalid"
            if "OUT_OF_USAGE_CREDITS" in body or "QUOTA" in body.upper():
                entry["quota_exhausted"] = True
        elif r.status_code == 429:
            entry["rate_limited"] = True
        elif r.status_code == 503:
            entry["off_season"] = True
        return entry
    except requests.exceptions.Timeout:
        entry["error"] = "timeout"
        entry["latency_ms"] = round((time.time() - t0) * 1000, 1)
        return entry
    except Exception as e:
        entry["error"] = str(e)[:200]
        entry["latency_ms"] = round((time.time() - t0) * 1000, 1)
        return entry

# ── Tier 1: Odds API (game lines for WNBA + MLB) ──
if ODDS_KEY:
    results["endpoints"].append(probe("Odds sports", f"{ODDS_BASE}/sports/", {"apiKey": ODDS_KEY}, key_label="ODDS_API_KEY"))
    results["endpoints"].append(probe("Odds WNBA odds", f"{ODDS_BASE}/odds/", {"sport_key": "basketball_wnba", "regions": "us", "apiKey": ODDS_KEY}, key_label="ODDS_API_KEY"))
    results["endpoints"].append(probe("Odds MLB odds", f"{ODDS_BASE}/odds/", {"sport_key": "baseball_mlb", "regions": "us", "apiKey": ODDS_KEY}, key_label="ODDS_API_KEY"))

# ── Tier 2: SGO (limited) ──
if SGO_KEY:
    for s in ["basketball_wnba"]:
        results["endpoints"].append(probe(f"SGO {s}", "https://api.sportsgameodds.com/v2/events",
            {"sportID": s, "limit": "100"},
            headers={"X-Api-Key": SGO_KEY}, free_tier=False))

# ── Tier 3: ESPN (free, rosters + embedded DK) ──
for name, url in [
    ("ESPN WNBA sb", "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard"),
    ("ESPN MLB sb", "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"),
    ("ESPN WC sb", "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"),
]:
    results["endpoints"].append(probe(name, url))

# ── Tier 4: SportsDataIO ──
if SDI_KEY:
    results["endpoints"].append(probe("SDIO MLB props", f"https://api.sportsdata.io/v3/mlb/odds/json/PlayerPropsByDate/2026-06-22", headers={"Ocp-Apim-Subscription-Key": SDI_KEY}, free_tier=False))

# ── Summary
total = len(results["endpoints"])
ok = sum(1 for e in results["endpoints"] if e.get("ok"))
failed = [e["name"] for e in results["endpoints"] if not e.get("ok")]
results["summary"] = {"total": total, "ok": ok, "failed": len(failed), "failed_names": failed}

REG_PATH.write_text(json.dumps(results, indent=2, default=str))
(CACHE_DIR / f"scan_{TIMESTAMP}.json").write_text(json.dumps(results, indent=2, default=str))

for e in results["endpoints"]:
    icon = "✓" if e.get("ok") else "✗"
    print(f"  {icon} {e['name']}: {e.get('status_code', e.get('error','?'))} ({e.get('latency_ms',0)}ms)")
print(f"\nRegistry: {REG_PATH}")