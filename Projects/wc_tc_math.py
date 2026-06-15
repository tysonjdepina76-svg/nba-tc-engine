#!/usr/bin/env python3
"""
World Cup TC Math - Bayesian calibration for FIFA World Cup player props.
Same architecture as tc_math.py (NBA/WNBA) but calibrated from 11,555 player-matches
across 4 tournaments (2010/2014/2018/2022, 256 events).

Hit rates from 2026-06-15 holdout (rolling 3-game avg, holdout next game):
  saves=90.8% (n=358), fouls=67.4% (n=2600), shots=66.1% (n=2174),
  shotsOnTarget=49.2% (n=1066), goals=26.1% (n=264), assists=10.5% (n=152),
  yellowCards=12.5% (n=232).

Best alpha=0 for every stat. WC player variance is high enough that the rolling
average is already the best predictor. Shrinkage toward position priors hurts.
"""
from typing import Dict

# League prior per stat per position. From 4-tournament means.
WC_LEAGUE_PRIOR: Dict[str, Dict[str, float]] = {
    "totalGoals":     {"FWD": 0.30, "MID": 0.10, "DEF": 0.04, "GK": 0.01, "UNK": 0.15},
    "goalAssists":    {"FWD": 0.15, "MID": 0.12, "DEF": 0.05, "GK": 0.01, "UNK": 0.10},
    "totalShots":     {"FWD": 2.40, "MID": 0.90, "DEF": 0.20, "GK": 0.01, "UNK": 1.20},
    "shotsOnTarget":  {"FWD": 1.00, "MID": 0.30, "DEF": 0.08, "GK": 0.01, "UNK": 0.50},
    "foulsCommitted": {"FWD": 1.30, "MID": 1.40, "DEF": 1.50, "GK": 0.10, "UNK": 1.30},
    "yellowCards":    {"FWD": 0.18, "MID": 0.20, "DEF": 0.25, "GK": 0.03, "UNK": 0.18},
    "saves":          {"FWD": 0.01, "MID": 0.01, "DEF": 0.01, "GK": 2.50, "UNK": 0.50},
}

# Calibrated alphas (all 0.0 - shrinkage hurts on WC)
WC_BAYES_ALPHA: Dict[str, float] = {
    "totalGoals": 0.0,
    "goalAssists": 0.0,
    "totalShots": 0.0,
    "shotsOnTarget": 0.0,
    "foulsCommitted": 0.0,
    "yellowCards": 0.0,
    "saves": 0.0,
}

# Stat playable? (above this hit rate, take the bet)
WC_PLAYABLE_HR = {
    "totalGoals": 0.55,
    "goalAssists": 0.55,
    "totalShots": 0.55,
    "shotsOnTarget": 0.55,
    "foulsCommitted": 0.55,
    "yellowCards": 0.55,
    "saves": 0.55,
}

# Position classifier: (display pos, sub-pos) -> canonical
def position_of_player(pos: str) -> str:
    """Map ESPN soccer position strings to FWD/MID/DEF/GK/UNK."""
    if not pos: return "UNK"
    p = pos.upper().strip()
    if "GK" in p or "GOALKEEPER" in p: return "GK"
    if "FWD" in p or "FORWARD" in p or "STRIKER" in p or "WINGER" in p: return "FWD"
    if "MID" in p or "MIDFIELDER" in p: return "MID"
    if "DEF" in p or "BACK" in p: return "DEF"
    return "UNK"

def wc_bayes_shrink(stat: str, sample_mean: float, pos_class: str = "UNK", alpha: float = 0.0, n_games: float = 3.0) -> float:
    """Bayesian shrinkage for WC. With alpha=0 this is identity (just returns sample_mean)."""
    stat_priors = WC_LEAGUE_PRIOR.get(stat, {"UNK": 0.5})
    prior = stat_priors.get(pos_class, stat_priors.get("UNK", 0.5))
    a = alpha if alpha is not None else WC_BAYES_ALPHA.get(stat, 0.0)
    if a <= 0:
        return float(sample_mean or 0)
    return (float(sample_mean or 0) * n_games + prior * a) / (n_games + a)

def is_playable(stat: str) -> bool:
    """Returns True if this stat is in the playable list (hit rate above 55%)."""
    return stat in WC_PLAYABLE_HR

def expected_hit_rate(stat: str) -> float:
    """Return the calibrated holdout hit rate for the stat. 0 if unknown."""
    return {
        "totalGoals": 0.261,
        "goalAssists": 0.105,
        "totalShots": 0.661,
        "shotsOnTarget": 0.492,
        "foulsCommitted": 0.674,
        "yellowCards": 0.125,
        "saves": 0.908,
    }.get(stat, 0.5)
