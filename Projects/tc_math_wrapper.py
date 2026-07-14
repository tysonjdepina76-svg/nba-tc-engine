#!/usr/bin/env python3
"""
tc_math_wrapper.py — Compatibility shim for TC math engine.

Re-exports the live hybrid engine so downstream stubs that import
`from tc_math_wrapper import get_math_engine` work without changes.
"""

from tc_math_hybrid import (
    over_under_signal_v1,
    over_under_signal_v2,
    get_correction_factor,
    apply_correction,
    hybrid_projection,
    get_mock_market_line,
    determine_pick,
)


def get_math_engine():
    """Return a namespace object exposing the live hybrid math functions."""

    class _Engine:
        pass

    engine = _Engine()
    engine.over_under_signal_v1 = over_under_signal_v1
    engine.over_under_signal_v2 = over_under_signal_v2
    engine.get_correction_factor = get_correction_factor
    engine.apply_correction = apply_correction
    engine.hybrid_projection = hybrid_projection
    engine.get_mock_market_line = get_mock_market_line
    engine.determine_pick = determine_pick
    return engine
