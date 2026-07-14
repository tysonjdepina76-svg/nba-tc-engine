import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
import logging
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path

from src.adapters.world_cup_adapter import WorldCupAdapter

logger = logging.getLogger(__name__)
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(h)
    logger.setLevel(logging.INFO)

CACHE_DIR = Path(__file__).parent.parent / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_path(date: str) -> Path:
    return CACHE_DIR / f"wc_odds_{date}.json"


def _american_to_decimal(odds: int) -> float:
    if odds is None:
        return 2.0
    if odds >= 100:
        return 1.0 + (odds / 100.0)
    if odds <= -100:
        return 1.0 + (100.0 / abs(odds))
    return 2.0


def _implied_prob(odds: int) -> float:
    if odds is None:
        return 0.5
    if odds >= 100:
        return 100.0 / (odds + 100.0)
    return abs(odds) / (abs(odds) + 100.0)


def _parse_match_round(league_season: Dict) -> str:
    season = (league_season or {}).get("type", {}).get("name", "").lower()
    if "final" in season and "group" not in season:
        return "final"
    if "semifinal" in season:
        return "semifinal"
    if "quarter" in season:
        return "quarterfinal"
    if "round of 16" in season or "round_of_16" in season:
        return "round_of_16"
    return "group_stage"


def fetch_wc_lines(date: str = None, use_cache: bool = True) -> Dict:
    """Fetch WC / soccer prop lines via ESPN. Returns dict of games with odds."""
    date = date or datetime.now().strftime("%Y%m%d")
    cache = _cache_path(date)
    if use_cache and cache.exists() and (datetime.now().timestamp() - cache.stat().st_mtime) < 3600:
        try:
            with open(cache) as f:
                logger.info(f"WC odds cache hit: {cache}")
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            pass

    adapter = WorldCupAdapter()
    events = adapter.get_events(date=date)
    games: List[Dict] = []
    for ev in events:
        comps = ev.get("competitions", [{}])[0].get("competitors", [{}, {}])
        if len(comps) < 2:
            continue
        ml_home = ev.get("moneyline_home")
        ml_away = ev.get("moneyline_away")
        ml_draw = ev.get("moneyline_draw")
        games.append({
            "game_id": ev.get("game_id"),
            "home": ev.get("home_team"),
            "away": ev.get("away_team"),
            "start_time": ev.get("start_time"),
            "match_round": _parse_match_round(ev.get("league_season", {})),
            "moneyline": {
                "home_odds": ml_home,
                "home_decimal": _american_to_decimal(ml_home),
                "home_prob": _implied_prob(ml_home),
                "away_odds": ml_away,
                "away_decimal": _american_to_decimal(ml_away),
                "away_prob": _implied_prob(ml_away),
                "draw_odds": ml_draw,
                "draw_prob": _implied_prob(ml_draw) if ml_draw else 0.0,
            },
        })

    out = {"date": date, "source": "espn_wc", "games": games, "fetched_at": datetime.now().isoformat()}
    try:
        with open(cache, "w") as f:
            json.dump(out, f, indent=2)
    except OSError as e:
        logger.error(f"WC odds cache write failed: {e}")
    logger.info(f"WC odds fetched: {len(games)} games for {date}")
    return out


def get_wc_picks_with_lines(date: str = None) -> List[Dict]:
    """Combine WC projections with fetched lines."""
    from sources.wc_tc_engine import generate_wc_picks
    date = date or datetime.now().strftime("%Y%m%d")
    projections = generate_wc_picks(date=date)
    odds = fetch_wc_lines(date=date)
    games_by_team = {}
    for g in odds.get("games", []):
        for side in ("home", "away"):
            t = g.get(side)
            if t:
                games_by_team.setdefault(t, g)
    for p in projections:
        g = games_by_team.get(p.get("team", ""))
        if g:
            p["game_id"] = g.get("game_id")
            p["moneyline"] = g.get("moneyline", {})
            p["start_time"] = g.get("start_time")
    return projections


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    out = get_wc_picks_with_lines()
    print(f"WC picks w/ lines: {len(out)}")
    for p in out[:2]:
        print(json.dumps(p, indent=2))
