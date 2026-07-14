"""Manual fallback grading for when automated settlement fails."""
import csv
import json
import logging
import os
import sys
from datetime import datetime
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

DAILY_LOG = "/home/workspace/Daily_Log"


def manual_grade_pick(date_str: str, pick_id: str, result: str) -> bool:
    """Manually grade a pick. result must be 'win', 'loss', or 'push'.

    Updates the graded_picks.csv for that date.
    """
    if result not in ("win", "loss", "push"):
        print(f"ERROR: result must be win/loss/push, got '{result}'")
        return False

    day_dir = os.path.join(DAILY_LOG, date_str)
    picks_csv = os.path.join(day_dir, "picks.csv")
    graded_csv = os.path.join(day_dir, "graded_picks.csv")

    if not os.path.exists(picks_csv):
        print(f"ERROR: {picks_csv} not found")
        return False

    # Read picks
    with open(picks_csv, "r") as f:
        reader = csv.DictReader(f)
        picks = list(reader)
        fieldnames = reader.fieldnames

    target = next((p for p in picks if str(p.get("pick_id")) == str(pick_id)), None)
    if not target:
        print(f"ERROR: pick_id {pick_id} not found in {picks_csv}")
        return False

    target["result"] = result
    target["graded_at"] = datetime.now().isoformat()
    target["graded_by"] = "manual"

    # Append to graded_picks.csv
    file_exists = os.path.exists(graded_csv)
    graded_fieldnames = fieldnames + ["result", "graded_at", "graded_by"]
    with open(graded_csv, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=graded_fieldnames, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        writer.writerow(target)

    print(f"✓ Graded pick {pick_id} as {result} for {date_str}")
    return True


def list_ungraded_picks(date_str: str) -> List[Dict]:
    """List picks for a date that haven't been graded yet."""
    day_dir = os.path.join(DAILY_LOG, date_str)
    picks_csv = os.path.join(day_dir, "picks.csv")
    graded_csv = os.path.join(day_dir, "graded_picks.csv")

    if not os.path.exists(picks_csv):
        return []

    with open(picks_csv, "r") as f:
        picks = list(csv.DictReader(f))

    graded_ids = set()
    if os.path.exists(graded_csv):
        with open(graded_csv, "r") as f:
            for row in csv.DictReader(f):
                graded_ids.add(str(row.get("pick_id", "")))

    return [p for p in picks if str(p.get("pick_id", "")) not in graded_ids]


def interactive_grade(date_str: str) -> None:
    """Interactive CLI for manually grading picks for a date."""
    pending = list_ungraded_picks(date_str)
    if not pending:
        print(f"No ungraded picks for {date_str}")
        return

    print(f"\n{len(pending)} ungraded picks for {date_str}:")
    for i, p in enumerate(pending, 1):
        print(f"  [{i}] {p.get('pick_id')} — {p.get('player_name', '?')} "
              f"{p.get('stat', '?')} {p.get('direction', '?')} {p.get('line', '?')}")

    print("\nEnter 'pick_id win/loss/push' to grade, or 'q' to quit")
    while True:
        try:
            line = input("> ").strip()
        except EOFError:
            break
        if line.lower() in ("q", "quit", "exit"):
            break
        parts = line.split()
        if len(parts) >= 2:
            pid, result = parts[0], parts[1]
            manual_grade_pick(date_str, pid, result)
        else:
            print("Format: <pick_id> <win|loss|push>")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) >= 2:
        date = sys.argv[1]
        if len(sys.argv) == 2:
            interactive_grade(date)
        else:
            manual_grade_pick(date, sys.argv[2], sys.argv[3])
    else:
        date = datetime.now().strftime("%Y-%m-%d")
        interactive_grade(date)
