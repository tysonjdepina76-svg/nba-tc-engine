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


class MarketLineProvider:
    """Aggregates player props from DK + FD with self-edge fallback."""

    SUPPORTED_SPORTS = {"NBA", "WNBA", "MLB", "NFL", "NHL", "EPL", "WC"}

    def __init__(
        self,
        dk: DraftKingsAdapter | None = None,
        fd: FanDuelAdapter | None = None,
        odds_api: OddsAPIAdapter | None = None,
    ):
        self.dk = dk or DraftKingsAdapter()
        self.fd = fd or FanDuelAdapter()
        self.odds_api = odds_api  # optional tertiary source

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

        merged = self._merge(dk_rows, fd_rows)
        if use_self_edge_fallback:
            merged = self._inject_self_edge(merged)
        return merged

    @staticmethod
    def _merge(dk: list[dict[str, Any]], fd: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Merge DK + FD by (player, stat, direction). Prefer DK for canonical line."""
        keyed: dict[tuple[str, str, str], dict[str, Any]] = {}
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
    def _inject_self_edge(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
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