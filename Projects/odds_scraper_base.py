#!/usr/bin/env python3
"""
odds_scraper_base.py — Shared base class for all sport-specific Odds API scrapers.

Schema (Odds API v4, root namespace, flat):
  {
    "success": true,
    "data": [
      {
        "event_id": "abc123",
        "sport_key": "basketball_wnba",
        "sport_title": "WNBA",
        "commence_time": "2026-07-12T23:00:00Z",
        "home_team": "Las Vegas Aces",
        "away_team": "Indiana Fever",
        "bookmakers": [
          {
            "key": "draftkings",
            "title": "DraftKings",
            "markets": [
              {
                "key": "h2h",
                "outcomes": [
                  {"name": "Las Vegas Aces", "price": -150},
                  {"name": "Indiana Fever", "price": 130}
                ]
              }
            ]
          }
        ]
      }
    ]
  }
"""
import os
import json
import logging
import requests
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("odds_scraper_base")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def _get_api_key() -> str:
    return (os.environ.get("THEODDSAPI")
            or os.environ.get("ODDS_API_KEY")
            or os.environ.get("THEODDSAPI_KEY")
            or "")


class OddsScraperBase:
    SPORT_KEY: str = "basketball_wnba"
    SPORT_LABEL: str = "WNBA"
    DEFAULT_MARKETS: str = "h2h,spreads,totals"
    MAX_CALLS_PER_DAY: int = 10

    def __init__(self, sport_key: Optional[str] = None, sport_label: Optional[str] = None):
        if sport_key:
            self.SPORT_KEY = sport_key
        if sport_label:
            self.SPORT_LABEL = sport_label
        self.api_key = _get_api_key()
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "tc-odds-scraper/1.0"})
        self.cache: Dict[str, list] = {}
        self._usage = self._load_usage()
        if not self.api_key:
            logger.warning("No Odds API key found — fetches will fail")

    def _today(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def _usage_path(self) -> Path:
        return Path(f"/home/workspace/Daily_Log/{self._today()}/odds/usage.json")

    def _load_usage(self) -> dict:
        p = self._usage_path()
        if p.exists():
            try:
                data = json.loads(p.read_text())
                if data.get("date") == self._today():
                    return data
            except Exception:
                pass
        return {"date": self._today(), "calls": 0}

    def _save_usage(self) -> None:
        p = self._usage_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self._usage, indent=2))

    def calls_used(self) -> int:
        if self._usage.get("date") != self._today():
            self._usage = {"date": self._today(), "calls": 0}
            self._save_usage()
        return int(self._usage.get("calls", 0))

    def calls_remaining(self) -> int:
        return max(0, self.MAX_CALLS_PER_DAY - self.calls_used())

    def _bump_call(self) -> None:
        if self._usage.get("date") != self._today():
            self._usage = {"date": self._today(), "calls": 0}
        self._usage["calls"] = int(self._usage.get("calls", 0)) + 1
        self._save_usage()

    def _out_path(self, ext: str) -> Path:
        today = self._today()
        p = Path(f"/home/workspace/Daily_Log/{today}/odds/{self.SPORT_KEY}.{ext}")
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def get_odds(self, date: Optional[str] = None, regions: str = "us",
                 markets: Optional[str] = None, odds_format: str = "american") -> List[Dict]:
        if not self.api_key:
            logger.error("ODDS_API_KEY / THEODDSAPI missing — cannot fetch")
            return []
        markets = markets or self.DEFAULT_MARKETS
        cache_key = f"{self.SPORT_KEY}_{date}_{regions}_{markets}"
        if cache_key in self.cache:
            logger.info(f"Returning cached {len(self.cache[cache_key])} games for {cache_key}")
            return self.cache[cache_key]
        if self.calls_remaining() <= 0:
            logger.warning(
                f"Daily cap hit ({self.calls_used()}/{self.MAX_CALLS_PER_DAY}). "
                f"Returning cache/empty for {self.SPORT_KEY}."
            )
            return self._load_disk_cache(date, regions, markets) or []
        params = {
            "apiKey": self.api_key,
            "regions": regions,
            "markets": markets,
            "oddsFormat": odds_format,
            "sport_key": self.SPORT_KEY,
        }
        if date:
            params["date"] = date
        url = "https://api.theoddsapi.com/odds/"
        try:
            logger.info(f"Fetching {self.SPORT_LABEL} odds for {date or 'now'}")
            r = self.session.get(url, params=params, timeout=30)
            self._bump_call()
            r.raise_for_status()
            payload = r.json()
            if isinstance(payload, dict) and "data" in payload:
                data = payload["data"]
            elif isinstance(payload, list):
                data = payload
            else:
                logger.error(f"Unexpected payload type: {type(payload).__name__}")
                return []
            self.cache[cache_key] = data
            self._save_disk_cache(data, date, regions, markets)
            logger.info(
                f"✅ Fetched {len(data)} games for {self.SPORT_LABEL} "
                f"(cap: {self.calls_used()}/{self.MAX_CALLS_PER_DAY})"
            )
            return data
        except requests.RequestException as e:
            logger.error(f"Failed to fetch odds: {e}")
            return []

    def _disk_cache_path(self, date, regions, markets) -> Path:
        today = self._today()
        return Path(f"/home/workspace/Daily_Log/{today}/odds/_raw_{self.SPORT_KEY}_{date}_{regions}_{markets}.json")

    def _save_disk_cache(self, data, date, regions, markets) -> None:
        p = self._disk_cache_path(date, regions, markets)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, indent=2))

    def _load_disk_cache(self, date, regions, markets) -> List[Dict]:
        p = self._disk_cache_path(date, regions, markets)
        if p.exists():
            try:
                return json.loads(p.read_text())
            except Exception:
                return []
        return []

    def parse_odds(self, odds_data: List[Dict]) -> pd.DataFrame:
        rows = []
        for g in odds_data:
            gid = g.get("event_id") or g.get("id")
            home = g.get("home_team")
            away = g.get("away_team")
            commence = g.get("commence_time")
            for book in g.get("bookmakers", []):
                bk = book.get("key")
                bk_title = book.get("title")
                for market in book.get("markets", []):
                    mk = market.get("key")
                    for outcome in market.get("outcomes", []):
                        rows.append({
                            "event_id": gid,
                            "commence_time": commence,
                            "home": home,
                            "away": away,
                            "book": bk,
                            "book_title": bk_title,
                            "market": mk,
                            "side": outcome.get("name"),
                            "price": outcome.get("price"),
                            "point": outcome.get("point"),
                        })
        return pd.DataFrame(rows)

    def run_daily(self, date: Optional[str] = None) -> pd.DataFrame:
        data = self.get_odds(date=date)
        if not data:
            return pd.DataFrame()
        df = self.parse_odds(data)
        if df.empty:
            return df
        csv_path = self._out_path("csv")
        json_path = self._out_path("json")
        df.to_csv(csv_path, index=False)
        df.to_json(json_path, orient="records", indent=2)
        logger.info(
            f"✅ Saved {len(df)} rows across {df['event_id'].nunique()} games to {csv_path}"
        )
        return df
