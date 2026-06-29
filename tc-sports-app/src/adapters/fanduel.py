"""FanDuel public odds adapter — no auth required.

FanDuel exposes public-facing event and market JSON behind their SPA.
We hit the public-odds endpoint and parse normalized player prop rows.
"""
from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urljoin
from urllib.request import Request, urlopen


class FanDuelAdapter:
    """Public FanDuel adapter for player props and game lines."""

    FD_BASE = "https://sportsbook.fanduel.com"
    API_BASE = "https://sportsbook.fanduel.com/sites/US-NJ-SB/api/v5"

    SPORT_PATHS: dict[str, str] = {
        "NBA": "basketball/nba",
        "WNBA": "basketball/wnba",
        "MLB": "baseball/mlb",
        "NFL": "football/nfl",
        "NHL": "hockey/nhl",
        "EPL": "soccer/epl",
        "WC": "soccer/fifa-world-cup",
    }

    def __init__(self, timeout: float = 15.0, user_agent: str | None = None):
        self.timeout = timeout
        self.ua = user_agent or (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        )

    def _fetch(self, url: str) -> dict[str, Any] | list[Any] | str:
        req = Request(url, headers={"User-Agent": self.ua, "Accept": "application/json"})
        with urlopen(req, timeout=self.timeout) as resp:
            raw = resp.read().decode("utf-8")
        try:
            return json.loads(raw)
        except Exception:
            return raw

    def get_events_page(self, sport: str) -> str:
        path = self.SPORT_PATHS.get(sport.upper(), self.SPORT_PATHS["NBA"])
        url = urljoin(self.FD_BASE + "/", path)
        return self._fetch(url) if isinstance(self._fetch(url), str) else ""

    def get_event_markets_json(self, event_id: str | int) -> dict[str, Any] | list[Any]:
        url = f"{self.API_BASE}/events/{event_id}/markets"
        try:
            return self._fetch(url)
        except Exception as e:
            print(f"[fanduel] event markets error for {event_id}: {e}")
            return {}

    # FanDuel uses camelCase market names similar to DK.
    MARKET_NAME_MAP = {
        "Player Points": "Points",
        "Player Rebounds": "Rebounds",
        "Player Assists": "Assists",
        "Player Threes": "3-Pointers Made",
        "Player Steals": "Steals",
        "Player Blocks": "Blocks",
        "Player Points + Rebounds + Assists": "PRA",
        "Player Points + Rebounds": "PR",
        "Player Points + Assists": "PA",
        "Player Rebounds + Assists": "RA",
    }

    _OVER_UNDER_RE = re.compile(r"(Over|Under)\s+(.*?)\s*\(([0-9.]+)\)", re.IGNORECASE)
    _ALT_RE = re.compile(r"^(.*?)\s*\(([0-9.]+)\)$")

    def parse_prop_outcomes(self, market: dict[str, Any]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        market_name_raw = market.get("marketName", market.get("name", ""))
        stat = self.MARKET_NAME_MAP.get(market_name_raw, market_name_raw)
        for runner in market.get("runners", []) or []:
            label = runner.get("runnerName", "") or runner.get("label", "")
            match = self._OVER_UNDER_RE.search(label)
            if not match:
                continue
            direction = match.group(1).upper()
            player = match.group(2).strip()
            try:
                line = float(match.group(3))
            except Exception:
                continue
            odds_decimal = runner.get("winRunnerOdds", {}).get("decimalOdds", 1.91)
            try:
                odds_american = runner.get("winRunnerOdds", {}).get("americanOdds") or self._dec_to_american(odds_decimal)
            except Exception:
                odds_american = -110
            rows.append({
                "player": player,
                "stat": stat,
                "direction": direction,
                "line": line,
                "odds_american": int(odds_american),
                "odds_decimal": float(odds_decimal),
                "book": "fanduel",
            })
        return rows

    @staticmethod
    def _dec_to_american(decimal_odds: float) -> int:
        try:
            d = float(decimal_odds)
        except Exception:
            return -110
        if d >= 2.0:
            return int(round((d - 1.0) * 100))
        return int(round(-100 / (d - 1.0)))

    def fetch_player_props(
        self,
        sport: str,
        stat_filter: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """High-level fetch of normalized player prop rows for a sport."""
        if stat_filter is None:
            stat_filter = list(self.MARKET_NAME_MAP.values())

        out: list[dict[str, Any]] = []
        page = self.get_events_page(sport)
        if not page:
            return out
        # Cheap heuristic: harvest any eventId pattern from the page payload.
        event_ids = list(set(re.findall(r'"eventId"\s*:\s*"?(\d+)"?', page)))[:25]
        for eid in event_ids:
            data = self.get_event_markets_json(eid)
            markets = data.get("markets", []) if isinstance(data, dict) else []
            for m in markets:
                market_name = m.get("marketName", m.get("name", ""))
                stat = self.MARKET_NAME_MAP.get(market_name, market_name)
                if stat not in stat_filter:
                    continue
                out.extend(self.parse_prop_outcomes(m))
        return out


if __name__ == "__main__":
    import sys
    sport = sys.argv[1] if len(sys.argv) > 1 else "NBA"
    a = FanDuelAdapter()
    rows = a.fetch_player_props(sport)
    print(f"fanduel {sport}: {len(rows)} rows")
    for r in rows[:5]:
        print(r)