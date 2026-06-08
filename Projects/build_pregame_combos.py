"""Build DK pregame combos using TC projections.

Inputs:
- SportsGameOdds v2 (DK player props + game ML/total) — already working key
- TC projections from /api/tc (sport, away, home, mode=project)

Outputs:
- /home/workspace/Daily_Log/2026-06-07/combos_sas_nyk.json   (full legs)
- /home/workspace/Daily_Log/2026-06-07/combos_sas_nyk.md     (human report)
"""

import json
import os
import re
import requests
from datetime import datetime
from pathlib import Path

SGO_KEY = "304fe645ff9982d29d9601fc66440c4d"
API_BASE = "https://true.zo.space"
LOG_DIR = Path("/home/workspace/Daily_Log/2026-06-07")
LOG_DIR.mkdir(parents=True, exist_ok=True)

STAT_MAP = {
    "PTS": "points",
    "REB": "rebounds",
    "AST": "assists",
    "3PM": "threes",
    "STL": "steals",
    "BLK": "blocks",
}


def sgo_events(league: str):
    r = requests.get(
        "https://api.sportsgameodds.com/v2/events",
        params={"leagueID": league, "oddsAvailable": "true", "apikey": SGO_KEY},
        headers={"x-api-key": SGO_KEY},
        timeout=30,
    )
    r.raise_for_status()
    return r.json().get("data", [])


def name_to_sgo_id(name: str) -> str:
    """Convert 'Jalen Brunson' -> 'JALEN_BRUNSON_1_NBA' (best-effort)."""
    s = re.sub(r"[^A-Za-z\s]", "", name).upper().strip()
    parts = s.split()
    return "_".join(parts) + "_1_NBA"


def extract_dk_lines(odds: dict) -> dict:
    """Pull all DK player-prop OU lines plus game total/ML."""
    out = {"players": {}, "game_total": None, "ml_home": None, "ml_away": None}
    for k, v in odds.items():
        dk = v.get("byBookmaker", {}).get("draftkings", {})
        if not dk or not dk.get("available"):
            continue
        # Player props: stat-playerID-...-game-ou-over
        m = re.match(r"^(points|rebounds|assists|threes|steals|blocks)-([A-Z0-9_]+)-game-ou-over$", k)
        if m:
            stat, pid = m.group(1), m.group(2)
            line = dk.get("overUnder")
            if line is None:
                continue
            try:
                line = float(line)
            except (TypeError, ValueError):
                continue
            out["players"].setdefault(pid, {}).setdefault(stat, {"line": line, "over_odds": dk.get("odds"), "under_odds": None})
            if stat == out["players"][pid].get(stat, {}).get("stat"):
                pass
            continue
        if k == "points-all-game-ou-over":
            out["game_total"] = float(dk.get("overUnder")) if dk.get("overUnder") else None
        elif k == "points-home-game-ml-home":
            out["ml_home"] = dk.get("odds")
        elif k == "points-away-game-ml-away":
            out["ml_away"] = dk.get("odds")
    return out


def fetch_tc_projection(sport: str, away: str, home: str) -> dict:
    r = requests.get(
        f"{API_BASE}/api/tc",
        params={"sport": sport, "away": away, "home": home, "mode": "project"},
        headers={"Accept": "application/json"},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def build_combos(sport: str, away: str, home: str) -> dict:
    print(f"[{datetime.now():%H:%M:%S}] Fetching TC projection {away}@{home}...")
    proj = fetch_tc_projection(sport, away, home)
    valid = [p for p in proj.get("valid_props", []) if p.get("valid")]
    print(f"  -> {len(valid)} TC valid props")

    league = "NBA" if sport.upper() == "NBA" else "WNBA"
    if league != "NBA":
        print(f"  {league} not on SGO (NBA only) — skipping DK match")
        return {"sport": sport, "away": away, "home": home, "legs": [], "note": "no SGO league"}

    print(f"  Fetching SGO events for {league}...")
    events = sgo_events(league)
    print(f"  -> {len(events)} SGO events")

    # Find matching event
    ev = None
    for e in events:
        if e["teams"]["away"]["names"]["short"] == away and e["teams"]["home"]["names"]["short"] == home:
            ev = e
            break
    if not ev:
        print(f"  No SGO event matched {away}@{home}")
        return {"sport": sport, "away": away, "home": home, "legs": [], "note": "no event"}

    dk = extract_dk_lines(ev.get("odds", {}))
    print(f"  -> {len(dk['players'])} players with DK props, total={dk['game_total']}, ML(home/away)={dk['ml_home']}/{dk['ml_away']}")

    # Match each TC pick to a DK line
    legs = []
    for p in valid:
        sgo_id = name_to_sgo_id(p["player"])
        stat = STAT_MAP.get(p["stat"])
        if not stat:
            continue
        dk_player = dk["players"].get(sgo_id)
        if not dk_player or stat not in dk_player:
            continue
        line = dk_player[stat]["line"]
        tc_proj = p.get("tc_projection") or p.get("tc_target")
        if tc_proj is None:
            continue
        edge = round(tc_proj - line, 2) if p["direction"] == "OVER" else round(line - tc_proj, 2)
        legs.append({
            "player": p["player"],
            "team": p["team"],
            "role": p.get("role"),
            "stat": p["stat"],
            "direction": p["direction"],
            "dk_line": line,
            "dk_odds": dk_player[stat]["over_odds"] if p["direction"] == "OVER" else dk_player[stat].get("under_odds"),
            "tc_projection": tc_proj,
            "tc_target": p.get("tc_target"),
            "raw_average": p.get("raw_average"),
            "edge": edge,
            "threshold": p.get("threshold"),
            "qualifies_edge": edge >= 2.0,
        })

    # Sort by edge (largest OVER edge first, then largest UNDER edge)
    legs.sort(key=lambda x: -x["edge"] if x["direction"] == "OVER" else x["edge"], reverse=False)
    legs.sort(key=lambda x: -x["edge"] if x["direction"] == "OVER" else x["edge"])

    qualified = [l for l in legs if l["qualifies_edge"]]

    return {
        "sport": sport,
        "away": away,
        "home": home,
        "tc_total_picks": len(valid),
        "sgo_event_id": ev.get("eventID"),
        "dk_game_total": dk["game_total"],
        "dk_ml_home": dk["ml_home"],
        "dk_ml_away": dk["ml_away"],
        "matched_legs": len(legs),
        "qualified_legs": len(qualified),
        "legs": legs,
        "qualified": qualified,
    }


def write_report(result: dict, out_md: Path, out_json: Path) -> None:
    out_json.write_text(json.dumps(result, indent=2))
    md = []
    md.append(f"# TC Pregame Combos — {result.get('away')}@{result.get('home')} ({result.get('sport')})")
    md.append("")
    md.append(f"- **TC valid picks**: {result.get('tc_total_picks', 'n/a')}")
    md.append(f"- **SGO event ID**: `{result.get('sgo_event_id','-')}`")
    md.append(f"- **DK game total**: {result.get('dk_game_total')}")
    md.append(f"- **DK ML (home/away)**: {result.get('dk_ml_home')} / {result.get('dk_ml_away')}")
    md.append(f"- **Matched legs (TC + DK)**: {result.get('matched_legs', 0)}")
    md.append(f"- **Edge-qualified (≥2.0)**: {result.get('qualified_legs', 0)}")
    if result.get("note"):
        md.append(f"- **Note**: {result['note']}")
    if result.get("error"):
        md.append(f"- **Error**: {result['error']}")
    md.append("")
    if result.get("qualified"):
        md.append("## Qualified Combo Legs")
        md.append("")
        md.append("| Player | Team | Role | Stat | Dir | DK Line | TC Proj | Edge | Odds |")
        md.append("|---|---|---|---|---|---|---|---|---|")
        for l in result["qualified"]:
            md.append(f"| {l['player']} | {l['team']} | {l['role']} | {l['stat']} | {l['direction']} | {l['dk_line']} | {l['tc_projection']} | {l['edge']} | {l['dk_odds']} |")
    if result.get("legs"):
        md.append("")
        md.append("## All Matched Legs (incl. non-qualified)")
        md.append("")
        md.append("| Player | Stat | Dir | DK | TC | Edge |")
        md.append("|---|---|---|---|---|---|")
        for l in result["legs"]:
            md.append(f"| {l['player']} | {l['stat']} | {l['direction']} | {l['dk_line']} | {l['tc_projection']} | {l['edge']} |")
    out_md.write_text("\n".join(md))


if __name__ == "__main__":
    today_games = [
        ("NBA", "SAS", "NYK"),
        ("WNBA", "CHI", "TOR"),
        ("WNBA", "POR", "LA"),
    ]
    summary = []
    for sport, away, home in today_games:
        try:
            r = build_combos(sport, away, home)
        except Exception as e:
            print(f"  ERROR: {e}")
            r = {"sport": sport, "away": away, "home": home, "legs": [], "qualified": [], "error": str(e)}
        safe = f"{away}_{home}".lower()
        write_report(r, LOG_DIR / f"combos_{safe}.md", LOG_DIR / f"combos_{safe}.json")
        summary.append({
            "matchup": f"{away}@{home}",
            "sport": sport,
            "matched": r.get("matched_legs", 0),
            "qualified": r.get("qualified_legs", 0),
            "dk_total": r.get("dk_game_total"),
        })
        print()
    (LOG_DIR / "combos_summary.json").write_text(json.dumps(summary, indent=2))
    print("=== SUMMARY ===")
    print(json.dumps(summary, indent=2))
