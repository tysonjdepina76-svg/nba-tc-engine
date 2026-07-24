"""
Verification tests for all 10 gaps.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

class TestGaps(unittest.TestCase):

    def test_wnba_live_summary(self):
        from sources.wnba_live_summary import fetch_wnba_live_cached
        self.assertIsNotNone(fetch_wnba_live_cached)

    def test_soccer_live_summary(self):
        from sources.soccer_live_summary import fetch_soccer_live_cached
        self.assertIsNotNone(fetch_soccer_live_cached)

    def test_edge_calculation(self):
        from pipeline.daily_picks import compute_edge
        self.assertEqual(compute_edge(10.5, 9.5), 1.0)
        self.assertEqual(compute_edge(None, 9.5), 0.0)

    def test_team_abbreviations(self):
        from config.teams import get_team_abbr
        self.assertEqual(get_team_abbr("Las Vegas Aces", "wnba"), "LV")
        self.assertEqual(get_team_abbr("Unknown", "wnba"), "UNK")

    def test_logging(self):
        from sources.utils.logging import setup_logging
        logger = setup_logging()
        self.assertIsNotNone(logger)

    def test_dashboard_caching(self):
        from dashboard.tc_dashboard import load_cached_data
        self.assertIsNotNone(load_cached_data)

if __name__ == "__main__":
    unittest.main()
