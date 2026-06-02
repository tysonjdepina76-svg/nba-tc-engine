"""Unit tests for the Crypto Leverage Sentinel.

Run:  python3 test_sentinel.py
Exit: 0 if all pass, 1 otherwise.
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leverage_check as lc

# -------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------


def short_pos(entry=70000.0, lev=20.0):
    return lc.Position(entry_price=entry, leverage=lev, position_type="short")


def long_pos(entry=70000.0, lev=20.0):
    return lc.Position(entry_price=entry, leverage=lev, position_type="long")


# -------------------------------------------------------------------------
# Status classification
# -------------------------------------------------------------------------


class TestStatusClassification(unittest.TestCase):
    def test_stable_below_60(self):
        status, coeff = lc.classify_status(45.0)
        self.assertEqual(status, "STABLE")
        self.assertEqual(coeff, lc.STOP_COEFF_STABLE)

    def test_elevated_between_60_and_80(self):
        status, coeff = lc.classify_status(70.0)
        self.assertEqual(status, "ELEVATED")
        self.assertEqual(coeff, lc.STOP_COEFF_ELEVATED)

    def test_critical_above_80(self):
        status, coeff = lc.classify_status(85.0)
        self.assertEqual(status, "CRITICAL")
        self.assertEqual(coeff, lc.STOP_COEFF_CRITICAL)

    def test_boundary_60_is_stable(self):
        # classify_status uses strict >. At 60.0, the ELEVATED branch is not
        # taken, so 60.0 is classified as STABLE.
        status, _ = lc.classify_status(60.0)
        self.assertEqual(status, "STABLE")

    def test_boundary_80_is_elevated(self):
        # At 80.0, the CRITICAL branch is not taken (strict >), so 80.0 is ELEVATED.
        status, _ = lc.classify_status(80.0)
        self.assertEqual(status, "ELEVATED")

    def test_just_above_60_is_elevated(self):
        status, _ = lc.classify_status(60.01)
        self.assertEqual(status, "ELEVATED")

    def test_just_above_80_is_critical(self):
        status, _ = lc.classify_status(80.01)
        self.assertEqual(status, "CRITICAL")


# -------------------------------------------------------------------------
# Liquidation math (short)
# -------------------------------------------------------------------------


class TestShortLiquidationMath(unittest.TestCase):
    def test_liquidation_price_20x_short(self):
        pos = short_pos(entry=70000, lev=20)
        # 20x short: liq is +5% above entry
        self.assertAlmostEqual(pos.liquidation_price(), 73500.0, places=2)

    def test_distance_positive_when_under_liq(self):
        # BTC is below the short liq — safe distance
        pos = short_pos(entry=70000, lev=20)
        m = lc.compute_metrics(pos, spot=70000.0, dvol=45.0)
        self.assertGreater(m.distance_to_liq_percent, 0)

    def test_unrealized_pnl_long_is_positive_when_price_up(self):
        # Long 20x: BTC up 1% → +20% on margin
        m = lc.compute_metrics(long_pos(entry=70000, lev=20), spot=70700.0, dvol=45.0)
        self.assertAlmostEqual(m.unrealized_pnl_percent, 20.0, places=2)

    def test_unrealized_pnl_short_is_positive_when_price_down(self):
        # Short 20x: BTC down 1% → +20% on margin
        m = lc.compute_metrics(short_pos(entry=70000, lev=20), spot=69300.0, dvol=45.0)
        self.assertAlmostEqual(m.unrealized_pnl_percent, 20.0, places=2)

    def test_recommended_stop_uses_volatility_coefficient(self):
        # distance to liq ~5% with 20x short at entry, spot=entry
        pos = short_pos(entry=70000, lev=20)
        m_stable = lc.compute_metrics(pos, spot=70000.0, dvol=45.0)
        m_crit = lc.compute_metrics(pos, spot=70000.0, dvol=85.0)
        # Critical regime should produce a tighter stop
        self.assertLess(m_crit.recommended_stop_percent, m_stable.recommended_stop_percent)

    def test_compute_metrics_returns_dataclass(self):
        pos = short_pos(entry=70000, lev=20)
        m = lc.compute_metrics(pos, spot=70000.0, dvol=45.0)
        self.assertIsInstance(m, lc.RiskMetrics)
        # All required fields present
        for attr in (
            "status",
            "current_btc_price",
            "volatility_index",
            "liquidation_price",
            "distance_to_liq_percent",
            "unrealized_pnl_percent",
            "recommended_stop_percent",
            "timestamp",
        ):
            self.assertTrue(hasattr(m, attr))


# -------------------------------------------------------------------------
# Alert classification
# -------------------------------------------------------------------------


class TestAlertClassification(unittest.TestCase):
    def test_margin_hazard_at_threshold(self):
        pos = short_pos(entry=70000, lev=20)
        # Manually craft a near-liq metrics object
        m = lc.compute_metrics(pos, spot=73575.0, dvol=45.0)
        # Force the distance below 1.5 by using a tighter scenario
        m_almost_liq = lc.RiskMetrics(
            status="CRITICAL",
            current_btc_price=m.current_btc_price,
            volatility_index=85.0,
            liquidation_price=73500.0,
            distance_to_liq_percent=1.0,
            unrealized_pnl_percent=0.0,
            recommended_stop_percent=0.15,
            timestamp="2026-06-02T00:00:00Z",
        )
        a = lc.classify_alert(m_almost_liq)
        self.assertEqual(a.key, "MARGIN_HAZARD")
        self.assertEqual(a.channel, "sms")
        self.assertTrue(a.is_emergency)
        self.assertIn("MARGIN HAZARD", a.message)

    def test_critical_alert(self):
        m = lc.RiskMetrics(
            status="CRITICAL",
            current_btc_price=70000.0,
            volatility_index=85.0,
            liquidation_price=73500.0,
            distance_to_liq_percent=3.0,
            unrealized_pnl_percent=0.0,
            recommended_stop_percent=0.45,
            timestamp="2026-06-02T00:00:00Z",
        )
        a = lc.classify_alert(m)
        self.assertEqual(a.key, "CRITICAL")
        self.assertEqual(a.channel, "email")

    def test_elevated_alert(self):
        m = lc.RiskMetrics(
            status="ELEVATED",
            current_btc_price=70000.0,
            volatility_index=70.0,
            liquidation_price=73500.0,
            distance_to_liq_percent=4.0,
            unrealized_pnl_percent=0.0,
            recommended_stop_percent=1.0,
            timestamp="2026-06-02T00:00:00Z",
        )
        a = lc.classify_alert(m)
        self.assertEqual(a.key, "ELEVATED")
        self.assertEqual(a.channel, "email")

    def test_stable_alert(self):
        m = lc.RiskMetrics(
            status="STABLE",
            current_btc_price=70000.0,
            volatility_index=45.0,
            liquidation_price=73500.0,
            distance_to_liq_percent=5.0,
            unrealized_pnl_percent=0.0,
            recommended_stop_percent=2.0,
            timestamp="2026-06-02T00:00:00Z",
        )
        a = lc.classify_alert(m)
        self.assertEqual(a.key, "STABLE")
        self.assertEqual(a.channel, "log")


# -------------------------------------------------------------------------
# Position loading
# -------------------------------------------------------------------------


class TestPositionLoading(unittest.TestCase):
    def test_load_position(self):
        pos = lc.load_position()
        self.assertEqual(pos.entry_price, 70250.0)
        self.assertEqual(pos.leverage, 20.0)
        self.assertEqual(pos.position_type, "short")


if __name__ == "__main__":
    unittest.main(verbosity=2)
