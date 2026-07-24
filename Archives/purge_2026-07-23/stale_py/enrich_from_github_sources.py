#!/usr/bin/env python3
"""enrich_from_github_sources.py
Fallback enrichment using free GitHub sports API packages.
Runs when SerpAPI is dead/capped. Never costs money.

Sources:
  MLB   → statsapi (MLB-StatsAPI) — live games, player stats, no key
  WNBA  → nba_api (stats.nba.com WNBA endpoints) — live stats, no key
  WC    → ESPN hidden API / Football-data.org free tier

Caps: NEVER more than 5 calls per sport per run.
"""

import os, sys, json, logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
SRC_ADAPTERS = Path(__file__).parent / "src" / "adapters"
sys.path.insert(0, str(Path(__file__).parent))

PER_RUN_MAX = 5
TRACKER_FILE = DATA_DIR / "github_enrich_usage.json"

# ---- Quota tracking ----
def _track(sport, n):
    d = {}
    if TRACKER_FILE.exists():
        d = json.loads(TRACKER_FILE.read_text())
    today = datetime.now(ET).strftime("%Y-%m-%d")
    key = f"{sport}_{today}"
    d[key] = d.get(key, 0) + n
    TRACKER_FILE.write_text(json.dumps(d))

def _remaining(sport):
    d = {}
    if TRACKER_FILE.exists():
        d = json.loads(TRACKER_FILE.read_text())
    today = datetime.now(ET).strftime("%Y-%m-%d")
    key = f"{sport}_{today}"
    return max(0, PER_RUN_MAX - d.get(key, 0))


# ═══════════════════════════════════════
#  MLB — statsapi (free, no key)
# ═══════════════════════════════════════
def enrich_mlb(projections):
    """Fetch live MLB stats via statsapi and annotate projections."""
    try:
        from src.adapters.mlb_api_adapter import get_todays_games, get_live_boxscore
    except Exception:
        logger.warning("[GitHub:MLB] statsapi adapter not available")
        return projections

    remain = _remaining("mlb")
    if remain <= 0:
        logger.info("[GitHub:MLB] cap reached for today")
        return projections

    try:
        games = get_todays_games()
        logger.info(f"[GitHub:MLB] {len(games)} games today")
        _track("mlb", 1)
    except Exception as e:
        logger.warning(f"[GitHub:MLB] get_todays_games failed: {e}")
        return projections

    for i, proj in enumerate(projections):
        proj.setdefault("github_enrich", False)

    for game in games[:PER_RUN_MAX]:
        try:
            box = get_live_boxscore(game.get("game_id", game.get("gamePk", 0)))
            if not box:
                continue
            _track("mlb", 1)

            for proj in projections:
                player = proj.get("name", proj.get("player", ""))
                if not player:
                    continue
                for side in ("home", "away"):
                    batters = box.get(side, {}).get("batters", [])
                    for b in batters:
                        if player.lower() in b.get("name", "").lower():
                            proj["live_stat"] = b.get(proj.get("stat", "").lower(), None)
                            proj["github_enrich"] = True
                            proj.setdefault("signal", "GITHUB_MLB")
        except Exception as e:
            logger.debug(f"[GitHub:MLB] boxscore error: {e}")
            continue

    return projections


# ═══════════════════════════════════════
#  WNBA — nba_api (free, no key)
# ═══════════════════════════════════════
def enrich_wnba(projections):
    """Fetch live WNBA stats via nba_api and annotate projections."""
    try:
        from src.adapters.wnba_api_adapter import get_wnba_games, get_wnba_boxscore
    except Exception:
        logger.warning("[GitHub:WNBA] nba_api adapter not available")
        return projections

    remain = _remaining("wnba")
    if remain <= 0:
        logger.info("[GitHub:WNBA] cap reached for today")
        return projections

    try:
        games = get_wnba_games()
        logger.info(f"[GitHub:WNBA] {len(games)} games today")
        _track("wnba", 1)
    except Exception as e:
        logger.warning(f"[GitHub:WNBA] get_wnba_games failed: {e}")
        return projections

    for i, proj in enumerate(projections):
        proj.setdefault("github_enrich", False)

    for game in games[:PER_RUN_MAX]:
        try:
            game_id = game.get("game_id", game.get("gameId", ""))
            if not game_id:
                continue
            box = get_wnba_boxscore(game_id)
            if not box:
                continue
            _track("wnba", 1)

            for proj in projections:
                player = proj.get("name", proj.get("player", ""))
                if not player:
                    continue
                for side in ("home", "away"):
                    players = box.get(side, {}).get("players", [])
                    for p in players:
                        if player.lower() in p.get("name", "").lower():
                            proj["live_stat"] = p.get("stats", {}).get(proj.get("stat", "").upper(), None)
                            proj["github_enrich"] = True
                            proj.setdefault("signal", "GITHUB_WNBA")
        except Exception as e:
            logger.debug(f"[GitHub:WNBA] boxscore error: {e}")
            continue

    return projections


# ═══════════════════════════════════════
#  WC — World Cup adapter (ESPN / free)
# ═══════════════════════════════════════
def enrich_wc(projections):
    """Fetch WC data via free ESPN endpoints and annotate projections."""
    try:
        from src.adapters.world_cup_adapter import WorldCupAdapter
    except Exception:
        logger.warning("[GitHub:WC] world_cup_adapter not available")
        return projections

    remain = _remaining("wc")
    if remain <= 0:
        logger.info("[GitHub:WC] cap reached for today")
        return projections

    try:
        adapter = WorldCupAdapter()
        games = adapter.get_games()
        logger.info(f"[GitHub:WC] {len(games)} fixtures")
        _track("wc", 1)
    except Exception as e:
        logger.warning(f"[GitHub:WC] get_games failed: {e}")
        return projections

    for i, proj in enumerate(projections):
        proj.setdefault("github_enrich", False)

    for game in games[:PER_RUN_MAX]:
        try:
            game_id = game.get("id", "")
            if not game_id:
                continue
            stats = adapter.get_game_stats(game_id)
            if not stats:
                continue
            _track("wc", 1)

            for proj in projections:
                player = proj.get("name", proj.get("player", ""))
                if not player:
                    continue
                for team_side in ("home", "away"):
                    players = stats.get(team_side, {}).get("players", [])
                    for p in players:
                        if player.lower() in p.get("name", "").lower():
                            stat_key = proj.get("stat", "").lower()
                            proj["live_stat"] = p.get("statistics", {}).get(stat_key, None)
                            proj["github_enrich"] = True
                            proj.setdefault("signal", "GITHUB_WC")
        except Exception as e:
            logger.debug(f"[GitHub:WC] stats error: {e}")
            continue

    return projections


# ═══════════════════════════════════════
#  Dispatcher — called from daily_picks.py
# ═══════════════════════════════════════
ENRICH_MAP = {
    "mlb": enrich_mlb,
    "wnba": enrich_wnba,
    "wc": enrich_wc,
}

def enrich_from_github(sport, projections):
    """Main entry: enrich projections with free GitHub-source live stats.
    Only runs if SerpAPI failed to enrich picks (signal still SELF_EDGE or empty)."""
    fn = ENRICH_MAP.get(sport.lower())
    if not fn:
        logger.warning(f"[GitHub] No free-source adapter for sport={sport}")
        return projections

    # Only fire for picks that SerpAPI couldn't touch
    needs_enrich = [p for p in projections
                    if p.get("signal", "") in ("", "SELF_EDGE")
                    and (p.get("line", 0) == 0 or not p.get("market_line"))]
    if not needs_enrich:
        logger.info(f"[GitHub:{sport.upper()}] All picks already enriched by SerpAPI, skipping")
        return projections

    logger.info(f"[GitHub:{sport.upper()}] {len(needs_enrich)} picks need fallback enrichment")
    return fn(projections)
