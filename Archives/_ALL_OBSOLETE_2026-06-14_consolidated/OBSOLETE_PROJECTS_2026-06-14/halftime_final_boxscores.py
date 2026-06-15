#!/usr/bin/env python3
"""Halftime + Final boxscore builder for backtests.

Reconstructs HALFTIME box scores (1H only stats) from ESPN's play-by-play
data by counting every individual scoring play (made FGs, made FTs, rebounds,
assists via the participants field) for each player in Q1+Q2. Saves both
halftime and final boxes in a unified format for TC backtest analysis.

Usage:
    python3 halftime_final_boxscores.py --sport WNBA --days 7
    python3 halftime_final_boxscores.py --sport NBA --days 3
    python3 halftime_final_boxscores.py --event 401856975
"""
from __future__ import annotations

import argparse
import json
import re
import requests
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

LOG_DIR = Path("/home/workspace/Daily_Log")
HALFTIME_DIR = LOG_DIR / "halftime"
FINAL_DIR = LOG_DIR / "final"
HALFTIME_DIR.mkdir(parents=True, exist_ok=True)
FINAL_DIR.mkdir(parents=True, exist_ok=True)

LEAGUE = {
    "WNBA": ("basketball/wnba", 2),  # WNBA = 2x20min = 4 quarters
    "NBA": ("basketball/nba", 2),    # NBA = 4x12min
}

# play types: text containing these substrings count as that stat
TYPE_PATTERNS = [
    ("points", re.compile(r"(?i)(made\s+.*?shot|3pt\s+made|free\s+throw|technical\s+ft)", re.I)),
]

def fetch_summary(sport_path, event_id):
    r = requests.get("https://site.api.espn.com/apis/site/v2/sports/" + sport_path + "/summary", params={"event": event_id}, timeout=20)
    return r.json() if r.status_code == 200 else None

def fetch_scoreboard(sport_path, date_str):
    r = requests.get("https://site.api.espn.com/apis/site/v2/sports/" + sport_path + "/scoreboard", params={"dates": date_str}, timeout=20)
    return r.json() if r.status_code == 200 else {}

def parse_int(s, default=0):
    try:
        return int(str(s).replace(",", ""))
    except (ValueError, TypeError):
        return default

def parse_final_box(summary, event_id, sport):
    """Convert ESPN boxscore to per-player dict."""
    out = {"event_id": event_id, "sport": sport, "scraped_at": datetime.utcnow().isoformat() + "Z", "type": "final", "players": {}}
    comp = summary.get("header", {}).get("competitions", [{}])[0]
    competitors = comp.get("competitors", [])
    team_names = {}
    for c in competitors:
        team_names[c.get("homeAway", "")] = c.get("team", {}).get("displayName", "?")
    for grp in summary.get("boxscore", {}).get("players", []):
        tname = grp.get("team", {}).get("displayName", "?")
        for stat in grp.get("statistics", []):
            keys = stat.get("keys", [])
            for ath in stat.get("athletes", []):
                nm = ath.get("athlete", {}).get("displayName", "?")
                raw = ath.get("stats", [])
                def to_int(x):
                    try: return int(str(x).replace(",", ""))
                    except: return 0
                row = {"name": nm, "team": tname, "pos": ath.get("athlete", {}).get("position", {}).get("abbreviation", "") if isinstance(ath.get("athlete", {}).get("position"), dict) else ""}
                # WNBA: keys = ['minutes','points','rebounds','assists','steals','blocks','turnovers','threePointFieldGoalsMade-threePointFieldGoalsAttempted','offensiveRebounds','defensiveRebounds','plusMinus','fouls']
                if "minutes" in keys:
                    row["minutes"] = raw[keys.index("minutes")] if keys.index("minutes") < len(raw) else "0"
                if "points" in keys:
                    row["pts"] = to_int(raw[keys.index("points")]) if keys.index("points") < len(raw) else 0
                if "rebounds" in keys:
                    row["reb"] = to_int(raw[keys.index("rebounds")]) if keys.index("rebounds") < len(raw) else 0
                if "assists" in keys:
                    row["ast"] = to_int(raw[keys.index("assists")]) if keys.index("assists") < len(raw) else 0
                if "offensiveRebounds" in keys:
                    row["oreb"] = to_int(raw[keys.index("offensiveRebounds")]) if keys.index("offensiveRebounds") < len(raw) else 0
                if "defensiveRebounds" in keys:
                    row["dreb"] = to_int(raw[keys.index("defensiveRebounds")]) if keys.index("defensiveRebounds") < len(raw) else 0
                if "threePointFieldGoalsMade-threePointFieldGoalsAttempted" in keys:
                    fg3 = raw[keys.index("threePointFieldGoalsMade-threePointFieldGoalsAttempted")] if keys.index("threePointFieldGoalsMade-threePointFieldGoalsAttempted") < len(raw) else "0-0"
                    row["fg3m"] = to_int(str(fg3).split("-")[0]) if "-" in str(fg3) else to_int(fg3)
                if "steals" in keys:
                    row["stl"] = to_int(raw[keys.index("steals")]) if keys.index("steals") < len(raw) else 0
                if "blocks" in keys:
                    row["blk"] = to_int(raw[keys.index("blocks")]) if keys.index("blocks") < len(raw) else 0
                if "turnovers" in keys:
                    row["to"] = to_int(raw[keys.index("turnovers")]) if keys.index("turnovers") < len(raw) else 0
                if "fouls" in keys:
                    row["pf"] = to_int(raw[keys.index("fouls")]) if keys.index("fouls") < len(raw) else 0
                out["players"][nm] = row
    out["score"] = {"away": parse_int(next((c.get("score") for c in competitors if c.get("homeAway") == "away"), 0)), "home": parse_int(next((c.get("score") for c in competitors if c.get("homeAway") == "home"), 0))}
    out["away_team"] = team_names.get("away", "?")
    out["home_team"] = team_names.get("home", "?")
    return out

def parse_halftime_from_plays(summary, final_box):
    """Reconstruct halftime stats by walking plays[period<=2] and counting scoring events per player."""
    plays = summary.get("plays", [])
    if not plays:
        return None
    p1p2 = [p for p in plays if (p.get("period") or {}).get("number") in (1, 2)]
    if not p1p2:
        return None
    # find halftime marker (end of Q2)
    halftime_play = None
    for p in p1p2:
        if (p.get("clock") or {}).get("displayValue") == "0.0" and (p.get("period") or {}).get("number") == 2:
            halftime_play = p
    if not halftime_play:
        return None
    away_h = parse_int(halftime_play.get("awayScore"))
    home_h = parse_int(halftime_play.get("homeScore"))
    p1p2_scoring = [p for p in p1p2 if p.get("scoringPlay")]
    # per-player accumulator
    box = {"event_id": final_box["event_id"], "sport": final_box["sport"], "scraped_at": datetime.utcnow().isoformat() + "Z", "type": "halftime", "score": {"away": away_h, "home": home_h}, "away_team": final_box["away_team"], "home_team": final_box["home_team"], "players": {}}
    # walk every scoring play, attribute to first participant
    for p in p1p2_scoring:
        text = p.get("text", "")
        points = parse_int(p.get("scoreValue"))
        # participant 0 is the shooter
        parts = p.get("participants") or []
        if not parts:
            continue
        nm = (parts[0].get("athlete") or {}).get("displayName", "")
        if not nm:
            continue
        row = box["players"].setdefault(nm, {"name": nm, "pts": 0, "fg3m": 0, "ast": 0})
        row["pts"] = row.get("pts", 0) + points
        if "three point" in text.lower() or "3pt" in text.lower():
            row["fg3m"] = row.get("fg3m", 0) + 1
    # try to also get rebounds/assists via second participants on "assists" or "rebound" plays
    for p in p1p2:
        text = p.get("text", "").lower()
        parts = p.get("participants") or []
        if not parts: continue
        if "rebound" in text:
            nm = (parts[0].get("athlete") or {}).get("displayName", "")
            if nm:
                row = box["players"].setdefault(nm, {"name": nm, "pts": 0, "reb": 0, "ast": 0})
                row["reb"] = row.get("reb", 0) + 1
        elif "assist" in text:
            nm = (parts[0].get("athlete") or {}).get("displayName", "")
            if nm:
                row = box["players"].setdefault(nm, {"name": nm, "pts": 0, "ast": 0})
                row["ast"] = row.get("ast", 0) + 1
    return box

def save(box, out_dir, label):
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe = (box.get("away_team", "?") + "_at_" + box.get("home_team", "?")).replace(" ", "")
    fn = box["sport"].lower() + "_" + safe + "_" + label + "_" + str(box["event_id"]) + "_" + stamp + ".json"
    p = out_dir / fn
    p.write_text(json.dumps(box, indent=2))
    return p

def process_event(sport, event_id):
    sport_path, _ = LEAGUE[sport]
    summary = fetch_summary(sport_path, event_id)
    if not summary: return None, None
    final = parse_final_box(summary, event_id, sport)
    if not final.get("players"): return None, None
    halftime = parse_halftime_from_plays(summary, final)
    fp = save(final, FINAL_DIR, "final")
    hp = save(halftime, HALFTIME_DIR, "halftime") if halftime else None
    return fp, hp

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sport", choices=list(LEAGUE), default=None)
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--event", default=None)
    args = ap.parse_args()
    if args.event:
        sport = args.sport or "WNBA"
        fp, hp = process_event(sport, args.event)
        print("event", args.event, "final:", fp, "halftime:", hp)
        return
    today = datetime.utcnow().date()
    for sport in ([args.sport] if args.sport else list(LEAGUE)):
        sport_path, _ = LEAGUE[sport]
        n_final = n_ht = 0
        for offset in range(args.days):
            d = today - timedelta(days=offset)
            dstr = d.strftime("%Y%m%d")
            sb = fetch_scoreboard(sport_path, dstr)
            for ev in sb.get("events", []):
                state = (ev.get("status") or {}).get("type") or {}
                if state.get("state") != "post":
                    continue
                fp, hp = process_event(sport, ev["id"])
                if fp: n_final += 1
                if hp: n_ht += 1
                print(" ", sport, dstr, ev["id"], "final:", fp is not None, "halftime:", hp is not None)
        print("[" + sport + "] finals saved:", n_final, "halftimes saved:", n_ht)

if __name__ == "__main__":
    main()