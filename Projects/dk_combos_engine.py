#!/usr/bin/env python3

# TC — Triple Conservative — Trademark June 2026 — All rights reserved.
"""dk_combos_engine.py — DK Combo Lines from SportsGameOdds.

No TC projection overlay. Just raw DraftKings PRA/PR/PA combo lines from SGO.
Outputs JSON for consumption by dashboard pages.

Usage:
  python3 dk_combos_engine.py                  # all sports, all upcoming
  python3 dk_combos_engine.py --sport NBA      # NBA only
  python3 dk_combos_engine.py --away SAS --home NYK  # specific matchup
  python3 dk_combos_engine.py --serve           # start HTTP server for combos

"""

import json
import os
import re
import sys
import argparse
import http.server
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional

import requests

SECRETS_FILE = "/root/.zo/secrets.env"

def load_secret(name: str) -> str:
    try:
        txt = Path(SECRETS_FILE).read_text()
        for line in txt.split("\n"):
            m = re.match(rf"^\s*{name}\s*=\s*[\"']?([^\"'\s#]+)", line)
            if m:
                return m.group(1)
    except Exception:
        pass
    return os.environ.get(name, "")

SGO_BASE = "https://api.sportsgameodds.com/v2"

LEAGUE_MAP = {"NBA": "NBA", "WNBA": "WNBA", "NCAAB": "NCAAB"}
# Odds API uses basketball_wnba for WNBA combo markets

@dataclass
class DKCombo:
    player: str
    team: str
    combo_type: str       # "PRA" | "PR" | "PA"
    dk_line: float
    dk_odds: str          # American odds e.g. "-121"
    book_over_under: str  # e.g. "23.5"
    odd_id: str
    bookmaker: str

def sgo_player_name(odd_id: str) -> str:
    """Parse player name from oddID. DEAARON_FOX_1_NBA → De'Aaron Fox"""
    parts = odd_id.split("-")
    if len(parts) < 2:
        return "Unknown"
    entity = parts[1]
    cleaned = re.sub(r"_\d+_\w+$", "", entity)
    cleaned = cleaned.replace("_", " ")
    # Very basic title-case with apostrophe support
    return cleaned.title().replace("'S", "'s").replace("'D", "'d")

def fetch_sgo_events(sport_key: str) -> List[dict]:
    """Fetch live events from SGO. Returns [] on 400 (e.g. WNBA tier restriction)."""
    url = f"{SGO_BASE}/events"
    try:
        r = requests.get(
            url,
            params={"leagueID": sport_key, "oddsAvailable": "true"},
            headers={"X-Api-Key": SGO_API_KEY, "Accept": "application/json"},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("data", [])
    except requests.exceptions.HTTPError as e:
        # SGO returns 400 when league is unavailable at current tier
        print(f"[sgo] {sport_key} unavailable: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"[sgo] error: {e}", file=sys.stderr)
        return []

    """Fetch WNBA/NBA events with DK player combo props from The Odds API.

    Two-step: list events, then fetch per-event odds with combo markets.
    Returns list of {"event": {...}, "bookmakers": [...]} dicts.
    """
    markets = "player_points_rebounds_assists,player_points_rebounds,player_points_assists"

    # Step 1: list events
    r = requests.get(
        f"{ODDS_BASE}/sports/{sport_path}/events",
        timeout=15,
    )
    r.raise_for_status()
    events = r.json()

    out: List[dict] = []
    for ev in events:
        eid = ev.get("id")
        if not eid:
            continue
        try:
            r2 = requests.get(
                f"{ODDS_BASE}/sports/{sport_path}/events/{eid}/odds",
                params={
                    "regions": "us",
                    "markets": markets,
                    "oddsFormat": "american",
                    "bookmakers": "draftkings",
                },
                timeout=15,
            )
            r2.raise_for_status()
            odds_data = r2.json()
        except Exception as e:
            print(f"[odds-api] {eid} odds fetch failed: {e}", file=__import__("sys").stderr)
            continue
        out.append({"event": ev, "bookmakers": odds_data.get("bookmakers", [])})
    return out

    """Fetch player combo markets for a single event from The Odds API."""
    odds_sport = "basketball_wnba"
    r = requests.get(
        f"{ODDS_BASE}/sports/{odds_sport}/events/{event_id}/odds",
        params={
            "markets": "player_points_rebounds_assists,player_points_rebounds,player_points_assists,player_points,player_rebounds,player_assists",
            "oddsFormat": "american",
            "bookmakers": "draftkings",
        },
        timeout=20,
    )
    r.raise_for_status()
    return r.json()

ODDS_MARKET_MAP = {
    "player_points_rebounds_assists": "PRA",
    "player_points_rebounds": "PR",
    "player_points_assists": "PA",
}
def event_safe(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")

def extract_dk_combos(events: List[dict], target_away: Optional[str] = None, target_home: Optional[str] = None) -> List[DKCombo]:
    """Extract PRA/PR/PA combo lines from SGO events."""
    combos: List[DKCombo] = []

    TEAM_NORM = {
        "SA": "SAS", "NY": "NYK", "NO": "NOP", "UTAH": "UTA", "WASH": "WAS",
        "WS": "WSH", "LVA": "LV", "LAS": "LA", "NYL": "NY", "GSW": "GS",
    }

    def norm_team(s: str) -> str:
        return TEAM_NORM.get(s.upper(), s.upper().replace(" ", ""))

    COMBO_PREFIXES = {
        "points+rebounds+assists": "PRA",
        "points+rebounds": "PR",
        "points+assists": "PA",
    }

    for ev in events:
        teams = ev.get("teams", {})
        away_team = norm_team(teams.get("away", {}).get("names", {}).get("short", ""))
        home_team = norm_team(teams.get("home", {}).get("names", {}).get("short", ""))

        if target_away and home_team and target_away.upper() not in (away_team, target_away.upper()):
            continue
        if target_home and home_team and target_home.upper() not in (home_team, target_home.upper()):
            continue

        odds = ev.get("odds", {})
        for odd_id, odd_data in odds.items():
            # Match combo patterns
            for prefix, combo_type in COMBO_PREFIXES.items():
                if not odd_id.startswith(prefix + "-"):
                    continue

                # Only over side (under side shares same line)
                if not odd_id.endswith("-ou-over"):
                    continue

                bm = odd_data.get("byBookmaker", {})
                dk = bm.get("draftkings", {})
                if not dk.get("available"):
                    continue

                line = dk.get("overUnder")
                dk_odds = dk.get("odds", "—")
                if line is None:
                    continue

                try:
                    line_f = float(line)
                except (ValueError, TypeError):
                    continue

                player = sgo_player_name(odd_id)

                combos.append(DKCombo(
                    player=player,
                    team="—",
                    combo_type=combo_type,
                    dk_line=line_f,
                    dk_odds=str(dk_odds),
                    book_over_under=str(line),
                    odd_id=odd_id,
                    bookmaker="draftkings",
                ))

    combos.sort(key=lambda c: c.dk_line, reverse=True)
    return combos

def serve_combos(port: int = 8515):
    """Start minimal HTTP server serving DK combos JSON."""
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith("/combos"):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()

                # Parse query params
                qs = self.path.split("?")[-1] if "?" in self.path else ""
                params = dict(p.split("=") for p in qs.split("&") if "=" in p)
                sport = params.get("sport", "NBA")
                away = params.get("away")
                home = params.get("home")

                sport_key = LEAGUE_MAP.get(sport.upper(), "NBA")
                events = fetch_sgo_events(sport_key)
                combos = extract_dk_combos(events, away, home)


                out = {
                    "sport": sport,
                    "away": away,
                    "home": home,
                    "combos": [asdict(c) for c in combos],
                    "count": len(combos),
                }
                self.wfile.write(json.dumps(out, indent=2).encode())
                return

            self.send_response(404)
            self.end_headers()

    server = http.server.HTTPServer(("0.0.0.0", port), Handler)
    print(f"DK Combos server on http://0.0.0.0:{port}/combos")
    server.serve_forever()

def main():
    p = argparse.ArgumentParser(description="DK Combo Lines from SGO")
    p.add_argument("--sport", default="NBA", help="NBA or WNBA")
    p.add_argument("--away", help="Away team code")
    p.add_argument("--home", help="Home team code")
    p.add_argument("--serve", action="store_true", help="Run as HTTP server")
    p.add_argument("--port", type=int, default=8515, help="Server port (default 8515)")
    args = p.parse_args()

    if args.serve:
        serve_combos(args.port)
        return

    sport_key = LEAGUE_MAP.get(args.sport.upper(), "NBA")
    events = fetch_sgo_events(sport_key)
    combos = extract_dk_combos(events, args.away, args.home)

    # WNBA fallback: SGO doesn't support WNBA on current tier

    print(json.dumps({"sport": args.sport, "combos": [asdict(c) for c in combos], "count": len(combos)}, indent=2))

if __name__ == "__main__":
    main()
