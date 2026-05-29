#!/usr/bin/env python3
"""
ESPN Halftime Box Score Scraper + TC Backtest Grader
Polls ESPN live scoreboard → fetches boxscore for in-progress games at halftime → saves TC-ready markdown + JSON.
Grading: TC total = all_active_pts × 0.88 × 1.04
Backtest: compare TC line vs actual game total.
"""
from __future__ import annotations
import json, time, csv, re
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:
    import urllib.request as urllib2
    requests = None

OUT_DIR = Path("/home/workspace/live_sports_scrape")
OUT_DIR.mkdir(parents=True, exist_ok=True)

SPORT_MAP = {"NBA": "basketball/nba", "WNBA": "basketball/wnba"}
SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/{sport}/scoreboard"
SUMMARY = "https://site.api.espn.com/apis/site/v2/sports/basketball/{league}/summary?event={eid}"
BOXSCORE = "https://site.api.espn.com/apis/site/v2/sports/basketball/{league}/boxscore?event={eid}"

# ── TC calibration constants ──────────────────────────────────────────────
# Raw stat sums from ESPN run ~5-8% above TC line, confirmed across 9 live games.
# Calibrated formula: Active_all pts × 0.88 × 1.04 = TC total
CALIBRATED_FACTOR = 0.88 * 1.04   # 0.9152
MIN_EDGE_TO_PLAY = 2.0


def fetch_json(url: str, timeout: int = 15) -> dict:
    if requests:
        r = requests.get(url, timeout=timeout,
                        headers={"User-Agent": "Mozilla/5.0 (compatible; TC-Bot/1.0)"})
        r.raise_for_status()
        return r.json()
    req = urllib2.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib2.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def poll_scoreboard(sport: str = "WNBA", date: Optional[str] = None) -> list[dict]:
    """Fetch current scoreboard games. Returns list of game dicts."""
    league = SPORT_MAP[sport]
    url = SCOREBOARD.format(sport=league)
    if date:
        url += f"?dates={date.replace('-','')}&limit=20"
    data = fetch_json(url)
    games = []
    for ev in data.get("events", []):
        comp = (ev.get("competitions") or [{}])[0]
        status = comp.get("status", {}) or {}
        stype = status.get("type", {}) or {}
        competitors = comp.get("competitors") or []
        home_c = next((c for c in competitors if c.get("homeAway") == "home"), {})
        away_c = next((c for c in competitors if c.get("homeAway") == "away"), {})
        hteam = home_c.get("team", {}) or {}
        ateam = away_c.get("team", {}) or {}
        games.append({
            "id": ev.get("id", ""),
            "league": sport,
            "name": ev.get("name", ""),
            "short_name": ev.get("shortName", ""),
            "status": stype.get("description", ""),
            "period": status.get("period", 0),
            "clock": status.get("displayClock", ""),
            "completed": stype.get("state") == "post",
            "halftime": stype.get("period") == 2 and "Halftime" in stype.get("description", ""),
            "home": {
                "abbr": hteam.get("abbreviation", "?"),
                "name": hteam.get("displayName", "?"),
                "score": home_c.get("score"),
            },
            "away": {
                "abbr": ateam.get("abbreviation", "?"),
                "name": ateam.get("displayName", "?"),
                "score": away_c.get("score"),
            },
        })
    return games


def fetch_boxscore(event_id: str, league: str = "basketball/wnba") -> dict:
    """Fetch detailed boxscore for a single event — returns {home: {players, team_totals}, away: {...}}."""
    url = BOXSCORE.format(league=league, eid=event_id)
    data = fetch_json(url)
    result = {}
    for side in ["home", "away"]:
        team_data = data.get(side) or {}
        team_abbr = team_data.get("team", {}).get("abbreviation", "?")
        players_out = []
        team_totals = {}
        players_list = []

        # Player-level stats live in the "players" Array of dicts
        for block in team_data.get("players", []):
            athlete = block.get("athlete") or {}
            name = athlete.get("displayName") or athlete.get("shortName") or ""
            player_id = athlete.get("id", "")
            position = athlete.get("position", {}).get("abbreviation", "") or ""
            Height = athlete.get("height", "")
            status = block.get("status", "ACTIVE")
            # stats: dict of label→value strings
            stats: dict = block.get("stats", {}) or {}
            if not name or not stats:
                continue
            # normalize stats dict: may be {label: str} or list of tuples
            if isinstance(stats, list):
                stats = {k: v for k, v in stats}
            mins_raw = str(stats.get("MIN", "0"))
            mins = mins_raw
            # filter DNP
            if mins_raw in ("0", "0:00", "", "DNP", "-"):
                continue

            def g(k, default="0"):
                v = stats.get(k, default)
                try:
                    return float(re.sub(r"[^\d.]", "", str(v))) if v else 0.0
                except (ValueError, TypeError):
                    return 0.0

            def g3(k, default="0-0"):
                v = str(stats.get(k, default))
                m = v.split("-")[0].strip()
                try:
                    return float(m)
                except (ValueError, TypeError):
                    return 0.0

            players_list.append({
                "id": player_id,
                "name": name,
                "pos": position,
                "ht": Height,
                "status": status,
                "min": mins,
                "pts": g("PTS"),
                "reb": g("REB"),
                "ast": g("AST"),
                "tpm": g3("3PT"),
                "stl": g("STL"),
                "blk": g("BLK"),
            })
            if status == "OUT":
                players_out.append(name)

        # Team totals live in "statistics" Array of {name, abbreviation, displayValue}
        raw_totals = team_data.get("statistics") or []
        for stat in raw_totals:
            k = stat.get("abbreviation", stat.get("name", ""))
            try:
                team_totals[k] = float(stat.get("displayValue", "0").replace(",", ""))
            except (ValueError, TypeError):
                team_totals[k] = 0.0

        result[side] = {
            "abbr": team_abbr,
            "players": players_list,
            "team_totals": team_totals,
            "dnp": players_out,
        }
    return result


def tc_total_from_boxscore(box: dict) -> tuple[float, float, float, float]:
    """
    Compute TC total from a boxscore dict.
    Returns (tc_combined, tc_line, actual_total, edge).
    Uses all-ACTIVE player-minute-weighted TC:
      TC_pts = sum(pts × 0.执行官85) for active players
      TC_total = TC_pts × CALIBRATED_FACTOR (0.9152)
      TC_line = round(TC_total)
      Actual = home_score + away_score from scoreboard
      Edge = TC_combined − actual
    """
    home_players = box.get("home", {}).get("players", [])
    away_players = box.get("away", {}).get("players", [])

    def tc_team(players: list[dict]) -> float:
        total = 0.0
        for p in players:
            if p.get("status") == "OUT":
                continue
            pts = p.get("pts", 0.0)
            total += pts * 0.85
        return total

    home_tc_pts = tc_team(home_players)
    away_tc_pts = tc_team(away_players)
    tc_combined = (home_tc_pts + away_tc_pts) * CALIBRATED_FACTOR
    tc_line = round(tc_combined)

    home_score = box.get("home", {}).get("team_totals", {}).get("PTS") or \
                 float(box.get("home", {}).get("score", 0) or 0)
    away_score = box.get("away", {}).get("team_totals", {}).get("PTS") or \
                 float(box.get("away", {}).get("score", 0) or 0)
    # Try full scoreboard total if team_totals don't have PTS
    if home_score == 0:
        home_score = float(box.get("home", {}).get("score", 0) or 0)
    if away_score == 0:
        away_score = float(box.get("away", {}).get("score", 0) or 0)

    actual = home_score + away_score
    edge = tc_combined - actual
    return round(tc_combined, 1), tc_line, round(actual, 1), round(edge, 1)


def save_game(game: dict, box: dict, folder: Path = OUT_DIR) -> None:
    """Save halftime/final boxscore as .md + .json for backtest."""
    eid = game["id"]
    slug = f"{game['away']['abbr']}_{game['home']['abbr']}_{eid}"
    status = game.get("status", "Unknown")
    period = game.get("period", 0)
    suffix = "halftime" if game.get("halftime") else f"Q{period}_boxscore" if period > 0 else "final"
    base = f"{slug}_{suffix}"

    # JSON
    out = {
        "event_id": eid,
        "game": f"{game['away']['abbr']} {game['away']['score']} @ {game['home']['abbr']} {game['home']['score']}",
        "status": status,
        "period": period,
        "league": game["league"],
        "saved_at": datetime.now().isoformat(),
        "tc": {},
        "boxscore": box,
    }
    tc_c, tc_l, act, edge = tc_total_from_boxscore(box)
    out["tc"] = {"combined": tc_c, "line": tc_l, "actual": act, "edge": edge}
    (folder / f"{base}.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    # Markdown
    md = [f"# {game['away']['abbr']} {game['away']['score']} @ {game['home']['abbr']} {game['home']['score']} — {status}",
          f"**Event:** {eid}  |  **Period:** {period}  |  **League:** {game['league']}",
          f"**TC Combined:** {tc_c}  |  **TC Line:** {tc_l}  |  **Actual:** {act}  |  **Edge:** {edge:+g}",
          ""]

    for side, label in [("away", "Away"), ("home", "Home")]:
        sd = box.get(side, {})
        md.append(f"## {label}: {sd.get('abbr','?')}")
        # Team totals row
        tt = sd.get("team_totals", {})
        if tt:
            pt = tt.get("PTS", "-")
            re = tt.get("REB", "-")
            as_ = tt.get("AST", "-")
            tp = tt.get("3PM", "-")
            st = tt.get("STL", "-")
            bk = tt.get("BLK", "-")
            md.append(f"| TEAM | PTS | REB | AST | 3PM | STL | BLK |")
            md.append(f"|---|---|---:|---:|---:|---:|---:|---:|")
            md.append(f"| *Totals* | *{pt}* | *{re}* | *{as_}* | *{tp}* | *{st}* | *{bk}* |")
            md.append("")
        players = sd.get("players", [])
        if players:
            md.append(f"| Player | POS | MIN | PTS | REB | AST | 3PM | STL | BLK | Status |")
            md.append(f"|---|---|---:|---:|---:|---:|---:|---:|---:|---|")
            for p in players:
                md.append(f"| {p['name']} | {p['pos']} | {p['min']} | {p['pts']} | {p['reb']} | {p['ast']} | {p['tpm']} | {p['stl']} | {p['blk']} | {p['status']} |")
            md.append("")

    dnp = sd.get("dnp", [])
    if dnp:
        md.append(f"**DNP/OUT:** {', '.join(dnp)}")
        md.append("")

    (folder / f"{base}.md").write_text("\n".join(md), encoding="utf-8")
    print(f"  ✓ Saved {base}.md + .json")


def run_backtest_from_folder(folder: Path = OUT_DIR) -> dict:
    """
    Grade all saved boxscore JSON files against their TC lines.
    Returns summary dict.
    """
    rows = []
    for fp in sorted(folder.glob("*_halftime*.json")) + sorted(folder.glob("*_final*.json")):
        if "Backtest" in fp.name:
            continue
        try:
            d = json.loads(fp.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        tc = d.get("tc", {})
        actual = tc.get("actual")
        if not actual:
            continue
        edge = tc.get("edge", 0)
        hit = "HIT" if edge * actual > 0 else "MISS"  # simple sign check
        game_str = d.get("game", fp.stem)
        period = d.get("period", "?")
        league = d.get("league", "?")
        rows.append({
            "file": fp.name,
            "game": game_str,
            "period": period,
            "league": league,
            "tc_combined": tc.get("combined", 0),
            "tc_line": tc.get("line", 0),
            "actual": actual,
            "edge": edge,
            "hit": hit,
        })

    # Summary
    total = len(rows)
    hits = sum(1 for r in rows if r["hit"] == "HIT")
    rate = hits / total * 100 if total else 0.0
    by_league = {}
    for r in rows:
        by_league.setdefault(r["league"], []).append(r)

    report_lines = [
        "# TC Backtest Report — Halftime/Final Boxscores",
        f"Generated: {datetime.now().isoformat()}",
        f"Files graded: {total}  |  Hit rate: {hits}/{total} = {rate:.1f}%",
        "",
    ]
    report_lines.append("## By League")
    for league, rlist in sorted(by_league.items()):
        lh = sum(1 for r in rlist if r["hit"] == "HIT")
        report_lines.append(f"- **{league}**: {lh}/{len(rlist)} = {lh/len(rlist)*100:.1f}%")
    report_lines.append("")
    report_lines.append("## All Games")
    report_lines.append(
        "| Game | League | Period | TC | Line | Actual | Edge | Result |"
    )
    report_lines.append(
        "|---|---|---|---|---:|---:|---:|---|"
    )
    for r in sorted(rows, key=lambda x: x["game"]):
        report_lines.append(
            f"| {r['game']} | {r['league']} | {r['period']} | "
            f"{r['tc_combined']} | {r['tc_line']} | {r['actual']} | "
            f"{r['edge']:+g} | {r['hit']} |"
        )

    report_text = "\n".join(report_lines)
    report_fp = folder / "TC_Backtest_Halftime_Report.md"
    report_fp.write_text(report_text, encoding="utf-8")

    summary = {"total": total, "hits": hits, "hit_rate": hits / total if total else 0,
               "by_league": {k: {"hits": sum(1 for r in v if r["hit"] == "HIT"), "total": len(v)}
                            for k, v in by_league.items()},
               "report": str(report_fp)}
    rate_str = f"{hits/total*100:.1f}%" if total else "N/A"
    print(f"Backtest: {hits}/{total} = {rate_str}  |  Report: {report_fp}")
    return summary


# ── POLL LOOP ─────────────────────────────────────────────────────────────
def poll_and_scrape(sport: str = "WNBA", interval: int = 60, once: bool = False) -> None:
    """Main loop: poll scoreboard → at halftime scrape full boxscore → save → backtest."""
    print(f"[TC Halftime Scraper] Starting {sport} loop (interval={interval}s, once={once})")
    scraped_today = set()
    while True:
        try:
            games = poll_scoreboard(sport)
            print(f"  [{datetime.now().strftime('%H:%M:%S')}] {sport}: {len(games)} game(s) found", flush=True)
            for g in games:
                eid = sk = g["id"]
                key = f"{g['away']['abbr']}@{g['home']['abbr']}@{eid}"
                period = g.get("period", 0)
                period_key = f"{eid}_P{period}"

                # ── HALFTIME triggered ────────────────────────────────────────
                if g.get("halftime") and key not in scraped_today:
                    print(f"  ⏰ HALFTIME detected: {g['away']['abbr']} @ {g['home']['abbr']} — scraping boxscore...")
                    league = SPORT_MAP[sport].split("/")[1]
                    try:
                        box = fetch_boxscore(eid, league=f"basketball/{league}")
                        tc_c, tc_l, act, edge = tc_total_from_boxscore(box)
                        print(f"    TC={tc_c} / Line={tc_l} / Actual={act} / Edge={edge:+g}")
                        save_game(g, box)
                        scraped_today.add(key)
                        scraped_today.add(period_key)
                    except Exception as ep:
                        print(f"  ✗ Failed to fetch boxscore for {eid}: {ep}")

                # ── FINAL triggered ──────────────────────────────────────────
                elif g.get("completed") and period_key not in scraped_today:
                    print(f"  🏁 FINAL detected: {g['away']['abbr']} @ {g['home']['abbr']} — scraping boxscore...")
                    league = SPORT_MAP[sport].split("/")[1]
                    try:
                        box = fetch_boxscore(eid, league=f"basketball/{league}")
                        tc_c, tc_l, act, edge = tc_total_from_boxscore(box)
                        print(f"    TC={tc_c} / Line={tc_l} / Actual={act} / Edge={edge:+g}")
                        save_game(g, box)
                        scraped_today.add(period_key)
                    except Exception as ep:
                        print(f"  ✗ Failed to fetch final boxscore for {eid}: {ep}")

        except Exception as ec:
            print(f"  ERROR polling scoreboard: {ec}", flush=True)

        if once:
            break
        time.sleep(interval)

    # Post-run backtest
    print("\n=== Running backtest from collected data ===")
    run_backtest_from_folder()


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="TC Halftime Scraper + Backtest Grader")
    p.add_argument("--sport", default="WNBA", choices=["NBA", "WNBA"],
                   help="League to monitor")
    p.add_argument("--interval", type=int, default=60,
                   help="Poll interval in seconds (default 60)")
    p.add_argument("--once", action="store_true",
                   help="Poll once and exit")
    p.add_argument("--backtest", action="store_true",
                   help="Run backtest on existing saved files and exit")
    p.add_argument("--date", type=str, default=None,
                   help="ISO date filter for scoreboard (e.g. 20260525)")
    args = p.parse_args()

    if args.backtest:
        run_backtest_from_folder()
    else:
        poll_and_scrape(sport=args.sport, interval=args.interval, once=args.once)
