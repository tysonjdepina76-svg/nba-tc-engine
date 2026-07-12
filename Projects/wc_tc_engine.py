#!/usr/bin/env python3
"""World Cup TC Engine — Player Props (Goals, Assists, Shots, SOT)

Note: this is a thin facade. The active implementation lives in
`soccer_tc_engine.py`, which already covers WC (FIFA) matchups + qualifiers
and is wired into api_tc_unified.py / daily_picks.py / sports_registry.py.
This stub keeps the wc_tc_engine import path stable for code that looks
for it by name.
"""

import json
import statistics
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WC_STATS = {
    "goals": {"label": "Goals", "weight": 1.0},
    "assists": {"label": "Assists", "weight": 1.0},
    "shots": {"label": "Shots", "weight": 1.0},
    "sot": {"label": "Shots on Target", "weight": 1.0},
}

class WCTCEngine:
    def __init__(self):
        self.stats = WC_STATS

    def get_player_projections(self, player, game, season_stats=None, recent_games=None):
        return {"goals": 0.5, "assists": 0.3, "shots": 3.0, "sot": 1.5}

def run_wc_engine(date=None):
    logger.info(f"WC TC Engine: stub delegating to soccer_tc_engine for {date or 'today'}")
    try:
        from soccer_tc_engine import run as _soccer_run
        return _soccer_run(date)
    except Exception as e:
        logger.warning(f"soccer_tc_engine delegation failed ({e}); returning empty slate")
        return {}

if __name__ == "__main__":
    run_wc_engine()
