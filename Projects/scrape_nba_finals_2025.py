#!/usr/bin/env python3
"""Scrape 2025 NBA Finals + WNBA final box scores, save to Daily_Log."""
import json, os, sys
import requests
from datetime import datetime, timezone
from pathlib import Path

OUT = Path("/home/workspace/Daily_Log/2025-06-13")
OUT.mkdir(parents=True, exist_ok=True)

def fetch_summary(sport: str, event_id: str):
    base = f"https://site.api.espn.com/apis/site/v2/sports/basketball/{sport}/summary"
    r = requests.get(base, params={"event": event_id}, timeout=20)
    r.raise_for_status()
    return r.json()

def parse_boxscore(summary: dict):
    teams = []
    box = summary.get("boxscore", {})
    for team_block in box.get("players", []):
        t = team_block.get("team", {})
        team_name = t.get("displayName")
        team_abbr = t.get("abbreviation")
        players = []
        for stat_group in team_block.get("statistics", []):
            keys = stat_group.get("keys", [])
            for ath in stat_group.get("athletes", []):
                a = ath.get("athlete", {})
                stats_vals = ath.get("stats", [])
                stat_map = {}
                for k, v in zip(keys, stats_vals):
                    stat_map[k] = v
                players.append({
                    "name": a.get("displayName"),
                    "id": a.get("id"),
                    "starter": ath.get("starter", False),
                    "dnp": ath.get("didNotPlay", False),
                    "stats": stat_map,
                })
        teams.append({
            "team": team_name,
            "abbr": team_abbr,
            "players": players,
        })
    return teams

# ── 2025 NBA Finals (Pacers vs Thunder) ─────────────────────────────────
NBA_FINALS = [
    ("G1", "401859963", "NYK@SAS", "2026-06-04"),
    ("G2", "401859964", "NYK@SAS", "2026-06-06"),
    ("G3", "401859965", "SAS@NYK", "2026-06-09"),
    ("G4", "401859966", "SAS@NYK", "2026-06-11"),
    ("G5", "401859967", "NYK@SAS", "2026-06-14"),
]

nba_finals_data = []
for label, eid, matchup, date in NBA_FINALS:
    try:
        summary = fetch_summary("nba", eid)
        teams = parse_boxscore(summary)
        nba_finals_data.append({
            "label": label, "event_id": eid, "matchup": matchup, "date": date,
            "summary_header": summary.get("header", {}),
            "teams": teams,
        })
        total_players = sum(len(t["players"]) for t in teams)
        print(f"  NBA Finals {label} {matchup}: {total_players} players")
    except Exception as e:
        print(f"  NBA Finals {label}: ERROR {e}")

(OUT / "finals_2025_nba.json").write_text(json.dumps(nba_finals_data, indent=2))
print(f"  → {OUT}/finals_2025_nba.json")

# ── WNBA 2025 season (all completed games) ──────────────────────────────
wnba_games = []
date_window = ["2025-05-01", "2025-05-15", "2025-05-30", "2025-06-01", "2025-06-08", "2025-06-13"]
seen = set()
for d in date_window:
    try:
        r = requests.get(
            "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard",
            params={"dates": d.replace("-", ""), "limit": 50},
            timeout=20,
        )
        r.raise_for_status()
        for ev in r.json().get("events", []):
            state = ev.get("status", {}).get("type", {}).get("name", "")
            if state != "STATUS_FINAL":
                continue
            eid = ev.get("id")
            if eid in seen:
                continue
            seen.add(eid)
            comps = ev.get("competitions", [{}])[0]
            competitors = comps.get("competitors", [])
            away = next((c for c in competitors if c.get("homeAway") == "away"), {})
            home = next((c for c in competitors if c.get("homeAway") == "home"), {})
            try:
                summary = fetch_summary("wnba", eid)
                teams = parse_boxscore(summary)
            except Exception:
                teams = []
            wnba_games.append({
                "event_id": eid,
                "date": ev.get("date"),
                "matchup": f"{away.get('team',{}).get('abbreviation','?')}@{home.get('team',{}).get('abbreviation','?')}",
                "away_score": away.get("score"),
                "home_score": home.get("score"),
                "teams": teams,
            })
    except Exception as e:
        print(f"  WNBA {d}: {e}")

(OUT / "finals_2025_wnba.json").write_text(json.dumps(wnba_games, indent=2))
total_wnba_players = sum(len(t["players"]) for g in wnba_games for t in g["teams"])
print(f"  WNBA: {len(wnba_games)} games, {total_wnba_players} player records")
print(f"  → {OUT}/finals_2025_wnba.json")
print(f"\nDone at {datetime.now(timezone.utc).isoformat()}")
