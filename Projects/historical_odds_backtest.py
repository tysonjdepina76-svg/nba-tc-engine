#!/usr/bin/env python3
"""Game-Level Historical Backtest — compares TC projections vs historical closing lines.

Uses The Odds API $30/mo tier:
  /v4/historical/sports/{sport}/odds → game-level (h2h, spreads, totals) with 10-min snapshots
  /v4/sports/{sport}/events/{id}/odds  → live player props (for current slate enrichment)

Backtests:
  - TC combined total vs DK market total (edge accuracy, OVER/UNDER signals)
  - TC spread projections vs DK closing spreads
  - Game-level hit rates across all WNBA dates in Daily_Log
"""

import json, csv, os, sys, requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict

ODDS_API_KEY = os.environ.get("ODDS_API_KEY", "")
BASE_URL = "https://api.the-odds-api.com"
WORKSPACE = Path("/home/workspace")
LOG_DIR = WORKSPACE / "Daily_Log"
BACKTEST_DIR = LOG_DIR / "backtests"
BACKTEST_DIR.mkdir(parents=True, exist_ok=True)

# Team name mapping: ESPN abbrev → Odds API full name
WNBA_ABBREV_TO_FULL = {
    "ATL": "Atlanta Dream",
    "CHI": "Chicago Sky",
    "CON": "Connecticut Sun",
    "DAL": "Dallas Wings",
    "GS": "Golden State Valkyries",
    "IND": "Indiana Fever",
    "LV": "Las Vegas Aces",
    "LA": "Los Angeles Sparks",
    "MIN": "Minnesota Lynx",
    "NY": "New York Liberty",
    "PHX": "Phoenix Mercury",
    "POR": "Portland Fire",
    "SEA": "Seattle Storm",
    "TOR": "Toronto Tempo",
    "WSH": "Washington Mystics",
}

NBA_ABBREV_TO_FULL = {
    "ATL": "Atlanta Hawks", "BOS": "Boston Celtics", "BKN": "Brooklyn Nets",
    "CHA": "Charlotte Hornets", "CHI": "Chicago Bulls", "CLE": "Cleveland Cavaliers",
    "DAL": "Dallas Mavericks", "DEN": "Denver Nuggets", "DET": "Detroit Pistons",
    "GS": "Golden State Warriors", "HOU": "Houston Rockets", "IND": "Indiana Pacers",
    "LAC": "Los Angeles Clippers", "LAL": "Los Angeles Lakers", "MEM": "Memphis Grizzlies",
    "MIA": "Miami Heat", "MIL": "Milwaukee Bucks", "MIN": "Minnesota Timberwolves",
    "NO": "New Orleans Pelicans", "NYK": "New York Knicks", "OKC": "Oklahoma City Thunder",
    "ORL": "Orlando Magic", "PHI": "Philadelphia 76ers", "PHX": "Phoenix Suns",
    "POR": "Portland Trail Blazers", "SAC": "Sacramento Kings", "SAS": "San Antonio Spurs",
    "TOR": "Toronto Raptors", "UTA": "Utah Jazz", "WSH": "Washington Wizards",
}

SPORT_TO_KEY = {"NBA": "basketball_nba", "WNBA": "basketball_wnba"}

def fetch_historical_game_odds(sport, game_date_str):
    """Fetch historical game-level odds (h2h, spreads, totals) for a date.
    Returns { (away_full, home_full): { spread, total, h2h } } keyed by DK lines.
    """
    sport_key = SPORT_TO_KEY.get(sport)
    if not sport_key:
        return {}
    
    # Use 22:00 UTC (6 PM ET) as snapshot time — close to game time
    date_iso = f"{game_date_str}T22:00:00Z"
    
    try:
        r = requests.get(f"{BASE_URL}/v4/historical/sports/{sport_key}/odds", params={
            "apiKey": ODDS_API_KEY,
            "regions": "us",
            "markets": "h2h,spreads,totals",
            "oddsFormat": "decimal",
            "date": date_iso,
        }, timeout=15)
        if not r.ok:
            return {}
        
        data = r.json()
        result = {}
        for g in data.get("data", []):
            away = g.get("away_team", "")
            home = g.get("home_team", "")
            dk_data = {}
            for bk in g.get("bookmakers", []):
                if bk.get("key") == "draftkings":
                    for m in bk.get("markets", []):
                        mk = m.get("key", "")
                        if mk == "h2h":
                            dk_data["h2h"] = {o["name"]: o["price"] for o in m.get("outcomes", [])}
                        elif mk == "spreads":
                            dk_data["spread"] = {o["name"]: o["point"] for o in m.get("outcomes", [])}
                        elif mk == "totals":
                            dk_data["total"] = {o["name"]: o["point"] for o in m.get("outcomes", [])}
                    break
            if dk_data:
                result[(away, home)] = dk_data
        return result
    except Exception as e:
        print(f"  ⚠️ History fetch error {game_date_str}: {e}")
        return {}


def resolve_team(abbrev, sport):
    """Resolve ESPN team abbreviation to Odds API full name."""
    mapping = WNBA_ABBREV_TO_FULL if sport == "WNBA" else NBA_ABBREV_TO_FULL
    return mapping.get(abbrev, abbrev)


def find_daily_log_dates():
    """Find all dates in Daily_Log that have projection files."""
    dates = set()
    for d in sorted(LOG_DIR.iterdir()):
        if not d.is_dir() or not d.name.startswith("20"):
            continue
        proj_files = list(d.glob("proj_*.json"))
        if proj_files:
            dates.add(d.name)
    return sorted(dates)


def backtest_game_level(dates, sports=("WNBA",)):
    """Run game-level backtest comparing TC projections vs historical DK lines."""
    all_rows = []
    
    for date_str in dates:
        print(f"\n📅 {date_str}")
        date_dir = LOG_DIR / date_str
        
        for sport in sports:
            sport_key = SPORT_TO_KEY.get(sport)
            if not sport_key:
                continue
            
            # Fetch historical game odds for this date
            hist_odds = fetch_historical_game_odds(sport, date_str)
            if not hist_odds:
                print(f"  ⚠️ No historical odds for {sport} on {date_str}")
                continue
            
            print(f"  {len(hist_odds)} games in historical odds")
            
            # Process each projection file
            for proj_file in sorted(date_dir.glob(f"proj_{sport}_*.json")):
                try:
                    proj = json.loads(proj_file.read_text())
                except:
                    continue
                
                away_abbrev = proj.get("away_team", "")
                home_abbrev = proj.get("home_team", "")
                if not away_abbrev or not home_abbrev:
                    continue
                
                away_full = resolve_team(away_abbrev, sport)
                home_full = resolve_team(home_abbrev, sport)
                matchup = f"{away_abbrev}@{home_abbrev}"
                
                # Find matching historical game
                game_key = None
                for (a, h) in hist_odds:
                    if (away_full in a or a in away_full) and (home_full in h or h in home_full):
                        game_key = (a, h)
                        break
                
                if not game_key:
                    continue
                
                hist = hist_odds[game_key]
                print(f"  ✅ {matchup}")
                
                # TC projections from the projection file
                tc_combined = proj.get("tc_combined")
                tc_line = proj.get("tc_line")
                market_total = proj.get("market_total")
                dk_total_from_proj = proj.get("dk_total")
                
                # Historical DK closing data
                hist_spread = hist.get("spread", {})
                hist_total = hist.get("total", {}).get("Over")  # Over/Under point is same
                hist_h2h = hist.get("h2h", {})
                
                row = {
                    "date": date_str,
                    "sport": sport,
                    "matchup": matchup,
                    "away": away_abbrev,
                    "home": home_abbrev,
                    "tc_combined": tc_combined,
                    "tc_line": tc_line,
                    "proj_market_total": market_total,
                    "proj_dk_total": dk_total_from_proj,
                    "hist_dk_total": hist_total,
                    "hist_dk_spread_away": hist_spread.get(away_full),
                    "hist_dk_spread_home": hist_spread.get(home_full),
                    "hist_h2h_away": hist_h2h.get(away_full),
                    "hist_h2h_home": hist_h2h.get(home_full),
                    "edge": proj.get("edge"),
                    "signal": proj.get("signal"),
                    "valid_prop_count": len(proj.get("valid_props", [])),
                }
                
                # Compute game-level accuracy metrics
                if tc_combined is not None and hist_total is not None:
                    row["tc_vs_hist_total_edge"] = round(tc_combined - hist_total, 1)
                    row["tc_total_over"] = tc_combined > hist_total
                    row["tc_total_under"] = tc_combined < hist_total
                
                all_rows.append(row)
    
    return all_rows


def generate_report(rows):
    """Generate backtest report from rows."""
    if not rows:
        return "# Historical Odds Backtest\n\nNo data available for backtesting.\n"
    
    lines = [
        "# Game-Level Historical Odds Backtest — WNBA",
        f"**Run:** {datetime.now().strftime('%Y-%m-%d %H:%M %Z')}",
        f"**Games matched:** {len(rows)}",
        "",
        "## TC Total vs DK Closing Total",
    ]
    
    # Total accuracy
    total_matches = [r for r in rows if r.get("tc_vs_hist_total_edge") is not None]
    if total_matches:
        edges = [r["tc_vs_hist_total_edge"] for r in total_matches]
        avg_edge = sum(edges) / len(edges)
        over_count = sum(1 for r in total_matches if r.get("tc_total_over"))
        under_count = sum(1 for r in total_matches if r.get("tc_total_under"))
        
        lines += [
            f"- **Games:** {len(total_matches)}",
            f"- **Avg TC edge vs DK close:** {avg_edge:+.1f} pts",
            f"- **TC projected OVER:** {over_count} games",
            f"- **TC projected UNDER:** {under_count} games",
            "",
            "| Matchup | TC Combined | DK Close Total | Edge | TC Signal |",
            "|---------|------------|---------------|------|-----------|",
        ]
        for r in sorted(total_matches, key=lambda x: x.get("tc_vs_hist_total_edge", 0) or 0, reverse=True):
            edge = r.get("tc_vs_hist_total_edge", "?")
            edge_str = f"+{edge:.1f}" if edge and edge >= 0 else f"{edge:.1f}" if edge else "?"
            signal = r.get("signal", "?")
            lines.append(
                f"| {r['matchup']} | {r['tc_combined']} | {r['hist_dk_total']} | {edge_str} | {signal} |"
            )
    
    lines += [
        "",
        "## Per-Date Breakdown",
    ]
    
    date_counts = defaultdict(list)
    for r in rows:
        date_counts[r["date"]].append(r)
    
    for d in sorted(date_counts):
        games = date_counts[d]
        total_with_edge = [r for r in games if r.get("tc_vs_hist_total_edge") is not None]
        if total_with_edge:
            avg_e = sum(r["tc_vs_hist_total_edge"] for r in total_with_edge) / len(total_with_edge)
            lines.append(f"- **{d}:** {len(games)} games, avg TC edge {avg_e:+.1f}")
        else:
            lines.append(f"- **{d}:** {len(games)} games")
    
    lines += [
        "",
        "## Notes",
        "- Player props historical data requires higher tier (not available on $30/mo plan)",
        "- Game-level data uses 6 PM ET closing snapshot from DK",
        "- TC combined = 0.88 × projected team total (conservative adjustment)",
    ]
    
    return "\n".join(lines)


def main():
    dates = find_daily_log_dates()
    print(f"📊 Found {len(dates)} dates with projections: {', '.join(dates[-7:])}")
    
    if not dates:
        print("No projection dates found in Daily_Log.")
        return
    
    # Backtest last 7 days
    backtest_dates = dates[-7:]
    rows = backtest_game_level(backtest_dates)
    
    if not rows:
        print("No matches found between projections and historical odds.")
        return
    
    # Save
    ts = datetime.now().strftime("%Y-%m-%d")
    csv_path = BACKTEST_DIR / f"odds_backtest_{ts}.csv"
    json_path = BACKTEST_DIR / f"odds_backtest_{ts}.json"
    report_path = BACKTEST_DIR / f"odds_backtest_report_{ts}.md"
    
    # CSV
    if rows:
        with open(csv_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=rows[0].keys())
            w.writeheader()
            w.writerows(rows)
    
    json_path.write_text(json.dumps(rows, indent=2))
    report_path.write_text(generate_report(rows))
    
    print(f"\n✅ CSV: {csv_path}")
    print(f"✅ JSON: {json_path}")
    print(f"✅ Report: {report_path}")
    
    # Quick summary
    total_with_edge = [r for r in rows if r.get("tc_vs_hist_total_edge") is not None]
    if total_with_edge:
        avg_e = sum(r["tc_vs_hist_total_edge"] for r in total_with_edge) / len(total_with_edge)
        print(f"\n📊 Summary: {len(rows)} games, avg TC edge vs DK close: {avg_e:+.1f}")
    else:
        print(f"\n📊 Summary: {len(rows)} games matched (no game-level edge data)")

if __name__ == "__main__":
    main()
