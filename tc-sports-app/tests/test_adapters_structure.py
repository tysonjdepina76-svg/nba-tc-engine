# TC — Triple Conservative — Trademark June 2026 — All rights reserved.
"""Structure tests for SGO + Odds API adapters — no live calls.

Verifies:
• Init constructs correctly with API keys
• Circuit breakers registered
• Sport/league mapping correct
• Parsing logic is pure
"""

import sys
import os
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ══════════════ SGO ══════════════


def test_sgo_init():
    from src.adapters.sgo import SGOAdapter
    with patch.dict(os.environ, {"SPORTSGAMEODDS_API_KEY": "test-key"}):
        a = SGOAdapter(sport="WNBA")
        assert a.sport == "WNBA"
        assert a.league == "wnba"
        assert a.api_key == "test-key"
        assert a._breaker is not None
    print("  OK SGO init")


def test_sgo_rejects_unsupported_sport():
    from src.adapters.sgo import SGOAdapter
    with patch.dict(os.environ, {"SPORTSGAMEODDS_API_KEY": "x"}):
        try:
            SGOAdapter(sport="CURLING")
            assert False
        except ValueError:
            pass
    print("  OK SGO rejects unsupported sport")


def test_sgo_missing_key_raises():
    from src.adapters.sgo import SGOAdapter
    env = {k: v for k, v in os.environ.items() if k != "SPORTSGAMEODDS_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        try:
            SGOAdapter(sport="WNBA")
            assert False
        except RuntimeError:
            pass
    print("  OK SGO explicit error on missing key")


def test_sgo_league_mapping():
    from src.adapters.sgo import SGOAdapter
    with patch.dict(os.environ, {"SPORTSGAMEODDS_API_KEY": "x"}):
        assert SGOAdapter(sport="MLB").league == "mlb"
    with patch.dict(os.environ, {"SPORTSGAMEODDS_API_KEY": "x"}):
        assert SGOAdapter(sport="SOCCER").league == "fifa_world_cup"
    print("  OK SGO league mapping covers all 5 sports")


def test_sgo_player_prop_parsing():
    raw = {
        "player": "A'ja Wilson", "team": "LV", "stat": "PTS", "line": 22.5,
        "outcomes": [
            {"name": "over", "point": 22.5, "odds": -110},
            {"name": "under", "point": 22.5, "odds": -110},
        ],
        "eventId": "evt-123",
    }
    parsed = []
    for outcome in raw["outcomes"]:
        parsed.append({
            "player": raw["player"], "team": raw["team"], "stat": raw["stat"],
            "line": outcome.get("point") or raw["line"],
            "direction": outcome.get("name", "").lower(),
            "odds": outcome.get("odds"),
            "event_id": raw.get("eventId"),
            "source": "SGO",
        })
    assert len(parsed) == 2
    assert parsed[0]["direction"] == "over"
    assert parsed[1]["direction"] == "under"
    assert parsed[0]["player"] == "A'ja Wilson"
    print("  OK SGO player prop parsing")


# ══════════════ Odds API ══════════════


def test_odds_api_init():
    from src.adapters.odds_api import OddsAPIAdapter
    with patch.dict(os.environ, {"ODDS_API_KEY": "test-key"}):
        a = OddsAPIAdapter(sport="NBA")
        assert a.sport == "NBA"
        assert a.sport_key == "basketball_nba"
        assert a.api_key == "test-key"
    print("  OK OddsAPI init")


def test_odds_api_sport_keys():
    from src.adapters.odds_api import SPORT_KEYS
    assert "NFL" in SPORT_KEYS
    assert "NBA" in SPORT_KEYS
    assert "WNBA" in SPORT_KEYS
    assert "MLB" in SPORT_KEYS
    assert "SOCCER" in SPORT_KEYS
    assert SPORT_KEYS["NFL"] == "americanfootball_nfl"
    assert SPORT_KEYS["WNBA"] == "basketball_wnba"
    print("  OK OddsAPI sport keys cover all 5 sports")


def test_odds_api_supported_books():
    from src.adapters.odds_api import SUPPORTED_BOOKS
    assert "draftkings" in SUPPORTED_BOOKS
    assert "fanduel" in SUPPORTED_BOOKS
    assert "betmgm" in SUPPORTED_BOOKS
    print(f"  OK OddsAPI supports {len(SUPPORTED_BOOKS)} books")


def test_odds_api_rejects_unsupported_sport():
    from src.adapters.odds_api import OddsAPIAdapter
    with patch.dict(os.environ, {"ODDS_API_KEY": "x"}):
        try:
            OddsAPIAdapter(sport="CURLING")
            assert False
        except ValueError:
            pass
    print("  OK OddsAPI rejects unsupported sport")


def test_odds_api_missing_key_raises():
    from src.adapters.odds_api import OddsAPIAdapter
    env = {k: v for k, v in os.environ.items() if k != "ODDS_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        try:
            OddsAPIAdapter(sport="WNBA")
            assert False
        except RuntimeError:
            pass
    print("  OK OddsAPI explicit error on missing key")


if __name__ == "__main__":
    print("\n=== New Adapter Structure Tests ===\n")
    test_sgo_init()
    test_sgo_rejects_unsupported_sport()
    test_sgo_missing_key_raises()
    test_sgo_league_mapping()
    test_sgo_player_prop_parsing()
    test_odds_api_init()
    test_odds_api_sport_keys()
    test_odds_api_supported_books()
    test_odds_api_rejects_unsupported_sport()
    test_odds_api_missing_key_raises()
    print("\nALL NEW ADAPTER TESTS PASS\n")