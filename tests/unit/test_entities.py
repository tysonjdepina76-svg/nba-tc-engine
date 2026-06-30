"""Unit tests for domain entities."""
import pytest
from entities import Player, Game, Projection


class TestPlayer:
    def test_from_dict(self, sample_player_dict):
        p = Player.from_dict(sample_player_dict)
        assert p.id == "lebron-james"
        assert p.name == "LeBron James"
        assert p.team == "LAL"

    def test_stat_lookup(self, sample_player_dict):
        p = Player.from_dict(sample_player_dict)
        assert p.get_stat("pts") == 25.7
        with pytest.raises(KeyError):
            p.get_stat("nope")

    def test_minutes_avg(self, sample_player_dict):
        p = Player.from_dict(sample_player_dict)
        assert p.minutes_avg == 35.5

    def test_repr(self, sample_player_dict):
        p = Player.from_dict(sample_player_dict)
        assert "LeBron James" in repr(p)
        assert "LAL" in repr(p)


class TestGame:
    def test_from_dict(self, sample_game_dict):
        g = Game.from_dict(sample_game_dict)
        assert g.id == "401585657"
        assert g.sport == "NBA"

    def test_team_abbreviations(self, sample_game_dict):
        g = Game.from_dict(sample_game_dict)
        assert g.home_team.abbr == "LAL"
        assert g.away_team.abbr == "BOS"

    def test_matchup_label(self, sample_game_dict):
        g = Game.from_dict(sample_game_dict)
        assert g.matchup == "BOS @ LAL" or g.matchup == "LAL vs BOS"

    def test_status_enum(self, sample_game_dict):
        g = Game.from_dict(sample_game_dict)
        assert g.is_scheduled is True
        assert g.is_final is False


class TestProjection:
    def test_from_dict(self, sample_projection_dict):
        pr = Projection.from_dict(sample_projection_dict)
        assert pr.stat == "pts"
        assert pr.line == 25.5
        assert pr.direction == "OVER"

    def test_edge_calc(self, sample_projection_dict):
        pr = Projection.from_dict(sample_projection_dict)
        assert pr.edge_pct > 0
        assert pr.edge_pct < 100

    def test_confidence_in_range(self, sample_projection_dict):
        pr = Projection.from_dict(sample_projection_dict)
        assert 0.0 <= pr.confidence <= 1.0

    def test_invalid_direction(self, sample_projection_dict):
        bad = dict(sample_projection_dict)
        bad["direction"] = "BOTH"
        with pytest.raises(ValueError):
            Projection.from_dict(bad)

    def test_to_dict_roundtrip(self, sample_projection_dict):
        pr = Projection.from_dict(sample_projection_dict)
        out = pr.to_dict()
        assert out["stat"] == "pts"
        assert out["line"] == 25.5
