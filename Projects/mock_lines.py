"""
Mock market line generator for self-edge picks.

When real DK / SGO / BetMGM lines are unavailable (quota exhausted, off-season,
or backtest replay), we synthesize a reasonable "market line" by regressing the
TC projection toward the position/role mean. The regression factor is
intentionally sport- and role-specific because:

- Soccer G/A are low-volume → heavy regression (0.92 / 0.95)
- Soccer volume stats (SOT, TKL, COR) regress more (0.90) because books shade
  those lines aggressively on totals
- MLB pitcher K/HA/ER regress hard (0.85) — books are sharp on SP props
- NBA/WNBA PTS/REB/AST regress lightly (0.92) — star players have stable rates

The point is not to be perfect — it's to give the OVER/UNDER dispatcher a
non-trivial "market" to compare against so we get graded signals during
self-edge mode.
"""
from typing import Optional


# Role-specific regression factors. Each is (mean_reversion_factor, floor)
# The floor keeps low-projection props from collapsing to zero.
DEFAULT_REGRESSION = 0.88
DEFAULT_FLOOR = 0.4


def get_mock_market_line(
    projection: float,
    sport: str,
    player_role: Optional[str] = None,
) -> float:
    """
    Synthesize a "market line" by regressing the TC projection to the mean.

    Args:
        projection: TC projection for this player/stat
        sport: Sport key (WC, MLB, NBA, WNBA, NHL, NFL)
        player_role: Stat role (goals, assists, cards, strikeouts, points, ...)

    Returns:
        Estimated market line as a float.
    """
    if projection is None or projection <= 0:
        return 0.0

    sport = (sport or "").upper()
    role = (player_role or "").lower()

    # ─── Soccer / World Cup ────────────────────────────────────────────────
    if sport in ("WC", "WORLD_CUP", "SOCCER"):
        if role in ("goals", "g"):
            factor, floor = 0.92, 0.4
        elif role in ("assists", "a", "cards", "crd"):
            factor, floor = 0.95, 0.1
        else:
            # Volume stats: SOT, TKL, COR, S, PAS — heavier regression
            factor, floor = 0.90, 0.5

    # ─── MLB ──────────────────────────────────────────────────────────────
    elif sport == "MLB":
        if role in ("strikeouts", "k", "hits_allowed", "ha", "earned_runs", "er"):
            # Pitcher props — books are sharp
            factor, floor = 0.85, 0.5
        elif role in ("total_bases", "tb", "hits", "h", "runs", "r", "rbi"):
            # Hitter props
            factor, floor = 0.90, 0.5
        else:
            factor, floor = DEFAULT_REGRESSION, DEFAULT_FLOOR

    # ─── NBA / WNBA ───────────────────────────────────────────────────────
    elif sport in ("NBA", "WNBA"):
        if role in ("points", "pts"):
            factor, floor = 0.92, 5.0
        elif role in ("rebounds", "reb", "assists", "ast"):
            factor, floor = 0.92, 1.0
        elif role in ("3pm", "threes", "steals", "stl", "blocks", "blk"):
            factor, floor = 0.90, 0.5
        else:
            factor, floor = DEFAULT_REGRESSION, DEFAULT_FLOOR

    # ─── NHL ──────────────────────────────────────────────────────────────
    elif sport == "NHL":
        factor, floor = 0.90, 0.2

    # ─── NFL ──────────────────────────────────────────────────────────────
    elif sport == "NFL":
        factor, floor = 0.90, 1.0

    else:
        factor, floor = DEFAULT_REGRESSION, DEFAULT_FLOOR

    line = max(floor, projection * factor)
    return round(line, 2)


def is_self_edge(source_label: str) -> bool:
    """Return True if the source tag means 'no real odds were available'."""
    if not source_label:
        return False
    s = source_label.upper()
    return s in ("SELF_EDGE", "MOCK", "ESPN CORE API (SELF-EDGE)")


__all__ = [
    "get_mock_market_line",
    "is_self_edge",
    "DEFAULT_REGRESSION",
    "DEFAULT_FLOOR",
]
