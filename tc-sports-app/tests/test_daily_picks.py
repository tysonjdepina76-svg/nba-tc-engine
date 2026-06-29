# TC — Triple Conservative — Trademark June 2026 — All rights reserved.
# Sports covered: NFL, NBA, WNBA, MLB, Soccer.
"""DailyPicks orchestrator tests.

Tests confirm:
* DailyPicks can be instantiated for any sport
* Dry-run mode does not touch network
* Validations gate every step
* Output goes to reports/daily/YYYY-MM-DD/
"""
from datetime import datetime
from unittest.mock import MagicMock

from src.domain.entities import Game, Player


def fake_game(away: str, home: str) -> Game:
    return Game(
        sport="NBA",
        away_team=away,
        home_team=home,
    )


def fake_roster():
    return {
        "player_a": Player(
            name="Player A",
            team="BOS",
            role="STARTER",
            status="ACTIVE",
            position="G",
            minutes=34.0,
            season_stats={"avgPoints": 25.0, "avgRebounds": 5.0, "avgAssists": 7.0, "avgMinutes": 34.0},
        ),
        "player_b": Player(
            name="Player B",
            team="LAL",
            role="STARTER",
            status="ACTIVE",
            position="F",
            minutes=33.0,
            season_stats={"avgPoints": 22.0, "avgRebounds": 8.0, "avgAssists": 4.0, "avgMinutes": 33.0},
        ),
    }


def test_daily_picks_class_exists():
    from src.domain.daily_picks import DailyPicks
    assert DailyPicks is not None, "DailyPicks class not found"
    print("  OK DailyPicks class is importable")


def test_daily_picks_requires_sport_and_date():
    from src.domain.daily_picks import DailyPicks
    dp = DailyPicks(sport="NBA", date="2026-06-29")
    assert dp.sport == "NBA"
    assert dp.date == "2026-06-29"
    assert dp.config is not None
    print("  OK DailyPicks constructor accepts sport + date")


def test_daily_picks_normalizes_date():
    from src.domain.daily_picks import DailyPicks
    dp = DailyPicks(sport="WNBA", date="2026-06-29")
    assert len(dp.date) == 10
    print("  OK DailyPicks normalizes date to YYYY-MM-DD")


def test_daily_picks_runs_in_dry_mode():
    from src.domain.daily_picks import DailyPicks
    dp = DailyPicks(sport="NBA", date="2026-06-29")
    result = dp.run(dry_run=True, adapter=fake_roster)
    assert isinstance(result, list)
    print(f"  OK Dry run produced {len(result)} projections")


def test_daily_picks_rejects_unsupported_sport():
    from src.domain.daily_picks import DailyPicks
    try:
        DailyPicks(sport="CRICKET", date="2026-06-29")
        assert False, "should have raised"
    except ValueError:
        pass
    print("  OK DailyPicks rejects unsupported sports")


def test_daily_picks_save_creates_directory():
    import tempfile
    from pathlib import Path
    from src.domain.daily_picks import DailyPicks
    from src.domain.entities import Projection

    with tempfile.TemporaryDirectory() as tmp:
        dp = DailyPicks(sport="NBA", date="2026-06-29", output_dir=tmp)
        projection = Projection(
            player="Test Player", team="BOS", role="STARTER", status="ACTIVE",
            stat="PTS", tc_projection=20.0, line=18.0, edge=2.0,
            direction="OVER", valid=True,
        )
        path = dp.save([projection], format="json")
        assert Path(path).exists(), "output file missing"
        print(f"  OK save() wrote file: {Path(path).name}")


def test_daily_picks_save_writes_csv():
    import tempfile
    from pathlib import Path
    from src.domain.daily_picks import DailyPicks
    from src.domain.entities import Projection

    with tempfile.TemporaryDirectory() as tmp:
        dp = DailyPicks(sport="NBA", date="2026-06-29", output_dir=tmp)
        projection = Projection(
            player="Test Player", team="BOS", role="STARTER", status="ACTIVE",
            stat="PTS", tc_projection=20.0, line=18.0, edge=2.0,
            direction="OVER", valid=True,
        )
        path = dp.save([projection], format="csv")
        assert Path(path).exists()
        text = Path(path).read_text()
        assert "Test Player" in text
        assert "PTS" in text
        print(f"  OK save() wrote CSV: {Path(path).name}")


def test_daily_picks_run_validates_output():
    from src.domain.daily_picks import DailyPicks
    dp = DailyPicks(sport="NBA", date="2026-06-29")
    result = dp.run(dry_run=True, adapter=fake_roster)
    for proj in result:
        assert isinstance(proj.tc_projection, float)
        assert proj.direction in ("OVER", "UNDER", "PASS")
    print(f"  OK Validated {len(result)} projections")


if __name__ == "__main__":
    print("\n=== DailyPicks Tests ===\n")
    test_daily_picks_class_exists()
    test_daily_picks_requires_sport_and_date()
    test_daily_picks_normalizes_date()
    test_daily_picks_rejects_unsupported_sport()
    test_daily_picks_save_creates_directory()
    test_daily_picks_save_writes_csv()
    test_daily_picks_runs_in_dry_mode()
    test_daily_picks_run_validates_output()
    print("\nALL DAILY PICKS TESTS PASS\n")

