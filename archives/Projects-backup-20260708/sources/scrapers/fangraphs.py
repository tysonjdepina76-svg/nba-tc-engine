"""FanGraphs scraper for advanced MLB stats (wOBA, wRC+, FIP, etc.).

Used as a tier-3 fallback alongside Baseball-Reference.

NOTE: As of 2026-07-05, FanGraphs.com is fully Cloudflare-protected and
blocks non-browser requests. The /api/leaders/major-league/data endpoint
returns an interactive challenge (cf_chl_opt) rather than JSON. We
intentionally do NOT attempt to bypass this — returns empty + clear error
so the fallback chain continues cleanly to ESPN / cache / self-edge.
"""
import requests
import re
from typing import List, Dict, Optional

CLOUDFLARE_BLOCKED_MSG = "FanGraphs blocked: Cloudflare anti-bot challenge"


class FanGraphsScraper:
    BASE_URL = "https://www.fangraphs.com/leaders/major-league"

    def __init__(self, season: int = 2026):
        self.season = season
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml",
        }

    def fetch_hitters(self) -> List[Dict]:
        """Fetch hitting leaderboard. Returns [] on Cloudflare block."""
        params = {
            "pos": "all", "stats": "bat", "lg": "all", "qual": "0",
            "type": "0", "season": str(self.season), "month": "0",
            "season1": str(self.season), "ind": "0", "team": "0",
            "rost": "0", "age": "0", "filter": "", "players": "0",
            "startdate": "", "enddate": "", "sort": "16,d", "page": "1_50",
        }
        return self._fetch_and_parse(params, "hitting")

    def fetch_pitchers(self) -> List[Dict]:
        """Fetch pitching leaderboard. Returns [] on Cloudflare block."""
        params = {
            "pos": "all", "stats": "pit", "lg": "all", "qual": "0",
            "type": "0", "season": str(self.season), "month": "0",
            "season1": str(self.season), "ind": "0", "team": "0",
            "rost": "0", "age": "0", "filter": "", "players": "0",
            "startdate": "", "enddate": "", "sort": "20,d", "page": "1_50",
        }
        return self._fetch_and_parse(params, "pitching")

    def _fetch_and_parse(self, params: Dict, kind: str) -> List[Dict]:
        try:
            resp = requests.get(
                self.BASE_URL,
                params=params,
                headers=self.headers,
                timeout=15,
            )
        except requests.RequestException as e:
            print(f"FanGraphs network error: {e}")
            return []

        # Cloudflare challenge — page is a JS challenge, not data
        if b"cf_chl_opt" in resp.content or b"challenge-platform" in resp.content:
            print(f"[fangraphs] {CLOUDFLARE_BLOCKED_MSG}")
            return []

        if resp.status_code != 200:
            print(f"FanGraphs HTTP {resp.status_code}")
            return []

        return self._parse_table(resp.text, kind)

    @staticmethod
    def _parse_table(html: str, kind: str) -> List[Dict]:
        """Parse the FanGraphs leaderboard table.

        FG wraps the table in a div and may lazy-render rows client-side.
        If we can't find rows, we return [] rather than guessing.
        """
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table", class_=re.compile(r"rgMasterTable|sortable"))
        if not table:
            table = soup.find("table", id=re.compile(r"LeaderBoard"))
        if not table:
            return []

        rows = table.find("tbody")
        if not rows:
            return []
        rows = rows.find_all("tr")

        results: List[Dict] = []
        for row in rows:
            cells = row.find_all(["th", "td"])
            if len(cells) < 4:
                continue
            name_cell = cells[1] if len(cells) > 1 else cells[0]
            name_link = name_cell.find("a")
            name = (name_link.text if name_link else name_cell.text).strip()
            team = cells[2].text.strip() if len(cells) > 2 else ""

            results.append(
                {
                    "name": name,
                    "team": team,
                    "raw_cells": [c.text.strip() for c in cells],
                }
            )
        return results

    @staticmethod
    def _safe_float(val) -> float:
        try:
            return float(str(val).strip())
        except (ValueError, AttributeError):
            return 0.0

    @staticmethod
    def _safe_int(val) -> int:
        try:
            return int(str(val).strip())
        except (ValueError, AttributeError):
            return 0


if __name__ == "__main__":
    scraper = FangraphsScraper(season=2026)
    hitters = scraper.fetch_hitters()
    print(f"Hitters: {len(hitters)}")
    if hitters:
        print(f"  sample: {hitters[0]}")
    pitchers = scraper.fetch_pitchers()
    print(f"Pitchers: {len(pitchers)}")
    if pitchers:
        print(f"  sample: {pitchers[0]}")
