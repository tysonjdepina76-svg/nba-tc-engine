"""Unit tests for TC engine math."""
import pytest
from engine import compute_tc, hit_rate, edge_pct, projection_vs_line


class TestComputeTC:
    def test_basic_over(self):
        """Projection above line returns positive edge."""
        edge = compute_tc(projection=27.3, line=25.5, std_dev=4.2, direction="OVER")
        assert edge > 0

    def test_basic_under(self):
        """Projection below line returns positive edge."""
        edge = compute_tc(projection=22.1, line=25.5, std_dev=4.2, direction="UNDER")
        assert edge > 0

    def test_zero_edge_at_line(self):
        """Projection exactly at line returns zero edge."""
        edge = compute_tc(projection=25.5, line=25.5, std_dev=4.2, direction="OVER")
        assert abs(edge) < 0.01

    def test_higher_confidence_lower_std(self):
        """Lower std dev yields higher confidence for same edge."""
        e1 = compute_tc(projection=27.3, line=25.5, std_dev=4.2, direction="OVER")
        e2 = compute_tc(projection=27.3, line=25.5, std_dev=2.1, direction="OVER")
        assert e2 > e1

    def test_invalid_direction_raises(self):
        with pytest.raises(ValueError):
            compute_tc(projection=27.3, line=25.5, std_dev=4.2, direction="SIDEWAYS")

    def test_negative_std_dev_raises(self):
        with pytest.raises(ValueError):
            compute_tc(projection=27.3, line=25.5, std_dev=-1.0, direction="OVER")


class TestHitRate:
    def test_perfect_over_hit(self):
        """100% hit when every sample is over."""
        samples = [30, 28, 31, 29, 32]
        rate = hit_rate(samples, line=25.5, direction="OVER")
        assert rate == 1.0

    def test_perfect_under_hit(self):
        rate = hit_rate(samples=[10, 12, 8, 9, 11], line=15.0, direction="UNDER")
        assert rate == 1.0

    def test_zero_hit_rate(self):
        rate = hit_rate(samples=[10, 12, 8], line=25.5, direction="OVER")
        assert rate == 0.0

    def test_partial_hit_rate(self):
        samples = [26, 24, 27, 23, 28]
        rate = hit_rate(samples, line=25.5, direction="OVER")
        assert rate == 0.6

    def test_empty_samples(self):
        with pytest.raises(ValueError):
            hit_rate(samples=[], line=25.5, direction="OVER")


class TestEdgePct:
    def test_positive_edge_over(self):
        edge = edge_pct(projection=27.3, line=25.5, direction="OVER")
        assert abs(edge - 7.06) < 0.1

    def test_positive_edge_under(self):
        edge = edge_pct(projection=22.1, line=25.5, direction="UNDER")
        assert abs(edge - 13.33) < 0.1

    def test_zero_edge(self):
        edge = edge_pct(projection=25.5, line=25.5, direction="OVER")
        assert edge == 0.0


class TestProjectionVsLine:
    def test_strong_over_signal(self):
        signal = projection_vs_line(projection=30.0, line=25.5, std_dev=2.0)
        assert signal in ("STRONG_OVER", "OVER")

    def test_strong_under_signal(self):
        signal = projection_vs_line(projection=20.0, line=25.5, std_dev=2.0)
        assert signal in ("STRONG_UNDER", "UNDER")

    def test_neutral_signal(self):
        signal = projection_vs_line(projection=25.5, line=25.5, std_dev=4.0)
        assert signal in ("NEUTRAL", "PASS")
