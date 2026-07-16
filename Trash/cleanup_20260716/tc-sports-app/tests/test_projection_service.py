"""Tests for ProjectionService."""
import sys
from pathlib import Path

# Make repo importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from src.domain.projection_service import ProjectionService


def test_get_projections():
    """ProjectionService.get_projections('WNBA') returns dict with 'projections' key."""
    service = ProjectionService()
    result = service.get_projections("WNBA")
    assert "projections" in result, f"Missing 'projections' key: {list(result.keys())}"
    assert "sport" in result and result["sport"] == "WNBA"
    assert "source" in result
    assert "count" in result
    assert "date" in result
    assert isinstance(result["projections"], list)
    assert result["count"] == len(result["projections"])


def test_invalid_sport_returns_errors():
    service = ProjectionService()
    result = service.get_projections("BOGUS_SPORT")
    assert "projections" in result
    assert result["projections"] == []
    assert "errors" in result and len(result["errors"]) > 0


def test_nba_off_season():
    """NBA is off-season until October."""
    service = ProjectionService()
    result = service.get_projections("NBA")
    assert "projections" in result
    # In July (current month) NBA should report off_season
    if result["source"] == "off_season":
        assert result["count"] == 0


def test_nhl_off_season():
    service = ProjectionService()
    result = service.get_projections("NHL")
    assert "projections" in result


def test_all_sports_no_crash():
    service = ProjectionService()
    for sport in ("WNBA", "NFL", "MLB", "NBA", "NHL", "SOCCER"):
        out = service.get_projections(sport)
        assert "projections" in out
        assert isinstance(out["count"], int)
        assert out["count"] >= 0


def test_team_filter():
    service = ProjectionService()
    out = service.get_projections("WNBA", team="NY")
    assert "projections" in out
    for p in out["projections"]:
        assert p["team"].upper() == "NY"


def test_projection_row_shape():
    """Each projection row has the expected keys."""
    service = ProjectionService()
    out = service.get_projections("WNBA")
    if out["projections"]:
        row = out["projections"][0]
        for key in ("player", "team", "stat", "line", "projection", "edge", "direction", "source"):
            assert key in row, f"Missing '{key}' in {row}"
