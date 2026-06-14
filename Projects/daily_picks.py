"""TC Daily Pick Log — captures every pick with full roster context for backtesting.

Runs on a schedule (5 min before tip) and writes:
- /home/workspace/Daily_Log/YYYY-MM-DD/slate_NBA.json  (raw responses)
- /home/workspace/Daily_Log/YYYY-MM-DD/slate_WNBA.json
- /home/workspace/Daily_Log/YYYY-MM-DD/picks.csv         (flat backtest table)
- /home/workspace/Daily_Log/YYYY-MM-DD/picks.json        (structured picks)
- /home/workspace/Daily_Log/last_run.json                (latest summary)

Designed to be the single source of truth for daily picks and historical results.
"""

import os
import json
import csv
import sys
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

ET = timezone(timedelta(hours=-5))
def now_et():
    return datetime.now(ET)
def today_et():
    return now_et().strftime("%Y-%m-%d")

# Load secrets so SGO/ODDS_API keys are available
try:
    _sec = Path("/root/.zo/secrets.env")
    if _sec.exists():
        for _line in _sec.read_text().splitlines():
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())
except Exception as _e:
    print(f"⚠️ secrets load failed: {_e}")

# Add workspace root for imports
WORKSPACE = Path("/home/workspace")
sys.path.insert(0, str(WORKSPACE))
sys.path.insert(0, str(WORKSPACE / "Skills" / "nba-odds-api" / "scripts"))

from odds_enricher import enrich_player_lines

API_BASE = "https://true.zo.space"
LOG_DIR = WORKSPACE / "Daily_Log"
LOG_DIR.mkdir(exist_ok=True)

ED_THRESHOLD = 2.0  # TC edge threshold to call OVER/UNDER signal

def fetch_live_slate(sport):
    """Fetch live slate for a sport. Returns games (future + recent)."""
    try:
        r = requests.get(
            f"{API_BASE}/api/tc",
            params={"sport": sport, "mode": "live-stats"},
            timeout=30,
            headers={"Accept": "application/json"},
        )
        if r.ok:
            return r.json()
        return {"error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"error": str(e)}


def filter_future_games(games, sport):
    """Return only games that haven't been completed yet.

    ESPN sometimes surfaces recent games for ~12h after they end. For a daily
    betting log we only want UPCOMING games with active DK lines.
    """
    out = []
    for g in games or []:
        if g.get("completed"):
            continue
        # If a status field is set to "Final", drop it too
        st = (g.get("status") or "").lower()
        if "final" in st:
            continue
        out.append(g)
    return out


def fetch_game_projection(sport, away, home):
    """Fetch full TC projection for a single game."""
    try:
        r = requests.get(
            f"{API_BASE}/api/tc",
            params={"sport": sport, "away": away, "home": home, "mode": "project"},
            timeout=60,
            headers={"Accept": "application/json"},
        )
        if r.ok:
            return r.json()
        return {"error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"error": str(e)}


def extract_picks(projection, sport, matchup):
    """Extract all valid prop picks from a projection response."""
    picks = []
    valid_props = projection.get("valid_props", [])
    for p in valid_props:
        if not p.get("valid"):
            continue
        picks.append({
            "date": now_et().strftime("%Y-%m-%d"),
            "league": sport,
            "matchup": matchup,
            "team": p.get("team"),
            "player": p.get("player"),
            "role": p.get("role"),
            "status": p.get("status"),
            "stat": p.get("stat"),
            "direction": p.get("direction"),
            "market_line": p.get("market_line"),
            "tc_projection": p.get("tc_projection"),
            "tc_target": p.get("tc_target"),
            "edge": p.get("edge"),
            "threshold": p.get("threshold"),
            "raw_average": p.get("raw_average"),
            "source": p.get("source"),
            "actual": p.get("actual"),
            "result": p.get("result", "PENDING"),
        })
    return picks


def extract_game_summary(projection, sport, matchup):
    """Extract top-line game summary."""
    a = projection.get("assessment", {})
    return {
        "date": now_et().strftime("%Y-%m-%d"),
        "sport": sport,
        "matchup": matchup,
        "away_team": projection.get("away_team"),
        "home_team": projection.get("home_team"),
        "tc_combined": projection.get("tc_combined"),
        "tc_line": projection.get("tc_line"),
        "market_total": projection.get("market_total"),
        "dk_total": projection.get("dk_total"),
        "edge": projection.get("edge"),
        "signal": projection.get("signal"),
        "source": projection.get("source"),
        "valid_prop_count": len(projection.get("valid_props", [])),
        "roster_size": sum(projection.get("roster_counts", {}).values()) if projection.get("roster_counts") else None,
    }


def run_daily_log(sports=("NBA", "WNBA")):
    """Run the full daily log capture. Filters out completed games."""
    now = now_et()
    today_dir = LOG_DIR / now.strftime("%Y-%m-%d")
    today_dir.mkdir(exist_ok=True)

    all_picks = []
    all_summaries = []
    errors = []
    skipped_completed = 0

    for sport in sports:
        print(f"[{now.strftime('%H:%M:%S')}] Fetching {sport} slate...")
        slate = fetch_live_slate(sport)
        if "error" in slate:
            errors.append(f"{sport} slate: {slate['error']}")
            continue

        raw_games = slate.get("games", [])
        games = filter_future_games(raw_games, sport)
        skipped_completed += len(raw_games) - len(games)

        # Save raw slate (full, including completed games, for backtest)
        (today_dir / f"slate_{sport}.json").write_text(json.dumps(slate, indent=2))
        print(f"  Slate has {len(raw_games)} game(s); {len(games)} upcoming after filtering completed")

        for g in games:
            away = g.get("away", {}).get("team", "")
            home = g.get("home", {}).get("team", "")
            if not away or not home:
                continue
            matchup = f"{away}@{home}"
            print(f"  Projecting {matchup}...")
            proj = fetch_game_projection(sport, away, home)
            if "error" in proj:
                errors.append(f"{sport} {matchup}: {proj['error']}")
                continue

            # Enrich with live Odds API player prop lines
            odds_enrichment = None
            try:
                odds_enrichment = enrich_player_lines(sport, away, home)
                if odds_enrichment and odds_enrichment.get("player_lines"):
                    proj["odds_api_lines"] = odds_enrichment
                    print(f"    → Odds API: {odds_enrichment.get('player_count', 0)} players enriched via {odds_enrichment.get('book', '?')}")
                    # Merge DK lines into valid_props with fuzzy name + stat mapping
                    player_lines = odds_enrichment.get("player_lines", {})
                    stat_map = {"PTS": "points", "REB": "rebounds", "AST": "assists", "3PM": "threePointersMade", "STL": "steals", "BLK": "blocks"}
                    for vp in proj.get("valid_props", []):
                        pl_name = vp.get("player", "")
                        stat_key = vp.get("stat", "")
                        dk_stat = stat_map.get(stat_key)
                        if not dk_stat:
                            continue
                        # Fuzzy player name match (last name or substring)
                        for dk_name in player_lines:
                            if pl_name == dk_name or pl_name in dk_name or dk_name in pl_name:
                                if dk_stat in player_lines[dk_name]:
                                    vp["market_line"] = player_lines[dk_name][dk_stat]
                                break
            except Exception as oe:
                print(f"    ⚠️ Odds enrichment skipped: {oe}")

            # Expand stat map to include all stats (Odds API keys)
            stat_map = {
                "PTS": "points", "REB": "rebounds", "AST": "assists",
                "3PM": "threes", "STL": "steals", "BLK": "blocks",
            }
            # Fuzzy matching helper
            def fuzzy_match(espn_name, dk_name):
                a = espn_name.lower().replace("'", "").replace(".", "")
                b = dk_name.lower().replace("'", "").replace(".", "")
                return a == b or a in b or b in a

            # --- SGO enrichment (NBA player props) ---
            sgo_path = today_dir / f"lines_sgo_{sport.lower()}.json"
            if sport == "NBA" and sgo_path.exists():
                try:
                    sgo_data = json.loads(sgo_path.read_text())
                    events = sgo_data if isinstance(sgo_data, list) else sgo_data.get("data", [])
                    matched_sgo = 0
                    for ev in events:
                        ev_away = ev.get("teams", {}).get("away", {}).get("names", {}).get("short", "")
                        ev_home = ev.get("teams", {}).get("home", {}).get("names", {}).get("short", "")
                        if ev_away.upper() != away.upper() or ev_home.upper() != home.upper():
                            continue
                        odds = ev.get("odds", {})
                        if not odds:
                            continue
                        # Build lookup: player_name -> {stat: bookOverUnder}
                        sgo_lines = {}
                        for odd_key, odd_val in odds.items():
                            if not isinstance(odd_val, dict):
                                continue
                            pid = odd_val.get("playerID", "")
                            if not pid:
                                continue
                            stat = odd_val.get("statID", "")
                            line = odd_val.get("bookOverUnder")
                            if not line or odd_val.get("betTypeID") != "ou":
                                continue
                            # Map SGO stat names to our stat keys
                            sgo_stat_map = {
                                "points": "PTS", "rebounds": "REB", "assists": "AST",
                                "threePointersMade": "3PM", "steals": "STL", "blocks": "BLK",
                            }
                            our_stat = sgo_stat_map.get(stat)
                            if not our_stat:
                                continue
                            player_name = pid.replace("_1_NBA", "").replace("_", " ").title().strip()
                            if player_name not in sgo_lines:
                                sgo_lines[player_name] = {}
                            # SGO lines are integers; Odds API style uses floats
                            sgo_lines[player_name][our_stat] = float(line)
                        # Match enriched DK lines to valid_props
                        for vp in proj.get("valid_props", []):
                            if vp.get("market_line"):
                                continue  # already has a DK line
                            pl_name = vp.get("player", "")
                            stat_key = vp.get("stat", "")
                            for sgo_player, sgo_props in sgo_lines.items():
                                if fuzzy_match(pl_name, sgo_player) and stat_key in sgo_props:
                                    vp["market_line"] = sgo_props[stat_key]
                                    matched_sgo += 1
                                    break
                        if matched_sgo > 0:
                            print(f"    → SGO: {matched_sgo} props enriched ({len(sgo_lines)} players with DK lines)")
                        break  # Found matching event
                except Exception as sgo_e:
                    print(f"    ⚠️ SGO enrichment skipped: {sgo_e}")

            # --- Odds API enrichment (original, kept for WNBA combos) ---
            try:
                odds_enrichment = enrich_player_lines(sport, away, home)
                if odds_enrichment and odds_enrichment.get("player_lines"):
                    proj["odds_api_lines"] = odds_enrichment
                    player_lines = odds_enrichment.get("player_lines", {})
                    stat_map = {"PTS": "points", "REB": "rebounds", "AST": "assists", "3PM": "threes", "STL": "steals", "BLK": "blocks"}
                    odds_count = 0
                    for vp in proj.get("valid_props", []):
                        if vp.get("market_line"):
                            continue  # already has a DK line from SGO
                        pl_name = vp.get("player", "")
                        stat_key = vp.get("stat", "")
                        dk_stat = stat_map.get(stat_key)
                        if not dk_stat:
                            continue
                        # Fuzzy player name match
                        for dk_name in player_lines:
                            a = pl_name.lower().replace("'", "").replace(".", "")
                            b = dk_name.lower().replace("'", "").replace(".", "")
                            if a == b or a in b or b in a:
                                if dk_stat in player_lines[dk_name]:
                                    vp["market_line"] = player_lines[dk_name][dk_stat]
                                    odds_count += 1
                                    break
                    if odds_count > 0:
                        print(f"    → Odds API: {odds_count} props enriched ({odds_enrichment.get('player_count', 0)} players via {odds_enrichment.get('book', '?')})")
            except Exception as oe:
                print(f"    ⚠️ Odds enrichment skipped: {oe}")

            # Save raw projection
            safe = matchup.replace("@", "_at_")
            (today_dir / f"proj_{sport}_{safe}.json").write_text(json.dumps(proj, indent=2))

            # Extract picks + summary
            picks = extract_picks(proj, sport, matchup)
            summary = extract_game_summary(proj, sport, matchup)
            # Mark which picks have a real DK market line
            pending = sum(1 for p in picks if p.get("market_line") in (None, ""))
            summary["pending_props_no_dk"] = pending
            summary["picks_with_dk"] = len(picks) - pending
            all_picks.extend(picks)
            all_summaries.append(summary)
            print(f"    -> {len(picks)} valid picks, signal={summary['signal']} (DK: {len(picks) - pending}, pending: {pending})")

    # Write flat CSV — deduplicated, keeping DK-enriched versions
    csv_path = today_dir / "picks.csv"
    csv_fields = [
        "date", "league", "matchup", "team", "player", "role", "status",
        "stat", "direction", "market_line", "tc_projection", "tc_target",
        "edge", "threshold", "raw_average", "source", "actual", "result",
    ]
    write_header = not csv_path.exists()
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=csv_fields)
        if write_header:
            w.writeheader()
        for p in all_picks:
            row = {k: p.get(k, "") for k in csv_fields}
            w.writerow(row)

    # Write structured picks
    (today_dir / "picks.json").write_text(json.dumps(all_picks, indent=2))
    (today_dir / "summaries.json").write_text(json.dumps(all_summaries, indent=2))

    # Write last_run summary
    last_run = {
        "timestamp": now.isoformat(),
        "sports": list(sports),
        "games_logged": len(all_summaries),
        "picks_logged": len(all_picks),
        "completed_games_skipped": skipped_completed,
        "errors": errors,
        "summaries": all_summaries,
    }
    (LOG_DIR / "last_run.json").write_text(json.dumps(last_run, indent=2))

    print(f"\nDone: {len(all_summaries)} games, {len(all_picks)} picks (skipped {skipped_completed} completed games)")
    if errors:
        print(f"Errors: {len(errors)}")
        for e in errors:
            print(f"  - {e}")

    # ── Build TC-enhanced DK combos (NBA + WNBA) ──
    try:
        from Projects.build_pregame_combos import build_combos, write_report
        combo_games = [(s["sport"], s["away_team"], s["home_team"]) for s in all_summaries]
        print(f"\nBuilding TC combos for {len(combo_games)} games...")
        combo_summary = []
        for sport, away, home in combo_games:
            try:
                r = build_combos(sport, away, home)
            except Exception as e:
                r = {"sport": sport, "away": away, "home": home,
                     "legs": [], "qualified": [], "error": str(e)}
            safe = f"{away}_{home}".lower()
            write_report(r, today_dir / f"combos_{safe}.md", today_dir / f"combos_{safe}.json")
            combo_summary.append({
                "matchup": f"{away}@{home}", "sport": sport,
                "matched": r.get("matched_legs", 0),
                "qualified": r.get("qualified_legs", 0),
            })
        (today_dir / "combos_summary.json").write_text(json.dumps(combo_summary, indent=2))
        print(f"Combos: {sum(c['qualified'] for c in combo_summary)} qualified legs across {len(combo_summary)} games")
    except Exception as e:
        print(f"Combo builder: {e}")

    return last_run


if __name__ == "__main__":
    sports = ("NBA", "WNBA")
    if len(sys.argv) > 1:
        sports = tuple(s.upper() for s in sys.argv[1:])
    run_daily_log(sports)
