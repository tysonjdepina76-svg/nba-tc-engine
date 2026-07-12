# tc_math.py - Complete Single Source of Truth
from typing import Literal, Tuple, Optional, Dict, Union
import math
import statistics
from dataclasses import dataclass
from enum import Enum

# ============= Types =============
Direction = Literal["OVER", "UNDER", "FLAT", "INVALID"]
Sport = Literal["NBA", "WNBA", "NFL", "MLB", "NHL", "WC", "NCAAB", "NCAAF", "UFC", "EPL"]

# ============= Sport Configurations =============
@dataclass
class SportConfig:
    """Sport-specific configuration for edge calculation"""
    min_edge: float                          # Minimum edge threshold
    use_pct: bool                           # True = percentage, False = absolute
    max_edge: Optional[float] = None        # Maximum edge (cap for outliers)
    min_market_line: float = 0.5            # Minimum valid market line
    name: str = ""

# Complete sport configurations
SPORT_CONFIGS: Dict[Sport, SportConfig] = {
    # Basketball
    "NBA": SportConfig(min_edge=0.5, use_pct=False, max_edge=15.0, min_market_line=0.5, name="NBA"),
    "WNBA": SportConfig(min_edge=0.5, use_pct=False, max_edge=15.0, min_market_line=0.5, name="WNBA"),
    "NCAAB": SportConfig(min_edge=1.0, use_pct=False, max_edge=25.0, min_market_line=0.5, name="NCAAB"),
    "NCAAF": SportConfig(min_edge=1.5, use_pct=False, max_edge=30.0, min_market_line=0.5, name="NCAAF"),

    # Football
    "NFL": SportConfig(min_edge=0.5, use_pct=False, max_edge=15.0, min_market_line=0.5, name="NFL"),

    # Baseball
    "MLB": SportConfig(min_edge=0.5, use_pct=False, max_edge=8.0, min_market_line=0.5, name="MLB"),

    # Hockey
    "NHL": SportConfig(min_edge=0.2, use_pct=False, max_edge=5.0, min_market_line=0.5, name="NHL"),

    # Soccer
    "WC": SportConfig(min_edge=0.005, use_pct=True, max_edge=0.50, min_market_line=0.5, name="WC/Soccer"),
    "EPL": SportConfig(min_edge=0.005, use_pct=True, max_edge=0.50, min_market_line=0.5, name="EPL"),

    # MMA
    "UFC": SportConfig(min_edge=0.01, use_pct=True, max_edge=0.50, min_market_line=1.0, name="UFC"),
}

# ============= Core Signal Functions =============

def over_under_signal(
    projection: float,
    market_line: float,
    min_abs_edge: float = 0.0,
    use_pct_edge: bool = True,
    max_edge: Optional[float] = None
) -> Tuple[Direction, float]:
    """Canonical projection vs market line comparison."""
    if market_line <= 0 or not math.isfinite(projection) or not math.isfinite(market_line):
        return "INVALID", 0.0
    if projection <= 0:
        return "INVALID", 0.0

    diff = projection - market_line
    abs_diff = abs(diff)

    if use_pct_edge:
        edge = abs_diff / market_line if market_line > 0 else 0.0
    else:
        edge = abs_diff

    if max_edge is not None and edge > max_edge:
        edge = max_edge

    if edge < min_abs_edge:
        return "FLAT", 0.0

    direction: Direction = "OVER" if diff > 0 else "UNDER" if diff < 0 else "FLAT"
    if direction == "FLAT":
        return "FLAT", 0.0

    return direction, edge


def sport_over_under_signal(
    projection: float,
    market_line: float,
    sport: Sport,
    min_edge: Optional[float] = None
) -> Tuple[Direction, float]:
    """Sport-specific projection vs market comparison."""
    config = SPORT_CONFIGS.get(sport)
    if config is None:
        config = SPORT_CONFIGS["NBA"]

    if market_line < config.min_market_line or not math.isfinite(projection):
        return "INVALID", 0.0
    if projection <= 0:
        return "INVALID", 0.0

    diff = projection - market_line
    abs_diff = abs(diff)

    if config.use_pct:
        edge = abs_diff / market_line if market_line > 0 else 0.0
    else:
        edge = abs_diff

    if config.max_edge is not None and edge > config.max_edge:
        edge = config.max_edge

    min_edge_val = min_edge if min_edge is not None else config.min_edge
    if edge < min_edge_val:
        return "FLAT", 0.0

    direction: Direction = "OVER" if diff > 0 else "UNDER" if diff < 0 else "FLAT"
    if direction == "FLAT":
        return "FLAT", 0.0

    return direction, edge


# ============= Multi-Book Consensus =============

def consensus_line(
    lines: list,
    method: str = "median",
    min_books: int = 3
) -> Tuple[Optional[float], int]:
    """Calculate consensus line across multiple sportsbooks."""
    if len(lines) < min_books:
        return None, len(lines)

    valid_lines = [l for l in lines if l > 0 and math.isfinite(l)]
    if len(valid_lines) < min_books:
        return None, len(valid_lines)

    if method == "median":
        return statistics.median(valid_lines), len(valid_lines)
    elif method == "mean":
        return statistics.mean(valid_lines), len(valid_lines)
    elif method == "sharp":
        return valid_lines[-1], len(valid_lines)
    elif method == "mode":
        rounded = [round(l * 2) / 2 for l in valid_lines]
        try:
            mode = statistics.mode(rounded) if rounded else None
        except statistics.StatisticsError:
            mode = rounded[0] if rounded else None
        return mode if mode is not None else (valid_lines[0] if valid_lines else None), len(valid_lines)
    else:
        return statistics.median(valid_lines), len(valid_lines)


def sharpest_line(lines_by_book: Dict[str, float]) -> Optional[float]:
    """Get line from sharpest available book. Priority: Pinnacle > Circa > DraftKings > FanDuel > others"""
    sharp_books = ["Pinnacle", "Circa", "DraftKings", "FanDuel", "BetMGM", "Caesars"]
    for book in sharp_books:
        if book in lines_by_book and lines_by_book[book] > 0:
            return lines_by_book[book]
    valid_lines = [v for v in lines_by_book.values() if v > 0]
    return valid_lines[0] if valid_lines else None


# ============= Edge Analysis =============

@dataclass
class BetRecommendation:
    """Complete bet recommendation"""
    direction: Direction
    edge: float
    market_line: float
    projection: float
    sport: Sport
    confidence: float
    expected_value: Optional[float] = None


def calculate_expected_value(
    direction: Direction,
    edge: float,
    odds: float,
    use_pct_edge: bool = True
) -> float:
    """Calculate expected value for a bet (American odds)."""
    if odds > 0:
        decimal_odds = (odds / 100) + 1
    else:
        decimal_odds = (100 / abs(odds)) + 1

    implied_prob = 1 / decimal_odds
    true_prob = implied_prob + (edge if use_pct_edge else 0)
    true_prob = max(0.01, min(0.99, true_prob))

    ev = (true_prob * decimal_odds) - 1
    return ev


def kelly_criterion(
    edge: float,
    odds: float,
    bankroll: float = 1.0,
    kelly_fraction: float = 0.25
) -> float:
    """Calculate Kelly Criterion stake size."""
    if edge <= 0:
        return 0.0

    if odds > 0:
        decimal_odds = (odds / 100) + 1
    else:
        decimal_odds = (100 / abs(odds)) + 1

    implied_prob = 1 / decimal_odds
    true_prob = implied_prob + edge
    true_prob = max(0.01, min(0.99, true_prob))

    b = decimal_odds - 1
    q = 1 - true_prob
    kelly_pct = ((b * true_prob) - q) / b
    if kelly_pct <= 0:
        return 0.0
    return bankroll * kelly_pct * kelly_fraction


# ============= Backtesting =============

def backtest_picks(picks: list, actuals: dict) -> Dict:
    """Backtest picks against actuals. Returns hit rate, ROI, Sharpe."""
    if not picks:
        return {"hit_rate": 0.0, "roi": 0.0, "sharpe": 0.0, "n": 0, "profit": 0.0}

    wins = 0
    losses = 0
    profit = 0.0
    returns = []

    for pick in picks:
        key = pick.get("key") or (pick.get("player"), pick.get("stat"))
        actual = actuals.get(key)
        if actual is None:
            continue

        line = pick.get("line", 0)
        direction = pick.get("direction", "OVER")
        odds = pick.get("odds", -110)

        if direction == "OVER":
            hit = actual > line
        elif direction == "UNDER":
            hit = actual < line
        else:
            continue

        if odds > 0:
            decimal_odds = (odds / 100) + 1
        else:
            decimal_odds = (100 / abs(odds)) + 1

        if hit:
            wins += 1
            profit += (decimal_odds - 1)
            returns.append(decimal_odds - 1)
        else:
            losses += 1
            profit -= 1
            returns.append(-1)

    n = wins + losses
    if n == 0:
        return {"hit_rate": 0.0, "roi": 0.0, "sharpe": 0.0, "n": 0, "profit": 0.0}

    hit_rate = wins / n
    roi = profit / n
    mean_ret = sum(returns) / n
    variance = sum((r - mean_ret) ** 2 for r in returns) / n if n > 1 else 0
    std = variance ** 0.5
    sharpe = (mean_ret / std) * (n ** 0.5) if std > 0 else 0.0

    return {
        "hit_rate": hit_rate,
        "roi": roi,
        "sharpe": sharpe,
        "n": n,
        "wins": wins,
        "losses": losses,
        "profit": profit,
    }


# ============= Validation =============

def validate_projection(projection: float, sport: Sport) -> bool:
    """Sport-specific range check for projection validity."""
    if not math.isfinite(projection) or projection <= 0:
        return False

    ranges = {
        "NBA": (5, 60), "WNBA": (5, 50), "NCAAB": (5, 60),
        "NFL": (0, 600), "NCAAF": (0, 700),
        "MLB": (0, 12), "NHL": (0, 8),
        "WC": (0, 8), "EPL": (0, 8), "UFC": (0, 30),
    }
    lo, hi = ranges.get(sport, (0, 1000))
    return lo <= projection <= hi


# ============= Display Helpers =============

def format_edge(edge: float, sport: Sport) -> str:
    """Format edge for display, percentage or absolute based on sport config."""
    config = SPORT_CONFIGS.get(sport, SPORT_CONFIGS["NBA"])
    if config.use_pct:
        return f"{edge * 100:.1f}%"
    return f"{edge:.1f}"


def direction_to_symbol(direction: Direction) -> str:
    """Map direction to display symbol."""
    return {"OVER": "▲", "UNDER": "▼", "FLAT": "—", "INVALID": "?"}.get(direction, "?")


def stat_symbol(stat: str) -> str:
    """Map stat to display symbol."""
    mapping = {
        "PTS": "★PTS", "REB": "◆REB", "AST": "▲AST", "STL": "◇STL",
        "BLK": "■BLK", "3PM": "●3PM", "PRA": "★PRA",
        "points": "★PTS", "rebounds": "◆REB", "assists": "▲AST",
        "goals": "▲G", "shots": "●S",
    }
    return mapping.get(stat, stat)


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





def mlb_over_under_signal(projection: float, line: float = None, market_line: float = None) -> tuple:
    """MLB-specific O/U signal. Returns (direction, edge_pct).
    Accepts both `line=` and `market_line=` for backwards compat.
    """
    actual_line = market_line if market_line is not None else line
    return over_under_signal(projection, actual_line, min_abs_edge=0.05, max_edge=0.5)
