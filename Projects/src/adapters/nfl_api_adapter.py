"""NFL live data adapter — free, no-key, nfl_data_py package. OFF-SEASON."""
from __future__ import annotations
import logging
from typing import Dict, List, Any, Optional
import nfl_data_py

logger = logging.getLogger(__name__)


def get_offseason_status() -> Dict[str, Any]:
    return {
        "status": "OFF-SEASON",
        "note": "NFL is off-season. Regular season starts September 2026.",
        "next_event": "Hall of Fame Game — August 2026",
        "regular_season_start": "September 2026",
    }


def get_schedule(season: int = 2026) -> List[Dict]:
    try:
        sched = nfl_data_py.import_schedules([season])
        if sched.empty:
            return []
        return sched.to_dict("records")
    except Exception as e:
        logger.warning(f"NFL schedule {season}: {e}")
        return []


def get_seasonal_rosters(season: int = 2026) -> List[Dict]:
    try:
        rosters = nfl_data_py.import_seasonal_rosters([season])
        if rosters.empty:
            return []
        return rosters.to_dict("records")
    except Exception as e:
        logger.warning(f"NFL rosters {season}: {e}")
        return []


def get_weekly_data(season: int = 2026) -> List[Dict]:
    try:
        weekly = nfl_data_py.import_weekly_data([season])
        if weekly.empty:
            return []
        return weekly.to_dict("records")
    except Exception as e:
        logger.warning(f"NFL weekly data {season}: {e}")
        return []


def get_player_ids() -> List[Dict]:
    try:
        ids = nfl_data_py.import_ids()
        if ids.empty:
            return []
        return ids.to_dict("records")
    except Exception as e:
        logger.warning(f"NFL player IDs: {e}")
        return []


def get_players() -> List[Dict]:
    try:
        players = nfl_data_py.import_players()
        if players.empty:
            return []
        return players.to_dict("records")
    except Exception as e:
        logger.warning(f"NFL players: {e}")
        return []


def get_snap_counts(season: int = 2026) -> List[Dict]:
    try:
        snaps = nfl_data_py.import_snap_counts([season])
        if snaps.empty:
            return []
        return snaps.to_dict("records")
    except Exception as e:
        logger.warning(f"NFL snap counts {season}: {e}")
        return []
