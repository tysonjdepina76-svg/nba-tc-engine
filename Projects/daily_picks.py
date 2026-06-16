# TC — Triple Conservative — Trademark June 2026 — All rights reserved.
"""TC Daily Pick Log — captures every pick with full roster context for backtesting.

Runs on a schedule (5 min before tip) and writes:
- /home/workspace/Daily_Log/YYYY-MM-DD/slate_NBA.json  (raw responses)
- /home/workspace/Daily_Log/YYYY-MM-DD/slate_WNBA.json
- /home/workspace/Daily_Log/YYYY-MM-DD/slate_MLB.json
- /home/workspace/Daily_Log/YYYY-MM-DD/slate_WORLD_CUP.json
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

# ── All active sports in the pipeline ─────────────────────
ALL_SPORTS = ("NBA", "WNBA", "MLB", "NHL", "WORLD_CUP")
BASKETBALL = {"NBA", "WNBA"}  # sports with full player props + rosters
MLB_SPORTS = {"MLB"}  # sports with

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
sys.path.insert(0, str(WORKSPACE / "Projects"))

from consensus_engine import fetch_consensus_for_matchup, CONSENSUS_SPORT_MAP, get_best_line
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
        # MLB/WC/NHL props don't have "valid" key — they're pre-filtered by the engine
        if "valid" in p and not p.get("valid"):
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
    # For NBA/WNBA: if no valid props but odds are available, add a TOTAL pick placeholder
    if not picks and sport in BASKETBALL:
        odds = projection.get("odds", {})
        if odds.get("total") is not None:
            picks.append({
                "date": now_et().strftime("%Y-%m-%d"),
                "league": sport,
                "matchup": matchup,
                "team": "",
                "player": "TOTAL",
                "role": "GAME",
                "status": "ACTIVE",
                "stat": "TOTAL",
                "direction": "N/A",
                "market_line": odds.get("total"),
                "tc_projection": projection.get("tc_combined"),
                "tc_target": projection.get("tc_line"),
                "edge": projection.get("edge"),
                "threshold": None,
                "raw_average": None,
                "source": odds.get("ml_source", projection.get("source", "")),
                "actual": None,
                "result": "PENDING",
            })
    # For non-basketball: also add game-level pick if no player props yet
    elif not picks and sport not in BASKETBALL:
        odds = projection.get("odds", {})
        if odds.get("total") is not None:
            picks.append({
                "date": now_et().strftime("%Y-%m-%d"),
                "league": sport,
                "matchup": matchup,
                "team": "",
                "player": "TOTAL",
                "role": "GAME",
                "status": "ACTIVE",
                "stat": "TOTAL",
                "direction": "N/A",
                "market_line": odds.get("total"),
                "tc_projection": projection.get("tc_combined"),
                "tc_target": projection.get("tc_line"),
                "edge": projection.get("edge"),
                "threshold": None,
                "raw_average": None,
                "source": odds.get("ml_source", projection.get("source", "")),
                "actual": None,
                "result": "PENDING",
            })
    return picks


def extract_game_summary(projection, sport, matchup):
    """Extract top-line game summary — handles both basketball and multi-sport."""
    if sport in BASKETBALL:
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
            "pending_props_no_dk": len(projection.get("prop_backtest", {}).get("rows", [])) - len([r for r in projection.get("prop_backtest", {}).get("rows", []) if r.get("market_line")]),
            "picks_with_dk": len([r for r in projection.get("prop_backtest", {}).get("rows", []) if r.get("market_line")]),
        }
    else:
        odds = projection.get("odds", {})
        roster_counts = projection.get("roster_counts", {})
        vp = projection.get("valid_props", [])
        return {
            "date": now_et().strftime("%Y-%m-%d"),
            "sport": sport,
            "matchup": matchup,
            "away_team": projection.get("away_team"),
            "home_team": projection.get("home_team"),
            "tc_combined": projection.get("tc_combined"),
            "tc_line": projection.get("tc_line"),
            "market_total": odds.get("total"),
            "dk_total": odds.get("total"),
            "edge": projection.get("edge"),
            "signal": projection.get("signal", "NO DK LINES"),
            "source": odds.get("ml_source", projection.get("source", "")),
            "valid_prop_count": len(vp),
            "roster_size": sum(roster_counts.values()) if roster_counts else 0,
            "pending_props_no_dk": 0,
            "picks_with_dk": len(vp),
        }


def run_daily_log(sports=ALL_SPORTS):
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
        # For sports with no games today, skip gracefully
        if not raw_games:
            print(f"  No games on slate for {sport} — skipping")
            # Still save empty slate
            (today_dir / f"slate_{sport}.json").write_text(json.dumps(slate, indent=2))
            continue

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

            # Only enrich with player props for basketball sports
            if sport in BASKETBALL:
                # Enrich with live Odds API player prop lines
                odds_enrichment = None
                try:
                    odds_enrichment = enrich_player_lines(sport, away, home)
                    if odds_enrichment and odds_enrichment.get("player_lines"):
                        proj["odds_api_lines"] = odds_enrichment
                        print(f"    → Odds API: {odds_enrichment.get('player_count', 0)} players enriched via {odds_enrichment.get('book', '?')}")
                        player_lines = odds_enrichment.get("player_lines", {})
                        stat_map = {"PTS": "points", "REB": "rebounds", "AST": "assists", "3PM": "threePointersMade", "STL": "steals", "BLK": "blocks"}
                        for vp in proj.get("valid_props", []):
                            pl_name = vp.get("player", "")
                            stat_key = vp.get("stat", "")
                            dk_stat = stat_map.get(stat_key)
                            if not dk_stat:
                                continue
                            for dk_name in player_lines:
                                if pl_name == dk_name or pl_name in dk_name or dk_name in pl_name:
                                    if dk_stat in player_lines[dk_name]:
                                        vp["market_line"] = player_lines[dk_name][dk_stat]
                                    break
                except Exception as oe:
                    print(f"    ⚠️ Odds enrichment skipped: {oe}")

                # Enrich with consensus engine (multi-book fallback)
                try:
                    matchup_key = f"{away}@{home}"
                    cons = fetch_consensus_for_matchup(sport, away, home)
                    if cons and not cons.get("error") and cons.get("players"):
                        cons_count = cons.get("player_count", 0)
                        cons_books = cons.get("available_books", [])
                        proj["consensus"] = cons
                        print(f"    → Consensus: {cons_count} players, {len(cons_books)} books ({', '.join(cons_books[:3])}...)")
                        matched = 0
                        for vp in proj.get("valid_props", []):
                            if vp.get("market_line"):
                                continue
                            line = get_best_line(cons, vp.get("player", ""), vp.get("stat", ""))
                            if line is not None:
                                vp["market_line"] = line
                                vp["consensus_source"] = cons.get("source", "unknown")
                                matched += 1
                        if matched:
                            print(f"    → Merged: {matched} props enriched with consensus lines")
                    else:
                        print(f"    ⚠️ Consensus: no data ({cons.get('error', 'no players') if cons else 'null'})")
                except Exception as ce:
                    print(f"    ⚠️ Consensus enrichment skipped: {ce}")
            else:
                # Non-basketball: log DK lines
                odds = proj.get("odds", {})
                if odds.get("total"):
                    print(f"    → DK lines: total={odds.get('total')}, spread={odds.get('home_spread')}, source={odds.get('ml_source', '?')}")
                else:
                    print(f"    → No DK lines available ({odds.get('ml_source', odds.get('source', '?'))})")

            # Save raw projection
            safe = matchup.replace("@", "_at_")
            (today_dir / f"proj_{sport}_{safe}.json").write_text(json.dumps(proj, indent=2))

            # Extract picks + summary
            picks = extract_picks(proj, sport, matchup)
            summary = extract_game_summary(proj, sport, matchup)
            if sport in BASKETBALL:
                pending = sum(1 for p in picks if p.get("market_line") in (None, ""))
                summary["pending_props_no_dk"] = pending
                summary["picks_with_dk"] = len(picks) - pending
            all_picks.extend(picks)
            all_summaries.append(summary)
            if sport in BASKETBALL:
                print(f"    -> {len(picks)} valid picks, signal={summary['signal']} (DK: {len(picks) - pending}, pending: {pending})")
            else:
                print(f"    -> {len(picks)} game-level entries, signal={summary['signal']}")

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

    # ── Build TC-enhanced DK combos (WNBA only) ──
    try:
        from Projects.build_pregame_combos import build_combos, write_report
        combo_games = [(s["sport"], s["away_team"], s["home_team"]) for s in all_summaries if s["sport"] == "WNBA"]
        if combo_games:
            print(f"\nBuilding TC combos for {len(combo_games)} basketball games...")
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
    sports_order = ["WNBA", "MLB"]
    if len(sys.argv) > 1:
        sports = tuple(s.upper() for s in sys.argv[1:])
    else:
        sports = sports_order
    run_daily_log(sports)
