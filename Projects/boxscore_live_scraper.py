"""Live box-score scraper — captures halftime + final boxes for WNBA + NBA games.

Polls ESPN every 60s. On every state transition (Scheduled -> InProgress -> Halftime -> Final),
saves a JSON snapshot under /home/workspace/Daily_Log/{halftime,final}/ and writes a
TC-hit-rate summary if TC picks exist for that matchup.

Usage:
    python3 boxscore_live_scraper.py            # run forever, poll all sports
    python3 boxscore_live_scraper.py --once     # poll once and exit
    python3 boxscore_live_scraper.py --sport WNBA
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

LOG_DIR = Path("/home/workspace/Daily_Log")
HALFTIME_DIR = LOG_DIR / "halftime"
FINAL_DIR = LOG_DIR / "final"
REPORT_DIR = LOG_DIR / "boxscore_reports"

LEAGUES = {
    "WNBA": ("basketball/wnba", "59"),
    "NBA": ("basketball/nba", "46"),
}

STATS_KEYS = [
    "minutes", "points", "rebounds", "assists", "steals", "blocks",
    "turnovers", "threePointFieldGoalsMade-threePointFieldGoalsAttempted",
    "offensiveRebounds", "defensiveRebounds", "plusMinus", "fouls",
]


def now_iso() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_json(url: str, timeout: int = 15) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.load(r)
    except Exception as e:
        print(f"  ! fetch error {url}: {e}")
        return None


def get_scoreboard(sport_path: str) -> list[dict]:
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_path}/scoreboard"
    data = fetch_json(url)
    return data.get("events", []) if data else []


def get_summary(sport_path: str, event_id: str) -> dict | None:
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_path}/summary?event={event_id}"
    return fetch_json(url)


def status_state(event: dict) -> str:
    """Return a normalized state token: scheduled / inprogress / halftime / final."""
    st = event.get("status", {}).get("type", {})
    desc = (st.get("description") or "").lower()
    detail = (st.get("shortDetail") or "").lower()
    state = (st.get("state") or "").lower()
    if state == "post" or "final" in desc:
        return "final"
    if "halftime" in desc or "halftime" in detail:
        return "halftime"
    if state == "in" or "in progress" in desc or "progress" in desc:
        return "inprogress"
    return "scheduled"


def clock_label(event: dict) -> str:
    return event.get("status", {}).get("displayClock", "")


def parse_player_stats(team_block: dict) -> list[dict]:
    """Convert ESPN boxscore.players[].statistics[].athletes[] -> per-player dicts."""
    out = []
    team_name = team_block.get("team", {}).get("displayName", "?")
    team_id = team_block.get("team", {}).get("id", "")
    for grp in team_block.get("statistics", []):
        keys = grp.get("keys", [])
        for ath in grp.get("athletes", []):
            athlete = ath.get("athlete", {})
            name = athlete.get("displayName", "?")
            jersey = athlete.get("jersey", "")
            pos = athlete.get("position", {}).get("abbreviation", "") if isinstance(athlete.get("position"), dict) else ""
            stats = ath.get("stats", [])
            row = {"name": name, "team": team_name, "team_id": team_id, "jersey": jersey, "position": pos}
            for k, v in zip(keys, stats):
                row[k] = v
            out.append(row)
    return out


def build_box(sport: str, summary: dict, scoreboard_event: dict) -> dict:
    """Return structured box with metadata + per-team player stats."""
    header = summary.get("header", {}) or {}
    competitors = header.get("competitions", [{}])[0].get("competitors", [])
    box_teams = summary.get("boxscore", {}).get("players", [])
    teams = []
    for comp in competitors:
        tname = comp.get("team", {}).get("displayName", "?")
        score = comp.get("score", 0)
        side = comp.get("homeAway", "")
        # find matching box
        player_block = next((b for b in box_teams if b.get("team", {}).get("displayName") == tname), None)
        players = parse_player_stats(player_block) if player_block else []
        teams.append({"team": tname, "side": side, "score": score, "players": players})
    return {
        "sport": sport,
        "event_id": scoreboard_event.get("id"),
        "name": scoreboard_event.get("name"),
        "date": scoreboard_event.get("date"),
        "scraped_at": now_iso(),
        "status_state": status_state(scoreboard_event),
        "clock": clock_label(scoreboard_event),
        "status_detail": (scoreboard_event.get("status", {}).get("type", {}) or {}).get("shortDetail", ""),
        "teams": teams,
    }


def already_saved(path: Path, event_id: str, state: str) -> bool:
    if not path.exists():
        return False
    for f in path.glob(f"*{state}*{event_id}*.json"):
        return True
    return False


def save_snapshot(box: dict, out_dir: Path, label: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_teams = box["name"].replace(" at ", "_AT_").replace(" ", "")
    fn = f"{box['sport'].lower()}_{safe_teams}_{label}_{box['event_id']}_{stamp}.json"
    p = out_dir / fn
    p.write_text(json.dumps(box, indent=2))
    return p


def find_tc_picks(sport: str, matchup: str) -> list[dict]:
    """Look for TC picks written by daily_picks.py for this matchup today."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    # possible file patterns
    candidates = list((LOG_DIR / today).glob(f"proj_{sport}_*.json")) if (LOG_DIR / today).exists() else []
    picks = []
    for f in candidates:
        try:
            data = json.loads(f.read_text())
        except Exception:
            continue
        matchup_norm = matchup.replace(" at ", "@").upper()
        if matchup_norm in f.name.upper() or data.get("matchup", "").upper() == matchup_norm:
            picks = data.get("picks") or data.get("valid_props") or []
            return picks
    return []


def compute_hit_rates(legs: list[dict], box: dict) -> dict:
    """For each TC pick, look up the player's actual stat in the final box."""
    if not legs or not box:
        return {"hit": 0, "miss": 0, "no_data": 0, "details": []}
    name_to_stats = {}
    for t in box.get("teams", []):
        for p in t.get("players", []):
            name_to_stats[p["name"].lower()] = p
    hits, misses, nodata = 0, 0, 0
    details = []
    for leg in legs:
        player = leg.get("player") or leg.get("name") or ""
        stat = (leg.get("stat") or "").upper()
        line = leg.get("dk_line") or leg.get("line")
        direction = leg.get("direction", "OVER")
        p = name_to_stats.get(player.lower())
        if not p:
            nodata += 1
            details.append({"player": player, "result": "no_data"})
            continue
        actual = p.get(stat.lower())
        try:
            actual = float(actual)
        except (TypeError, ValueError):
            nodata += 1
            details.append({"player": player, "result": "no_data", "actual": actual})
            continue
        try:
            line = float(line)
        except (TypeError, ValueError):
            nodata += 1
            continue
        win = (actual > line) if direction == "OVER" else (actual < line)
        if actual == line:
            push = True
            win = None
        else:
            push = False
        if push:
            nodata += 1
            details.append({"player": player, "stat": stat, "line": line, "actual": actual, "result": "push"})
        elif win:
            hits += 1
            details.append({"player": player, "stat": stat, "line": line, "actual": actual, "result": "hit", "direction": direction})
        else:
            misses += 1
            details.append({"player": player, "stat": stat, "line": line, "actual": actual, "result": "miss", "direction": direction})
    total = hits + misses
    return {
        "hits": hits, "misses": misses, "no_data": nodata,
        "hit_rate": round(hits / total, 3) if total else None,
        "details": details,
    }


def process_event(sport_name: str, sport_path: str, event: dict) -> None:
    eid = event.get("id")
    name = event.get("name", "?")
    state = status_state(event)
    detail = (event.get("status", {}).get("type", {}) or {}).get("shortDetail", "")
    clk = clock_label(event)
    print(f"  {sport_name} {eid} {name} -> {state} ({detail}) clk={clk}")

    if state == "scheduled":
        return
    if state == "inprogress":
        # only save halftime snapshots (we don't spam every minute)
        return

    label = "halftime" if state == "halftime" else "final"
    out_dir = HALFTIME_DIR if state == "halftime" else FINAL_DIR

    if already_saved(out_dir, eid, label):
        print(f"    already saved, skip")
        return

    summary = get_summary(sport_path, eid)
    if not summary:
        return
    box = build_box(sport_name, summary, event)
    p = save_snapshot(box, out_dir, label)
    print(f"    saved: {p}")

    if state == "final":
        # match against TC picks
        tc = find_tc_picks(sport_name, name)
        if tc:
            rate = compute_hit_rates(tc, box)
            REPORT_DIR.mkdir(parents=True, exist_ok=True)
            stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            rpt = REPORT_DIR / f"{sport_name.lower()}_{name.replace(' at ','_AT_')}_hitrate_{eid}_{stamp}.json"
            payload = {"event_id": eid, "matchup": name, "sport": sport_name, "legs_total": len(tc), **rate}
            rpt.write_text(json.dumps(payload, indent=2))
            print(f"    hit-rate: {rate['hits']}/{rate['hits']+rate['misses']} = {rate['hit_rate']} ({len(tc)} TC legs) -> {rpt}")
        else:
            print(f"    no TC picks matched for {name}")


def poll_once(sport_filter: str | None = None) -> None:
    for sport_name, (sport_path, _league_id) in LEAGUES.items():
        if sport_filter and sport_name != sport_filter:
            continue
        events = get_scoreboard(sport_path)
        print(f"[{datetime.utcnow():%H:%M:%S}] {sport_name}: {len(events)} events")
        for ev in events:
            try:
                process_event(sport_name, sport_path, ev)
            except Exception as e:
                print(f"  ! error on {ev.get('id')}: {e}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="poll once and exit")
    ap.add_argument("--sport", default=None, help="filter to one sport (WNBA/NBA)")
    ap.add_argument("--interval", type=int, default=60, help="poll seconds")
    args = ap.parse_args()

    print(f"Box-score scraper starting (once={args.once}, sport={args.sport}, interval={args.interval}s)")
    if args.once:
        poll_once(args.sport)
    else:
        while True:
            poll_once(args.sport)
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
