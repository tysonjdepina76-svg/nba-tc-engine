#!/usr/bin/env python3
# TC — Triple Conservative — Trademark June 2026
"""Wire the 4 missing modules into the daily picks flow.

Reads `picks.json` (or list of pick dicts), runs each through:
  - PositionManager (Kelly-based stake sizing)
  - PredictiveEngine (ML confidence boost)
  - HistoricalTracker (record + grade after the fact)

Writes `wiring.json` next to picks.json with sized positions + ML scores.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Allow running from anywhere
_HERE = Path(__file__).resolve().parent
_PROJ = _HERE.parent.parent
if str(_PROJ) not in sys.path:
    sys.path.insert(0, str(_PROJ))

from src.trading.position_manager import PositionManager
from src.tracking.historical_tracker import HistoricalTracker
from src.ml.predictive_engine import PredictiveEngine


def _load_picks(src: str | Path) -> List[Dict]:
    p = Path(src)
    if not p.exists():
        return []
    if p.suffix == ".json":
        data = json.loads(p.read_text())
        if isinstance(data, dict) and "picks" in data:
            return data["picks"]
        if isinstance(data, list):
            return data
        return []
    if p.suffix == ".csv":
        import csv
        out = []
        with p.open() as f:
            for row in csv.DictReader(f):
                out.append(row)
        return out
    return []


def _edge(d: Dict) -> float:
    for k in ("edge", "proj_edge", "model_edge"):
        if k in d and d[k] is not None:
            try:
                return float(d[k])
            except (TypeError, ValueError):
                continue
    return 0.0


def _american_to_decimal(odds):
    if odds is None:
        return 1.91
    if odds >= 100 or odds <= -100:
        return 1.0 + (odds / 100.0 if odds > 0 else 100.0 / abs(odds))
    return odds if odds > 1.0 else 1.91


def _odds(d):
    for k in ("odds", "price", "decimal_odds"):
        if k in d and d[k] is not None:
            try:
                return _american_to_decimal(float(d[k]))
            except (TypeError, ValueError):
                continue
    return 1.91


def enhance(
    picks: List[Dict],
    bankroll: float = 10000.0,
    db_path: Optional[str] = None,
) -> Dict:
    """Size picks, score with ML, return enhanced dict."""
    pm = PositionManager(bankroll=bankroll)
    ml = PredictiveEngine()
    tracker = HistoricalTracker(db_path=db_path) if db_path else None

    enhanced: List[Dict] = []
    total_stake = 0.0

    for p in picks:
        edge = _edge(p)
        odds = _odds(p)
        stake = pm.size(edge=edge, odds=odds, confidence=1.0)
        pos = pm.open_position(
            sport=p.get("sport", ""),
            game=p.get("matchup") or p.get("game", ""),
            player=p.get("player", ""),
            stat=p.get("stat", ""),
            direction=p.get("direction", "OVER"),
            line=float(p.get("line", 0) or 0),
            odds=odds,
            edge=edge,
            confidence=1.0,
            meta={"source": p.get("source", "daily_picks")},
        )
        if pos is None:
            continue
        total_stake += stake
        enhanced.append({
            **p,
            "stake": round(stake, 2),
            "position_id": pos.id,
            "bankroll_after": round(pm.bankroll - total_stake, 2),
        })

    ml_scores: List[Dict] = []
    if enhanced:
        try:
            preds = ml.predict(enhanced)
            for e, pr in zip(enhanced, preds):
                e["ml_score"] = pr.get("score", 0.0)
                ml_scores.append({"player": e.get("player", ""), "ml_score": e.get("ml_score", 0.0)})
        except Exception as exc:  # graceful — ML is optional
            for e in enhanced:
                e["ml_score"] = 0.0
            ml_scores = [{"warning": f"ml_predict_failed: {exc}"}]

    if tracker is not None:
        for e in enhanced:
            try:
                bid = tracker.record_bet({
                    "sport": e.get("sport", ""),
                    "matchup": e.get("matchup") or e.get("game", ""),
                    "player": e.get("player", ""),
                    "stat": e.get("stat", ""),
                    "direction": e.get("direction", "OVER"),
                    "line": float(e.get("line", 0) or 0),
                    "odds": float(e.get("odds", 1.91) or 1.91),
                    "edge": float(e.get("edge", 0) or 0),
                    "stake": float(e.get("stake", 0) or 0),
                    "placed_at": datetime.utcnow().isoformat(),
                })
                e["bet_id"] = bid
            except Exception as exc:
                e["bet_error"] = str(exc)

    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "bankroll": bankroll,
        "total_stake": round(total_stake, 2),
        "exposure_pct": round(total_stake / max(bankroll, 1.0) * 100, 2),
        "positions": enhanced,
        "ml_scores": ml_scores,
        "perf_30d": tracker.performance() if tracker else {},
    }


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--picks", required=True, help="picks.json or picks.csv")
    ap.add_argument("--out", required=True, help="wiring.json output path")
    ap.add_argument("--bankroll", type=float, default=10000.0)
    ap.add_argument("--db", default=None, help="historical tracker sqlite path")
    args = ap.parse_args()

    picks = _load_picks(args.picks)
    if not picks:
        print(f"No picks found in {args.picks}", file=sys.stderr)
        out = {"generated_at": datetime.utcnow().isoformat() + "Z", "positions": [], "total_stake": 0}
        Path(args.out).write_text(json.dumps(out, indent=2))
        return 0

    result = enhance(picks, bankroll=args.bankroll, db_path=args.db)
    Path(args.out).write_text(json.dumps(result, indent=2))
    print(f"Enhanced {len(result['positions'])} picks → {args.out} "
          f"(${result['total_stake']} staked, {result['exposure_pct']}% exposure)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
