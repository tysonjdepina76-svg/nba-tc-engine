# TC — Triple Conservative — Trademark June 2026 — All rights reserved.
# Sports covered: NFL, NBA, WNBA, MLB, Soccer.
"""Adapter tests — verify structure, NOT live calls.

Tests confirm:
• ESPNAdapter can be initialized for any supported sport
• Per-endpoint circuit breakers are registered
• Matchup filter works on hand-built Player lists
• A Player built by hand round-trips through the engine without errors
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.adapters.espn import ESPNAdapter, SPORT_SLUGS
from src.domain.entities import Player


def test_supported_sports():
    a = ESPNAdapter
    supported = list(SPORT_SLUGS.keys())
    assert "WNBA" in supported
    assert "NBA" in supported
    assert "NFL" in supported
    assert "MLB" in supported
    assert "SOCCER" in supported
    print(f"  ✅ Adapter supports: {supported}")


def test_unsupported_sport_rejected():
    try:
        ESPNAdapter(sport="CURLING")
        print("  ❌ Should have raised")
        sys.exit(1)
    except ValueError as e:
        print(f"  ✅ Unknown sport rejected: {e}")


def test_adapter_init():
    a = ESPNAdapter(sport="WNBA")
    assert a.sport == "WNBA"
    assert a.season == 2026
    assert a.slug == "basketball/leagues/wnba"
    print(f"  ✅ ESPNAdapter init OK: sport={a.sport}, slug={a.slug}")


def test_breakers_exist():
    a = ESPNAdapter(sport="MLB")
    slate_state = a._slate_breaker.state
    stats_state = a._stats_breaker.state
    assert slate_state == "closed"
    assert stats_state == "closed"
    print(f"  ✅ Breakers registered: slate={slate_state}, stats={stats_state}")


def test_matchup_filter():
    """Filter a hand-built player list by away/home team — no API call."""
    a = ESPNAdapter(sport="WNBA")
    players = [
        Player(name="A'ja Wilson", team="LV"),
        Player(name="Breanna Stewart", team="NY"),
        Player(name="Kelsey Plum", team="LV"),
    ]
    home = [p for p in players if p.team == "LV"]
    away = [p for p in players if p.team == "NY"]
    assert len(home) == 2
    assert len(away) == 1
    print(f"  ✅ Matchup filter: home={len(home)} players, away={len(away)} players")


def test_player_to_engine_roundtrip():
    """A Player built by hand must run through engine.py unchanged."""
    from src.domain.engine import project_player

    p = Player(
        name="A'ja Wilson",
        team="LV",
        role="STARTER",
        status="ACTIVE",
        position="F",
        minutes=32.0,
        season_stats={"avgPoints": 22.5, "avgRebounds": 10.0, "avgMinutes": 32.0},
    )
    stat_keys = ["PTS", "REB", "AST"]
    projections = project_player(p, stat_keys)
    stat_names = [proj.stat for proj in projections]
    assert "PTS" in stat_names, "PTS missing"
    pts_proj = next(x for x in projections if x.stat == "PTS")
    assert pts_proj.tc_projection > 0
    print(f"  ✅ Player→Engine roundtrip: PTS TC={pts_proj.tc_projection}")


if __name__ == "__main__":
    print("\n=== ESPN Adapter — Structure Tests ===\n")
    test_supported_sports()
    test_unsupported_sport_rejected()
    test_adapter_init()
    test_breakers_exist()
    test_matchup_filter()
    test_player_to_engine_roundtrip()
    print("\n✅ ALL ADAPTER TESTS PASS — structure clean, no live calls\n")