#!/usr/bin/env python3
"""
predictive_engine.py — ML-enriched pick evaluation.
Blends rule-based self-edge with calibrated ML probability.
Provides direction bias and WNBA-specific overrides.
"""

import sys
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
logger = logging.getLogger("predictive_engine")

DIRECTION_BIAS = {
    "MLB": {"OVER": 0.80, "UNDER": 1.20},
    "WNBA": {"OVER": 0.75, "UNDER": 1.25},
    "NBA": {"OVER": 0.85, "UNDER": 1.15},
    "NFL": {"OVER": 0.80, "UNDER": 1.20},
    "NHL": {"OVER": 0.85, "UNDER": 1.15},
}

def _load_model():
    try:
        from engine.ml_predictor import MLProbabilityPredictor
        model_path = Path(__file__).resolve().parent.parent.parent / "models" / "probability_model.joblib"
        if model_path.exists():
            predictor = MLProbabilityPredictor()
            predictor.load_model(str(model_path))
            logger.info(f"[PredictiveEngine] Model loaded from {model_path}")
            return predictor
    except Exception as e:
        logger.warning(f"[PredictiveEngine] Model not available: {e}")
    return None

_predictor = _load_model()

def apply_direction_bias(pick: Dict[str, Any]) -> Dict[str, Any]:
    edge = pick.get("edge", 0)
    direction = pick.get("direction", "OVER")
    sport = pick.get("sport", "").upper()
    bias = DIRECTION_BIAS.get(sport, {"OVER": 0.85, "UNDER": 1.10})
    if direction == "OVER":
        pick["edge"] = edge * bias["OVER"]
    else:
        pick["edge"] = edge * bias["UNDER"]
    return pick

def wnba_override(pick: Dict[str, Any]) -> bool:
    sport = pick.get("sport", "")
    stat = pick.get("stat", "")
    direction = pick.get("direction", "")
    if sport.upper() != "WNBA":
        return True
    edge = pick.get("edge", 0)
    if stat in ("PTS",) and edge < 0.20:
        return False
    if direction == "OVER" and edge < 0.12:
        return False
    return True

def enrich_picks_ml(picks: List[Dict]) -> List[Dict]:
    if _predictor is None:
        return picks
    for pick in picks:
        features = {
            "proj_edge": abs(pick.get("edge", 0)),
            "direction_encoded": 1 if pick.get("direction") == "OVER" else 0,
            "stat_avg": 1.0,
            "stat_std": 0.2,
            "recent_trend": 0.0,
            "market_line": pick.get("line", 0),
            "opponent_rank": 0.5,
        }
        try:
            pick["ml_prob"] = _predictor.predict_probability(features)
        except Exception:
            pick["ml_prob"] = 0.5
    return picks

def filter_ml_picks(picks: List[Dict], min_ml_prob: float = 0.45) -> List[Dict]:
    if _predictor is None:
        return picks
    filtered = []
    for pick in picks:
        ml_prob = pick.get("ml_prob", 0.5)
        if ml_prob >= min_ml_prob:
            filtered.append(pick)
    removed = len(picks) - len(filtered)
    if removed:
        logger.info(f"[PredictiveEngine] ML filter removed {removed} low-probability picks")
    return filtered

def apply_ml_override(sport, picks):
    """Apply ML-based overrides (WNBA direction bias, stat-specific filters)."""
    if not picks:
        return picks
    from src.ml.predictive_engine import wnba_override, apply_direction_bias
    picks = [p for p in picks if wnba_override(p)]
    picks = [apply_direction_bias(p) for p in picks]
    logger.info(f"[ML_OVERRIDE] {sport}: {len(picks)} picks after ML overrides")
    return picks

def enrich_ml_probabilities(sport, picks):
    """Enrich picks with ML probabilities, filter by confidence."""
    if not picks:
        return picks
    from src.ml.predictive_engine import enrich_picks_ml, filter_ml_picks
    picks = enrich_picks_ml(picks)
    picks = filter_ml_picks(picks, min_ml_prob=0.45)
    logger.info(f"[ML_ENRICH] {sport}: {len(picks)} picks after ML enrichment")
    return picks
