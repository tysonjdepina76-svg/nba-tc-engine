"""Unit tests for sport_config (all sports)."""
import pytest
from sport_config import SPORTS, get_config, list_sports, StatProfile


class TestSportRegistry:
    def test_all_sports_present(self):
        assert "NBA" in SPORTS
        assert "WNBA" in SPORTS
        assert "MLB" in SPORTS
        assert "NHL" in SPORTS
        assert "EPL" in SPORTS or "SOCCER" in SPORTS

    def test_list_sports(self):
        sports = list_sports()
        assert isinstance(sports, list)
        assert "NBA" in sports


class TestNBAConfig:
    def test_nba_stats(self):
        cfg = get_config("NBA")
        assert "pts" in cfg.stats
        assert "reb" in cfg.stats
        assert "ast" in cfg.stats
        assert "3pm" in cfg.stats or "fg3m" in cfg.stats

    def test_nba_stat_profile(self):
        cfg = get_config("NBA")
        pts = cfg.get_stat("pts")
        assert isinstance(pts, StatProfile)
        assert pts.min_value >= 0
        assert pts.max_value > 0


class TestWNBAConfig:
    def test_wnba_stats(self):
        cfg = get_config("WNBA")
        assert "pts" in cfg.stats
        assert "reb" in cfg.stats
        assert "ast" in cfg.stats

    def test_wnba_lower_minutes(self):
        cfg = get_config("WNBA")
        assert cfg.avg_minutes < 40  # WNBA games are 40 min


class TestMLBConfig:
    def test_mlb_stats(self):
        cfg = get_config("MLB")
        assert "hits" in cfg.stats or "h" in cfg.stats
        assert "rbi" in cfg.stats or "rbi" in cfg.stats
        assert "hr" in cfg.stats or "home_runs" in cfg.stats

    def test_mlb_hitter_focus(self):
        cfg = get_config("MLB")
        assert cfg.primary_position_group == "hitters" or cfg.mode == "hitter"


class TestNHLConfig:
    def test_nhl_stats(self):
        cfg = get_config("NHL")
        assert "goals" in cfg.stats or "g" in cfg.stats
        assert "assists" in cfg.stats or "a" in cfg.stats
        assert "shots" in cfg.stats or "sog" in cfg.stats


class TestSoccerConfig:
    def test_soccer_stats(self):
        cfg = get_config("EPL") or get_config("SOCCER")
        assert "goals" in cfg.stats
        assert "shots" in cfg.stats or "sot" in cfg.stats

    def test_soccer_match_format(self):
        cfg = get_config("EPL") or get_config("SOCCER")
        assert cfg.match_minutes == 90


class TestConfigErrors:
    def test_unknown_sport_raises(self):
        with pytest.raises(KeyError):
            get_config("CRICKET")
