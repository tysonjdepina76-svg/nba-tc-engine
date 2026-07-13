"""Soccer / World Cup line fetcher.

Pulls game-level lines (h2h, totals, btts) for today's events.
Uses soccer_tc_engine.fetch_world_cup_events() to discover events, then calls
fetch_soccer_odds() per event. Odds API quota is currently maxed (Business tier
quota exhausted) so the 401 fallback is expected — we just return None values
and let the registry/dashboard know lines are unavailable.

Returns: {"games": [{"event_id", "away", "home", "h2h", "totals", "btts", "source"}], "source": "..."}
"""

import sys
from pathlib import Path
from typing import Dict, List, Any

WORKSPACE = Path("/home/workspace")
sys.path.insert(0, str(WORKSPACE / "Projects"))


def _flatten_odds_for_matchup(result: dict) -> dict:
    """Pull out the first available book's h2h/totals/btts into top-level fields.

    Schema returns nested {bookmaker_key: {market_key: {outcome: {price, point}}}}.
    We just want the first book with data for each market.
    """
    out = {"h2h": None, "totals": None, "btts": None, "source": None}
    for book_key, markets in result.items():
        if book_key in ("event_id", "home_team", "away_team", "commence_time", "error"):
            continue
        if not isinstance(markets, dict):
            continue
        for mk in ("h2h", "totals", "btts"):
            if mk in markets and out[mk] is None:
                out[mk] = markets[mk]
        out["source"] = book_key
        if out["h2h"] and out["totals"]:
            break
    return out


def fetch_soccer_lines(date: str = None) -> Dict[str, Any]:
    """Fetch game lines for today's World Cup events.

    Args:
        date: Optional YYYY-MM-DD filter (unused for now — engine returns today).

    Returns:
        {"games": [...], "source": "odds_api" | "espn" | "none"}
    """
    try:
        from soccer_tc_engine import fetch_world_cup_events, fetch_soccer_odds
    except ImportError as e:
        return {"games": [], "source": "none", "error": f"import: {e}"}

    try:
        events = fetch_world_cup_events() or []
    except Exception as e:
        return {"games": [], "source": "none", "error": f"events: {e}"}

    if not events:
        return {"games": [], "source": "none"}

    games = []
    quota_exhausted = False
    for ev in events:
        eid = ev.get("id") or ev.get("event_id")
        home = ev.get("home_team", "")
        away = ev.get("away_team", "")
        if not eid or not home or not away:
            continue
        try:
            odds = fetch_soccer_odds(eid)
        except Exception:
            odds = {"error": "fetch failed"}

        if odds.get("error"):
            err_str = str(odds.get("error", "")).lower()
            if "401" in err_str or "quota" in err_str or "unauthorized" in err_str:
                quota_exhausted = True
            continue

        flat = _flatten_odds_for_matchup(odds)
        games.append({
            "event_id": eid,
            "away": away,
            "home": home,
            "h2h": flat["h2h"],
            "totals": flat["totals"],
            "btts": flat["btts"],
            "source": flat["source"] or "odds_api",
        })

    source = "odds_api" if games else ("quota_exhausted" if quota_exhausted else "none")
    return {"games": games, "source": source}
