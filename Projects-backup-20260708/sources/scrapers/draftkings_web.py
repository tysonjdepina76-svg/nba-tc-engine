"""DraftKings web scraper (sportsbook.draftkings.com).

Fallback when the DK public API returns 403. Scrapes the sportsbook pages
directly and parses window.__INITIAL_STATE__ if present.
"""
import json
import re
from typing import List, Dict

import requests
from bs4 import BeautifulSoup


class DraftKingsWebScraper:
    BASE_URL = "https://sportsbook.draftkings.com"

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://www.draftkings.com/",
        }

    def fetch_mlb_lines(self) -> List[Dict]:
        return self._fetch_lines(f"{self.BASE_URL}/leagues/baseball/mlb", "mlb")

    def fetch_wnba_lines(self) -> List[Dict]:
        return self._fetch_lines(f"{self.BASE_URL}/leagues/basketball/wnba", "wnba")

    def fetch_soccer_lines(self) -> List[Dict]:
        return self._fetch_lines(f"{self.BASE_URL}/leagues/soccer/world-cup", "soccer")

    def _fetch_lines(self, url: str, sport: str) -> List[Dict]:
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            print(f"[{sport}] DK web fetch failed: {e}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")

        # Try __INITIAL_STATE__ first (most reliable)
        script = soup.find("script", text=re.compile(r"window\.__INITIAL_STATE__"))
        if script and script.string:
            json_match = re.search(
                r"window\.__INITIAL_STATE__\s*=\s*({.*?});", script.string, re.DOTALL
            )
            if json_match:
                try:
                    data = json.loads(json_match.group(1))
                    parsed = self._parse_state(data, sport)
                    if parsed:
                        return parsed
                except (ValueError, json.JSONDecodeError) as e:
                    print(f"[{sport}] DK state parse failed: {e}")

        return self._parse_html(soup, sport)

    def _parse_state(self, data: dict, sport: str) -> List[Dict]:
        """Extract games from __INITIAL_STATE__. The shape varies by sport/season,
        so we walk a few common paths and stop at the first one with content."""
        games: List[Dict] = []

        def _walk(obj, depth=0):
            if depth > 8 or not isinstance(obj, (dict, list)):
                return None
            if isinstance(obj, dict):
                # Look for event-shaped dicts
                if all(k in obj for k in ("awayTeam", "homeTeam")) or (
                    "name" in obj and "teamShortName" in obj and "odds" in obj
                ):
                    return obj
                for v in obj.values():
                    found = _walk(v, depth + 1)
                    if found:
                        return found
            elif isinstance(obj, list) and obj:
                for v in obj:
                    found = _walk(v, depth + 1)
                    if found:
                        return found
            return None

        # Try a few common root keys first
        for key in ("events", "offers", "eventGroups", "league", "data"):
            if key in data:
                games = self._extract_games(data[key], sport)
                if games:
                    return games

        # Fallback: deep walk
        event = _walk(data)
        if event:
            games = [self._normalize_event(event, sport)]

        return games

    def _extract_games(self, node, sport: str) -> List[Dict]:
        games: List[Dict] = []
        if isinstance(node, list):
            for item in node:
                g = self._normalize_event(item, sport)
                if g:
                    games.append(g)
        elif isinstance(node, dict):
            g = self._normalize_event(node, sport)
            if g:
                games.append(g)
        return games

    def _normalize_event(self, event: dict, sport: str) -> Dict:
        """Try to extract a single game dict in line_fetcher standard shape."""
        if not isinstance(event, dict):
            return None

        away = event.get("awayTeam", {}).get("name") or event.get("away", {}).get("name")
        home = event.get("homeTeam", {}).get("name") or event.get("home", {}).get("name")
        if not away and "name" in event:
            # Single-team entries (leaderboards, etc.) — skip
            return None
        if not (away and home):
            return None

        return {
            "away": away,
            "home": home,
            "spread": None,
            "moneyline": None,
            "total": None,
            "sport": sport,
        }

    def _parse_html(self, soup: BeautifulSoup, sport: str) -> List[Dict]:
        """Fallback HTML table parser for non-JS-rendered pages."""
        games: List[Dict] = []
        tables = soup.find_all("table", class_=re.compile(r"sportsbook", re.I))
        for table in tables:
            for row in table.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) >= 5:
                    games.append(
                        {
                            "away": cells[0].text.strip(),
                            "home": cells[1].text.strip(),
                            "spread": cells[2].text.strip(),
                            "total": cells[3].text.strip(),
                            "moneyline": cells[4].text.strip(),
                            "sport": sport,
                        }
                    )
        return games
