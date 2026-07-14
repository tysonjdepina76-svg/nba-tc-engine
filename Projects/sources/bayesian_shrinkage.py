#!/usr/bin/env python3
"""
Bayesian Shrinkage
"""

def shrink(player_avg, league_avg, n_games, alpha=5):
    return (league_avg * alpha + player_avg * n_games) / (alpha + n_games)
