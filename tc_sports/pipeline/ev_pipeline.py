#!/usr/bin/env python3
"""ev_pipeline.py — Expected Value Pipeline.

Reads real picks from Daily_Log/$(date)/picks.csv.
Calibrates edge using historical hit-rates from tc_pipeline.db.
Writes alerts.json + alerts.csv for the dashboard.
No mock data — exits with error if no picks found.
"""

import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

ZONE_ET = __import__("zoneinfo").ZoneInfo("America/New_York")
NOW = datetime.now(ZONE_ET)
TODAY = NOW.strftime("%Y-%m-%d")

DAILY_LOG = Path(os.environ.get("TC_DAILY_LOG", "/home/workspace/Daily_Log"))
DATA_DIR = Path(os.environ.get("TC_DATA", "/home/workspace/data"))
ALERTS_JSON = Path(os.environ.get("TC_ALERTS", str(DATA_DIR / "processed/alerts.json")))
ALERTS_CSV = Path(os.environ.get("TC_ALERTS_CSV", str(DATA_DIR / "processed/alerts.csv")))
PICKS_DB = Path(os.environ.get("TC_PICKS_DB", "/home/workspace/Projects/data/tc_pipeline.db"))
EDGE_THRESHOLD = float(os.environ.get("TC_EDGE_THRESHOLD", "0.04"))
MIN_CONFIDENCE = float(os.environ.get("TC_MIN_CONFIDENCE", "0.55"))
MAX_ALERTS = int(os.environ.get("TC_MAX_ALERTS", "50"))


def load_historical_hit_rates() -> Dict[str, float]:
    """Query tc_pipeline.db for per-stat hit rates."""
    rates: Dict[str, float] = {}
    try:
        import sqlite3
        conn = sqlite3.connect(str(PICKS_DB))
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in c.fetchall()]

        if "graded_picks" in tables:
            c.execute("SELECT sport, stat, COUNT(*) as n, AVG(CASE WHEN correct=1 THEN 1.0 ELSE 0.0 END) as hit_pct FROM graded_picks GROUP BY sport, stat")
            for row in c.fetchall():
                key = f"{row['sport']}:{row['stat']}"
                rates[key] = float(row["hit_pct"])
                rates[f"{row['sport']}:ALL"] = float(row["hit_pct"]) if rates.get(f"{row['sport']}:ALL", 0) < float(row["hit_pct"]) else rates.get(f"{row['sport']}:ALL", 0)

        conn.close()
        print(f"Loaded {len(rates)} historical hit-rate keys from graded_picks")
    except Exception as e:
        print(f"Warning: Could not load historical rates ({e}) — using default prior 0.55")

    return rates


def compute_true_probability(edge: float, league: str, stat: str, hist_rates: Dict[str, float]) -> float:
    """Bayesian-like adjustment: prior = historical hit rate, likelihood = edge."""
    key = f"{league.upper()}:{stat}"
    sport_key = f"{league.upper()}:ALL"
    prior = hist_rates.get(key, hist_rates.get(sport_key, 0.55))

    weight = 0.35
    if abs(edge) > 0.10:
        weight = 0.28
    elif abs(edge) < 0.06:
        weight = 0.42

    adjusted = (1 - weight) * prior + weight * (0.50 + edge * 0.8)
    return round(min(max(adjusted, 0.30), 0.95), 4)


def classify_alert(true_prob: float, edge: float) -> str:
    if true_prob >= 0.72 and abs(edge) >= 0.10:
        return "STRONG"
    elif true_prob >= 0.63 and abs(edge) >= 0.07:
        return "STRONG"
    elif true_prob >= 0.58 and abs(edge) >= 0.05:
        return "MODERATE"
    elif true_prob >= 0.55 and abs(edge) >= EDGE_THRESHOLD:
        return "MODERATE"
    return "WEAK"


def load_picks() -> List[Dict[str, str]]:
    """Load todays picks.csv."""
    today_dir = DAILY_LOG / TODAY
    picks_file = today_dir / "picks.csv"

    if not picks_file.exists():
        alt = list(today_dir.glob("picks*.csv"))
        if alt:
            picks_file = alt[0]
        else:
            print(f"ERROR: No picks file found in {today_dir}")
            sys.exit(1)

    rows = []
    with open(picks_file, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    print(f"Loaded {len(rows)} raw picks from {picks_file}")
    return rows


def run():
    print(f"=== TC EV Pipeline {TODAY} ===")

    ALERTS_JSON.parent.mkdir(parents=True, exist_ok=True)

    hist_rates = load_historical_hit_rates()
    raw_picks = load_picks()

    alerts: List[Dict[str, Any]] = []

    for pick in raw_picks:
        try:
            edge = float(pick.get("edge", "0"))
            market_line = float(pick.get("market_line", "0"))
            tc_proj = float(pick.get("tc_projection", "0"))
        except (ValueError, TypeError):
            continue

        league = pick.get("league", "UNKNOWN")
        stat = pick.get("stat", "UNKNOWN")
        direction = pick.get("direction", "OVER")
        player = pick.get("player", "Unknown")
        matchup = pick.get("matchup", "")
        why = pick.get("why", "")
        signal = pick.get("signal", "")

        if abs(edge) < EDGE_THRESHOLD:
            continue

        true_prob = compute_true_probability(edge, league, stat, hist_rates)
        confidence = round(true_prob * 100, 1)
        alert_level = classify_alert(true_prob, edge)

        if true_prob < MIN_CONFIDENCE:
            continue

        alerts.append({
            "player": player,
            "league": league,
            "matchup": matchup,
            "stat": stat,
            "direction": direction,
            "tc_projection": tc_proj,
            "market_line": market_line,
            "edge": round(edge, 4),
            "true_probability": round(true_prob, 4),
            "confidence": confidence,
            "alert_level": alert_level,
            "why": why,
            "generated": NOW.isoformat(),
        })

    alerts = sorted(alerts, key=lambda a: a["true_probability"], reverse=True)[:MAX_ALERTS]
    print(f"Processed {len(raw_picks)} picks → {len(alerts)} alerts (edge ≥ {EDGE_THRESHOLD*100:.0f}%, prob ≥ {MIN_CONFIDENCE*100:.0f}%)")

    output = {
        "generated": NOW.isoformat(),
        "thresholds": {
            "edge_minimum": EDGE_THRESHOLD,
            "confidence_minimum": MIN_CONFIDENCE,
        },
        "calibration_source": "tc_pipeline.db graded_picks" if hist_rates else "default prior 0.55",
        "alerts": alerts,
    }

    with open(ALERTS_JSON, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Wrote {len(alerts)} alerts to {ALERTS_JSON}")

    stats = {
        "total_alerts": len(alerts),
        "strong": sum(1 for a in alerts if a["alert_level"] == "STRONG"),
        "moderate": sum(1 for a in alerts if a["alert_level"] == "MODERATE"),
        "weak": sum(1 for a in alerts if a["alert_level"] == "WEAK"),
        "avg_confidence": sum(a["confidence"] for a in alerts) / len(alerts) if alerts else 0,
        "avg_edge": sum(a["edge"] for a in alerts) / len(alerts) if alerts else 0,
    }
    summary_path = DATA_DIR / "processed" / "pipeline_summary.json"
    with open(summary_path, "w") as f:
        json.dump({"generated": NOW.isoformat(), "stats": stats}, f, indent=2)
    print(f"Summary: {json.dumps(stats)}")

    if alerts:
        csv_path = ALERTS_CSV
        fieldnames = list(alerts[0].keys())
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(alerts)
        print(f"Wrote {csv_path}")

    print("Pipeline complete.")


if __name__ == "__main__":
    run()
