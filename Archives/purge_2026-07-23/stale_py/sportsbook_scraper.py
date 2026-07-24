"""
Sportsbook Scraper — DK/FD/BetMGM via ESPN v2 + Odds API fallback.
Sandbox-safe: no Playwright/Redis required. Headless = True.
Streams to stdout + JSONL file. Use for backtest + live props.
"""
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional

import requests

# ===================== CONFIG =====================
ESPN_V2 = "https://site.api.espn.com/apis/site/v2/sports"
ODDS_API = "https://api.the-odds-api.com/v4"
ODDS_API_KEY = os.environ.get("ODDS_API_KEY", "")
REDIS_HOST = os.environ.get("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
HEADLESS = True  # sandbox-safe default

SPORT_PATHS = {
    "NBA": ("basketball", "nba"),
    "WNBA": ("basketball", "wnba"),
    "NFL": ("football", "nfl"),
    "MLB": ("baseball", "mlb"),
    "NHL": ("hockey", "nhl"),
    "SOCCER": ("soccer", "eng.1"),
    "WC": ("soccer", "fifa.world"),
    "NCAAF": ("football", "college-football"),
    "NCAAB": ("basketball", "mens-college-basketball"),
}

# ===================== SCRAPER ENGINE =====================
class LiveOddsScraper:
    def __init__(self, use_redis: bool = False, output_dir: str = "/home/workspace/data/odds"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.intercepted_data: List[dict] = []
        self.redis_client = None
        if use_redis:
            try:
                import redis
                self.redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
                self.redis_client.ping()
            except Exception as e:
                print(f"WARN Redis disabled: {e}")
                self.redis_client = None

    def detect_sport(self, url: str) -> str:
        for sport, (cat, _) in SPORT_PATHS.items():
            if cat in url.lower() or sport.lower() in url.lower():
                return sport
        return "UNKNOWN"

    def fetch_espn_odds(self, sport: str) -> List[dict]:
        """ESPN v2 scoreboard — public, no key required."""
        if sport not in SPORT_PATHS:
            return []
        category, league = SPORT_PATHS[sport]
        url = f"{ESPN_V2}/{category}/{league}/scoreboard"
        try:
            r = requests.get(url, timeout=10, params={"limit": 200})
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"WARN ESPN {sport} fetch failed: {e}")
            return []
        events = []
        for ev in data.get("events", []):
            comp = ev.get("competitions", [{}])[0]
            competitors = comp.get("competitors", [])
            home = next((c for c in competitors if c.get("homeAway") == "home"), {})
            away = next((c for c in competitors if c.get("homeAway") == "away"), {})
            odds_block = comp.get("odds", [{}])[0] if comp.get("odds") else {}
            events.append({
                "event_id": ev.get("id"),
                "sport": sport,
                "home_team": home.get("team", {}).get("displayName"),
                "away_team": away.get("team", {}).get("displayName"),
                "game_time": ev.get("date"),
                "status": ev.get("status", {}).get("type", {}).get("description"),
                "spread": odds_block.get("details"),
                "spread_odds": odds_block.get("homeTeamOdds", {}).get("odds") if odds_block.get("homeTeamOdds") else None,
                "total": odds_block.get("overUnder"),
                "moneyline_home": odds_block.get("homeTeamOdds", {}).get("odds") if odds_block.get("homeTeamOdds") else None,
                "moneyline_away": odds_block.get("awayTeamOdds", {}).get("odds") if odds_block.get("awayTeamOdds") else None,
                "source": "ESPN",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            })
        return events

    def fetch_odds_api(self, sport: str, markets: str = "h2h,spreads,totals") -> List[dict]:
        """Odds API — needs key. Used as fallback for DK/FD/BetMGM specifics."""
        if not ODDS_API_KEY:
            return []
        sport_key_map = {
            "NBA": "basketball_nba", "WNBA": "basketball_wnba", "NFL": "americanfootball_nfl",
            "MLB": "baseball_mlb", "NHL": "icehockey_nhl", "SOCCER": "soccer_epl",
            "WC": "soccer_fifa_world_cup", "NCAAF": "americanfootball_ncaaf", "NCAAB": "basketball_ncaab",
        }
        if sport not in sport_key_map:
            return []
        url = f"{ODDS_API}/sports/{sport_key_map[sport]}/odds/"
        try:
            r = requests.get(url, timeout=10, params={
                "apiKey": ODDS_API_KEY, "regions": "us",
                "markets": markets, "oddsFormat": "american", "dateFormat": "iso",
            })
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"WARN Odds API {sport} fetch failed: {e}")
            return []

    def fetch_player_props(self, sport: str) -> List[dict]:
        """ESPN summary endpoint — has player stats, not prop lines. Lines come from Odds API."""
        if sport not in SPORT_PATHS:
            return []
        category, league = SPORT_PATHS[sport]
        url = f"{ESPN_V2}/{category}/{league}/scoreboard"
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"WARN ESPN props {sport} fetch failed: {e}")
            return []
        props = []
        for ev in data.get("events", []):
            for comp in ev.get("competitions", []):
                for stat_type in ["leaders", "playerStats"]:
                    for entry in comp.get(stat_type, []) or []:
                        leader = entry.get("athlete", {}) or entry.get("player", {})
                        props.append({
                            "event_id": ev.get("id"),
                            "sport": sport,
                            "player_name": leader.get("displayName"),
                            "team": leader.get("team", {}).get("displayName") if isinstance(leader.get("team"), dict) else None,
                            "stat_type": entry.get("name") or entry.get("type"),
                            "value": entry.get("value") or entry.get("displayValue"),
                            "source": "ESPN",
                        })
        return props

    def parse_sportsbook_data(self, raw_json: dict, url: str) -> dict:
        sport = self.detect_sport(url)
        structured = {"timestamp": datetime.now(timezone.utc).isoformat(), "endpoint": url, "sport": sport, "events": [], "player_props": []}
        for event in raw_json.get("events", []):
            structured["events"].append({
                "event_id": event.get("id"),
                "home_team": event.get("home_team") or event.get("homeTeam"),
                "away_team": event.get("away_team") or event.get("awayTeam"),
                "game_time": event.get("game_time") or event.get("startTime"),
                "status": event.get("status"),
                "spread": event.get("spread"),
                "total": event.get("total"),
                "moneyline": event.get("moneyline"),
            })
        for prop in raw_json.get("player_props", []):
            structured["player_props"].append({
                "player_name": prop.get("player_name") or prop.get("player"),
                "team": prop.get("team"),
                "stat_type": prop.get("stat_type") or prop.get("statType"),
                "line": prop.get("line"),
                "over_odds": prop.get("over_odds") or prop.get("overOdds"),
                "under_odds": prop.get("under_odds") or prop.get("underOdds"),
            })
        return structured

    def save_snapshot(self, data: List[dict], sport: str):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(self.output_dir, f"odds_{sport}_{ts}.jsonl")
        with open(path, "w") as f:
            for row in data:
                f.write(json.dumps(row) + "\n")
        print(f"OK Saved {len(data)} rows -> {path}")
        if self.redis_client:
            try:
                self.redis_client.xadd("live_odds_stream", {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "sport": sport, "count": len(data),
                })
            except Exception as e:
                print(f"WARN Redis stream failed: {e}")
        return path

    def run(self, sports: List[str], include_props: bool = True) -> Dict[str, List[dict]]:
        results = {}
        for sport in sports:
            events = self.fetch_espn_odds(sport)
            props = self.fetch_player_props(sport) if include_props else []
            results[sport] = {"events": events, "player_props": props, "fetched_at": datetime.now(timezone.utc).isoformat()}
            self.intercepted_data.extend(events)
            if events or props:
                self.save_snapshot(events + props, sport)
            else:
                print(f"WARN {sport}: no data returned")
        return results


# ===================== CLI =====================
def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--sport", choices=list(SPORT_PATHS.keys()) + ["all"], default="NBA")
    p.add_argument("--include-props", action="store_true")
    p.add_argument("--use-redis", action="store_true")
    p.add_argument("--output-dir", default="/home/workspace/data/odds")
    args = p.parse_args()
    scraper = LiveOddsScraper(use_redis=args.use_redis, output_dir=args.output_dir)
    sports = list(SPORT_PATHS.keys()) if args.sport == "all" else [args.sport]
    results = scraper.run(sports, include_props=args.include_props)
    print(json.dumps({"summary": {s: len(r["events"]) for s, r in results.items()}}, indent=2))


if __name__ == "__main__":
    main()
