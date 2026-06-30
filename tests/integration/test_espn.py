"""Integration tests for ESPN adapter."""
import json
from pathlib import Path
import pytest
from adapters.espn import ESPNClient


FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "adapters"


@pytest.fixture
def espn_client():
    return ESPNClient()


def load_fixture(name):
    return json.loads((FIXTURE_DIR / name).read_text())


class TestESPNGames:
    def test_fetch_nba_games(self, mocker, espn_client):
        payload = load_fixture("espn_nba_scoreboard.json")
        mocker.patch.object(espn_client, "_get", return_value=payload)
        games = espn_client.fetch_games(sport="NBA")
        assert len(games) > 0
        assert games[0].sport == "NBA"

    def test_fetch_wnba_games(self, mocker, espn_client):
        payload = load_fixture("espn_wnba_scoreboard.json")
        mocker.patch.object(espn_client, "_get", return_value=payload)
        games = espn_client.fetch_games(sport="WNBA")
        assert len(games) > 0

    def test_game_has_teams(self, mocker, espn_client):
        payload = load_fixture("espn_nba_scoreboard.json")
        mocker.patch.object(espn_client, "_get", return_value=payload)
        games = espn_client.fetch_games(sport="NBA")
        g = games[0]
        assert g.home_team.abbr
        assert g.away_team.abbr


class TestESPNPlayers:
    def test_fetch_team_roster(self, mocker, espn_client):
        payload = load_fixture("espn_team_roster.json")
        mocker.patch.object(espn_client, "_get", return_value=payload)
        players = espn_client.fetch_team_roster(team_id="13", sport="NBA")
        assert len(players) > 0
        assert all(p.team for p in players)

    def test_player_has_stats(self, mocker, espn_client):
        payload = load_fixture("espn_team_roster.json")
        mocker.patch.object(espn_client, "_get", return_value=payload)
        players = espn_client.fetch_team_roster(team_id="13", sport="NBA")
        p = players[0]
        assert isinstance(p.stats, dict)


class TestESPNBoxscore:
    def test_fetch_boxscore(self, mocker, espn_client):
        payload = load_fixture("espn_boxscore.json")
        mocker.patch.object(espn_client, "_get", return_value=payload)
        box = espn_client.fetch_boxscore(event_id="401585657", sport="NBA")
        assert box.game_id == "401585657"
        assert len(box.player_stats) > 0

    def test_boxscore_player_stats_have_minutes(self, mocker, espn_client):
        payload = load_fixture("espn_boxscore.json")
        mocker.patch.object(espn_client, "_get", return_value=payload)
        box = espn_client.fetch_boxscore(event_id="401585657", sport="NBA")
        ps = box.player_stats[0]
        assert ps.minutes > 0
