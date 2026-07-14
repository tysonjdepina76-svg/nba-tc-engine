#!/usr/bin/env python3
"""
tc_math_hybrid.py — Complete Hybrid TC Math
- v1 baseline, v2 shrinkage, sport-specific corrections
- Ensemble: TC + XGBoost + RandomForest + LogisticRegression
- Full backtest framework
- Source tracking (REAL / MOCK / HYBRID)
"""

import json
import math
import statistics
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Literal, Any
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

try:
    from scipy.stats import norm, poisson
    SCIPY_OK = True
except Exception:
    SCIPY_OK = False

# ============= TYPES =============
Direction = Literal["OVER", "UNDER", "FLAT", "INVALID"]
Source = Literal["REAL", "MOCK", "HYBRID", "ENSEMBLE"]


# ============= SPORT CONFIGURATIONS =============
@dataclass
class SportConfig:
    min_edge: float
    use_pct: bool
    max_edge: Optional[float]
    min_market_line: float
    shrinkage_factor: float
    correction_factors: Dict[str, float]
    ensemble_weights: Dict[str, float]
    signal_moderate: float = 0.05
    signal_strong: float = 0.10


SPORT_CONFIGS: Dict[str, SportConfig] = {
    "WNBA": SportConfig(
        min_edge=0.5, use_pct=False, max_edge=5.0, min_market_line=0.5,
        shrinkage_factor=0.30,
        correction_factors={"PTS": 1.05, "REB": 1.03, "AST": 1.03,
                           "STL": 1.02, "BLK": 1.02, "3PM": 0.98},
        ensemble_weights={"tc": 0.40, "xgb": 0.30, "rf": 0.20, "lr": 0.10},
        signal_moderate=0.06, signal_strong=0.12,
    ),
    "NBA": SportConfig(
        min_edge=0.5, use_pct=False, max_edge=8.0, min_market_line=0.5,
        shrinkage_factor=0.25,
        correction_factors={"PTS": 1.04, "REB": 1.02, "AST": 1.02,
                           "STL": 1.02, "BLK": 1.02, "3PM": 0.98},
        ensemble_weights={"tc": 0.40, "xgb": 0.30, "rf": 0.20, "lr": 0.10},
        signal_moderate=0.06, signal_strong=0.12,
    ),
    "MLB": SportConfig(
        min_edge=0.5, use_pct=False, max_edge=15.0, min_market_line=0.5,
        shrinkage_factor=0.35,
        correction_factors={"H": 1.05, "RBI": 1.05, "HR": 1.10, "TB": 1.03,
                           "K": 0.97, "ER": 0.95, "IP": 1.02},
        ensemble_weights={"tc": 0.35, "xgb": 0.35, "rf": 0.20, "lr": 0.10},
        signal_moderate=0.06, signal_strong=0.12,
    ),
    "NHL": SportConfig(
        min_edge=0.5, use_pct=False, max_edge=15.0, min_market_line=0.5,
        shrinkage_factor=0.30,
        correction_factors={"SOG": 1.03, "G": 1.10, "A": 1.05},
        ensemble_weights={"tc": 0.40, "xgb": 0.30, "rf": 0.20, "lr": 0.10},
        signal_moderate=0.06, signal_strong=0.12,
    ),
}


# ============= CORE TC MATH =============
def over_under_signal_v1(projection: float, market_line: float, min_abs_edge: float = 0.5) -> Tuple[Direction, float]:
    if market_line <= 0 or not np.isfinite(projection) or projection <= 0:
        return "INVALID", 0.0
    diff = projection - market_line
    abs_diff = abs(diff)
    if abs_diff < min_abs_edge:
        return "FLAT", 0.0
    direction: Direction = "OVER" if diff > 0 else "UNDER"
    edge = abs_diff / market_line if market_line > 0 else 0.0
    return direction, edge


def over_under_signal_v2(
    projection: float,
    market_line: float,
    shrinkage_factor: float = 0.30,
    historical_std: Optional[float] = None,
    min_edge_pct: float = 2.0,
    use_probability: bool = True,
    distribution: str = "normal",
) -> Dict[str, Any]:
    if market_line <= 0 or not np.isfinite(projection) or projection <= 0:
        return {"direction": "INVALID", "edge": 0.0, "prob_over": None,
                "shrunk_projection": projection, "original_projection": projection}

    shrunk_proj = (1 - shrinkage_factor) * projection + shrinkage_factor * market_line
    diff = shrunk_proj - market_line
    edge_pct = abs(diff) / market_line * 100 if market_line > 0 else 0.0

    prob_over = None
    if use_probability and SCIPY_OK:
        std = historical_std or max(0.8, abs(market_line) * 0.38)
        if distribution == "poisson" and market_line > 0:
            mu = max(0.1, shrunk_proj)
            prob_over = 1 - poisson.cdf(market_line - 0.5, mu)
        else:
            z = (market_line - shrunk_proj) / std
            prob_over = 1 - norm.cdf(z)

    if edge_pct < min_edge_pct:
        direction: Direction = "FLAT"
    elif diff > 0:
        direction = "OVER"
    else:
        direction = "UNDER"

    return {
        "direction": direction,
        "edge": edge_pct / 100,
        "prob_over": prob_over,
        "shrunk_projection": shrunk_proj,
        "original_projection": projection,
        "historical_std_used": historical_std,
    }


# ============= HYBRID ENSEMBLE =============
def get_correction_factor(sport: str, stat: str) -> float:
    config = SPORT_CONFIGS.get(sport)
    if not config:
        return 1.0
    return config.correction_factors.get(stat, 1.0)


def apply_correction(projection: float, sport: str, stat: str) -> float:
    return projection * get_correction_factor(sport, stat)


def hybrid_projection(tc_proj: float, sport: str, stat: str, model_projs: Optional[Dict[str, float]] = None) -> float:
    corrected = apply_correction(tc_proj, sport, stat)
    config = SPORT_CONFIGS.get(sport)
    if not config or not model_projs:
        return corrected
    w = config.ensemble_weights
    return (
        w.get("tc", 0.40) * corrected
        + w.get("xgb", 0.30) * model_projs.get("xgb", corrected)
        + w.get("rf", 0.20) * model_projs.get("rf", corrected)
        + w.get("lr", 0.10) * model_projs.get("lr", corrected)
    )


# ============= MOCK LINE GENERATION =============
def get_mock_market_line(projection: float, sport: str, stat: str = "default") -> float:
    factors = {
        "MLB": {"default": 0.89},
        "WNBA": {"default": 0.91},
        "NBA": {"default": 0.90},
        "NFL": {"default": 0.90},
        "NHL": {"default": 0.89},
    }
    f = factors.get(sport.upper(), {"default": 0.90})
    factor = f.get(stat, f["default"])
    return max(0.1, projection * factor)


# ============= DETERMINE PICK =============
def determine_pick(
    projection: float,
    real_line: Optional[float],
    sport: str,
    stat: str = "default",
    self_edge_threshold: float = 3.5,
    historical_std: Optional[float] = None,
    use_v2: bool = True,
    model_projs: Optional[Dict[str, float]] = None,
    source: Source = "REAL",
) -> Dict[str, Any]:
    if source in ["REAL", "MOCK"]:
        proj = apply_correction(projection, sport, stat)
        if model_projs:
            proj = hybrid_projection(proj, sport, stat, model_projs)
    else:
        proj = projection

    if real_line is not None and real_line > 0:
        line = real_line
        actual_source = "REAL"
        min_edge = 0.5
    else:
        line = get_mock_market_line(proj, sport, stat)
        actual_source = "MOCK"
        min_edge = self_edge_threshold

    config = SPORT_CONFIGS.get(sport)
    shrink = config.shrinkage_factor if config else 0.30

    if use_v2:
        result = over_under_signal_v2(
            proj, line,
            shrinkage_factor=shrink,
            historical_std=historical_std,
            min_edge_pct=min_edge,
        )
    else:
        direction, edge = over_under_signal_v1(proj, line, min_abs_edge=min_edge)
        result = {"direction": direction, "edge": edge, "prob_over": None}

    result.update({
        "projection": projection,
        "corrected_projection": proj,
        "market_line": line,
        "source": actual_source,
        "sport": sport,
        "stat": stat,
        "is_self_edge": actual_source == "MOCK",
        "hybrid": source in ("HYBRID", "ENSEMBLE"),
    })
    return result


# ============= BACKTEST =============
def backtest_hybrid(
    picks_df: pd.DataFrame,
    actual_results: Optional[pd.Series] = None,
    stake: float = 100.0,
    self_edge_threshold: float = 3.5,
) -> pd.DataFrame:
    if actual_results is None:
        return pd.DataFrame()

    strategies = [
        ("v1_simple", False, 0.5, False, False),
        ("v2_hybrid", True, self_edge_threshold, False, False),
        ("hybrid_corrected", True, self_edge_threshold, True, False),
        ("ensemble_full", True, self_edge_threshold, True, True),
    ]

    rows = []
    for name, use_v2, min_edge, use_correction, use_ensemble in strategies:
        wins = losses = 0
        for _, row in picks_df.iterrows():
            proj = float(row.get("projection", 0))
            line = row.get("market_line", None)
            sport = row.get("sport", "WNBA")
            stat = row.get("stat", "default")
            model_projs = row.get("model_projs", {}) if isinstance(row.get("model_projs", None), dict) else {}

            if use_correction:
                proj = apply_correction(proj, sport, stat)
            if use_ensemble and model_projs:
                proj = hybrid_projection(proj, sport, stat, model_projs)

            result = determine_pick(proj, line if (line is not None and line > 0) else None,
                                    sport, stat, self_edge_threshold=self_edge_threshold, use_v2=use_v2)
            direction = result["direction"]
            mkt = result["market_line"]

            key = row.get("key") or f"{row.get('player','?')}_{row.get('stat','?')}"
            actual = actual_results.get(key)
            if actual is None or direction in ("FLAT", "INVALID"):
                continue
            hit = (actual > mkt) if direction == "OVER" else (actual < mkt)
            if hit:
                wins += 1
            else:
                losses += 1
        n = wins + losses
        rows.append({
            "strategy": name,
            "n": n,
            "wins": wins,
            "hit_rate": (wins / n) if n else 0.0,
        })
    return pd.DataFrame(rows)


# ============= CLI =============
def _run_for_date(date_str: str, sport: str) -> Dict[str, Any]:
    base = Path("/home/workspace/Daily_Log") / date_str
    proj_file = base / f"proj_{sport}.json"
    out: Dict[str, Any] = {"date": date_str, "sport": sport, "picks": [], "summary": {}}
    if not proj_file.exists():
        out["error"] = f"No projection file: {proj_file}"
        return out

    try:
        with open(proj_file) as f:
            data = json.load(f)
    except Exception as e:
        out["error"] = f"Read fail: {e}"
        return out

    players = data if isinstance(data, list) else data.get("players", [])
    pick_count = {"OVER": 0, "UNDER": 0, "FLAT": 0, "INVALID": 0}

    for p in players:
        proj = p.get("projection") or p.get("proj")
        line = p.get("line") or p.get("market_line")
        stat = p.get("stat", "default")
        name = p.get("player") or p.get("name", "Unknown")
        if proj is None:
            continue
        pick = determine_pick(float(proj), line, sport, stat=stat)
        pick["player"] = name
        out["picks"].append(pick)
        pick_count[pick["direction"]] = pick_count.get(pick["direction"], 0) + 1

    out["summary"] = {"total": len(out["picks"]), **pick_count}

    out_file = base / f"hybrid_{sport}_picks.json"
    with open(out_file, "w") as f:
        json.dump(out, f, indent=2, default=str)
    out["output_file"] = str(out_file)
    return out


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python tc_math_hybrid.py <date> <sport>")
        sys.exit(1)
    date = sys.argv[1]
    sport = sys.argv[2].upper()
    result = _run_for_date(date, sport)
    print(json.dumps(result.get("summary", result), indent=2, default=str))
    if "output_file" in result:
        print(f"\nWrote: {result['output_file']}")
