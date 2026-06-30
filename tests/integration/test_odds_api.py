"""Integration tests for OddsAPI adapter."""
import json
from pathlib import Path
import pytest
from adapters.odds_api import OddsAPIClient


FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "adapters"


@pytest.fixture
def client():
    return OddsAPIClient(api_key="TEST_KEY")


def load_fixture(name):
    return json.loads((FIXTURE_DIR / name).read_text())


class TestOddsAPIEvents:
    def test_fetch_nba_events(self, mocker, client):
        payload = load_fixture("odds_api_nba_events.json")
        mocker.patch.object(client, "_get", return_value=payload)
        events = client.fetch_events(sport="basketball_nba")
        assert len(events) > 0
        assert events[0].id

    def test_event_has_teams(self, mocker, client):
        payload = load_fixture("odds_api_nba_events.json")
        mocker.patch.object(client, "_get", return_value=payload)
        events = client.fetch_events(sport="basketball_nba")
        e = events[0]
        assert e.home_team
        assert e.away_team


class TestOddsAPIPlayerProps:
    def test_fetch_player_props(self, mocker, client):
        payload = load_fixture("odds_api_player_props.json")
        mocker.patch.object(client, "_get", return_value=payload)
        props = client.fetch_player_props(sport="basketball_nba", event_id="abc123")
        assert len(props) > 0
        assert props[0].market in ("player_points", "player_rebounds", "player_assists", "player_threes")

    def test_prop_market_normalized(self, mocker, client):
        payload = load_fixture("odds_api_player_props.json")
        mocker.patch.object(client, "_get", return_value=payload)
        props = client.fetch_player_props(sport="basketball_nba", event_id="abc123")
        p = props[0]
        assert p.stat in ("pts", "reb", "ast", "3pm")

    def test_prop_has_bookmaker_prices(self, mocker, client):
        payload = load_fixture("odds_api_player_props.json")
        mocker.patch.object(client, "_get", return_value=payload)
        props = client.fetch_player_props(sport="basketball_nba", event_id="abc123")
        p = props[0]
        assert p.best_over_price is not None or p.best_under_price is not None


class TestOddsAPIErrors:
    def test_missing_api_key_raises(self):
        with pytest.raises(ValueError):
            OddsAPIClient(api_key=None)
