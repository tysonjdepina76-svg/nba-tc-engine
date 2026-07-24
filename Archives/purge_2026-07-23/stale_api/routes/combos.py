#!/usr/bin/env python3
"""Combo Builder API — parlay-eligible combinations from picks."""
from fastapi import APIRouter, Query
import pandas as pd
from datetime import datetime
from pathlib import Path

router = APIRouter()


@router.get("/combos")
def get_combos(
    sport: str = Query("mlb"),
    date: str = Query(None),
    min_legs: int = Query(2),
    max_legs: int = Query(4),
    min_edge: float = Query(0.5),
    max_combos: int = Query(20),
):
    """Generate +EV parlay combos from daily picks."""
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    picks_path = Path(f"/home/workspace/Projects/data/picks/{sport}_{date}.csv")
    if not picks_path.exists():
        return {"error": f"No picks file: {picks_path}", "sport": sport, "date": date}

    try:
        df = pd.read_csv(picks_path)

        required = ["player", "sport", "stat", "projection", "line", "edge", "direction"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            return {"error": f"Missing columns: {missing}", "sport": sport, "date": date}

        df = df[df["edge"].abs() >= min_edge].copy()
        if len(df) < min_legs:
            return []

        df = df.sort_values("edge", key=abs, ascending=False)

        combos = []
        players = df.to_dict("records")

        for i in range(len(players)):
            leg = players[i]
            if len(combos) >= max_combos:
                break
            combo = {
                "legs": [{
                    "player": leg["player"],
                    "stat": leg["stat"],
                    "projection": leg["projection"],
                    "line": leg["line"],
                    "edge": leg["edge"],
                    "direction": leg.get("direction", "OVER"),
                }],
                "total_edge": leg["edge"],
                "leg_count": 1,
            }
            combos.append(combo)

        return combos
    except Exception as e:
        return {"error": str(e), "sport": sport, "date": date}


@router.get("/combos/parlay")
def get_parlay_combos(
    sport: str = Query("mlb"),
    date: str = Query(None),
    min_legs: int = Query(3),
    max_legs: int = Query(4),
    min_edge: float = Query(1.0),
    max_combos: int = Query(10),
):
    """Generate multi-leg parlay combos with edge stacking."""
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    picks_path = Path(f"/home/workspace/Projects/data/picks/{sport}_{date}.csv")
    if not picks_path.exists():
        return {"error": f"No picks: {picks_path}", "sport": sport, "date": date}

    try:
        df = pd.read_csv(picks_path)

        if "edge" not in df.columns or "player" not in df.columns:
            return {"error": "Missing columns", "sport": sport, "date": date}

        df = df[df["edge"].abs() >= min_edge].copy()
        qualified = df.to_dict("records")

        combos = []
        for i, leg1 in enumerate(qualified):
            for j, leg2 in enumerate(qualified):
                if j <= i:
                    continue
                total_edge = leg1["edge"] + leg2["edge"]
                combo = {
                    "legs": [
                        {"player": leg1["player"], "stat": leg1.get("stat", ""), "edge": leg1["edge"]},
                        {"player": leg2["player"], "stat": leg2.get("stat", ""), "edge": leg2["edge"]},
                    ],
                    "total_edge": round(total_edge, 2),
                    "leg_count": 2,
                }
                combos.append(combo)

        combos.sort(key=lambda x: abs(x["total_edge"]), reverse=True)
        return combos[:max_combos]
    except Exception as e:
        return {"error": str(e), "sport": sport, "date": date}
