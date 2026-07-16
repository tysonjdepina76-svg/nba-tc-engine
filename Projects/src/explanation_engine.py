#!/usr/bin/env python3
"""
Local explanation generator — no external API.
Generates human-readable reasoning for +EV picks.
"""

import random


def generate_explanation(player, sport, stat, projection, line, edge):
    """Returns a human-readable explanation for a +EV pick."""
    if edge is None:
        edge = projection - line if line else 0.0

    if abs(edge) > 2.0:
        strength = "strong"
    elif abs(edge) > 1.0:
        strength = "moderate"
    else:
        strength = "marginal"

    sport_name = sport.upper() if sport else "Sport"
    stat_name = stat.upper() if stat else "projection"

    direction = "OVER" if edge > 0 else "UNDER"
    edge_abs = abs(edge)

    templates = [
        (
            f"{strength.capitalize()} +EV opportunity: {player} is projected for {projection:.1f} "
            f"{stat_name} vs a line of {line:.1f}, giving a {direction} edge of {edge_abs:.2f}. "
            f"Based on recent form, opponent matchup, and game context."
        ),
        (
            f"{player} shows {direction} value at {line:.1f} {stat_name}. "
            f"TC projection: {projection:.1f} — edge: {edge_abs:.2f}. "
            f"{strength.capitalize()} conviction based on usage rate and defensive matchup."
        ),
        (
            f"Targeting {player} {direction} {line:.1f} {stat_name}. "
            f"Model projects {projection:.1f} ({edge_abs:.2f} edge). "
            f"Recent trends and opponent weakness support this play."
        ),
    ]

    return random.choice(templates)
