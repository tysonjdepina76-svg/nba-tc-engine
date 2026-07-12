"""Append shrink_projection + is_sane_edge to tc_math.py"""
import re

path = "/home/workspace/Projects/tc_math.py"
with open(path) as f:
    code = f.read()

helpers = '''

def is_sane_edge(tc_val: float, line_val: float, max_ratio: float = 2.5) -> bool:
    """Reject edge if TC is wildly off market line (>max_ratio or 0)."""
    if line_val is None or line_val <= 0:
        return True  # No market line; allow self-edge
    if tc_val is None or tc_val <= 0:
        return False
    ratio = max(tc_val, line_val) / min(tc_val, line_val)
    return ratio <= max_ratio


def shrink_projection(tc_val: float, line_val: float, sample: int = 1, k: int = 20) -> float:
    """Bayesian-shrink TC projection toward market line based on sample size.
    Higher sample = trust TC more; low sample = regress toward line.
    """
    if not tc_val or not line_val or sample is None or sample <= 0:
        return tc_val
    weight = sample / (sample + k)
    return weight * tc_val + (1 - weight) * line_val
'''

if "def is_sane_edge" not in code:
    with open(path, "a") as f:
        f.write(helpers)
    print("Added shrink_projection + is_sane_edge")
else:
    print("Already present")
