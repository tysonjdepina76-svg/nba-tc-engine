#!/usr/bin/env python3
"""
over_discounts.py - Stat-specific discount factors for MLB OVER picks.
Derived from 30-day backtest bias analysis.
"""

OVER_DISCOUNT = {
    'HR': 0.88,
    'SB': 0.85,
    'RBI': 0.92,
    'R': 0.94,
    'H': 0.96,
    'K': 1.02,
}

def apply_over_discount(stat: str, projection: float) -> float:
    """Apply discount factor for MLB OVER projections."""
    return projection * OVER_DISCOUNT.get(stat, 1.0)
