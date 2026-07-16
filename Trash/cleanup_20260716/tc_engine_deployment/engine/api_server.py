#!/usr/bin/env python3
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import json
import glob
from datetime import datetime
from typing import Optional

app = FastAPI(title="TC Engine API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")
MODEL_DIR = os.environ.get("MODEL_DIR", "/app/models")
DAILY_LOG_DIR = os.environ.get("DAILY_LOG_DIR", "/app/daily_log")


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.get("/api/projections")
async def projections(
    sport: str = Query("wnba"),
    date: Optional[str] = Query(None),
    game: Optional[str] = Query(None),
):
    target_date = date or datetime.now().strftime("%Y-%m-%d")
    sport_upper = sport.upper()

    pattern = os.path.join(DAILY_LOG_DIR, target_date, f"proj_{sport_upper}_*.json")
    files = sorted(glob.glob(pattern))

    if game:
        files = [f for f in files if game.replace(" ", "_") in os.path.basename(f)]

    results = []
    for fpath in files:
        try:
            with open(fpath) as f:
                data = json.load(f)
            results.append({
                "file": os.path.basename(fpath),
                "players": len(data.get("players", data.get("player_projections", []))),
                "data": data,
            })
        except Exception as e:
            results.append({"file": os.path.basename(fpath), "error": str(e)})

    return {
        "sport": sport,
        "date": target_date,
        "games": len(results),
        "projections": results,
    }


@app.get("/api/picks")
async def picks(
    sport: Optional[str] = Query(None),
    date: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
):
    target_date = date or datetime.now().strftime("%Y-%m-%d")
    path = os.path.join(DAILY_LOG_DIR, target_date, "picks.csv")

    if not os.path.exists(path):
        return {"date": target_date, "picks": [], "count": 0}

    import csv
    rows = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if sport and row.get("sport", "").lower() != sport.lower():
                continue
            rows.append(row)
            if len(rows) >= limit:
                break

    return {
        "date": target_date,
        "count": len(rows),
        "picks": rows,
    }


@app.get("/api/model/meta")
async def model_meta():
    meta_path = os.path.join(MODEL_DIR, "model_meta.json")
    if not os.path.exists(meta_path):
        return {"status": "no_model_trained"}

    with open(meta_path) as f:
        meta = json.load(f)

    return {"status": "trained", **meta}


@app.get("/api/backtest/summary")
async def backtest_summary():
    picks_dir = os.environ.get("HISTORICAL_PICKS_DIR", "/app/historical_picks")
    files = glob.glob(os.path.join(picks_dir, "*.csv"))

    if not files:
        return {"status": "no_data"}

    import pandas as pd
    dfs = []
    for f in files:
        try:
            df = pd.read_csv(f)
            if "hit" in df.columns:
                dfs.append(df)
        except Exception:
            pass

    if not dfs:
        return {"status": "no_graded_data"}

    combined = pd.concat(dfs, ignore_index=True)
    graded = combined[combined["hit"].notna()]

    return {
        "total_picks": int(len(graded)),
        "overall_hit_rate": float(graded["hit"].mean()),
        "by_sport": {
            sport: {
                "count": int(len(grp)),
                "hit_rate": float(grp["hit"].mean()),
            }
            for sport, grp in graded.groupby("sport") if len(grp) > 0
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
