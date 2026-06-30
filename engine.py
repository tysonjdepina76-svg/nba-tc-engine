"""TC engine — projection vs line, edge %, confidence."""

from typing import List


def compute_tc(projection: float, line: float, std_dev: float, direction: str) -> float:
    if std_dev < 0:
        raise ValueError("std_dev cannot be negative")
    if direction not in ("OVER", "UNDER"):
        raise ValueError(f"direction must be OVER or UNDER, got {direction!r}")
    if std_dev == 0:
        return 0.0
    delta = projection - line
    if direction == "UNDER":
        delta = -delta
    return round(delta / std_dev, 4)


def hit_rate(samples: List[float], line: float, direction: str) -> float:
    if direction not in ("OVER", "UNDER"):
        raise ValueError(f"direction must be OVER or UNDER, got {direction!r}")
    if not samples:
        raise ValueError("samples cannot be empty")
    if direction == "OVER":
        hits = sum(1 for s in samples if s > line)
    else:
        hits = sum(1 for s in samples if s < line)
    return round(hits / len(samples), 4)


def edge_pct(projection: float, line: float, direction: str) -> float:
    if line == 0:
        return 0.0
    if direction == "OVER":
        return round(((projection - line) / line) * 100, 2)
    if direction == "UNDER":
        return round(((line - projection) / line) * 100, 2)
    raise ValueError(f"direction must be OVER or UNDER, got {direction!r}")


def projection_vs_line(projection: float, line: float, std_dev: float) -> str:
    delta = projection - line
    threshold = 1.0 * std_dev if std_dev > 0 else 0.5
    if delta > threshold:
        return "STRONG_OVER"
    if delta > 0.5:
        return "OVER"
    if delta < -threshold:
        return "STRONG_UNDER"
    if delta < -0.5:
        return "UNDER"
    return "NEUTRAL"
