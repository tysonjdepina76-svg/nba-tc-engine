#!/usr/bin/env python3
"""
TC Comprehensive Integration
- Live scrape final boxscores NBA/WNBA
- Run backtest with all parameters
- Include h2h/team history
- Scan all TC equation parameters
"""
import json
import sys
import requests
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import csv

# Import existing modules
sys.path.insert(0, "/home/workspace/Projects")
import tc_math

WORKSPACE = Path("/home/workspace")
DAILY_LOG = WORKSPACE / "Daily_Log"
DAILY_LOG.mkdir(exist_ok=True)

# ══════════════════════════════════════════════════════════════════
# PHASE 1: LIVE SCRAPE FINAL BOXSCORES (ESPN v2)
# ══════════════════════════════════════════════════════════════════

def scrape_espn_boxscores(sport, days_back=5):
    """Live scrape ESPN final boxscores for completed games"""
    league = "basketball/nba" if sport == "NBA" else "basketball/wnba"
    url = f"https://site.api.espn.com/apis/site/v2/sports/{league}/scoreboard"
    
    all_games = []
    
    for i in range(days_back):
        date = (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y%m%d")
        
        try:
            r = requests.get(url, params={"dates": date}, timeout=15)
            d = r.json()
            
            for ev in d.get("events", []):
                comp = ev.get("competitions", [{}])[0]
                state = comp.get("status", {}).get("type", {}).get("state", "")
                
                if state != "post":  # Only completed games
                    continue
                
                eid = ev["id"]
                home = next((c["team"]["abbreviation"] for c in comp.get("competitors", []) if c.get("homeAway")=="home"), "?")
                away = next((c["team"]["abbreviation"] for c in comp.get("competitors", []) if c.get("homeAway")=="away"), "?")
                
                # Get full boxscore
                r2 = requests.get(f"https://site.api.espn.com/apis/site/v2/sports/{league}/summary", 
                                 params={"event": eid}, timeout=15)
                summary = r2.json()
                
                # Extract player stats
                players = {}
                for grp in summary.get("boxscore", {}).get("players", []):
                    team = grp.get("team", {}).get("abbreviation", "?")
                    for stat_grp in grp.get("statistics", []):
                        keys = stat_grp.get("keys", [])
                        if "points" not in keys:
                            continue
                        
                        i_pts = keys.index("points")
                        i_reb = keys.index("rebounds") if "rebounds" in keys else -1
                        i_ast = keys.index("assists") if "assists" in keys else -1
                        
                        for ath in stat_grp.get("athletes", []):
                            name = ath.get("athlete", {}).get("displayName", "?")
                            stats = ath.get("stats", [])
                            
                            def to_int(x):
                                try: return int(x)
                                except: return 0
                            
                            players[name.lower()] = {
                                "name": name,
                                "team": team,
                                "pts": to_int(stats[i_pts]) if i_pts >= 0 and i_pts < len(stats) else 0,
                                "reb": to_int(stats[i_reb]) if i_reb >= 0 and i_reb < len(stats) else 0,
                                "ast": to_int(stats[i_ast]) if i_ast >= 0 and i_ast < len(stats) else 0
                            }
                
                all_games.append({
                    "date": date,
                    "game": f"{away}@{home}",
                    "sport": sport,
                    "event_id": eid,
                    "players": players,
                    "scraped_at": datetime.now(timezone.utc).isoformat()
                })
                
        except Exception as e:
            print(f"Error scraping {sport} {date}: {e}")
    
    return all_games

# ══════════════════════════════════════════════════════════════════
# PHASE 2: TC PARAMETERS SCAN
# ══════════════════════════════════════════════════════════════════

def scan_tc_parameters():
    """Scan all TC equation parameters"""
    
    print("\n" + "="*70)
    print("TC MATHEMATICAL EQUATION PARAMETERS")
    print("="*70)
    
    params = {
        "SPORT_PROFILES": {
            "NBA": tc_math.SPORT_PROFILE["NBA"],
            "WNBA": tc_math.SPORT_PROFILE["WNBA"]
        },
        "STAT_CONS": tc_math.STAT_CONS,
        "BAYES_ALPHA": tc_math.BAYES_ALPHA,
        "LEAGUE_PRIOR": tc_math.LEAGUE_PRIOR,
        "LINE_FACTOR": tc_math.LINE_FACTOR,
        "FORMULA": {
            "project_stat": "shrunk × CONS × status_factor × minutes_norm",
            "project_combo": "sum(raw × CONS × reb_ast_lift) × status_factor × minutes_norm",
            "bayesShrink": "(sample_mean × n_games + prior × alpha) / (n_games + alpha)",
            "line_from_tc": "floor(TC × 0.88)"
        }
    }
    
    print(json.dumps(params, indent=2))
    
    return params

# ══════════════════════════════════════════════════════════════════
# PHASE 3: BACKTEST WITH ALL FACTORS
# ══════════════════════════════════════════════════════════════════

def run_comprehensive_backtest(games):
    """Run TC backtest considering all game situations"""
    
    results = []
    
    for game_data in games:
        sport = game_data["sport"]
        game = game_data["game"]
        players = game_data["players"]
        
        # Import projections if exist
        proj_file = None
        for p in DAILY_LOG.glob(f"*/proj_{sport}*{game.replace('@', '_at_')}*.json"):
            proj_file = p
            break
        
        if not proj_file:
            continue
        
        proj = json.loads(proj_file.read_text())
        
        # Match projected vs actual
        for side in ("away", "home"):
            for role in ("starters", "bench"):
                for p in proj.get(side, {}).get(role, {}).get("players", []):
                    name = p.get("name", "").lower()
                    if not name or name not in players:
                        continue
                    
                    actual = players[name]
                    
                    # Grade each stat
                    for stat in ["pts", "reb", "ast"]:
                        raw = p.get(stat, 0) or 0
                        actual_val = actual.get(stat, 0)
                        
                        # Compute TC projection
                        tc_proj = tc_math.project_stat(stat, raw, "ACTIVE", sport)
                        
                        # Grade
                        hit = actual_val > tc_proj * 0.99
                        
                        results.append({
                            "sport": sport,
                            "game": game,
                            "player": name,
                            "team": actual.get("team"),
                            "stat": stat,
                            "raw_avg": raw,
                            "tc_proj": round(tc_proj, 2),
                            "actual": actual_val,
                            "hit": hit,
                            "edge": round(actual_val - tc_proj, 2)
                        })
    
    return results

# ══════════════════════════════════════════════════════════════════
# PHASE 4: H2H AND TEAM HISTORY
# ══════════════════════════════════════════════════════════════════

def load_h2h_history(team_abbr):
    """Load head-to-head history (stub for future enhancement)"""
    # TODO: Implement h2h loading from saved matchup data
    return {
        "avg_pts": 0,
        "avg_reb": 0,
        "avg_ast": 0,
        "games": 0
    }

def load_team_history(team_abbr, days=30):
    """Load team performance history"""
    # TODO: Scan Daily_Log for team's recent games
    return {
        "avg_pts": 0,
        "avg_reb": 0,
        "avg_ast": 0,
        "wins": 0,
        "losses": 0
    }

# ══════════════════════════════════════════════════════════════════
# MAIN EXECUTION
# ══════════════════════════════════════════════════════════════════

def main():
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print("\n" + "="*70)
    print("COMPREHENSIVE TC BACKTEST")
    print("="*70)
    
    # Phase 1: Scrape
    print("\nPhase 1: Live scrape final boxscores...")
    wnba_games = scrape_espn_boxscores("WNBA", days_back=5)
    nba_games = scrape_espn_boxscores("NBA", days_back=5)
    
    print(f"  WNBA games: {len(wnba_games)}")
    print(f"  NBA games: {len(nba_games)}")
    
    # Save
    all_games = wnba_games + nba_games
    out_file = DAILY_LOG / f"final_boxscores_{stamp}.json"
    out_file.write_text(json.dumps(all_games, indent=2))
    print(f"  Saved to {out_file}")
    
    # Phase 2: Scan parameters
    params = scan_tc_parameters()
    
    # Phase 3: Backtest
    print("\nPhase 3: Run comprehensive backtest...")
    results = run_comprehensive_backtest(all_games)
    
    if results:
        # Save results
        results_file = WORKSPACE / "Reports" / f"comprehensive_backtest_{stamp}.csv"
        results_file.parent.mkdir(exist_ok=True)
        
        with open(results_file, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
            w.writeheader()
            w.writerows(results)
        
        # Summary stats
        from collections import Counter
        by_sport = Counter(r["sport"] for r in results)
        hits = sum(1 for r in results if r["hit"])
        total = len(results)
        
        print(f"\n  Total picks: {total}")
        print(f"  Hits: {hits} ({round(100*hits/total, 1)}%)")
        print(f"  By sport: {dict(by_sport)}")
        print(f"  Saved to {results_file}")
    else:
        print("  No results (no matching projections)")
    
    # Phase 4: H2H/Team History (stub)
    print("\nPhase 4: H2H and team history")
    print("  (Future enhancement - need more historical data)")
    
    print("\n" + "="*70)
    print("COMPLETE")
    print("="*70)

if __name__ == "__main__":
    main()
