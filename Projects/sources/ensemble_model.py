#!/usr/bin/env python3
"""
Ensemble Model
"""

def ensemble(predictions, weights=None):
    if not predictions:
        return 0
    if not weights:
        weights = [1/len(predictions)] * len(predictions)
    return sum(p * w for p, w in zip(predictions, weights))
