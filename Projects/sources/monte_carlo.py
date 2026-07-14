#!/usr/bin/env python3
"""
Monte Carlo
"""

import random

def monte_carlo(projection, std_dev, n_sims=10000):
    samples = [random.gauss(projection, std_dev) for _ in range(n_sims)]
    return sum(samples) / len(samples)
