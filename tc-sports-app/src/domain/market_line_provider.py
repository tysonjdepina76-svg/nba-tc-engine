"""Market line provider — wires DK and FD adapters with self-edge fallback.

Provides a single interface `get_market_lines(sport, stat)` that:
  1. Tries DraftKings (DK) for the canonical line
  2. Tries FanDuel (FD) for comparison
  3. Falls back to a "self-edge" generated line when both books miss
"""
from __future__ import annotations

from typing import Any

from ..adapters.draftkings import DraftKingsAdapter
from ..adapters.fanduel import FanDuelAdapter
from ..adapters.odds_api import OddsAPIAdapter
from ..adapters.self_edge import SelfEdgeLineProvider


class MarketLineProvider:
    """Aggregates player props from OddsAPI (primary) + DK + FD + SelfEdge."""

    SUPPORTED_SPORTS = {"NBA", "WNBA", "MLB", "NFL", "NHL", "EPL", "WC"}

    def __init__(
        self,
        dk: DraftKingsAdapter | None = None,
        fd: FanDuelAdapter | None = None,
        odds_api: OddsAPIAdapter | None = None,
        self_edge: SelfEdgeLineProvider | None = None,
    ):
        self.dk = dk or DraftKingsAdapter()
        self.fd = fd or FanDuelAdapter()
        self.odds_api = self._init_odds_api(odds_api)
        self.self_edge = self_edge or SelfEdgeLineProvider()

    @staticmethod
    def _init_odds_api(override: OddsAPIAdapter | None) -> OddsAPIAdapter | None:
        if override is not None:
            return override
        try:
            return OddsAPIAdapter(sport="WNBA")
        except Exception as e:
            print(f"[market_line_provider] OddsAPI init failed: {e}")
            return None

    def get_market_lines(
        self,
        sport: str,
        stat: str | None = None,
        use_self_edge_fallback: bool = True,
    ) -> list[dict[str, Any]]:
        """Fetch player prop lines for sport (and optional stat filter).

        Returns list of normalized rows (player/stat/direction/line/odds/book).
        When DK + FD both miss for a player/stat, the row is dropped unless
        `use_self_edge_fallback` is True, in which case a synthetic line is
        injected using the player's TC projection (edge=0 marker).
        """
        sport = sport.upper()
        if sport not in self.SUPPORTED_SPORTS:
            raise ValueError(f"unsupported sport: {sport}")

        stat_filter = [stat] if stat else None

        odds_rows = self._fetch_oddsapi(sport, stat_filter)
        dk_rows = []
        fd_rows = []
        try:
            dk_rows = self.dk.fetch_player_props(sport, stat_filter=stat_filter)
        except Exception as e:
            print(f"[market_line_provider] DK fetch failed: {e}")
        try:
            fd_rows = self.fd.fetch_player_props(sport, stat_filter=stat_filter)
        except Exception as e:
            print(f"[market_line_provider] FD fetch failed: {e}")

        merged = self._merge(odds_rows, dk_rows, fd_rows)
        if use_self_edge_fallback:
            merged = self._inject_self_edge(merged, sport, stat_filter)
        return merged

    def _fetch_oddsapi(self, sport: str, stat_filter) -> list:
        if not self.odds_api:
            return []
        try:
            self.odds_api.sport = sport
            self.odds_api.sport_key = self.odds_api.__class__.__init__.__globals__["SPORT_KEYS"][sport]
            events = self.odds_api.fetch_events()
            rows: list = []
            for ev in events:
                if not isinstance(ev, dict):
                    continue
                eid = ev.get("id")
                if not eid:
                    continue
                props = self.odds_api.fetch_player_props(eid)
                rows.extend(self._normalize_oddsapi(props, stat_filter))
            return rows
        except Exception as e:
            print(f"[market_line_provider] OddsAPI fetch failed: {e}")
            return []

    @staticmethod
    def _normalize_oddsapi(props, stat_filter) -> list:
        """Convert OddsAPI raw event payload → canonical rows.

        OddsAPI format: event.bookmakers[].markets[].outcomes[]
        with name=player, price=odds, point=line, key=stat (over/under).
        """
        rows: list = []
        for ev in props if isinstance(props, list) else []:
            book = ""
            for bm in ev.get("bookmakers", []):
                book = bm.get("key", "oddsapi")
                for mkt in bm.get("markets", []):
                    stat_key = mkt.get("key", "")
                    if stat_filter and stat_key not in stat_filter:
                        continue
                    stat = self_edge_stat_name(stat_key) if False else _ODDSAPI_STAT_MAP.get(stat_key, stat_key)
                    for oc in mkt.get("outcomes", []):
                        rows.append({
                            "player": oc.get("name", ""),
                            "stat": stat,
                            "direction": oc.get("name", "").upper(),  # "Over"/"Under"
                            "line": oc.get("point", 0.0),
                            "odds_american": oc.get("price", -110),
                            "book": book,
                        })
        return rows

    @staticmethod
    def _merge(odds: list[dict[str, Any]], dk: list[dict[str, Any]], fd: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Merge OddsAPI + DK + FD by (player, stat, direction). Prefer OddsAPI line, DK for canonical."""
        keyed: dict[tuple[str, str, str], dict[str, Any]] = {}
        for row in odds:
            key = (row["player"], row["stat"], row["direction"])
            entry = dict(row)
            entry["sources"] = ["oddsapi"]
            keyed[key] = entry
        for row in dk:
            key = (row["player"], row["stat"], row["direction"])
            entry = dict(row)
            entry["sources"] = ["draftkings"]
            keyed[key] = entry
        for row in fd:
            key = (row["player"], row["stat"], row["direction"])
            if key in keyed:
                keyed[key]["sources"].append("fanduel")
                keyed[key]["fd_line"] = row["line"]
                keyed[key]["fd_odds_american"] = row["odds_american"]
            else:
                entry = dict(row)
                entry["sources"] = ["fanduel"]
                keyed[key] = entry
        return list(keyed.values())

    @staticmethod
    def _inject_self_edge(rows: list[dict[str, Any]], sport: str, stat_filter) -> list[dict[str, Any]]:
        """Annotate rows with a `self_edge` marker if only one book or none provided a line.

        For now, this is a passive marker — TC engine can use it to decide
        whether the row is safe to bet on (only self-edge) or sharps agree (DK+FD).
        """
        for r in rows:
            r["self_edge"] = len(r.get("sources", [])) < 2
        return rows

    def best_line(self, sport: str, player: str, stat: str, direction: str) -> dict[str, Any] | None:
        """Return the tightest available line for player/stat/direction."""
        rows = self.get_market_lines(sport, stat=stat, use_self_edge_fallback=False)
        candidates = [r for r in rows if r["player"].lower() == player.lower() and r["direction"] == direction.upper()]
        if not candidates:
            return None
        # tightest line = lowest absolute line (favor under) for OVER, highest for UNDER
        if direction.upper() == "OVER":
            return sorted(candidates, key=lambda r: r["line"])[0]
        return sorted(candidates, key=lambda r: -r["line"])[0]


if __name__ == "__main__":
    import sys
    sport = sys.argv[1] if len(sys.argv) > 1 else "NBA"
    p = MarketLineProvider()
    rows = p.get_market_lines(sport)
    print(f"{sport}: {len(rows)} merged rows")
    for r in rows[:5]:
        print(r)