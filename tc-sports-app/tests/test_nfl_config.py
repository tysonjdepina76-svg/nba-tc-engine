# TC — Triple Conservative — Trademark June 2026 — All rights reserved.
"""NFL config tests — verify the NFL block is complete and sane."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.domain.sport_config import (
    SPORT_CONFIG,
    NFL_STAT_KEYS,
    NFL_STAT_MAP,
    NFL_POSITIONS,
    NFL_SCORING,
    NFL_THRESHOLDS,
    get_config,
    get_nfl_scoring,
    get_nfl_stat_map,
    get_nfl_positions,
)


def test_nfl_in_sport_config():
    assert "NFL" in SPORT_CONFIG, "NFL missing from SPORT_CONFIG"
    print("  ✅ NFL key present in SPORT_CONFIG")


def test_nfl_stat_keys_complete():
    expected = {"PASS_YDS", "PASS_TD", "RUSH_YDS", "RUSH_TD", "REC", "REC_YDS", "REC_TD"}
    actual = set(NFL_STAT_KEYS)
    missing = expected - actual
    assert not missing, f"Missing NFL stat keys: {missing}"
    print(f"  ✅ NFL stat keys: {len(NFL_STAT_KEYS)} keys, all major categories present")


def test_nfl_stat_map_coverage():
    """Every stat key must have a mapping (or be intentionally unmapped)."""
    for key in NFL_STAT_KEYS:
        assert key in NFL_STAT_MAP, f"No stat_map entry for {key}"
    print(f"  ✅ NFL stat map: {len(NFL_STAT_MAP)} mappings, all keys covered")


def test_nfl_positions_present():
    assert "QB" in NFL_POSITIONS
    assert "RB" in NFL_POSITIONS
    assert "WR" in NFL_POSITIONS
    assert "TE" in NFL_POSITIONS
    print(f"  ✅ NFL positions: {NFL_POSITIONS}")


def test_nfl_scoring_weights():
    s = NFL_SCORING
    assert s["pass_td"] == 4.0, "Pass TD should weigh 4 pts"
    assert s["rush_td"] == 6.0, "Rush TD should weigh 6 pts"
    assert s["rec_td"] == 6.0, "Rec TD should weigh 6 pts"
    assert s["pass_int"] < 0, "INTs should be negative"
    assert s["fumble_lost"] < 0, "Fumbles should be negative"
    print(f"  ✅ NFL scoring weights: pass_td={s['pass_td']}, rush_td={s['rush_td']}, rec_td={s['rec_td']}")


def test_nfl_thresholds_sensible():
    t = NFL_THRESHOLDS
    assert t["edge_threshold"] >= 2.0, "NFL edge threshold should be ≥ 2.0"
    assert t["line_factor"] == 0.88, "Line factor must match TC default"
    assert 0 <= t["q_factor"] <= 1, "Q factor must be 0-1"
    print(f"  ✅ NFL thresholds: edge={t['edge_threshold']}, line_factor={t['line_factor']}, q_factor={t['q_factor']}")


def test_get_config_nfl():
    cfg = get_config("NFL")
    assert cfg["stat_keys"] == NFL_STAT_KEYS
    assert cfg["stat_map"] == NFL_STAT_MAP
    assert cfg["positions"] == NFL_POSITIONS
    print("  ✅ get_config('NFL') returns complete config")


def test_helpers_return_copies():
    """Helper functions must return copies, not references."""
    a = get_nfl_scoring()
    a["pass_td"] = 999.0
    b = get_nfl_scoring()
    assert b["pass_td"] == 4.0, "Helper leaked reference to module state"
    print("  ✅ Helpers return copies (no mutation leak)")


if __name__ == "__main__":
    print("\n=== NFL Config Tests ===\n")
    test_nfl_in_sport_config()
    test_nfl_stat_keys_complete()
    test_nfl_stat_map_coverage()
    test_nfl_positions_present()
    test_nfl_scoring_weights()
    test_nfl_thresholds_sensible()
    test_get_config_nfl()
    test_helpers_return_copies()
    print("\n✅ ALL NFL CONFIG TESTS PASS\n")
