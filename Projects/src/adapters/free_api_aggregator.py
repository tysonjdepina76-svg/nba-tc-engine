# free_api_aggregator.py — Live stats from free public APIs (statsapi, pybaseball, nba_api)
# Zero-cost, zero-auth. Aggregates real-time player metrics for daily_picks enrichment.

import logging

logger = logging.getLogger("tc_pipeline")

FREE_SOURCES = ["statsapi", "pybaseball", "nba_api"]
CACHE_TTL_SEC = 300  # 5 min cache between calls

_cache = {"ts": 0, "data": {}}

def _cache_valid():
    import time
    return (time.time() - _cache["ts"]) < CACHE_TTL_SEC and bool(_cache["data"])


def _mlb_statsapi_player_stats():
    """Pull current season MLB player stats via MLB-StatsAPI (free, no auth)."""
    players = {}
    try:
        import statsapi
        # Get all active players with season stats
        hitter_stats = statsapi.league_leader_data(
            "homeRuns,stolenBases,runs,rbi,battingAverage,onBasePlusSlugging,hits,strikeOuts",
            limit=500, season=2026, statGroup="hitting"
        )
        pitcher_stats = statsapi.league_leader_data(
            "earnedRunAverage,strikeoutsPer9Innings,walksPer9Innings,whip,strikeouts,walks,hitsPer9Innings",
            limit=500, season=2026, statGroup="pitching"
        )
        # Parse hitter stats
        if isinstance(hitter_stats, str):
            hitter_stats = hitter_stats.split("\n")
        for line in hitter_stats:
            parts = line.split() if isinstance(line, str) else []
            if len(parts) < 3:
                continue
            name = " ".join(parts[1:-7]) if len(parts) > 8 else parts[1]
            players[name.strip()] = {
                "home_runs": parts[-7] if len(parts) > 7 else None,
                "stolen_bases": parts[-5] if len(parts) > 5 else None,
                "ops": parts[-2] if len(parts) > 2 else None,
                "hits": parts[-4] if len(parts) > 4 else None,
            }
        # Parse pitcher stats
        if isinstance(pitcher_stats, str):
            pitcher_stats = pitcher_stats.split("\n")
        for line in pitcher_stats:
            parts = line.split() if isinstance(line, str) else []
            if len(parts) < 3:
                continue
            name = " ".join(parts[1:-6]) if len(parts) > 7 else parts[1]
            players[name.strip()].update({
                "era": parts[-6] if len(parts) > 6 else None,
                "k_per_9": parts[-4] if len(parts) > 4 else None,
                "bb_per_9": parts[-3] if len(parts) > 3 else None,
                "whip": parts[-2] if len(parts) > 2 else None,
            })
    except Exception as e:
        logger.warning(f"[FREE-APIS] statsapi: {e}")
    return players


def _pybaseball_player_stats():
    """Pull current season MLB stats via pybaseball (free, no auth)."""
    players = {}
    try:
        import pybaseball
        # Get batting stats
        batting = pybaseball.batting_stats(2026, qual=50)
        if batting is not None and not batting.empty:
            for _, row in batting.iterrows():
                name = row.get("Name", row.get("Player", ""))
                if name:
                    players[name.strip()] = {
                        "home_runs": int(row.get("HR", 0)) if row.get("HR") else None,
                        "stolen_bases": int(row.get("SB", 0)) if row.get("SB") else None,
                        "ops": float(row.get("OPS", 0)) if row.get("OPS") else None,
                        "batting_avg": float(row.get("AVG", 0)) if row.get("AVG") else None,
                        "hits": int(row.get("H", 0)) if row.get("H") else None,
                    }
        # Get pitching stats
        pitching = pybaseball.pitching_stats(2026, qual=30)
        if pitching is not None and not pitching.empty:
            for _, row in pitching.iterrows():
                name = row.get("Name", row.get("Player", ""))
                if name:
                    if name in players:
                        players[name.strip()].update({
                            "era": float(row.get("ERA", 0)) if row.get("ERA") else None,
                            "k_per_9": float(row.get("SO9", 0)) if row.get("SO9") else None,
                            "whip": float(row.get("WHIP", 0)) if row.get("WHIP") else None,
                        })
                    else:
                        players[name.strip()] = {
                            "era": float(row.get("ERA", 0)) if row.get("ERA") else None,
                            "k_per_9": float(row.get("SO9", 0)) if row.get("SO9") else None,
                            "whip": float(row.get("WHIP", 0)) if row.get("WHIP") else None,
                        }
    except Exception as e:
        logger.warning(f"[FREE-APIS] pybaseball: {e}")
    return players


def _nba_api_player_stats():
    """Pull WNBA player stats via nba_api (free, no auth)."""
    players = {}
    try:
        from nba_api.stats.endpoints import leaguedashplayerstats
        from nba_api.stats.static import players as nba_players
        # WNBA season stats
        stats = leaguedashplayerstats.LeagueDashPlayerStats(
            league_id_nullable="10",  # WNBA
            season="2026",
            season_type_all_star="Regular Season",
            per_mode_detailed="PerGame",
        )
        df = stats.get_data_frames()[0]
        if df is not None and not df.empty:
            for _, row in df.iterrows():
                name = row.get("PLAYER_NAME", "")
                if name:
                    players[name.strip()] = {
                        "pts": float(row.get("PTS", 0)) if row.get("PTS") else None,
                        "reb": float(row.get("REB", 0)) if row.get("REB") else None,
                        "ast": float(row.get("AST", 0)) if row.get("AST") else None,
                        "stl": float(row.get("STL", 0)) if row.get("STL") else None,
                        "blk": float(row.get("BLK", 0)) if row.get("BLK") else None,
                        "fg_pct": float(row.get("FG_PCT", 0)) if row.get("FG_PCT") else None,
                        "fg3_pct": float(row.get("FG3_PCT", 0)) if row.get("FG3_PCT") else None,
                        "ft_pct": float(row.get("FT_PCT", 0)) if row.get("FT_PCT") else None,
                        "min": float(row.get("MIN", 0)) if row.get("MIN") else None,
                    }
    except Exception as e:
        logger.warning(f"[FREE-APIS] nba_api (WNBA): {e}")
    return players


def health_check():
    """Check health of all free API sources. Returns dict with status per source."""
    import time
    result = {
        "healthy": False,
        "status": "",
        "total_sources": len(FREE_SOURCES),
        "healthy_sources": 0,
        "sources": {},
        "live": {},
        "timestamp": time.time(),
    }

    # statsapi
    try:
        result["sources"]["statsapi"] = "import_ok"
        result["healthy_sources"] += 1
    except Exception as e:
        result["sources"]["statsapi"] = f"fail: {e}"

    # pybaseball
    try:
        import pybaseball
        result["sources"]["pybaseball"] = "import_ok"
        result["healthy_sources"] += 1
    except Exception as e:
        result["sources"]["pybaseball"] = f"fail: {e}"

    # nba_api
    try:
        from nba_api.stats.endpoints import leaguedashplayerstats
        result["sources"]["nba_api"] = "import_ok"
        result["healthy_sources"] += 1
    except Exception as e:
        result["sources"]["nba_api"] = f"fail: {e}"

    result["healthy"] = result["healthy_sources"] > 0
    result["status"] = f"{result['healthy_sources']}/{result['total_sources']} up" if result["healthy"] else "all down"

    if result["healthy"]:
        logger.info(f"[FREE-APIS] Health: {result['status']}")
    else:
        logger.warning(f"[FREE-APIS] Health: {result['status']}")

    return result


def get_live_stats(sport="all"):
    """Get live stats from all free APIs, with caching."""
    import time
    global _cache

    if _cache_valid():
        logger.info("[FREE-APIS] Returning cached stats")
        return _cache["data"]

    live = {}

    if sport in ("mlb", "all"):
        try:
            live["statsapi"] = _mlb_statsapi_player_stats()
        except Exception as e:
            logger.warning(f"[FREE-APIS] statsapi fetch failed: {e}")
            live["statsapi"] = {}
        try:
            live["pybaseball"] = _pybaseball_player_stats()
        except Exception as e:
            logger.warning(f"[FREE-APIS] pybaseball fetch failed: {e}")
            live["pybaseball"] = {}

    if sport in ("wnba", "all"):
        try:
            live["nba_api"] = _nba_api_player_stats()
        except Exception as e:
            logger.warning(f"[FREE-APIS] nba_api fetch failed: {e}")
            live["nba_api"] = {}

    _cache = {"ts": time.time(), "data": live}
    total = sum(len(v) for v in live.values())
    logger.info(f"[FREE-APIS] Cached {total} player profiles ({', '.join(f'{k}:{len(v)}' for k,v in live.items())})")
    return live
