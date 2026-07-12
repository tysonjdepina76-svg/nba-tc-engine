#!/usr/bin/env python3
"""wnba_odds_scraper.py — Real Odds API integration (all 11 books, flat schema)."""
import os, json, time, logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import requests
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("wnba_odds")

BASE = "https://api.theoddsapi.com/odds"


def get_api_key() -> str:
    return (os.environ.get("ODDS_API_KEY")
            or os.environ.get("THEODDSAPI")
            or os.environ.get("THEODDSAPI_KEY")
            or "")


class WNBAOddsScraper:
    DAILY_CAP = 10

    def __init__(self, api_key: Optional[str] = None, sport: str = "WNBA"):
        self.api_key = api_key or get_api_key()
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "wnba-tc-scraper/1.0"})
        self.cache: Dict[str, list] = {}
        self.sport = sport
        self._usage = self._load_usage()

    def _usage_path(self) -> Path:
        return Path(f"/home/workspace/Daily_Log/{self._today()}/odds/usage.json")

    def _today(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def _load_usage(self) -> Dict:
        p = self._usage_path()
        if p.exists():
            try:
                return json.loads(p.read_text())
            except Exception:
                pass
        return {"date": self._today(), "calls": {}}

    def _save_usage(self):
        p = self._usage_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self._usage, indent=2))

    def calls_used(self) -> int:
        if self._usage.get("date") != self._today():
            self._usage = {"date": self._today(), "calls": {}}
            self._save_usage()
        return self._usage.get("calls", {}).get(self.sport, 0)

    def calls_remaining(self) -> int:
        return max(0, self.DAILY_CAP - self.calls_used())

    def _bump_call(self):
        calls = self._usage.setdefault("calls", {})
        calls[self.sport] = calls.get(self.sport, 0) + 1
        self._save_usage()

    def _get_cached_odds(self, sport_key: str) -> Optional[list]:
        if sport_key in self.cache:
            return self.cache[sport_key]
        today = self._today()
        for ext in ("csv", "json"):
            p = Path(f"/home/workspace/Daily_Log/{today}/odds/{self.sport.lower()}_odds.{ext}")
            if p.exists():
                logger.info(f"📦 Using cached odds: {p}")
                if ext == "csv":
                    return pd.read_csv(p).to_dict("records")
                return json.loads(p.read_text())
        return None

    def get_odds(self, sport_key="basketball_wnba", regions="us",
                 markets="h2h,spreads,totals", odds_format="american",
                 date: Optional[str] = None) -> List[Dict]:
        params = {"apiKey": self.api_key, "sport_key": sport_key,
                  "regions": regions, "markets": markets,
                  "oddsFormat": odds_format}
        if date:
            params["date"] = date
        cache_key = f"{sport_key}_{date}_{regions}_{markets}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        try:
            logger.info(f"Fetching WNBA odds for {date or 'today'}")
            r = self.session.get(BASE, params=params, timeout=15)
            r.raise_for_status()
            payload = r.json()
        except Exception as e:
            logger.error(f"Fetch failed: {e}")
            return []
        # Odds API wraps as {"success":true,"data":[...]} OR returns list directly
        if isinstance(payload, dict) and "data" in payload:
            data = payload["data"]
        elif isinstance(payload, list):
            data = payload
        else:
            logger.error(f"Unexpected payload type: {type(payload)}")
            return []
        self.cache[cache_key] = data
        logger.info(f"✅ Fetched {len(data)} games")
        return data

    def parse_odds(self, odds_data: List[Dict]) -> pd.DataFrame:
        rows = []
        for g in odds_data:
            gid = g.get("event_id") or g.get("id")
            home = g.get("home_team", "")
            away = g.get("away_team", "")
            start = g.get("start_time") or g.get("commence_time", "")
            for bk in g.get("books", []) or g.get("bookmakers", []):
                book = bk.get("book") or bk.get("key", "")
                updated = bk.get("updated_at") or bk.get("last_update", "")
                # Schema A: flat books[{book, market, outcomes:[{name,price,point}]}]
                if "market" in bk:
                    for o in bk.get("outcomes", []):
                        rows.append({
                            "game_id": gid, "home_team": home, "away_team": away,
                            "start_time": start, "book": book, "market": bk["market"],
                            "updated_at": updated,
                            "name": o.get("name", ""), "price": o.get("price"),
                            "point": o.get("point"),
                        })
                # Schema B: bookmakers[{key, markets:[{key, outcomes}]}]
                else:
                    for m in bk.get("markets", []):
                        for o in m.get("outcomes", []):
                            rows.append({
                                "game_id": gid, "home_team": home, "away_team": away,
                                "start_time": start, "book": book, "market": m.get("key", ""),
                                "updated_at": updated,
                                "name": o.get("name", ""), "price": o.get("price"),
                                "point": o.get("point"),
                            })
        df = pd.DataFrame(rows)
        if not df.empty:
            logger.info(f"✅ Parsed {len(df)} odds rows")
        return df

    def get_player_props(self, game_id: str, sport_key="basketball_wnba") -> List[Dict]:
        url = f"{BASE}/sports/{sport_key}/events/{game_id}/odds"
        params = {"apiKey": self.api_key, "regions": "us",
                  "markets": "player_points,player_rebounds,player_assists,"
                             "player_threes,player_blocks,player_steals",
                  "oddsFormat": "american"}
        try:
            r = self.session.get(url, params=params, timeout=15)
            r.raise_for_status()
            return r.json().get("data", r.json()) if isinstance(r.json(), dict) else r.json()
        except Exception as e:
            logger.error(f"Props fetch failed: {e}")
            return []

    def save_odds(self, df: pd.DataFrame, date: str) -> Path:
        out_dir = Path(f"/home/workspace/Daily_Log/{date}/odds")
        out_dir.mkdir(parents=True, exist_ok=True)
        csv = out_dir / "wnba_odds.csv"
        jsn = out_dir / "wnba_odds.json"
        df.to_csv(csv, index=False)
        df.to_json(jsn, orient="records", indent=2)
        logger.info(f"✅ Saved {len(df)} rows to {csv}")
        return csv

    def run_daily(self, date: Optional[str] = None) -> Optional[pd.DataFrame]:
        date = date or datetime.now().strftime("%Y-%m-%d")
        odds = self.get_odds(date=date)
        if not odds:
            return None
        df = self.parse_odds(odds)
        if df.empty:
            return None
        self.save_odds(df, date)
        games = df["game_id"].nunique()
        books = df["book"].nunique()
        print(f"\n{'='*60}\nWNBA ODDS — {date}\n{'='*60}")
        print(f"Games: {games} | Books: {books} | Rows: {len(df)}\n{'='*60}")
        return df


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("date", nargs="?", default=None)
    p.add_argument("--sport", default="basketball_wnba",
                   help="Odds API sport key (e.g. basketball_wnba, baseball_mlb)")
    args = p.parse_args()
    scraper = WNBAOddsScraper()
    # When a different sport is requested, reuse get_odds directly and save under sport-tagged name.
    odds = scraper.get_odds(sport_key=args.sport, date=args.date)
    if not odds:
        print(f"No odds for {args.sport} on {args.date or 'today'}")
        return
    df = scraper.parse_odds(odds)
    if df.empty:
        print(f"Parsed 0 rows for {args.sport}")
        return
    date = args.date or datetime.now().strftime("%Y-%m-%d")
    out_dir = Path(f"/home/workspace/Daily_Log/{date}/odds")
    out_dir.mkdir(parents=True, exist_ok=True)
    sport_short = args.sport.split("_")[-1]  # wnba, mlb, nfl, nba, nhl
    csv = out_dir / f"{sport_short}_odds.csv"
    jsn = out_dir / f"{sport_short}_odds.json"
    df.to_csv(csv, index=False)
    df.to_json(jsn, orient="records", indent=2)
    print(f"✅ Saved {len(df)} rows → {csv}")
    print(f"Games: {df['game_id'].nunique()} | Books: {df['book'].nunique()}")


if __name__ == "__main__":
    main()
