#!/usr/bin/env python3
"""Free-tier API scanner + registry builder.

Probes every API endpoint the pipeline uses, records status/latency/credits,
and writes api_registry.json with scan timestamps so the daily pipeline can
check freshness and warn before hitting rate limits.
"""
import json
import os
import time
import requests
from datetime import datetime, timezone
from pathlib import Path

REG_PATH = Path("/home/workspace/Daily_Log/api_registry.json")
CACHE_DIR = Path("/home/workspace/Daily_Log/cache/api_scan")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
REG_PATH.parent.mkdir(parents=True, exist_ok=True)

# Load keys from secrets.env (no value leak — only length)
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

SDI_KEY = _key("SPORTS_DATA_API_KEY")
BDL_KEY = _key("BALLDONTLIE_API_KEY")

NOW = datetime.now(timezone.utc).isoformat()
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

results = {"scanned_at": NOW, "endpoints": [], "summary": {}}

def probe(name, url, params=None, headers=None, timeout=15, key_label=None, free_tier=True):
    """Hit endpoint, return dict with status, latency, info."""
    t0 = time.time()
    entry = {
        "name": name,
        "url": url,
        "key_label": key_label,
        "free_tier": free_tier,
        "scanned_at": NOW,
    }
    try:
        r = requests.get(url, params=params or {}, headers=headers or {}, timeout=timeout)
        latency = round((time.time() - t0) * 1000, 1)
        entry["latency_ms"] = latency
        entry["status_code"] = r.status_code
        entry["ok"] = 200 <= r.status_code < 300
        # Try to extract credit/quota info
        body = r.text[:2000]
        try:
            data = r.json()
            if isinstance(data, dict):
                for k in ("remaining_credits", "remaining", "credits", "quota", "requests_remaining", "quota_remaining"):
                    if k in data:
                        entry[k] = data[k]
                if "message" in data:
                    entry["message"] = str(data["message"])[:200]
        except Exception:
            pass
        if r.status_code == 401:
            entry["auth"] = "missing_or_invalid"
            # Detect quota-exhausted specifically
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

# ── Tier 1: SGO (SportsGameOdds — paid but we already have key) ────────
if SGO_KEY:
    for sport in ["basketball_nba", "basketball_wnba", "baseball_mlb"]:
        ep = probe(
            name=f"SGO events {sport}",
            url="https://api.sportsgameodds.com/v2/events",
            params={"sportID": sport, "x-api-key": SGO_KEY},
            free_tier=False,
        )
        results["endpoints"].append(ep)

# ── Tier 2+3: Odds API (The Odds API — has free tier at 500 req/mo) ──
    for key, label in [("key", "label")]:
        if not key:
            continue
        is_free = "FREE" in label or "BACKUP" in label
        # Check remaining credits (Odds API has /v4/sports endpoint that's cheap)
        # Sports list — v5 root namespace
        ep = probe(
            name=f"Odds API sports list ({label})",
            params={"apiKey": key},
            key_label=label,
            free_tier=is_free,
        )
        results["endpoints"].append(ep)
        # WNBA events — v5 root namespace
        ep2 = probe(
            name=f"Odds API WNBA events ({label})",
            params={"apiKey": key, "sport_key": "basketball_wnba"},
            key_label=label,
            free_tier=is_free,
        )
        results["endpoints"].append(ep2)

# ── Tier 4: ESPN (free, no key needed) ─────────────────────────────────
espn_endpoints = [
    ("ESPN WNBA scoreboard", "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard"),
    ("ESPN WNBA teams", "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/teams"),
    ("ESPN MLB scoreboard", "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"),
    ("ESPN MLB teams", "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/teams"),
    ("ESPN soccer scoreboard", "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"),
    ("ESPN NBA teams", "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams"),
]
for name, url in espn_endpoints:
    ep = probe(name=name, url=url, free_tier=True, key_label=None)
    results["endpoints"].append(ep)

# ── BallDontLie (free tier with key) ──────────────────────────────────
if BDL_KEY:
    ep = probe(
        name="BallDontLie WNBA games",
        url="https://api.balldontlie.io/wnba/v1/games",
        params={"per_page": 5},
        headers={"Authorization": BDL_KEY},
        key_label="BALLDONTLIE_API_KEY",
        free_tier=True,
    )
    results["endpoints"].append(ep)

# ── SportsDataIO (paid, already loaded) ───────────────────────────────
if SDI_KEY:
    ep = probe(
        name="SportsDataIO MLB games",
        url="https://api.sportsdata.io/v3/mlb/scores/json/GamesByDate/2026-06-17",
        headers={"Ocp-Apim-Subscription-Key": SDI_KEY},
        key_label="SPORTS_DATA_API_KEY",
        free_tier=False,
    )
    results["endpoints"].append(ep)

# ── Summary ──────────────────────────────────────────────────────────
total = len(results["endpoints"])
ok = sum(1 for e in results["endpoints"] if e.get("ok"))
failed = [e["name"] for e in results["endpoints"] if not e.get("ok") and not e.get("off_season")]
results["summary"] = {
    "total_endpoints": total,
    "ok": ok,
    "failed": len(failed),
    "failed_names": failed,
    "free_tier_count": sum(1 for e in results["endpoints"] if e.get("free_tier")),
    "keys_loaded": {
        "SPORTS_DATA_API_KEY": bool(SDI_KEY),
        "BALLDONTLIE_API_KEY": bool(BDL_KEY),
    },
}

# Write
REG_PATH.write_text(json.dumps(results, indent=2, default=str))
# Also snapshot by timestamp
(CACHE_DIR / f"scan_{TIMESTAMP}.json").write_text(json.dumps(results, indent=2, default=str))

# Console summary
print(f"Total endpoints: {total}")
print(f"OK: {ok}/{total}")
print(f"Failed: {len(failed)}")
for name in failed:
    print(f"  ✗ {name}")
print(f"\nFree-tier endpoints: {results['summary']['free_tier_count']}")
print(f"Keys loaded: {sum(1 for v in results['summary']['keys_loaded'].values() if v)}/{len(results['summary']['keys_loaded'])}")
print(f"\nRegistry: {REG_PATH}")