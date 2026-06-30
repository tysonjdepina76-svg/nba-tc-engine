"""Integration tests for SGO (SportsGameOdds) adapter."""
import json
from pathlib import Path
import pytest
from adapters.sgo import SGOClient


FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "adapters"


@pytest.fixture
def sgo_client():
    return SGOClient(api_key="TEST_KEY")


def load_fixture(name):
    return json.loads((FIXTURE_DIR / name).read_text())


class TestSGOProps:
    def test_fetch_nba_props(self, mocker, sgo_client):
        payload = load_fixture("sgo_nba_props.json")
        mocker.patch.object(sgo_client, "_get", return_value=payload)
        props = sgo_client.fetch_player_props(sport="NBA")
        assert len(props) > 0
        assert all(p.line > 0 for p in props)

    def test_fetch_wnba_props(self, mocker, sgo_client):
        payload = load_fixture("sgo_wnba_props.json")
        mocker.patch.object(sgo_client, "_get", return_value=payload)
        props = sgo_client.fetch_player_props(sport="WNBA")
        assert len(props) > 0

    def test_prop_has_player_and_stat(self, mocker, sgo_client):
        payload = load_fixture("sgo_nba_props.json")
        mocker.patch.object(sgo_client, "_get", return_value=payload)
        props = sgo_client.fetch_player_props(sport="NBA")
        p = props[0]
        assert p.player_name
        assert p.stat in ("pts", "reb", "ast", "3pm", "stl", "blk")

    def test_prop_has_over_under(self, mocker, sgo_client):
        payload = load_fixture("sgo_nba_props.json")
        mocker.patch.object(sgo_client, "_get", return_value=payload)
        props = sgo_client.fetch_player_props(sport="NBA")
        p = props[0]
        assert p.over_odds is not None or p.under_odds is not None


class TestSGOErrors:
    def test_missing_api_key_raises(self):
        with pytest.raises(ValueError):
            SGOClient(api_key=None)

    def test_503_block_returns_empty(self, mocker, sgo_client):
        mocker.patch.object(sgo_client, "_get", side_effect=Exception("HTTP 503"))
        props = sgo_client.fetch_player_props(sport="NBA")
        assert props == []
