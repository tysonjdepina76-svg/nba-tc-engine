"""Test all sports configurations — TC Sports App."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.domain.sport_config import get_config
from src.domain.entities import Sport, BADGE_COLORS
from src.domain.engine import TCEngine

ALL_SPORTS = ["NBA", "WNBA", "NFL", "MLB", "SOCCER", "NHL", "TENNIS", "GOLF", "CFB", "CBB"]


class TestAllSports:
    def test_all_sports_have_config(self):
        for sport in ALL_SPORTS:
            config = get_config(sport)
            assert "stat_keys" in config, f"{sport} missing stat_keys"
            assert "line_factor" in config, f"{sport} missing line_factor"
            assert "edge_threshold" in config, f"{sport} missing edge_threshold"
            print(f"OK {sport} configured")

    def test_all_sports_have_engine(self):
        for sport in ALL_SPORTS:
            engine = TCEngine(sport)
            assert engine.sport == sport
            assert engine.stat_keys
            print(f"OK {sport} engine ready")

    def test_all_sports_in_enum(self):
        sport_names = [s.value for s in Sport]
        for sport in ALL_SPORTS:
            assert sport in sport_names, f"{sport} missing from Sport enum"
            print(f"OK {sport} in Sport enum")

    def test_badge_colors_for_all_sports(self):
        for sport in ALL_SPORTS:
            assert sport in BADGE_COLORS, f"{sport} missing badge color"
            assert BADGE_COLORS[sport].startswith("#")
            print(f"OK {sport} badge color")
