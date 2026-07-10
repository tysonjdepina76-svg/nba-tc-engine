"""Test ALL 9 SportsDataIO NFL endpoints."""
import sys
import types
import importlib.util

# Stub src.domain.entities before any module loads
entities_stub = types.ModuleType("src.domain.entities")
class Player:
    def __init__(self, **kw): self.__dict__.update(kw)
class Game:
    def __init__(self, **kw): self.__dict__.update(kw)
class Projection:
    def __init__(self, **kw): self.__dict__.update(kw)
class Sport:
    def __init__(self, **kw): self.__dict__.update(kw)
entities_stub.Player = Player
entities_stub.Game = Game
entities_stub.Projection = Projection
entities_stub.Sport = Sport
sys.modules["src"] = types.ModuleType("src")
sys.modules["src.domain"] = types.ModuleType("src.domain")
sys.modules["src.domain.entities"] = entities_stub
sys.modules["src.adapters"] = types.ModuleType("src.adapters")
sys.modules["src.adapters.sportsdataio"] = types.ModuleType("src.adapters.sportsdataio")

# Load base
spec_base = importlib.util.spec_from_file_location("src.adapters.sportsdataio.base", "src/adapters/sportsdataio/base.py")
sdio_base = importlib.util.module_from_spec(spec_base)
sys.modules["src.adapters.sportsdataio.base"] = sdio_base
spec_base.loader.exec_module(sdio_base)

# Load nfl
spec_nfl = importlib.util.spec_from_file_location("src.adapters.sportsdataio.nfl", "src/adapters/sportsdataio/nfl.py")
sdio_nfl = importlib.util.module_from_spec(spec_nfl)
sys.modules["src.adapters.sportsdataio.nfl"] = sdio_nfl
spec_nfl.loader.exec_module(sdio_nfl)

NFLAdapter = sdio_nfl.NFLAdapter

print("=" * 60)
print("SportsDataIO NFL — All 9 Endpoints Test")
print("=" * 60)

try:
    adapter = NFLAdapter()
    print(f"Adapter sport: {adapter.sport}")
    print(f"Key ending: ...{adapter.api_key[-8:] if adapter.api_key else 'NONE'}\n")
except Exception as e:
    print(f"Init failed: {e}")
    sys.exit(1)

tests = [
    ("[1] Headshot (Mahomes, 2000)", "fetch_headshot", {"player_id": 2000}),
    ("[2] News by Team (KC, 12)", "fetch_news_by_team", {"team_id": 12}),
    ("[3] News by Player (2000)", "fetch_news_by_player", {"player_id": 2000}),
    ("[4] News by Date (2026-07-08)", "fetch_news_by_date", {"date": "2026-07-08"}),
    ("[5] Player News Notes (2000)", "fetch_player_news_notes", {"player_id": 2000}),
    ("[6] DFS Slates by Week (week 1)", "fetch_dfs_slates_by_week", {"week": 1, "season": 2026}),
    ("[7] DFS Slates by Date (2026-09-10)", "fetch_dfs_slates_by_date", {"date": "2026-09-10"}),
    ("[8] IDP ADP (2026)", "fetch_idp_adp", {"season": 2026}),
    ("[9] Fantasy Points by Week (week 1)", "fetch_fantasy_points_by_week", {"week": 1, "season": 2026}),
    ("[10] Fantasy ADP (2026)", "fetch_fantasy_adp", {"season": 2026}),
]

passed = 0
for label, method, kwargs in tests:
    print(f"--- {label} ---")
    try:
        result = getattr(adapter, method)(**kwargs)
        if isinstance(result, list):
            print(f"  OK: {len(result)} items")
            if result and isinstance(result[0], dict):
                first = result[0].get("Title") or result[0].get("title") or result[0].get("Name") or str(result[0])[:80]
                print(f"  First: {str(first)[:80]}")
        else:
            print(f"  OK: {str(result)[:120]}")
        passed += 1
    except Exception as e:
        print(f"  ERR: {type(e).__name__}: {str(e)[:160]}")

print(f"\n{'=' * 60}")
print(f"RESULT: {passed}/{len(tests)} endpoints returned data (others 401 = key needs SDIO subscription tier)")
print("=" * 60)
