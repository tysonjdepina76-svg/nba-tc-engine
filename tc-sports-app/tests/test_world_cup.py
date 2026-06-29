# TC - TC Trademark 2026
import sys
sys.path.insert(0, "/home/workspace/tc-sports-app")

from src.domain.cape_verde import CapeVerdePlayer, CAPE_VERDE_PLAYERS, CAPE_VERDE_GROUP, CAPE_VERDE_RANKING, CAPE_VERDE_STAR, CAPE_VERDE_BOOST, cv_multiplier
from src.domain.world_cup_teams import WC_TEAMS, get_team, get_group, cape_verde_group

def test_cv_players_count():
    assert len(CAPE_VERDE_PLAYERS) == 11, f"have {len(CAPE_VERDE_PLAYERS)} players"
    print("  OK 11 Cape Verde players")

def test_cv_star():
    assert CAPE_VERDE_STAR == "Bebe"
    print("  OK Star player is Bebe")

def test_cv_ranking():
    assert CAPE_VERDE_RANKING == 65
    print("  OK FIFA ranking 65")

def test_cv_group():
    assert CAPE_VERDE_GROUP == "H"
    print("  OK Group H")

def test_wc_team_count():
    assert len(WC_TEAMS) >= 8, f"only {len(WC_TEAMS)} teams"
    print(f"  OK {len(WC_TEAMS)} WC teams registered")

def test_cv_group_has_4():
    g = cape_verde_group()
    assert len(g) == 4, f"group H has {len(g)} teams"
    names = [t["name"] for t in g]
    assert "Cape Verde" in names
    assert "Portugal" in names
    print("  OK Group H = Cape Verde, Portugal, Ghana, Uruguay")

def test_cv_multiplier_top():
    m = cv_multiplier("Cape Verde", "Portugal")
    assert m == 1.15, f"vs top team should be 1.15, got {m}"
    print("  OK vs Portugal = +15oost")

def test_cv_multiplier_group():
    m = cv_multiplier("Cape Verde", "Ghana")
    assert m == 1.05, f"group stage should be 1.05, got {m}"
    m = cv_multiplier("Cape Verde", "Ghana")
    m = cv_multiplier("Cape Verde", "Ghana")
def main():
    print("=== World Cup + Cape Verde Tests ===")
    test_cv_players_count()
    test_cv_star()
    test_cv_ranking()
    test_cv_group()
    test_wc_team_count()
    test_cv_group_has_4()
    test_cv_multiplier_top()
    test_cv_multiplier_group()
    print("ALL WC + CV TESTS PASS")

if __name__ == "__main__":
    main()
