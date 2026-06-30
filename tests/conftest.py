"""Test configuration and shared fixtures."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


@pytest.fixture
def sample_player_dict():
    return {
        "id": "lebron-james",
        "name": "LeBron James",
        "team": "LAL",
        "position": "SF",
        "stats": {"pts": 25.7, "reb": 7.3, "ast": 7.0, "stl": 1.3, "blk": 0.5, "tov": 3.5, "min": 35.5, "gp": 70},
    }


@pytest.fixture
def sample_game_dict():
    return {
        "id": "401585657",
        "sport": "NBA",
        "home": "LAL",
        "away": "BOS",
        "start_time": "2026-06-29T23:00:00Z",
    }


@pytest.fixture
def sample_projection_dict():
    return {
        "player_id": "lebron-james",
        "player_name": "LeBron James",
        "team": "LAL",
        "stat": "pts",
        "line": 25.5,
        "projection": 28.2,
        "std_dev": 5.5,
        "direction": "OVER",
    }


@pytest.fixture
def espn_nba_fixture_path():
    return Path(__file__).parent / "fixtures" / "adapters" / "espn_nba_scoreboard.json"


@pytest.fixture
def espn_wnba_fixture_path():
    return Path(__file__).parent / "fixtures" / "adapters" / "espn_wnba_scoreboard.json"


@pytest.fixture
def espn_roster_fixture_path():
    return Path(__file__).parent / "fixtures" / "adapters" / "espn_team_roster.json"


@pytest.fixture
def espn_boxscore_fixture_path():
    return Path(__file__).parent / "fixtures" / "adapters" / "espn_boxscore.json"


@pytest.fixture
def sgo_nba_fixture_path():
    return Path(__file__).parent / "fixtures" / "adapters" / "sgo_nba_props.json"


@pytest.fixture
def sgo_wnba_fixture_path():
    return Path(__file__).parent / "fixtures" / "adapters" / "sgo_wnba_props.json"


@pytest.fixture
def odds_api_events_fixture_path():
    return Path(__file__).parent / "fixtures" / "adapters" / "odds_api_nba_events.json"


@pytest.fixture
def odds_api_props_fixture_path():
    return Path(__file__).parent / "fixtures" / "adapters" / "odds_api_player_props.json"


@pytest.fixture
def sample_nba_projection_path():
    return Path(__file__).parent / "fixtures" / "projections" / "sample_nba_proj.json"


@pytest.fixture
def sample_combo_path():
    return Path(__file__).parent / "fixtures" / "combos" / "sample_combo_3leg.json"
