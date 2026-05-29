#!/usr/bin/env python3
"""
NBA Odds Fetcher — Triple Conservative Pipeline
================================================
Fetches live odds from The Odds API v4, applies TC formulas,
and outputs edge-qualified picks.

Usage:
  python odds_fetcher.py --sport basketball_nba --regions us --markets h2h,spreads,totals
  python odds_fetcher.py --mode tc --date 2026-04-27
  python odds_fetcher.py --help
"""

import argparse
import json
import os
import sys
from datetime import datetime, date
from pathlib import Path

try:
    import requests
except ImportError:
    print("❌ requests not installed. Run: pip install -r requirements.txt")
    sys.exit(1)

# ─── CONFIG ───────────────────────────────────────────────────────────────────
ODDS_API_KEY = os.environ.get("ODDS_API_KEY") or os.environ.get("ODDS_API_SECRET")
BASE_URL = "https://api.the-odds-api.com/v4"

ODDS_DIR = Path.home() / ".zo" / "odds"
ODDS_DIR.mkdir(parents=True, exist_ok=True)

# Default bookmakers (sharpest books for best lines)
DEFAULT_BOOKMAKERS = ["draftkings", "fanduel", "betmgm", "caesars", "pinnacle"]

SPORT_OPTIONS = {
    "NBA": "basketball_nba",
    "WNBA": "basketball_wnba",
}

DEFAULT_MARKETS = "h2h,spreads,totals"

# ─── TC CONSTANTS (from triple_conservative_v5.py) ────────────────────────────
PLAYER_FACTOR = 0.85
TEAM_FACTOR   = 0.88
EDGE_THRESHOLD_LEG   = 2.0
EDGE_THRESHOLD_PROP  = 3.0
CONFIDENCE_THRESHOLD = 0.88

# ─── API HELPERS ───────────────────────────────────────────────────────────────
def get_sports(api_key: str) -> list[dict]:
    url = f"{BASE_URL}/sports"
    r = requests.get(url, params={"apiKey": api_key}, timeout=10)
    r.raise_for_status()
    return r.json()

def get_odds(api_key: str, sport: str, regions: str = "us",
             markets: str = "h2h,spreads,totals",
             bookmakers: str = "") -> dict:
    url = f"{BASE_URL}/sports/{sport}/odds"
    params = {
        "apiKey": api_key,
        "regions": regions,
        "markets": markets,
        "oddsFormat": "american",
    }
    if bookmakers:
        params["bookmakers"] = bookmakers
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    return r.json()

# ─── ODDS PARSING ─────────────────────────────────────────────────────────────
def parse_h2h(markets: list) -> dict | None:
    for m in markets:
        if m.get("key") == "h2h":
            outcomes = m.get("outcomes", [])
            return {o["name"]: o["price"] for o in outcomes}
    return None

def parse_spreads(markets: list) -> dict | None:
    for m in markets:
        if m.get("key") == "spreads":
            outcomes = m.get("outcomes", [])
            result = {}
            for o in outcomes:
                result[o["name"]] = {"point": o["point"], "price": o["price"]}
            return result
    return None

def parse_totals(markets: list) -> dict | None:
    for m in markets:
        if m.get("key") == "totals":
            outcomes = m.get("outcomes", [])
            result = {}
            for o in outcomes:
                result[o["name"]] = {"point": o["point"], "price": o["price"]}
            return result
    return None

def parse_player_props(markets: list) -> dict:
    result = {}
    for m in markets:
        if m["key"] in ("player_points", "player_rebounds", "player_assists"):
            for o in m.get("outcomes", []):
                name = o.get("description", o["name"])
                result[name] = {"line": o.get("point"), "price": o["price"]}
    return result

# ─── TC PICK BUILDER ──────────────────────────────────────────────────────────
def tc_project(player_avg: float, status: str | None = None) -> float:
    base = player_avg * PLAYER_FACTOR
    if status == "OUT":
        return 0.0
    if status == "Q":
        base *= 0.55
    return round(base, 1)

def tc_team_total(total: int, spread: int) -> tuple[int, int]:
    fav_raw = (total + abs(spread)) / 2
    dog_raw = total - fav_raw
    tc_fav  = int(fav_raw * TEAM_FACTOR)
    tc_dog  = int(dog_raw * TEAM_FACTOR)
    return tc_fav, tc_dog

def build_pick(pick_type: str, team: str, projected: float,
               line: float, odds: int, confidence: float,
               description: str) -> dict:
    edge = round(projected - line, 1)
    threshold = EDGE_THRESHOLD_PROP if pick_type == "PROP" else EDGE_THRESHOLD_LEG
    qual      = "✅" if abs(edge) >= threshold else "⚠️"
    decimal   = (abs(odds) / 100) + 1 if odds > 0 else (100 / abs(odds)) + 1
    return {
        "pick_type": pick_type,
        "team": team,
        "description": description,
        "projected": projected,
        "line": line,
        "edge": edge,
        "qualifier": qual,
        "odds": odds,
        "decimal_odds": round(decimal, 3),
        "confidence": confidence,
    }

# ─── REPORT GENERATOR ─────────────────────────────────────────────────────────
def generate_report(game: dict, picks: list[dict],
                   fav_key: str, dog_key: str,
                   injury_notes: str = "") -> str:
    sport_key  = game.get("sport_key", "")
    home_team  = game.get("home_team", "")
    away_team  = game.get("away_team", "")
    commence   = game.get("commence_time", "")[:16]

    lines = [
        f"# {away_team} @ {home_team} — TC Picks Report",
        f"**Date:** {commence}",
        f"**Sport:** {sport_key}",
        "",
        "## Injury Notes",
        injury_notes or "No significant injuries reported.",
        "",
        "## TC Rules Applied",
        "1. Player props: ≤85% of season avg (TC floor)",
        "2. Team totals: derived from Vegas lines × 0.88 factor",
        "3. T-targets are WHOLE NUMBERS only — no decimals",
        "4. Minimum edge: +2 pts (legs), +3 pts (player props)",
        "5. Under selected for totals (safer in playoff games)",
        "6. Confidence threshold: 88%+ from last-5-games sample",
        "7. Injury: OUT = 0 min, Q = 55% min",
        "",
        "## Picks",
    ]

    for i, pick in enumerate(picks, 1):
        edge_str = f"+{pick['edge']:.1f}" if pick['edge'] >= 0 else f"{pick['edge']:.1f}"
        odds_str  = f"+{pick['odds']}" if pick['odds'] > 0 else str(pick['odds'])
        lines.append(
            f"**Leg {i}:** {pick['pick_type']} — {pick['team']}\n"
            f"  Proj: {pick['projected']:.1f} | Line: {pick['line']} | "
            f"Edge: {edge_str} {pick['qualifier']} | Odds: {odds_str} | "
            f"Conf: {pick['confidence']:.0%}\n"
            f"  → {pick['description']}"
        )

    # Payout calc
    decimal = 1.0
    for p in picks:
        decimal *= p["decimal_odds"]
    stake   = 10.0
    payout  = round(decimal * stake, 2)
    net     = round(payout - stake, 2)
    odds_strs = [f"+{p['odds']}" if p['odds'] > 0 else str(p['odds']) for p in picks]
    lines += [
        "",
        "## Payout Summary",
        f"- Stake: ${stake:.2f}",
        f"- Combined Odds: {' / '.join(odds_strs)}",
        f"- Combined Decimal: {decimal:.3f}",
        f"- **Payout: ${payout:.2f}**",
        f"- Net Win: ${net:.2f}",
        "",
        "## Backtest Checklist",
        "□ Verify each leg against last 5 games of opponent",
        "□ Reduce stake if any leg confidence < 88%",
        "□ Confirm starting lineup before tip",
        "□ Check for late injury updates",
    ]
    return "\n".join(lines)

# ─── MAIN FETCHER ─────────────────────────────────────────────────────────────
def fetch_and_process(sport: str, regions: str, markets: str,
                     bookmakers: str, output_dir: Path,
                     mode: str = "odds", target_date: str = ""):
    if not ODDS_API_KEY:
        print("❌ No API key found. Set ODDS_API_KEY in [Settings > Advanced](/?t=settings&s=advanced)")
        print("   Or export: export ODDS_API_KEY=your-key-here")
        return

    print(f"🎯 Fetching {sport} odds from The Odds API...")
    try:
        data = get_odds(ODDS_API_KEY, sport, regions, markets, bookmakers)
    except Exception as e:
        print(f"❌ API error: {e}")
        return

    out_file = output_dir / f"live_odds_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(out_file, "w") as f:
        json.dump(data, f, indent=2)
    print(f"✅ Saved raw odds: {out_file}")
    print(f"📡 Fetched {len(data)} games\n")

    if mode == "tc":
        print("=" * 60)
        print("Running TC pipeline...")
        print("=" * 60)
        for game in data:
            _generate_tc_for_game(game)
        print(f"\n📄 All TC reports saved to: {output_dir}")

def _generate_tc_for_game(game: dict):
    home = game.get("home_team", "")
    away = game.get("away_team", "")
    bookmaker = game.get("bookmakers", [{}])[0]
    bk_name   = bookmaker.get("title", "Unknown")
    markets   = bookmaker.get("markets", [])

    h2h     = parse_h2h(markets)
    spreads = parse_spreads(markets)
    totals  = parse_totals(markets)

    if not all([h2h, spreads, totals]):
        print(f"  ⚠️ Skipping {away} @ {home} — missing market data")
        return

    print(f"\n🏀 {away} @ {home} ({bk_name})")
    print(f"   ML: {h2h}")
    print(f"   Spread: {spreads}")
    print(f"   Total: {totals}")

    # Build picks — placeholder, user overrides with actual STATS
    picks = []

    # Write report
    report = generate_report(game, picks, "", "", "")
    safe_name = home.replace(" ", "_")[:12]
    ts = datetime.now().strftime("%Y%m%d")
    out_path = Path.home() / ".zo" / "odds" / f"TC_{away[:3]}_at_{safe_name}_{ts}.md"
    with open(out_path, "w") as f:
        f.write(report)
    print(f"   📄 Report: {out_path}")

# ─── CLI ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="NBA Odds Fetcher — TC Pipeline")
    parser.add_argument("--sport",    default="basketball_nba",
                        help="Sport key (default: basketball_nba)")
    parser.add_argument("--regions",  default="us",
                        help="Regions (default: us)")
    parser.add_argument("--markets",  default="h2h,spreads,totals",
                        help="Markets (default: h2h,spreads,totals)")
    parser.add_argument("--bookmakers", default="",
                        help="Comma-separated bookmaker slugs (optional)")
    parser.add_argument("--output",   default=str(ODDS_DIR),
                        help=f"Output dir (default: {ODDS_DIR})")
    parser.add_argument("--mode",     default="odds",
                        choices=["odds", "tc"],
                        help="'odds' = raw only, 'tc' = process with TC formulas")
    parser.add_argument("--date",     default="",
                        help="Target date YYYY-MM-DD (for TC mode)")

    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    fetch_and_process(
        sport=args.sport,
        regions=args.regions,
        markets=args.markets,
        bookmakers=args.bookmakers,
        output_dir=output_dir,
        mode=args.mode,
        target_date=args.date,
    )

if __name__ == "__main__":
    main()