# TC — Triple Conservative — Trademark June 2026 — All rights reserved.
"""Tests for combo_qualifier: median line, edge filter, correlation, hit_prob.

No market dependency — self-edge only. Median aggregation across DK/FD/ESPN
sources when present.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from domain.combo_qualifier import (
    ComboQualifier,
    median_line,
    aggregate_lines,
    is_offensive_stat,
)
from domain.entities import Projection


def _proj(player="A", team="BOS", stat="PTS", line=20.0, proj=24.0, valid=True,
          role="STARTER", status="ACTIVE"):
    return Projection(
        player=player,
        team=team,
        role=role,
        status=status,
        stat=stat,
        tc_projection=proj,
        line=line,
        edge=proj - line,
        direction="OVER" if proj >= line else "UNDER",
        valid=valid,
    )


class TestMedianLine(unittest.TestCase):
    def test_median_two_values(self):
        self.assertEqual(median_line([10.5, 11.5]), 11.0)

    def test_median_three_values(self):
        self.assertEqual(median_line([10.0, 11.0, 12.0]), 11.0)

    def test_median_filters_none_and_zero(self):
        self.assertEqual(median_line([None, 10.0, 0, 11.0]), 10.5)

    def test_median_all_none_returns_none(self):
        self.assertIsNone(median_line([None, None]))


class TestAggregateLines(unittest.TestCase):
    def test_three_source_agreement(self):
        r = aggregate_lines({"dk": 20.0, "fd": 20.5, "espn": 20.0})
        self.assertAlmostEqual(r["median"], 20.0, places=1)
        self.assertGreater(r["agreement"], 0.9)

    def test_spread_lowers_agreement(self):
        r = aggregate_lines({"dk": 20.0, "fd": 30.0, "espn": 20.0})
        self.assertLessEqual(r["agreement"], 0.6)

    def test_single_source_full_agreement(self):
        r = aggregate_lines({"dk": 20.0})
        self.assertEqual(r["agreement"], 1.0)


class TestIsOffensiveStat(unittest.TestCase):
    def test_nba_offensive(self):
        self.assertTrue(is_offensive_stat("PTS"))
        self.assertTrue(is_offensive_stat("REB"))

    def test_nfl_offensive(self):
        self.assertTrue(is_offensive_stat("PASS_YDS"))
        self.assertTrue(is_offensive_stat("RUSH_TD"))

    def test_unknown_returns_false(self):
        self.assertFalse(is_offensive_stat("UNKNOWN"))


class TestFilterProjections(unittest.TestCase):
    def test_high_edge_passes(self):
        q = ComboQualifier("NBA")
        ps = [_proj(proj=28.0)]
        report = q.filter_projections(ps)
        self.assertEqual(len(report.passed), 1)

    def test_low_edge_filtered(self):
        q = ComboQualifier("NBA")
        ps = [_proj(proj=20.5)]
        report = q.filter_projections(ps)
        self.assertEqual(len(report.filtered), 1)
        self.assertIn("edge", report.filtered[0][1])

    def test_invalid_filtered(self):
        q = ComboQualifier("NBA")
        ps = [_proj(proj=28.0, valid=False)]
        report = q.filter_projections(ps)
        self.assertEqual(len(report.filtered), 1)
        self.assertEqual(report.filtered[0][1], "invalid projection")


class TestQualify(unittest.TestCase):
    def test_teammates_pair_builds_combo(self):
        q = ComboQualifier("NBA")
        ps = [
            _proj(player="A", team="BOS", stat="PTS", line=20, proj=28),
            _proj(player="B", team="BOS", stat="AST", line=5, proj=9),
        ]
        combos, _ = q.qualify(ps)
        self.assertGreaterEqual(len(combos), 1)

    def test_cross_team_no_correlation(self):
        q = ComboQualifier("NBA")
        ps = [
            _proj(player="A", team="BOS", stat="PTS", line=20, proj=28),
            _proj(player="X", team="LAL", stat="PTS", line=20, proj=28),
        ]
        combos, _ = q.qualify(ps)
        self.assertEqual(len(combos), 0)

    def test_three_leg_combo(self):
        q = ComboQualifier("NBA")
        ps = [
            _proj(player="A", team="BOS", stat="PTS", line=20, proj=28),
            _proj(player="B", team="BOS", stat="AST", line=5, proj=9),
            _proj(player="C", team="BOS", stat="REB", line=7, proj=11),
        ]
        combos, _ = q.qualify(ps)
        legs_seen = {c.total_legs for c in combos}
        self.assertIn(3, legs_seen)

    def test_combo_sorted_by_hit_prob(self):
        q = ComboQualifier("NBA")
        ps = [
            _proj(player="A", team="BOS", stat="PTS", line=20, proj=28),
            _proj(player="B", team="BOS", stat="AST", line=5, proj=9),
        ]
        combos, _ = q.qualify(ps)
        probs = [c.hit_probability for c in combos]
        self.assertEqual(probs, sorted(probs, reverse=True))

    def test_mlb_max_5_legs(self):
        q = ComboQualifier("MLB")
        ps = [
            _proj(player=f"P{i}", team="NYY", stat="HITS", line=1, proj=5)
            for i in range(5)
        ]
        combos, _ = q.qualify(ps)
        self.assertGreater(len(combos), 0)

    def test_nhl_hockey(self):
        q = ComboQualifier("NHL")
        ps = [
            _proj(player="A", team="BOS", stat="GOALS", line=0.5, proj=2.5),
            _proj(player="B", team="BOS", stat="ASSISTS", line=0.5, proj=2.5),
        ]
        combos, _ = q.qualify(ps)
        self.assertGreaterEqual(len(combos), 1)


if __name__ == "__main__":
    unittest.main()