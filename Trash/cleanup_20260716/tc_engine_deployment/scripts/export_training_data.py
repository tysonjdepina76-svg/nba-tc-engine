import os
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

DAILY_LOG = Path(os.environ.get("DAILY_LOG", "/home/workspace/Daily_Log"))
OUTPUT = Path(os.environ.get("DATA_DIR", "data")) / "training_data.csv"

def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    cutoff = datetime.now() - timedelta(days=30)

    for date_dir in sorted(DAILY_LOG.iterdir(), reverse=True):
        if not date_dir.is_dir():
            continue
        try:
            dir_date = datetime.strptime(date_dir.name, "%Y-%m-%d")
            if dir_date < cutoff:
                continue
        except ValueError:
            continue

        picks_file = date_dir / "picks.csv"
        if not picks_file.exists():
            continue

        df = pd.read_csv(picks_file)
        for _, row in df.iterrows():
            features = {
                "player": row.get("player", ""),
                "sport": row.get("sport", ""),
                "stat": row.get("stat", ""),
                "direction": row.get("direction", "OVER"),
                "edge": float(row.get("edge", 0)),
                "signal": row.get("signal", "WEAK"),
                "line": float(row.get("line", 0)),
                "projection": float(row.get("projection", 0)),
                "date": date_dir.name,
                "won": row.get("won") if "won" in row and pd.notna(row.get("won")) else None,
            }
            rows.append(features)

    if not rows:
        print("No graded picks found in last 30 days.")
        return

    df_out = pd.DataFrame(rows)
    df_out.to_csv(OUTPUT, index=False)
    graded = df_out.dropna(subset=["won"])
    print(f"Exported {len(df_out)} picks ({len(graded)} graded) to {OUTPUT}")

if __name__ == "__main__":
    main()
