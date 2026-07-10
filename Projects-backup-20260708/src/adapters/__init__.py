from . import cache
from . import espn
from . import sgo
from . import odds_api

__all__ = ["cache", "espn", "sgo", "odds_api"]


def daily_usage() -> dict:
    """Return today's call counts per adapter + total / cap."""
    from .cache import quota_state, DAILY_LIMIT
    state = quota_state()
    counts = state.get("counts", {})
    total = sum(counts.values())
    return {
        "date": state.get("date", ""),
        "counts": counts,
        "total": total,
        "limit": DAILY_LIMIT,
        "remaining": max(0, DAILY_LIMIT - total),
        "pct_used": round(100.0 * total / DAILY_LIMIT, 1) if DAILY_LIMIT > 0 else 0.0,
    }