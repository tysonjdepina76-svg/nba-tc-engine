#!/usr/bin/env python3
"""Opening Line Generator — computes fair win probability for WNBA/MLB/WC props.

Primary: static fallback (league-average priors with opponent/usage adjustments).
Secondary: TheOddsAPI (gated by quota availability; falls back gracefully).

Truth: Odds API Business tier is quota-maxed as of July 2026.
This module defaults to the static fallback and records the source.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np

_HERE = Path(__file__).resolve().parent
_PROJ = _HERE.parent
if str(_PROJ) not in sys.path:
    sys.path.insert(0, str(_PROJ))

ODDS_API_KEY = os.getenv("THE_ODDS_API_KEY", "")
BASE_URL = "https://api.the-odds-api.com"


class OpeningLineGenerator:
    """Generate fair opening probabilities for player props."""

    def __init__(self):
        self.prior_league_avg = 0.50

    def compute_fair_prob(
        self,
        sport: str,
        player_stat: str,
        opponent_def: float = 110.0,
        usage: float = 0.20,
        minutes: Optional[float] = None,
        source: str = "static",
    ) -> Tuple[float, str]:
        """
        Returns (fair_probability, source_label).

        source_label is one of:
          - "static" — league-average prior with opponent/usage adjustment
          - "theoddsapi" — live line from TheOddsAPI (rare, quota maxed)
        """
        sport_lower = sport.lower()

        if sport_lower in ("wnba", "nba"):
            if minutes is None:
                minutes = 34.0
            expected = (usage * 0.8 + (110 - opponent_def) * 0.2) * (minutes / 36.0)
            threshold = 20.5
            prob = 1.0 / (1.0 + np.exp(-(expected - threshold) * 0.3))
            return round(prob, 4), source

        if sport_lower == "mlb":
            if player_stat.upper() in ("H", "HITS"):
                return round(0.48 + usage * 0.10, 4), source
            if player_stat.upper() in ("HR", "HOME_RUN"):
                return round(0.18 + usage * 0.08, 4), source
            if player_stat.upper() in ("R", "RUNS"):
                return round(0.45 + usage * 0.08, 4), source
            if player_stat.upper() in ("RBI", "RBIS"):
                return round(0.42 + usage * 0.08, 4), source
            if "SO" in player_stat.upper() or "K" in player_stat.upper():
                return round(0.38 + usage * 0.15, 4), source
            if player_stat.upper() in ("TB", "TOTAL_BASES"):
                return round(0.55 + usage * 0.10, 4), source
            return round(0.50, 4), source

        if sport_lower in ("wc", "world_cup", "soccer"):
            if player_stat.upper() in ("G", "GOALS"):
                return round(0.08 + usage * 0.05, 4), source
            if player_stat.upper() in ("A", "ASSISTS"):
                return round(0.10 + usage * 0.05, 4), source
            if player_stat.upper() in ("SOG", "SHOTS_ON_GOAL"):
                return round(0.25 + usage * 0.10, 4), source
            return round(0.50, 4), source

        return round(self.prior_league_avg, 4), source

    def fetch_from_api(self, sport: str, team: str) -> Optional[Dict]:
        """Attempt to fetch live opening lines from TheOddsAPI.

        Returns None on any failure (quota maxed, network error, etc.).
        """
        if not ODDS_API_KEY:
            return None
        sport_map = {
            "wnba": "basketball_wnba",
            "mlb": "baseball_mlb",
            "wc": "soccer_world_cup",
            "world_cup": "soccer_world_cup",
            "soccer": "soccer_world_cup",
        }
        odds_sport = sport_map.get(sport.lower(), sport.lower())
        url = f"{BASE_URL}/v4/sports/{odds_sport}/odds"
        params = {
            "apiKey": ODDS_API_KEY,
            "regions": "us",
            "markets": "h2h",
            "oddsFormat": "american",
        }
        try:
            import requests
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 401:
                return None
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return None
