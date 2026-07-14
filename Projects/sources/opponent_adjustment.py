#!/usr/bin/env python3
"""
Opponent Adjustment
"""

def adjust(projection, opponent_rank):
    factor = 1 + ((32 - opponent_rank) / 32 - 0.5) * 0.4
    return projection * factor
