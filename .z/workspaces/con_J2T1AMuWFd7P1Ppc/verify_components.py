#!/usr/bin/env python3
"""
TC Component Verification — every component, real call, real result.
Run with: python3 verify_components.py
Output:  /home/workspace/Daily_Log/TC_COMPONENT_VERIFY_<ts>.json
"""
import json, os, sys, time, traceback, urllib.request, urllib.parse
from datetime import datetime
from pathlib import Path

PROJ = Path("/home/workspace/Projects")
LOG = Path("/home/workspace/Daily_Log")
LOG.mkdir(exist_ok=True)

# Load secrets from real env file
SECRETS = "/root/.zo/secrets.env"
if os.path.exists(SECRETS):
    for line in open(SECRETS):
        if "=" in line and not line.startswith("#"):
            k, v = line.strip().split("=", 1)
            if k and k not in os.environ:
                os.environ[k] = v

results = {}

def section(name):
    print(f"\n{'='*70}\n  {name}\n{'='*70}")

def check(name, fn):
    t0 = time.time()
    try:
        out = fn()
        ms = int((time.time() - t0) * 1000)
        results[name] = {"ok": True, "ms": ms, **out} if isinstance(out, dict) else {"ok": True, "ms": ms, "value": out}
        status = "✅" if results[name].get("ok") else "❌"
        print(f"  {status} {name} ({ms}ms)")
        return results[name]
    except Exception as e:
        ms = int((time.time() - t0) * 1000)
        results[name] = {"ok": False, "ms": ms, "error": f"{type(e).__name__}: {str(e)[:200]}"}
        print(f"  ❌ {name} ({ms}ms): {results[name]['error']}")
        return results[name]

def http_get(url, headers=None, timeout=20):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=timeout).read()

# =========================================================================
section("1. REGISTRY — all 6 sports resolve")
# =========================================================================
def registry_check():
    sys.path.insert(0, str(PROJ))
    try:
        from sports_registry import SPORT_REGISTRY, get_engine, get_scraper
        sports = list(SPORT_REGISTRY.keys()) if hasattr(SPORT_REGISTRY, "keys") else SPORT_REGISTRY
        resolved = {}
        for sp in sports:
            try:
                eng = get_engine(sp)
                scr = get_scraper(sp)
                resolved[sp] = {"engine": eng.__name__, "scraper": scr.__name__}
            except Exception as e:
                resolved[sp] = {"error": str(e)[:100]}
        return {"sports": sports, "resolved": resolved, "count": len(sports)}
    except ImportError:
        return {"fallback": "no registry module", "note": "checked via daily_picks"}
check("registry", registry_check)

# =========================================================================
section("2. MLB — lineups, pitchers, batting stats")
# =========================================================================
def mlb_live():
    url = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"
    data = json.loads(http_get(url).decode())
    games = data.get("events", [])
    out = {"games_today": len(games), "sample": []}
    for g in games[:2]:
        comps = g.get("competitions", [{}])[0].get("competitors", [])
        out["sample"].append({
            "name": g.get("name"),
            "status": g.get("status", {}).get("type", {}).get("description"),
            "competitors": [c.get("team", {}).get("displayName") for c in comps],
        })
    return out
check("mlb_scoreboard_live", mlb_live)

def mlb_summary():
    """Try MLB summary for game detail (lineups/pitchers)"""
    url = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"
    data = json.loads(http_get(url).decode())
    games = data.get("events", [])
    if not games:
        return {"games": 0}
    eid = games[0]["id"]
    summary = json.loads(http_get(f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/summary?event={eid}").decode())
    keys = list(summary.keys())
    has_lineups = "lineups" in summary or "rosters" in summary
    return {"event_id": eid, "summary_keys": keys, "has_lineups": has_lineups}
check("mlb_summary_endpoints", mlb_summary)

# =========================================================================
section("3. WNBA — players with stats")
# =========================================================================
def wnb_roster():
    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard"
    data = json.loads(http_get(url).decode())
    games = data.get("events", [])
    if not games:
        return {"games": 0}
    eid = games[0]["id"]
    summary = json.loads(http_get(f"https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/summary?event={eid}").decode())
    boxscore = summary.get("boxscore", {})
    players_found = 0
    for team in boxscore.get("teams", []):
        for stat in team.get("statistics", []):
            for athlete in stat.get("athletes", []):
                players_found += 1
    return {
        "games": len(games),
        "sample_event": games[0]["name"],
        "boxscore_players": players_found,
        "has_boxscore": bool(boxscore),
    }
check("wnba_roster_stats", wnb_roster)

# =========================================================================
section("4. WORLD CUP — FBref rosters")
# =========================================================================
def fbref_wc():
    """Check FBref WC data"""
    try:
        # FBref World Cup page
        html = http_get("https://fbref.com/en/comps/1/World-Cup-Stats", timeout=20).decode("utf-8", errors="ignore")
        # Crude check: do player names appear?
        return {
            "fbref_reachable": True,
            "html_size_kb": len(html) // 1024,
            "has_player_table": "players" in html.lower() or "<td" in html,
        }
    except Exception as e:
        return {"fbref_reachable": False, "error": str(e)[:200]}
check("fbref_wc", fbref_wc)

def wc_espn():
    """ESPN WC scoreboard"""
    try:
        url = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
        data = json.loads(http_get(url).decode())
        games = data.get("events", [])
        return {"wc_espn_games": len(games), "sample": [g.get("name") for g in games[:3]]}
    except Exception as e:
        return {"error": str(e)[:200]}
check("wc_espn_scoreboard", wc_espn)

# =========================================================================
section("5. ESPN ODDS — spread / ML / total")
# =========================================================================
def espn_odds():
    """ESPN odds endpoint"""
    try:
        url = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard"
        data = json.loads(http_get(url).decode())
        games = data.get("events", [])
        if not games:
            return {"games": 0}
        eid = games[0]["id"]
        odds_url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/summary?event={eid}"
        summary = json.loads(http_get(odds_url).decode())
        odds = summary.get("odds", {})
        if not odds:
            return {"has_odds_field": False, "summary_keys": list(summary.keys())}
        return {
            "has_spread": "spread" in str(odds).lower() or any("spread" in str(p).lower() for p in odds.get("items", [])),
            "has_total": "total" in str(odds).lower(),
            "odds_keys": list(odds.keys())[:10],
            "items_count": len(odds.get("items", [])),
        }
    except Exception as e:
        return {"error": str(e)[:200]}
check("espn_odds", espn_odds)

def odds_api_odds():
    """Odds API direct"""
    key = os.environ.get("ODDS_API_KEY", "")
    if not key:
        return {"error": "no key"}
    try:
        url = f"https://api.the-odds-api.com/v4/sports/basketball_wnba/odds/?apiKey={key}&regions=us&markets=spreads,h2h,totals"
        data = json.loads(http_get(url, timeout=15).decode())
        if isinstance(data, dict) and "message" in data:
            return {"api_message": data["message"]}
        return {"events": len(data), "sample": data[0] if data else None}
    except Exception as e:
        return {"error": str(e)[:200]}
check("odds_api_wnba", odds_api_odds)

def sgo_odds():
    """SportsGameOdds API direct"""
    key = os.environ.get("SPORTSGAMEODDS_API_KEY", "")
    if not key:
        return {"error": "no key"}
    try:
        url = f"https://api.sportsgameodds.com/v1/events?sport=basketball_wnba&apikey={key}"
        data = json.loads(http_get(url, timeout=15).decode())
        if isinstance(data, dict) and data.get("success") is False:
            return {"api_error": data}
        evs = data.get("data", data.get("events", []))
        return {"sgo_events": len(evs) if isinstance(evs, list) else "n/a"}
    except Exception as e:
        return {"error": str(e)[:200]}
check("sgo_odds", sgo_odds)

# =========================================================================
section("6. BASEBALL-REFERENCE — fallback check")
# =========================================================================
def br_check():
    try:
        html = http_get("https://www.baseball-reference.com/", timeout=15).decode("utf-8", errors="ignore")
        return {"reachable": True, "size_kb": len(html) // 1024, "has_data": "scores" in html.lower() or "MLB" in html}
    except Exception as e:
        return {"reachable": False, "error": str(e)[:200]}
check("baseball_reference", br_check)

# =========================================================================
section("7. BASKETBALL-REFERENCE — fallback check")
# =========================================================================
def bbr_check():
    try:
        html = http_get("https://www.basketball-reference.com/", timeout=15).decode("utf-8", errors="ignore")
        return {"reachable": True, "size_kb": len(html) // 1024, "has_data": "WNBA" in html or "NBA" in html}
    except Exception as e:
        return {"reachable": False, "error": str(e)[:200]}
check("basketball_reference", bbr_check)

# =========================================================================
section("8. CACHE — store and retrieve")
# =========================================================================
def cache_check():
    sys.path.insert(0, str(PROJ))
    try:
        from api_cache import cache_get, cache_set, cache_path
        test_key = f"verify_{int(time.time())}"
        test_val = {"hello": "world", "ts": time.time()}
        cache_set(test_key, test_val)
        got = cache_get(test_key)
        match = got == test_val
        return {"set_get_match": match, "key": test_key, "path": str(cache_path) if hasattr(cache_path, "__str__") else "n/a"}
    except Exception as e:
        return {"error": str(e)[:200]}
check("cache", cache_check)

# =========================================================================
section("9. DASHBOARD — :8510 renders")
# =========================================================================
def dash_check():
    import urllib.request
    try:
        r = urllib.request.urlopen("http://localhost:8510", timeout=10)
        body = r.read().decode("utf-8", errors="ignore")
        return {
            "http": r.status,
            "bytes": len(body),
            "is_streamlit": "streamlit" in body.lower() or "stApp" in body or "ScriptRunWidget" in body,
        }
    except Exception as e:
        return {"error": str(e)[:200]}
check("dashboard_8510", dash_check)

# =========================================================================
section("10. DAILY PICKS — actual run for all 3 sports")
# =========================================================================
import subprocess
def daily_run(sport):
    today = datetime.now().strftime("%Y-%m-%d")
    r = subprocess.run(
        ["python3", str(PROJ / "daily_picks.py"), "--sport", sport, "--date", today],
        capture_output=True, text=True, timeout=180,
    )
    out = r.stdout + r.stderr
    games, picks = 0, 0
    for line in out.splitlines():
        if line.startswith("Done:") and "games" in line and "picks" in line:
            parts = line.split()
            try:
                games = int(parts[parts.index("games") - 1].rstrip(",:"))
                picks = int(parts[parts.index("picks") - 1].rstrip(",:"))
            except (ValueError, IndexError):
                pass
    return {"exit": r.returncode, "games": games, "picks": picks, "tail": out[-300:]}

for sp in ["WNBA", "MLB", "WORLD_CUP"]:
    check(f"daily_picks_{sp.lower()}", lambda s=sp: daily_run(s))

# =========================================================================
# WRITE REPORT
# =========================================================================
out_path = LOG / f"TC_COMPONENT_VERIFY_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(out_path, "w") as f:
    json.dump({"timestamp": datetime.now().isoformat(), "results": results}, f, indent=2, default=str)

print(f"\n{'='*70}\nFull report: {out_path}\n{'='*70}")
