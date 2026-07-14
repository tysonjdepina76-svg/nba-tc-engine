#!/usr/bin/env python3
"""
TC Math Hybrid — v1-v7 complete
"""

class TCHybridMath:
    def __init__(self):
        self.version = "7.0.0"
        self.cons = 0.85

    def get_projection(self, player_stats, sport, stat):
        if not player_stats:
            return 0.0
        avg = sum(player_stats) / len(player_stats)
        return avg * self.cons
