#!/usr/bin/env python3
"""
ESPN Odds Fallback - Public ESPN odds pages for MLB/NBA/NFL when Odds API 401s.

Strategy:
  1. Try ESPN's public odds page (static HTML, no auth) via requests+BS4
  2. Fall back to ESPN's internal scoreboard API endpoint (JSON, no auth)
  3. If both fail, return empty + log so caller can use self-edge projections

Scope: game lines (moneyline / spread / total). Player props are NOT on the
public ESPN odds page — those require a sportsbook and are unavailable here.
This is a hard honest limitation, not a bug to fix with random data.

Sports mapped (URL slugs):
  MLB  -> mlb
  NBA  -> nba
  NFL  -> nfl
  NHL  -> nhl
  WNBA -> wnba
  SOCCER -> soccer
  WORLD_CUP -> soccer
"""

import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SPORT_TO_SLUG = {
    "MLB": "baseball/mlb",
    "NBA": "basketball/nba",
    "NFL": "football/nfl",
    "NHL": "hockey/nhl",
    "WNBA": "basketball/wnba",
    "SOCCER": "soccer",
    "WORLD_CUP": "soccer",
}


def _core_slug(site_slug: str) -> str:
    """site API uses baseball/mlb; core API needs baseball/leagues/mlb."""
    parts = site_slug.split("/")
    if len(parts) == 2:
        return f"{parts[0]}/leagues/{parts[1]}"
    return site_slug

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
}


@dataclass
class OddsLine:
    bookmaker: str = "ESPN"
    moneyline: Optional[float] = None
    spread: Optional[float] = None
    spread_price: Optional[float] = None
    total: Optional[float] = None
    total_price: Optional[float] = None
    player_props: Dict[str, Dict] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "bookmaker": self.bookmaker,
            "moneyline": self.moneyline,
            "spread": self.spread,
            "spread_price": self.spread_price,
            "total": self.total,
            "total_price": self.total_price,
            "player_props": self.player_props or {},
        }


class ESPNOddsScraper:
    """Public ESPN odds scraper. No auth, no Selenium. Requests + BS4 only."""

    def __init__(self, cache_ttl: int = 300, timeout: int = 15):
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.cache: Dict[str, Dict] = {}
        self.cache_ttl = cache_ttl
        self.timeout = timeout

    # ------------------------------------------------------------------ public

    def get_odds_for_game(self, game: str, sport: str = "mlb") -> Dict:
        """
        Get odds for a single game keyed by `game` (e.g. "PHI@DET" or "LAL@BOS").
        Returns a dict with keys: lines, bookmaker, source, raw. Empty dict on miss.
        """
        cache_key = f"{sport}_{game}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if time.time() - cached["timestamp"] < self.cache_ttl:
                return cached["data"]

        slug = SPORT_TO_SLUG.get(sport.upper(), sport.lower())
        result: Dict = self._scrape_scoreboard_api(slug)

        if not result:
            result = self._scrape_odds_page(slug)

        if result:
            result = self._match_game(result, game)
            self.cache[cache_key] = {"data": result, "timestamp": time.time()}
            if result:
                logger.info(f"ESPN odds for {game}: matched (source={result.get('source')})")
            else:
                logger.info(f"ESPN odds for {game}: page scraped but game not matched")
        else:
            logger.warning(f"ESPN odds for {game}: no data from any source")

        return result or {}

    def get_all_odds(self, sport: str = "mlb", date: Optional[str] = None) -> Dict:
        """Get all games + lines for a sport on a given date (YYYY-MM-DD)."""
        date = date or datetime.now().strftime("%Y-%m-%d")
        cache_key = f"all_{sport}_{date}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if time.time() - cached["timestamp"] < self.cache_ttl:
                return cached["data"]

        slug = SPORT_TO_SLUG.get(sport.upper(), sport.lower())
        # JSON scoreboard is the only working path (HTML page is bot-blocked 202)
        result: Dict = self._scrape_scoreboard_api(slug, date=date)
        if not result:
            result = self._scrape_odds_page(slug, date=date)

        if result:
            result.setdefault("sport", sport)
            result.setdefault("date", date)
            result.setdefault("timestamp", datetime.utcnow().isoformat())
            self.cache[cache_key] = {"data": result, "timestamp": time.time()}
        return result

    # ----------------------------------------------------------------- scraping

    def _scrape_odds_page(self, slug: str, date: Optional[str] = None) -> Dict:
        """Scrape the public ESPN odds page. Returns dict with `games` list or empty."""
        if date:
            date_compact = date.replace("-", "")
            url = f"https://www.espn.com/{slug}/odds/_/date/{date_compact}"
        else:
            url = f"https://www.espn.com/{slug}/odds"

        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code != 200:
                logger.warning(f"ESPN odds page {url} -> HTTP {resp.status_code}")
                return {}
            soup = BeautifulSoup(resp.text, "html.parser")
        except requests.RequestException as e:
            logger.warning(f"ESPN odds page request failed: {e}")
            return {}

        games = self._parse_odds_table(soup)
        if not games:
            return {}
        return {
            "source": "espn_odds_page",
            "sport": slug,
            "total_games": len(games),
            "games": games,
        }

    def _scrape_scoreboard_api(self, slug: str, date: Optional[str] = None) -> Dict:
        """ESPN's public scoreboard endpoint (JSON, no auth)."""
        url = f"https://site.api.espn.com/apis/site/v2/sports/{slug}/scoreboard"
        params = {}
        if date:
            y, m, d = date.split("-")
            params["dates"] = f"{y}{m}{d}"
        try:
            resp = self.session.get(url, params=params, timeout=self.timeout)
            if resp.status_code != 200:
                return {}
            data = resp.json()
        except (requests.RequestException, json.JSONDecodeError) as e:
            logger.warning(f"ESPN scoreboard API failed: {e}")
            return {}

        games = []
        for ev in data.get("events", []):
            comps = ev.get("competitions", [{}])[0]
            competitors = comps.get("competitors", [])
            if len(competitors) < 2:
                continue
            home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
            away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])
            odds_block = comps.get("odds", [])
            line: Dict = {"bookmaker": "ESPN"}
            # If scoreboard didn't include odds, try the core-API competition odds subpath
            if not odds_block:
                ev_id = ev.get("id") or ev.get("uid")
                comp_id = comps.get("id") or ev_id
                if ev_id:
                    sub = self._fetch_competition_odds(sport_slug=slug, event_id=ev_id, comp_id=comp_id)
                    if sub:
                        odds_block = [sub]
            if odds_block:
                o = odds_block[0]
                line["moneyline"] = self._to_float(o.get("moneyline"))
                line["spread"] = self._to_float(o.get("spread"))
                line["spread_price"] = self._to_float(o.get("spreadOdds") or o.get("pointSpreadOdds"))
                line["total"] = self._to_float(o.get("overUnder"))
                line["total_price"] = self._to_float(o.get("overOdds") or o.get("underOdds"))
            games.append({
                "game": f"{away['team']['abbreviation']}@{home['team']['abbreviation']}",
                "matchup": f"{away['team'].get('displayName','')} @ {home['team'].get('displayName','')}",
                "lines": line,
            })
        if not games:
            return {}
        return {
            "source": "espn_scoreboard_api",
            "sport": slug,
            "total_games": len(games),
            "games": games,
        }

    # ----------------------------------------------------------------- parsing

    def _fetch_competition_odds(self, sport_slug: str, event_id: str, comp_id: str) -> Dict:
        """Pull real DraftKings odds for a single event/competition.

        Endpoint: https://sports.core.api.espn.com/v2/sports/{sport}/events/{eid}/competitions/{cid}/odds
        Returns DraftKings items with moneyline/spread/total.
        """
        # sport_slug like "baseball/mlb" — convert to "baseball/mlb"
        url = f"https://sports.core.api.espn.com/v2/sports/{_core_slug(sport_slug)}/events/{event_id}/competitions/{comp_id}/odds"
        try:
            resp = self.session.get(url, timeout=10)
        except Exception as e:
            logger.debug(f"competition odds fetch error {url}: {e}")
            return {}
        if resp.status_code != 200:
            return {}
        try:
            data = resp.json()
        except Exception:
            return {}
        items = data.get("items") or []
        for it in items:
            prov = it.get("provider") or {}
            name = (prov.get("name") or "").lower()
            if "draftkings" not in name and "dk" not in name and "consensus" not in name and "caesars" not in name:
                continue
            away = (it.get("awayTeamOdds") or {})
            home = (it.get("homeTeamOdds") or {})
            return {
                "bookmaker": prov.get("name"),
                "provider_id": prov.get("id"),
                "lines": {
                    "team_0_moneyline": self._to_float(away.get("moneyLine")),
                    "team_1_moneyline": self._to_float(home.get("moneyLine")),
                    "team_0_spread": self._to_float(away.get("pointSpread", {}).get("value") if isinstance(away.get("pointSpread"), dict) else None),
                    "team_1_spread": self._to_float(home.get("pointSpread", {}).get("value") if isinstance(home.get("pointSpread"), dict) else None),
                    "spread": self._to_float(it.get("spread")),
                    "total": self._to_float(it.get("overUnder")),
                    "over_odds": self._to_float(it.get("overOdds")),
                    "under_odds": self._to_float(it.get("underOdds")),
                },
                "raw": it,
            }
        return {}

    def _parse_odds_table(self, soup: BeautifulSoup) -> List[Dict]:
        """Parse the ESPN odds page table. The page is loosely structured; we
        walk all `.Table--odds-row` (or fallback selectors) and pull the 2
        team rows + bookmaker cells.

        Returns list of dicts: {game, matchup, lines: {bookmaker, ml/spread/total}}.
        Empty list if page structure doesn't match (caller will try API).
        """
        # ESPN renders one section per game with multiple bookmakers. We grab
        # the first bookmaker's row per game (typically consensus/DK).
        games: List[Dict] = []
        # The 2024+ ESPN page uses <section> with classnames like
        # 'OddsTables__Container' or 'Table--odds'. Be liberal.
        sections = soup.find_all("section")
        for sec in sections:
            try:
                teams = sec.find_all("span", class_=re.compile(r"team-name|TeamName|abbrev"))
                if len(teams) < 2:
                    continue
                team0 = teams[0].get_text(strip=True)
                team1 = teams[1].get_text(strip=True)
                if not team0 or not team1:
                    continue

                # Pull moneyline, spread, total from cells with known classes
                line: Dict = {"bookmaker": "ESPN Consensus"}
                ml_cells = sec.find_all("span", class_=re.compile(r"moneyline|ML"))
                if len(ml_cells) >= 2:
                    line["moneyline_home"] = self._american_to_int(ml_cells[0].get_text())
                    line["moneyline_away"] = self._american_to_int(ml_cells[1].get_text())
                spread_cells = sec.find_all("span", class_=re.compile(r"spread|Spread"))
                if len(spread_cells) >= 2:
                    line["spread"] = self._to_float(spread_cells[0].get_text())
                    line["spread_price"] = self._to_float(spread_cells[1].get_text())
                total_cells = sec.find_all("span", class_=re.compile(r"total|OverUnder|ou"))
                if total_cells:
                    line["total"] = self._to_float(total_cells[0].get_text())

                games.append({
                    "game": f"{team1}@{team0}",  # away@home
                    "matchup": f"{team1} @ {team0}",
                    "lines": line,
                })
            except Exception as e:
                logger.debug(f"Section parse error: {e}")
                continue
        return games

    def _match_game(self, scraped: Dict, game: str) -> Optional[Dict]:
        """Match a single game by 'AWAY@HOME' key against scraped games."""
        if not scraped:
            return None
        target = game.upper().replace(" ", "")
        for g in scraped.get("games", []):
            if g.get("game", "").upper() == target:
                return {
                    "lines": g.get("lines", {}),
                    "bookmaker": g.get("lines", {}).get("bookmaker", "ESPN"),
                    "source": scraped.get("source", "espn"),
                    "raw": g,
                }
        # Fuzzy fallback: match on substring of both team abbreviations
        if "@" in target:
            away, home = target.split("@", 1)
            for g in scraped.get("games", []):
                key = g.get("game", "").upper()
                if away in key and home in key:
                    return {
                        "lines": g.get("lines", {}),
                        "bookmaker": g.get("lines", {}).get("bookmaker", "ESPN"),
                        "source": scraped.get("source", "espn"),
                        "raw": g,
                    }
        return None

    # ----------------------------------------------------------------- helpers

    @staticmethod
    def _to_float(s) -> Optional[float]:
        if s is None:
            return None
        try:
            cleaned = re.sub(r"[^\d.\-+]", "", str(s))
            return float(cleaned) if cleaned not in ("", "-", "+") else None
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _american_to_int(s) -> Optional[int]:
        if s is None:
            return None
        cleaned = str(s).strip().replace("+", "")
        if cleaned in ("", "-", "EV", "EVEN"):
            return 100 if cleaned in ("EV", "EVEN") else None
        try:
            return int(cleaned)
        except ValueError:
            return None


# ----------------------------------------------------------------- CLI smoke

if __name__ == "__main__":
    import sys
    sport = sys.argv[1] if len(sys.argv) > 1 else "mlb"
    scraper = ESPNOddsScraper()
    out = scraper.get_all_odds(sport=sport)
    print(json.dumps(out, indent=2, default=str)[:3000])
