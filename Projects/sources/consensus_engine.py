#!/usr/bin/env python3
"""
Consensus Engine
"""

def get_consensus(lines):
    if not lines:
        return None
    return sum(lines) / len(lines)
