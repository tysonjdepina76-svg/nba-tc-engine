#!/usr/bin/env python3
"""Backfill ESPN final boxscores for WNBA, MLB, World Cup for specified dates."""
import json, requests, sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path("/home/workspace")
FIN_DIR = WORKSPACE / "Daily_Log" / "final"
WC_DIR = WORKSPACE / "Daily_Log" / "wc_boxscores"
MLB_DIR = WORKSPACE / "Daily_Log" / "mlb_boxscores"
REG_PATH = WORKSPACE / "Daily_Log" / "boxscore_registry.json"

for d in [FIN_DIR, WC_DIR, MLB_DIR]:
    d.mkdir(parents=True, exist_ok=True)

def _loadreg():
    try: return json.loads(REG_PATH.read_text()) if REG_PATH.exists() else {}
    except: return {}
def _savereg(r):
    REG_PATH.write_text(json.dumps(r, indent=2))
def already_saved(eid, boxtype, out_dir):
    key = f"{eid}:{boxtype}"
    reg = _loadreg()
    if key in reg:
        return True
    for f in out_dir.glob(f"*{eid}*.json"):
        reg[key] = str(f.stat().st_mtime)
        _savereg(reg)
        return True
    return False
def mark_saved(eid, boxtype, info=""):
    reg = _loadreg()
    reg[f"{eid}:{boxtype}"] = info or datetime.now(timezone.utc).isoformat()
    _savereg(reg)

def _int(v, d=0):
    try: return int(str(v).replace(",",""))
    except: return d

# ─── WNBA capture ────────────────────────────────────────
def capture_wnba(eid, dstr):
    if already_saved(eid, "final", FIN_DIR):
        print(f"  WNBA [{eid}] already saved")
        return
    r = requests.get(
        "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/summary",
        params={"event": eid}, timeout=20)
    if r.status_code != 200:
        print(f"  WNBA [{eid}] — HTTP {r.status_code}")
        return
    s = r.json()
    comp = (s.get("header") or {}).get("competitions", [{}])[0]
    cs = comp.get("competitors", [])
    teams = {}
    for c in cs:
        teams[c.get("homeAway","")] = c.get("team",{}).get("displayName","?")
    
    players = {}
    for grp in (s.get("boxscore") or {}).get("players", []):
        tn = grp.get("team",{}).get("displayName","?")
        for sbh in grp.get("statistics", []):
            keys = sbh.get("keys", [])
            for ath in sbh.get("athletes", []):
                nm = ath.get("athlete",{}).get("displayName","?")
                if not nm or nm == "?":
                    continue
                raw = ath.get("stats", [])
                row = {"name": nm, "team": tn}
                def _g(field, idx_key):
                    if idx_key in keys and keys.index(idx_key) < len(raw):
                        row[field] = _int(raw[keys.index(idx_key)])
                _g("pts", "points")
                _g("reb", "rebounds")
                _g("ast", "assists")
                _g("stl", "steals")
                _g("blk", "blocks")
                _g("to", "turnovers")
                _g("pf", "fouls")
                t3k = "threePointFieldGoalsMade-threePointFieldGoalsAttempted"
                if t3k in keys and keys.index(t3k) < len(raw):
                    v = str(raw[keys.index(t3k)])
                    row["fg3m"] = _int(v.split("-")[0]) if "-" in v else _int(v)
                if "minutes" in keys and keys.index("minutes") < len(raw):
                    row["minutes"] = str(raw[keys.index("minutes")])
                players[nm] = row
    
    if not players:
        print(f"  WNBA [{eid}] — no player data")
        return
    
    away = teams.get("away","?")
    home = teams.get("home","?")
    away_score = _int(next((c.get("score") for c in cs if c.get("homeAway")=="away"), 0))
    home_score = _int(next((c.get("score") for c in cs if c.get("homeAway")=="home"), 0))
    
    box = {
        "event_id": eid, "sport": "wnba", "date": dstr,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "type": "final", "players": players,
        "score": {"away": away_score, "home": home_score},
        "away_team": away, "home_team": home
    }
    safe = f"{away}_at_{home}".replace(" ","")
    fn = f"wnba_{safe}_final_{eid}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    (FIN_DIR / fn).write_text(json.dumps(box, indent=2))
    mark_saved(eid, "final", f"{away} {away_score}-{home_score} {home}")
    print(f"  WNBA [{eid}] ✅ {away} {away_score}-{home_score} {home} ({len(players)} players)")

# ─── MLB capture ──────────────────────────────────────────
def capture_mlb(eid, dstr):
    if already_saved(eid, "final", MLB_DIR):
        print(f"  MLB [{eid}] already saved")
        return
    r = requests.get(
        "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/summary",
        params={"event": eid}, timeout=20)
    if r.status_code != 200:
        print(f"  MLB [{eid}] — HTTP {r.status_code}")
        return
    s = r.json()
    comp = (s.get("header") or {}).get("competitions", [{}])[0]
    cs = comp.get("competitors", [])
    teams = {}
    for c in cs:
        teams[c.get("homeAway","")] = c.get("team",{}).get("displayName","?")
    
    batting = {}
    pitching = {}
    for grp in (s.get("boxscore") or {}).get("players", []):
        tn = grp.get("team",{}).get("displayName","?")
        for sbh in grp.get("statistics", []):
            keys = sbh.get("keys", [])
            if not keys:
                continue
            is_pitching = "ERA" in keys or "fullInnings" in str(keys[0])
            target = pitching if is_pitching else batting
            for ath in sbh.get("athletes", []):
                nm = ath.get("athlete",{}).get("displayName","?")
                if not nm or nm == "?":
                    continue
                raw = ath.get("stats", [])
                row = {"name": nm, "team": tn}
                if is_pitching:
                    def _gp(field, idx_key):
                        if idx_key in keys and keys.index(idx_key) < len(raw):
                            row[field] = str(raw[keys.index(idx_key)])
                    _gp("ip", "fullInnings.partInnings")
                    _gp("h", "hits")
                    _gp("r", "runs")
                    _gp("er", "earnedRuns")
                    _gp("bb", "walks")
                    _gp("so", "strikeouts")
                    _gp("hr", "homeRuns")
                    _gp("era", "ERA")
                    _gp("pitches", "pitches")
                else:
                    def _gb(field, idx_key):
                        if idx_key in keys and keys.index(idx_key) < len(raw):
                            row[field] = str(raw[keys.index(idx_key)])
                    _gb("ab", "atBats")
                    _gb("r", "runs")
                    _gb("h", "hits")
                    _gb("rbi", "RBIs")
                    _gb("hr", "homeRuns")
                    _gb("bb", "walks")
                    _gb("so", "strikeouts")
                    _gb("avg", "avg")
                target[nm] = row
    
    away = teams.get("away","?")
    home = teams.get("home","?")
    away_score = _int(next((c.get("score") for c in cs if c.get("homeAway")=="away"), 0))
    home_score = _int(next((c.get("score") for c in cs if c.get("homeAway")=="home"), 0))
    
    box = {
        "event_id": eid, "sport": "mlb", "date": dstr,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "type": "final",
        "batting": batting, "pitching": pitching,
        "score": {"away": away_score, "home": home_score},
        "away_team": away, "home_team": home
    }
    safe = f"{away}_at_{home}".replace(" ","")
    fn = f"mlb_{safe}_final_{eid}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    (MLB_DIR / fn).write_text(json.dumps(box, indent=2))
    mark_saved(eid, "final", f"{away} {away_score}-{home_score} {home}")
    print(f"  MLB [{eid}] ✅ {away} {away_score}-{home_score} {home} ({len(batting)} batters, {len(pitching)} pitchers)")

# ─── World Cup capture ─────────────────────────────────────
def capture_wc(eid, dstr):
    if already_saved(eid, "final", WC_DIR):
        print(f"  WC [{eid}] already saved")
        return
    
    # Use the soccer_boxscore_capture.py logic inline
    WC_SPATH = "soccer/fifa.world"
    # Get summary
    r = requests.get(
        f"https://site.api.espn.com/apis/site/v2/sports/{WC_SPATH}/summary",
        params={"event": eid}, timeout=20)
    if r.status_code != 200:
        print(f"  WC [{eid}] — HTTP {r.status_code}")
        return
    summary = r.json()
    
    header = summary.get("header", {})
    comp = (header.get("competitions") or [{}])[0]
    cs = comp.get("competitors", [])
    away_name = cs[0].get("team",{}).get("displayName","?") if len(cs)>0 else "?"
    home_name = cs[1].get("team",{}).get("displayName","?") if len(cs)>1 else "?"
    away_abbr = cs[0].get("team",{}).get("abbreviation","?") if len(cs)>0 else "?"
    home_abbr = cs[1].get("team",{}).get("abbreviation","?") if len(cs)>1 else "?"
    
    # Get plays for stats (just page 1 for now, full capture if needed)
    plays_url = f"https://sports.core.api.espn.com/v2/sports/soccer/leagues/fifa.world/events/{eid}/competitions/{eid}/plays"
    plays_r = requests.get(plays_url, params={"limit": 500}, timeout=20)
    all_plays = []
    if plays_r.status_code == 200:
        data = plays_r.json()
        all_plays = data.get("items", [])
        for page in range(2, data.get("pageCount", 1)+1):
            pr = requests.get(plays_url, params={"limit": 500, "page": page}, timeout=20)
            if pr.status_code == 200:
                all_plays.extend(pr.json().get("items", []))
    
    # Parse goals from plays
    players = defaultdict(lambda: {"goals": 0, "assists": 0})
    for play in all_plays:
        ptype = play.get("type",{}).get("text","")
        text = play.get("text","")
        if ptype in ("Goal", "Goal - Header") and " (" in text:
            name = text.split(" (")[0].strip().split(". ")[-1].strip()
            if name:
                players[name]["goals"] += 1
        if ptype == "Assist" and " (" in text:
            name = text.split(" (")[0].strip()
            if name:
                players[name]["assists"] += 1
    
    final_score = {"away": 0, "home": 0}
    if all_plays:
        last = all_plays[-1]
        final_score = {"away": last.get("awayScore",0) or 0, "home": last.get("homeScore",0) or 0}
    
    box = {
        "event_id": eid, "sport": "world_cup", "date": dstr,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "away": {"team": away_name, "abbr": away_abbr, "score": final_score["away"]},
        "home": {"team": home_name, "abbr": home_abbr, "score": final_score["home"]},
        "players": dict(players),
        "total_plays": len(all_plays)
    }
    safe = f"{away_abbr}_at_{home_abbr}".replace(" ","_")
    fn = f"wc_{safe}_{eid}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    (WC_DIR / fn).write_text(json.dumps(box, indent=2, ensure_ascii=False))
    mark_saved(eid, "final", f"{away_abbr} {final_score['away']}-{final_score['home']} {home_abbr}")
    print(f"  WC [{eid}] ✅ {away_abbr} {final_score['away']}-{final_score['home']} {home_abbr} ({len(players)} scorers)")

# ─── Scan dates ────────────────────────────────────────────
SPORTS_CONFIG = {
    "WNBA": ("basketball/wnba", capture_wnba),
    "MLB": ("baseball/mlb", capture_mlb),
    "WC": ("soccer/fifa.world", capture_wc),
}

DATES = ["20260614", "20260615", "20260616", "20260617"]

for dstr in DATES:
    print(f"\n{'='*50}")
    print(f"📅 {dstr}")
    for sport, (spath, capture_fn) in SPORTS_CONFIG.items():
        try:
            r = requests.get(
                f"https://site.api.espn.com/apis/site/v2/sports/{spath}/scoreboard",
                params={"dates": dstr}, timeout=15)
            if r.status_code != 200:
                print(f"  {sport}: HTTP {r.status_code}")
                continue
            events = r.json().get("events", [])
            post = [e for e in events if e.get("status",{}).get("type",{}).get("state","") == "post"]
            if not post:
                print(f"  {sport}: 0 finals")
                continue
            print(f"  {sport}: {len(post)} finals")
            for e in post:
                eid = str(e.get("id",""))
                if eid:
                    capture_fn(eid, dstr)
        except Exception as ex:
            print(f"  {sport}: ERROR — {ex}")

# Summary
print(f"\n{'='*50}")
print("📊 Backfill complete")
for d in [FIN_DIR, WC_DIR, MLB_DIR]:
    files = list(d.glob("*.json"))
    print(f"  {d.name}: {len(files)} files")
