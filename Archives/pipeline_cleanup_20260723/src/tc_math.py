#!/usr/bin/env python3
"""TC Math — implied probability, vig removal, edge calculation."""
import math

def implied_prob_from_odds(odds):
    """American odds to implied probability."""
    if isinstance(odds, str):
        odds = int(odds)
    if odds > 0:
        return 100.0 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)

def remove_vig(prob):
    """Remove standard 4.55% vig from fair odds for -110/-110 market."""
    return prob / (prob + (1 - prob) * 1.1)

def edge_from_prob(true_prob, book_prob):
    """Calculate edge as difference between true and book probability."""
    return true_prob - book_prob

def kelly_fraction(edge, odds_decimal):
    """Kelly criterion: fraction of bankroll to wager."""
    if edge <= 0 or odds_decimal <= 1:
        return 0
    p = edge + (1.0 / odds_decimal)
    q = 1 - p
    b = odds_decimal - 1
    return max(0, (p * b - q) / b) if b > 0 else 0
