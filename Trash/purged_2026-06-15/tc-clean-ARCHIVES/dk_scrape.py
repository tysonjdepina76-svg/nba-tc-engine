#!/usr/bin/env python3
"""
DK_LINES — Extract real DraftKings game lines (ML, Spread, Total)
for NBA (and other sports) directly from ESPN's DraftKings-embedded scoreboard API.

ESPN puts the full DraftKings odds object inside their scoreboard JSON at:
  events[].competitions[].odds[ provider.name=="DraftKings" ]
  ↳ .moneyline   → home/away ML with open/close odds
  ↳ .pointSpread → home/away spread + odds
  ↳ .total       → over/under with odds

No API key required. Works for any game that ESPN shows DraftKings odds for.
"""
import json, sys, re
from typing import Optional

try:
    import requests
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False

SPORT_MAP = {
    "NBA":  "basketball/nba",
    "WNBA": "basketball/wnba",
    "NCAAB":"basketball/mens-college-basketball",
    "MLB":  "baseball/mlb",
    "NHL":  "hockey/nhl",
}

TEAM_ALIASES = {
    "SA": "SAS", "NY": "NYK", "NO": "NOP", "UTAH": "UTA",
    "WASH": "WAS", "WS": "WSH", "LVA": "LV", "LAS": "LA",
    "NYL": "NY", "GSW": "GS",
}

def norm(code: str) -> str:
    return TEAM_ALIASES.get(code.upper(), code.upper())

def fetch_dk_from_espn(sport: str, away: str, home: str) -> dict:
    """
    Fetch DraftKings game lines from ESPN scoreboard for away vs home.
    Returns dict with: total, away_ml, home_ml, away_spread, home_spread,
                       spread_pick, ml_source, spread_source, total_source
    """
    results = {
        "total": None, "away_ml": None, "home_ml": None,
        "away_spread": None, "home_spread": None,
        "spread_pick": None,
        "ml_source": None, "spread_source": None, "total_source": None,
    }

    if not REQUESTS_OK:
        return results

    path = SPORT_MAP.get(sport.upper(), f"basketball/{sport.lower()}")
    url = f"https://site.api.espn.com/apis/site/v2/sports/{path}/scoreboard"
    Away = norm(away)
    Home = norm(home)

    try:
        r = requests.get(
            url,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
        )
        if not r.ok:
            return results
        data = r.json()
    except Exception as e:
        print(f"[DK ESPN] Fetch error: {e}", file=sys.stderr)
        return results

    for event in data.get("events", []):
        comp = event.get("competitions", [{}])[0]
        teams = comp.get("competitors", [])

        away_team = next(
            (t["team"]["abbreviation"] for t in teams if t.get("homeAway") == "away"),
            None,
        )
        home_team = next(
            (t["team"]["abbreviation"] for t in teams if t.get("homeAway") == "home"),
            None,
        )

        # Normalize for alias matching
        if norm(away_team) != Away or norm(home_team) != Home:
            continue

        for odds_obj in comp.get("odds", []):
            if odds_obj.get("provider", {}).get("name") != "DraftKings":
                continue

            # ── Total ─────────────────────────────────────────────────────────
            total_block = odds_obj.get("total", {})
            if total_block and isinstance(total_block, dict):
                for side in ("over", "under"):
                    if side in total_block:
                        close = total_block[side].get("close", {})
                        line_str = close.get("line", "")
                        # line looks like "o218.5" or "u218.5"
                        m = re.search(r"[ou]?(\d+\.?\d*)", str(line_str))
                        if m:
                            results["total"] = float(m.group(1))
                            results["total_source"] = "ESPN DraftKings embedded"
                            break

            # ── Moneyline ───────────────────────────────────────────────────────
            ml_block = odds_obj.get("moneyline", {})
            if ml_block and isinstance(ml_block, dict):
                for side in ("home", "away"):
                    if side in ml_block:
                        close = ml_block[side].get("close", {})
                        odds_val = close.get("odds", "")
                        try:
                            val = int(float(odds_val))
                        except (ValueError, TypeError):
                            val = None
                        if side == "away":
                            results["away_ml"] = val
                        else:
                            results["home_ml"] = val
                if results["away_ml"] is not None or results["home_ml"] is not None:
                    results["ml_source"] = "ESPN DraftKings embedded"

            # ── Spread ────────────────────────────────────────────────────────
            spread_block = odds_obj.get("pointSpread", {})
            if spread_block and isinstance(spread_block, dict):
                for side in ("home", "away"):
                    if side in spread_block:
                        close = spread_block[side].get("close", {})
                        line_val = close.get("line", "")
                        try:
                            val = float(line_val)
                        except (ValueError, TypeError):
                            val = None
                        if side == "away":
                            results["away_spread"] = val
                        else:
                            results["home_spread"] = val
                if results["away_spread"] is not None or results["home_spread"] is not None:
                    results["spread_source"] = "ESPN DraftKings embedded"

                # Spread pick: side with negative value is favorite
                if results["away_spread"] is not None and results["home_spread"] is not None:
                    av = results["away_spread"]
                    hv = results["home_spread"]
                    if av < 0:
                        results["spread_pick"] = Away
                    elif hv < 0:
                        results["spread_pick"] = Home
                    else:
                        results["spread_pick"] = "PASS"

            # Stop after finding the DraftKings block for this game
            if results["ml_source"] == "ESPN DraftKings embedded":
                return results

    return results


def get_ml_display(ml_val: Optional[int], team: str) -> str:
    if ml_val is None:
        return f"{team} —"
    prefix = "+" if ml_val > 0 else ""
    return f"{team} {prefix}{ml_val}"


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Get DK lines from ESPN for a game")
    parser.add_argument("away", help="Away team (e.g. BOS)")
    parser.add_argument("home", help="Home team (e.g. NYK)")
    parser.add_argument("--sport", default="NBA", help="Sport (NBA, WNBA, etc.)")
    args = parser.parse_args()

    r = fetch_dk_from_espn(args.sport, args.away, args.home)

    print("=== DraftKings Game Lines (via ESPN) ===")
    print(f"  Away ML:     {get_ml_display(r['away_ml'], args.away)}")
    print(f"  Home ML:     {get_ml_display(r['home_ml'], args.home)}")
    print(f"  Away Spread:{args.away} {r['away_spread']}")
    print(f"  Home Spread:{args.home} {r['home_spread']}")
    print(f"  Total:      {r['total']}")
    print(f"  Spread Pick: {r['spread_pick']}")
    print(f"  ML Source:  {r['ml_source']}")
    print()
    print("Raw output:")
    print(json.dumps(r, indent=2))
