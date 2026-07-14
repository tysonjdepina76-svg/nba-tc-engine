"""
LEGACY: pasted 2026-07-13 from an older tc-sports-app structure.
NOT integrated — replaced by /home/workspace/Projects/src/adapters/odds_api.py
(extending CacheAdapter with live /v4/sports, /v4/events, /v4/odds, and
historical /v4/historical endpoints). The legacy version's reference to
`src.adapters.cache_adapter` and `pandas`/`numpy` in an adapter layer was
duplicative of the current CacheAdapter implementation.

Re-extractable bits:
- Caching pattern (CacheAdapter) — already in current src/adapters/cache.py
- Random walk for synthetic baselines — replaced by tc_math_hybrid.py
- Bookmaker key mapping — mirrored in current odds_api.py
"""
