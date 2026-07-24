"""fantasy_images.py — Generate fantasy sports lineup graphics.
Usage: python3 fantasy_images.py [player_csv_path]
"""
import os
import sys
import json
from pathlib import Path

DEFAULT_CSV = "/home/workspace/Projects/data/fantasy/lineups.csv"
OUT_DIR = Path("/home/workspace/Projects/images/fantasy")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def render_lineup_card(player: str, team: str, projection: float, game: str) -> str:
    return f"""
+-------------------------------------+
|  FANTASY LINEUP — {team:<20}|
|  Player: {player:<27}|
|  Proj:   {projection:<27}|
|  Game:   {game:<27}|
+-------------------------------------+
"""


def main(csv_path: str = DEFAULT_CSV) -> int:
    csv_p = Path(csv_path)
    if not csv_p.exists():
        print(f"No fantasy CSV at {csv_path} (skipping)")
        return 0
    written = 0
    import csv as _csv
    with csv_p.open() as f:
        for row in _csv.DictReader(f):
            card = render_lineup_card(
                row.get("player", "?"),
                row.get("team", "?"),
                row.get("projection", "?"),
                row.get("game", "?"),
            )
            out = OUT_DIR / f"{row.get('player','x').replace(' ','_')}.txt"
            out.write_text(card)
            written += 1
    print(f"Rendered {written} fantasy cards to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CSV
    sys.exit(main(path))
