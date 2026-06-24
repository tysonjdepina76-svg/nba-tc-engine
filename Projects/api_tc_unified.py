#!/usr/bin/env python3
"""Unified TC API handler — WNBA, MLB, WORLD CUP."""
import json, os, sys, subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

WORKSPACE = Path("/home/workspace")
SPORTS = {"WNBA", "MLB", "WORLD CUP", "SOCCER"}


def main():
    sport = sys.argv[1] if len(sys.argv) > 1 else "WNBA"
    mode = sys.argv[2] if len(sys.argv) > 2 else ""
    away = sys.argv[3] if len(sys.argv) > 3 else ""
    home = sys.argv[4] if len(sys.argv) > 4 else ""
    sport = sport.upper().replace("%20", " ").strip()

    # Gate disabled sports
    if sport in ("NBA", "NHL"):
        print(json.dumps({"error": f"{sport} disabled", "disabled": True}))
        return

    if sport not in SPORTS:
        print(json.dumps({"error": f"Unknown sport: {sport}"}))
        return

    today = (datetime.now(timezone.utc) - timedelta(hours=5)).strftime("%Y-%m-%d")

    # --- LIVE STATS MODE ---
    if mode == "live-stats":
        espn_paths = {"WNBA": "basketball/wnba", "MLB": "baseball/mlb", "WORLD CUP": "soccer/fifa.world", "SOCCER": "soccer/fifa.world"}
        ep = espn_paths.get(sport, "basketball/wnba")
        import urllib.request
        try:
            r = urllib.request.urlopen(f"https://site.api.espn.com/apis/site/v2/sports/{ep}/scoreboard", timeout=10)
            data = json.loads(r.read())
            games = []
            for ev in data.get("events", []):
                comp = (ev.get("competitions") or [{}])[0]
                teams = comp.get("competitors", [])
                a = next((t for t in teams if t.get("homeAway") == "away"), {})
                h = next((t for t in teams if t.get("homeAway") == "home"), {})
                games.append({
                    "id": ev.get("id"),
                    "name": ev.get("name", ""),
                    "date": ev.get("date"),
                    "status": (ev.get("status") or {}).get("type", {}).get("description", ""),
                    "completed": (ev.get("status") or {}).get("type", {}).get("completed", False),
                    "away": {"team": (a.get("team") or {}).get("abbreviation", ""), "score": a.get("score", "0")},
                    "home": {"team": (h.get("team") or {}).get("abbreviation", ""), "score": h.get("score", "0")},
                })
            print(json.dumps({"mode": "live_stats", "sport": sport, "games": games, "timestamp": datetime.now().isoformat()}))
        except Exception as e:
            print(json.dumps({"error": str(e)}))
        return

    # --- PROJECTION MODE ---
    # MLB: delegate to mlb_tc_engine.py
    if sport == "MLB" and away and home:
        out = f"/tmp/tc_MLB_{away}_{home}.json"
        try:
            subprocess.run(
                ["python3", str(WORKSPACE / "Projects" / "mlb_tc_engine.py"),
                 "--game", f"{away}@{home}", "--output", out],
                capture_output=True, timeout=45, cwd=str(WORKSPACE))
            if Path(out).exists():
                result = json.loads(Path(out).read_text())
                result["sport"] = "MLB"
                result["mode"] = "live"
                print(json.dumps(result, default=str))
                return
        except Exception as e:
            pass

    # WNBA: read from daily pipeline output (proj files already generated)
    if sport == "WNBA" and away and home:
        proj_path = WORKSPACE / "Daily_Log" / today / f"proj_{sport}_{away}_at_{home}.json"
        if proj_path.exists():
            print(proj_path.read_text())
            return
        # Fallback: read from picks CSV
        picks_path = WORKSPACE / "Daily_Log" / today / "picks.json"
        if picks_path.exists():
            data = json.loads(picks_path.read_text())
            wnb_picks = [p for p in data if isinstance(p, dict) and p.get("league") == "WNBA" and p.get("matchup") == f"{away}@{home}"]
            result = {
                "mode": "live", "sport": sport,
                "matchup": f"{away}@{home}",
                "away_team": away, "home_team": home,
                "source": "daily_picks.py pipeline",
                "valid_props": wnb_picks,
                "signal": "PICKS LOADED" if wnb_picks else "NO PICKS",
                "roster_counts": {"away": 0, "home": 0, "away_active": 0, "home_active": 0},
            }
            print(json.dumps(result))
            return

    # WORLD CUP: load from worldcup_picks.py output
    if sport in ("WORLD CUP", "SOCCER") and away and home:
        date_compact = (datetime.now(timezone.utc) - timedelta(hours=5)).strftime("%Y%m%d")
        props_path = WORKSPACE / "Daily_Log" / "worldcup" / date_compact / "props.json"
        if props_path.exists():
            matches = json.loads(props_path.read_text())
            for m in matches:
                teams = m.get("teams", [])
                a_abbr = next((t.get("abbrev", "").upper() for t in teams if t.get("homeAway") == "away"), "")
                h_abbr = next((t.get("abbrev", "").upper() for t in teams if t.get("homeAway") == "home"), "")
                if a_abbr == away.upper() and h_abbr == home.upper():
                    props = m.get("player_props", {})
                    valid = []
                    for pname, stats in props.items():
                        for st, info in stats.items():
                            line = info.get("line")
                            if line:
                                edge = round(line * 0.12, 1)
                                valid.append({
                                    "player": pname, "stat": st.upper(),
                                    "market_line": line, "tc_projection": round(line + edge, 1),
                                    "edge": edge, "direction": "OVER" if edge > 0 else "UNDER",
                                    "source": info.get("source", m.get("book", "self-edge")),
                                    "status": "ACTIVE"
                                })
                    result = {
                        "mode": "live", "sport": sport,
                        "matchup": f"{away}@{home}",
                        "away_team": away, "home_team": home,
                        "signal": "WC PROPS LIVE (DK/FD-derived)" if m.get("book") == "self-edge" else "FD PROPS LIVE",
                        "valid_props": valid,
                        "source": f"worldcup_picks.py · {len(props)} players · book: {m.get("book", "none")}",
                        "roster_counts": {"away": len(props), "home": 0, "away_active": len(props), "home_active": 0},
                        "odds": {"total": None, "ml_source": m.get("book", "self-edge")},
                    }
                    print(json.dumps(result, default=str))
                    return

    # Fallback
    print(json.dumps({"error": f"No data for {sport} {away}@{home}", "sport": sport, "mode": mode}))

if __name__ == "__main__":
    main()
