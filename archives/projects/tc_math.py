"""
Sport-specific projection vs market comparison.

Replaces ad-hoc per-sport thresholds with a single dispatcher. Each sport
declares its own min edge (absolute for high-volume sports, percentage for
low-volume / sharp markets like soccer).
"""
from typing import Literal, Tuple, Optional
import math

Direction = Literal["OVER", "UNDER", "FLAT", "INVALID"]
Sport = Literal["NBA", "WNBA", "NFL", "MLB", "NHL", "WC", "WORLD_CUP", "SOCCER"]

# Per-sport thresholds.
#   use_pct=True  -> edge = |proj - line| / line (soccer / sharp markets)
#   use_pct=False -> edge = |proj - line|            (most sports, absolute units)
SPORT_THRESHOLDS = {
    "NBA":        {"min_edge": 0.5,   "use_pct": False},  # 0.5 points
    "WNBA":       {"min_edge": 0.5,   "use_pct": False},  # 0.5 points
    "NFL":        {"min_edge": 0.5,   "use_pct": False},  # 0.5 points / yards
    "MLB":        {"min_edge": 0.5,   "use_pct": False},  # 0.5 runs / Ks
    "NHL":        {"min_edge": 0.2,   "use_pct": False},  # 0.2 goals
    "WC":         {"min_edge": 0.005, "use_pct": True},   # 0.5% edge
    "WORLD_CUP":  {"min_edge": 0.005, "use_pct": True},
    "SOCCER":     {"min_edge": 0.005, "use_pct": True},
}


def sport_over_under_signal(
    projection: float,
    market_line: float,
    sport: str,
    min_edge: Optional[float] = None,
) -> Tuple[str, float]:
    """
    Compare a TC projection to a market line and return (direction, edge).

    Returns:
        ("OVER"|"UNDER", edge_value)  when |edge| >= threshold
        ("FLAT", 0.0)                 when below threshold (no value)
        ("INVALID", 0.0)              when inputs unusable
    """
    if market_line is None or market_line <= 0 or not math.isfinite(projection):
        return "INVALID", 0.0

    sport_key = (sport or "").upper()
    cfg = SPORT_THRESHOLDS.get(sport_key, SPORT_THRESHOLDS["NBA"])
    threshold = min_edge if min_edge is not None else cfg["min_edge"]

    diff = projection - market_line
    abs_diff = abs(diff)

    if cfg["use_pct"]:
        edge = abs_diff / market_line
    else:
        edge = abs_diff

    if edge < threshold:
        return "FLAT", 0.0

    direction = "OVER" if diff > 0 else "UNDER"
    return direction, edge


def debug_over_signal(projection: float, market_line: float, sport: str = "WC",
                      min_edge: Optional[float] = None) -> Tuple[str, float]:
    """
    Diagnostic wrapper: prints projection/line/edge% then returns the signal.
    Useful for live debugging of the OVER/UNDER bias in any sport.
    """
    direction, edge = sport_over_under_signal(
        projection=projection,
        market_line=market_line,
        sport=sport,
        min_edge=min_edge,
    )
    print(f"Proj: {projection:.2f} | Line: {market_line:.2f} | Sport: {sport}")
    print(f"Diff: {projection - market_line:.2f}")
    if market_line > 0:
        cfg = SPORT_THRESHOLDS.get((sport or "").upper(), SPORT_THRESHOLDS["NBA"])
        if cfg["use_pct"]:
            print(f"Edge %: {edge * 100:.2f}%")
        else:
            print(f"Edge (abs): {edge:.2f}")
    else:
        print("Edge %: N/A (line <= 0)")
    print(f"Direction: {direction} | Edge: {edge:.4f}")
    print("-" * 40)
    return direction, edge


# Convenience aliases for the sport-specific helpers in the spec.
def mlb_over_under_signal(projection: float, market_line: float) -> Tuple[str, float]:
    return sport_over_under_signal(projection, market_line, "MLB")


def nhl_over_under_signal(projection: float, market_line: float) -> Tuple[str, float]:
    return sport_over_under_signal(projection, market_line, "NHL")


def wc_over_under_signal(projection: float, market_line: float) -> Tuple[str, float]:
    return sport_over_under_signal(projection, market_line, "WC")


__all__ = [
    "over_under_signal",
    "mlb_over_under_signal",
    "nba_over_under_signal",
    "nhl_over_under_signal",
    "wc_over_under_signal",
    "sport_over_under_signal",
    "debug_over_signal",
    "Direction",
]


def over_under_signal(
    projection: float,
    market_line: float,
    min_abs_edge: float = 0.5,
) -> Tuple[str, float]:
    """Generic dispatcher. Defaults to a 0.5% edge floor (percentage-based)."""
    return sport_over_under_signal(
        projection=projection,
        market_line=market_line,
        sport="GENERIC",
        min_edge=min_abs_edge,
    )


def debug_over_signal(
    projection: float,
    market_line: float,
    sport: str = "GENERIC",
    min_abs_edge: float = None,
) -> Tuple[str, float]:
    """Log-friendly signal diagnostic. Prints decision + reason."""
    sport_defaults = {
        "MLB": (0.5, "pct"),
        "NBA": (0.5, "pct"),
        "NHL": (0.5, "pct"),
        "WORLD_CUP": (0.005, "pct"),
        "WC": (0.005, "pct"),
        "GENERIC": (0.5, "pct"),
    }
    if min_abs_edge is None:
        min_abs_edge = sport_defaults.get(sport.upper(), (0.5, "pct"))[0]
    direction, edge = sport_over_under_signal(
        projection=projection,
        market_line=market_line,
        sport=sport,
        min_edge=min_abs_edge,
    )
    print(
        f"[debug_over_signal] {sport} proj={projection:.3f} line={market_line:.3f} "
        f"edge={edge:.4f} → {direction}"
    )
    return direction, edge

# Self-edge thresholds (no real market line). Higher than real-odds because
# the "market" is a mock_lines regression - noisier than a real book.
# Values are PERCENT (3.5 = 3.5%).
SELF_EDGE_THRESHOLDS = {
    "WC":   3.5,
    "MLB":  4.0,
    "WNBA": 2.5,
    "NBA":  2.0,
    "NHL":  3.0,
    "NFL":  3.0,
}


def self_edge_signal(
    projection: float,
    sport: str,
    player_role: str = None,
) -> Tuple[str, float, float]:
    """
    Build a mock market line, then call sport_over_under_signal against it.

    Returns:
        (direction, edge_pct, market_line)
        direction in {"OVER", "UNDER", "FLAT", "INVALID"}
    """
    try:
        from mock_lines import get_mock_market_line
    except Exception:
        return "INVALID", 0.0, 0.0

    sport_key = (sport or "").upper()
    if sport_key == "WORLD_CUP":
        sport_key = "WC"

    market_line = get_mock_market_line(projection, sport_key, player_role)
    threshold = SELF_EDGE_THRESHOLDS.get(sport_key, 3.0) / 100.0  # pct to fraction

    direction, edge = sport_over_under_signal(
        projection=projection,
        market_line=market_line,
        sport=sport_key,
        min_edge=threshold,
    )
    return direction, edge, market_line


def is_sane_edge(tc_val: float, line_val: float, max_ratio: float = 2.5) -> bool:
    """Reject edge if TC is wildly off market line (>max_ratio or 0)."""
    if line_val is None or line_val <= 0:
        return True  # No market line; allow self-edge
    if tc_val is None or tc_val <= 0:
        return False
    ratio = max(tc_val, line_val) / min(tc_val, line_val)
    return ratio <= max_ratio


def shrink_projection(tc_val: float, line_val: float, sample: int = 1, k: int = 20) -> float:
    """Bayesian-shrink TC projection toward market line based on sample size.
    Higher sample = trust TC more; low sample = regress toward line.
    """
    if not tc_val or not line_val or sample is None or sample <= 0:
        return tc_val
    weight = sample / (sample + k)
    return weight * tc_val + (1 - weight) * line_val
