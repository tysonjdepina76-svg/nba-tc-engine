#!/usr/bin/env python3
"""
Historical Odds Backtest — pulls closing lines + results for WC/MLB/NHL/WNBA/NBA.
Outputs to /home/workspace/Daily_Log/backtests/YYYY-MM-DD/
"""
import json, os, re, requests, sys
from datetime import datetime, timedelta
from pathlib import Path

ODDS_KEY = os.environ.get("ODDS_API_KEY", "")
if not ODDS_KEY:
    secrets = Path("/root/.zo/secrets.env").read_text()
    m = re.search(r'^ODDS_API_KEY=(\S+)', secrets, re.MULTILINE)
    ODDS_KEY = m.group(1) if m else ""

BASE = "https://api.the-odds-api.com/v4"
SPORTS = {
    "mlb": "baseball_mlb",
    "nhl": "icehockey_nhl",
    "wnba": "basketball_wnba",
    "nba": "basketball_nba",
    "worldcup": "soccer_fifa_world_cup",
}

OUT_DIR = Path(f"/home/workspace/Daily_Log/backtests/{datetime.now().strftime('%Y-%m-%d')}")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def fmt_date(d):
    return d.strftime("%Y-%m-%dT12:00:00Z")

def fetch_historical(sport_key, date_str):
    """Pull closing lines for a sport on a given date."""
    url = f"{BASE}/historical/sports/{sport_key}/odds"
    params = {"apiKey": ODDS_KEY, "date": date_str, "markets": "h2h,spreads,totals"}
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data.get("data", [])

def fetch_scores(sport_key, date_str):
    """Pull final scores (if available)."""
    url = f"{BASE}/historical/sports/{sport_key}/scores"
    params = {"apiKey": ODDS_KEY, "date": date_str}
    r = requests.get(url, params=params, timeout=30)
    if r.status_code == 404:
        return []
    r.raise_for_status()
    return r.json()

def main():
    today = datetime.now()
    results = {}
    
    for label, sport_key in SPORTS.items():
        print(f"\n[{label.upper()}] Fetching {sport_key}...")
        try:
            # Last 7 days of data
            all_lines = []
            for d in range(7, 0, -1):
                date = today - timedelta(days=d)
                date_str = fmt_date(date)
                try:
                    lines = fetch_historical(sport_key, date_str)
                    if lines:
                        print(f"  {date_str[:10]} -> {len(lines)} games")
                        all_lines.extend(lines)
                except Exception as e:
                    print(f"  {date_str[:10]} -> {e}")
            
            # Save
            fname = f"{label}_historical_lines.json"
            (OUT_DIR / fname).write_text(json.dumps(all_lines, indent=2))
            
            # Extract summary stats
            game_count = len(all_lines)
            results[label] = {"games": game_count, "sport_key": sport_key}
            print(f"  Saved {game_count} games to {fname}")
            
        except Exception as e:
            print(f"  ERROR: {e}")
            results[label] = {"error": str(e)}
    
    # Save summary
    summary = {
        "generated": datetime.now().isoformat(),
        "sports": results,
        "output_dir": str(OUT_DIR),
    }
    (OUT_DIR / "backtest_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\n✅ Saved summary to {OUT_DIR}/backtest_summary.json")
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
