#!/usr/bin/env python3
"""
TC NBA Live — Clean Production File v4
Scans all games with player prop odds and generates qualified TC picks.
API: SportsGameOdds — playerID field + bookOverUnder + bookOdds
"""
import sys
sys.path.insert(0, '/home/workspace')

from odds_fetcher.sportsgameodds_client import fetch_nba_events
from tc_model.rosters import TEAMS
from tc_model.tc_calculator import TC_WEIGHT, GAP_PTS, GAP_REB, GAP_AST, GAP_3PM, MIN_EDGE_PTS, MIN_EDGE_REB, MIN_EDGE_AST, MIN_EDGE_3PM

STAT_MAP = {"points": "pts", "rebounds": "reb", "assists": "ast", "threes": "3pm"}
FIELDS = {"pts": "pts", "reb": "reb", "ast": "ast", "3pm": "tpm"}
MIN_EDGE = {"pts": MIN_EDGE_PTS, "reb": MIN_EDGE_REB, "ast": MIN_EDGE_AST, "3pm": MIN_EDGE_3PM}
GAP = {"pts": GAP_PTS, "reb": GAP_REB, "ast": GAP_AST, "3pm": GAP_3PM}

def tc_calc(avg, stat, status):
    if status == "OUT": return 0.0
    return round(avg * TC_WEIGHT[stat] + GAP[stat], 1)

def kelly_size(bankroll, edge, odds=-110):
    if edge <= 0: return 0.0
    b = abs(odds) / 100
    p = min(0.72, 0.52 + min(edge, 10) * 0.02)
    k = (b * p - (1 - p)) / b if b else 0.0
    return round(max(0, bankroll * k * 0.5), 2)

# Build player lookup (keyed by last name lower)
PLAYER_LOOKUP = {}
for abbr, team in TEAMS.items():
    for p in team["players"]:
        PLAYER_LOOKUP[p.name.split()[-1].lower()] = (p, abbr)

if __name__ == "__main__":
    print("=" * 72)
    print("  TC NBA LIVE — Clean Production v4")
    print("=" * 72)

    data = fetch_nba_events(True)
    events = data.get("data", [])

    all_picks = []
    bankroll = 1000.0

    for event in events:
        teams = event.get("teams", {})
        home_name = teams.get("home", {}).get("name", "")
        away_name = teams.get("away", {}).get("name", "")

        name_map = {
            "Philadelphia 76ers": "PHI", "New York Knicks": "NYK",
            "Minnesota Timberwolves": "MIN", "San Antonio Spurs": "SA",
            "Cleveland Cavaliers": "CLE", "Detroit Pistons": "DET",
            "Los Angeles Lakers": "LAL", "Oklahoma City Thunder": "OKC",
        }
        home_abbr = name_map.get(home_name, "")
        away_abbr = name_map.get(away_name, "")

        # Build player map from event
        player_map = {}
        for pid, pinfo in event.get("players", {}).items():
            player_map[pid] = pinfo.get("name", "")

        game_picks = []
        for odd_id, odd in event.get("odds", {}).items():
            stat_id = odd.get("statID", "")
            if stat_id not in STAT_MAP:
                continue
            stat = STAT_MAP[stat_id]
            player_id = odd.get("playerID")
            if not player_id or player_id not in player_map:
                continue
            book_ou = odd.get("bookOverUnder")
            if not book_ou:
                continue
            try:
                line = float(book_ou)
            except:
                continue

            book_odds = odd.get("bookOdds", -110)
            try:
                odds = int(str(book_odds).replace("+", ""))
            except:
                odds = -110

            player_name = player_map[player_id]
            last = player_name.split()[-1].lower()
            if last not in PLAYER_LOOKUP:
                continue

            pobj, team_abbr = PLAYER_LOOKUP[last]
            avg = getattr(pobj, FIELDS[stat], 0)
            if stat == "3pm": avg = pobj.tpm
            if avg == 0: continue

            tc_val = tc_calc(avg, stat, pobj.status)
            edge = round(tc_val - line, 1)
            pick_dir = "OVER" if edge > 0 else "UNDER"
            qual = abs(edge) >= MIN_EDGE[stat]
            icon = "✅" if qual else "  "
            k = kelly_size(bankroll, edge, odds)
            conf = min(72, 52 + min(abs(edge), 10) * 2)
            flag = {"OUT": "🔴 OUT", "Q": "⚠️ Q", "QUESTIONABLE": "⚠️ Q"}.get(pobj.status, "")
            print(f"  {icon} {team_abbr:<4} {player_name:<22} {stat.upper():>4} | "
                  f"TC:{tc_val:>5.1f} | Mkt:{line:>5.1f} | E:{edge:>+5.1f} | "
                  f"{pick_dir:<5} | K:${k:>5.2f} | C:{conf:.0f}% {flag}")

            if qual:
                game_picks.append({
                    "player": player_name, "team": team_abbr, "stat": stat,
                    "tc": tc_val, "line": line, "edge": edge,
                    "pick": pick_dir, "kelly": k, "conf": conf, "odds": odds,
                    "game": f"{away_name} @ {home_name}",
                })

        all_picks.extend(game_picks)

    total_kelly = sum(p["kelly"] for p in all_picks)
    print(f"\n{'=' * 72}")
    print(f"  QUALIFIED: {len(all_picks)} picks | Bankroll: ${bankroll}")
    print(f"  TOTAL KELLY: ${total_kelly:.2f}")
    print(f"{'=' * 72}")

    if all_picks:
        print("\n  TOP PICKS BY EDGE:")
        for p in sorted(all_picks, key=lambda x: abs(x["edge"]), reverse=True)[:10]:
            print(f"  → {p['team']} {p['player']} {p['pick']} {p['line']} "
                  f"| TC:{p['tc']} | E:{p['edge']:+.1f} | K:${p['kelly']:.2f} | C:{p['conf']:.0f}%")