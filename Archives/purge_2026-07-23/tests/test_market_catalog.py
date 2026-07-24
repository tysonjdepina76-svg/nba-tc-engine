import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from market_catalog import catalog_for, is_real_book_source, normalize_period, truth_metadata


def test_period_aliases_and_catalogs():
    assert normalize_period("first_quarter") == "Q1"
    assert normalize_period("first_inning") == "1ST_INNING"
    assert "Q1" in catalog_for("NBA")["periods"]
    assert "1H" in catalog_for("NFL")["periods"]
    assert "F5" in catalog_for("MLB")["periods"]


def test_book_line_truth_gate():
    assert is_real_book_source("DK")
    assert is_real_book_source("ESPN_ODDS")
    assert not is_real_book_source("fd-derived")
    assert truth_metadata(market_line=10.5, source="DK", period="Q1")["alert_eligible"]
    assert not truth_metadata(market_line=10.5, source="SELF_EDGE", period="Q1")["alert_eligible"]
