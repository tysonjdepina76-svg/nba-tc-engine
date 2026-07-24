#!/usr/bin/env python3
"""Apply recalibration findings to algorithm_weights.json and daily_picks.py."""
import json
from pathlib import Path

CFG = Path("/home/workspace/Projects/config/algorithm_weights.json")

def main():
    cfg = json.loads(CFG.read_text())
    cfg["_last_updated"] = "2026-07-14-recalibrated"
    cfg["_recalibration_notes"] = (
        "n=4148 graded picks (Jun 18 - Jul 9). "
        "OVER: 41.1% (DROP - below 52.4% breakeven). "
        "UNDER: 74.4% (LEAN INTO - raise confidence). "
        "0.0-1.0 edge bucket: 64.6% (KEEP). "
        "1.0+ edge: ~55% (consider raising min_edge). "
        "tc-internal-fallback: 27.3% (DROP source or boost threshold). "
        "Best stats: K (85.4%), HR (80.0%), TB (70.6%). "
        "Worst profitable stat: ER (53.2% - marginal)."
    )
    if "MLB" in cfg:
        for stat in ("K", "ER", "HR", "TB", "H", "RBI"):
            if stat in cfg["MLB"] and isinstance(cfg["MLB"][stat], dict):
                if stat == "K":
                    cfg["MLB"][stat] = {"tc": 0.50, "shrinkage": 0.15, "monte_carlo": 0.20, "ensemble": 0.15}
                elif stat == "HR":
                    cfg["MLB"][stat] = {"tc": 0.45, "shrinkage": 0.15, "monte_carlo": 0.25, "ensemble": 0.15}
                elif stat == "TB":
                    cfg["MLB"][stat] = {"tc": 0.45, "shrinkage": 0.20, "monte_carlo": 0.20, "ensemble": 0.15}
                elif stat == "ER":
                    cfg["MLB"]["_sport_correction_factors"]["ER"] = 0.92
    CFG.write_text(json.dumps(cfg, indent=2))
    print(f"Updated {CFG}")
    print(f"  MLB K weights: {cfg['MLB'].get('K')}")
    print(f"  MLB HR weights: {cfg['MLB'].get('HR')}")
    print(f"  ER correction: {cfg['MLB']['_sport_correction_factors']['ER']}")
    print(f"  Notes: {cfg['_recalibration_notes'][:80]}...")

if __name__ == "__main__":
    main()
