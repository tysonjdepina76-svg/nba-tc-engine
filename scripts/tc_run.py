#!/usr/bin/env python3
"""
TC NBA Pipeline Runner — Full workflow execution
Usage: python tc_run.py
"""
import sys; sys.path.insert(0,"/home/workspace")

from odds_fetcher.sportsgameodds_client import fetch_nba_events, extract_player_props
from nba_tc_final import OKC, LAL
from tc_model.tc_calculator import kelly_bet
import json, os

# ── TC CONSTANTS ─────────────────────────────────────────────────────────────────
# Player prop weights (per-stat, not team-total weights)
CONS_PLAYER = {"pts": 0.85, "reb": 0.80, "ast": 0.75, "3pm": 0.70}
GAP         = {"pts": -3.0, "reb": -1.5, "ast": -1.0, "3pm": -0.8}   # empirical gaps (TC - market line)
MIN_EDGE    = {"pts": 2.5,  "reb": 1.0,  "ast": 0.8,  "3pm": 0.5}     # qualify threshold
PLAYOFF_MULT = 1.18
BANKROLL    = 1000.0
KELLY_FRAC  = 0.50

TEAM_MAP = {"OKLAHOMA_CITY_THUNDER_NBA": OKC, "LOS_ANGELES_LAKERS_NBA": LAL}

def get_tc(name, stat, team_obj):
    """Compute TC for a player given stat. Returns (tc_raw, tc_estimate)."""
    for p in team_obj.players:
        if p.name == name:
            status = getattr(p, "status", "ACTIVE")
            if status == "OUT": return 0.0, 0.0
            q = 0.55 if status == "QUESTIONABLE" else 1.0
            val = getattr(p, stat, 0.0)
            raw = round(val * CONS_PLAYER[stat] * q, 1)
            est = round(raw + GAP.get(stat, 0.0), 1)
            return raw, est
    return None, None

def run_game(home_abbr, away_abbr, market_total=214.5):
    """Run full TC pipeline for a game. Returns picks + report dict."""
    # Resolve teams
    team_objs = {"OKC": OKC, "LAL": LAL}
    home = team_objs.get(home_abbr.upper())
    away = team_objs.get(away_abbr.upper())
    if not home or not away:
        return {"error": f"Unknown team: {home_abbr} or {away_abbr}"}

    # Fetch live market data
    data = fetch_nba_events(odds_available=True)
    props = extract_player_props(data)
    if not props:
        return {"error": "No props found from API"}

    # Deduplicate (best edge per player/stat/line across books)
    seen = {}
    for prop in props:
        tid = prop.get("teamID", "")
        if tid not in TEAM_MAP: continue
        name = prop["player"]; stat = prop["stat"]
        line = prop["line"]; raw_odds = prop.get("bookOdds", "-110")
        try: mkt_odds = int(str(raw_odds).replace("+", ""))
        except: mkt_odds = -110
        tc_raw, tc_est = get_tc(name, stat, TEAM_MAP[tid])
        if tc_raw is None: continue
        edge = round(tc_raw - line, 1)
        key = (name, stat, line)
        if key not in seen or abs(edge) > abs(seen[key]["edge"]):
            seen[key] = {
                "edge": edge, "tc_raw": tc_raw, "tc_est": tc_est,
                "odds": raw_odds, "mkt_odds": mkt_odds,
                "qual": abs(edge) >= MIN_EDGE.get(stat, 1.0)
            }

    picks = []
    for (name, stat, line), info in seen.items():
        abbr = "OKC" if any(p.name == name for p in OKC.players) else "LAL"
        edge = info["edge"]; mkt_odds = info["mkt_odds"]; qual = info["qual"]
        kelly = kelly_bet(BANKROLL, abs(edge), mkt_odds, KELLY_FRAC) if qual else 0.0
        picks.append({
            "player": name, "team": abbr, "stat": stat,
            "tc_raw": info["tc_raw"], "tc_est": info["tc_est"],
            "market_line": line, "edge": edge,
            "odds": info["odds"], "mkt_odds": mkt_odds,
            "kelly": kelly,
            "pick": "OVER" if edge > 0 else "UNDER",
            "qual": qual
        })

    # Sort
    sorted_picks = sorted(picks, key=lambda x: x["kelly"], reverse=True)
    qualified = [p for p in picks if p["kelly"] > 0]
    best = qualified[:6]

    # Parlay calc
    stake = 10.0; total_dec = 1.0
    for p in best:
        b = abs(p["mkt_odds"]) / 100 if p["mkt_odds"] > 0 else 100 / abs(p["mkt_odds"])
        dec = (1 + b) if p["mkt_odds"] < 0 else (1 + 100 / abs(p["mkt_odds"]))
        total_dec *= dec

    payout = round(total_dec * stake, 2)
    net = round(payout - stake * len(best), 2)

    # Game total
    raw_totals = {}
    for abbr, team in [("OKC", OKC), ("LAL", LAL)]:
        g = {s: 0.0 for s in CONS_PLAYER}
        for p in team.players:
            status = getattr(p, "status", "ACTIVE")
            q = 0.55 if status == "QUESTIONABLE" else 1.0
            for s, w in CONS_PLAYER.items():
                g[s] += getattr(p, s, 0.0) * w * q
        raw_totals[abbr] = sum(g.values())

    return {
        "home": home_abbr.upper(), "away": away_abbr.upper(),
        "game_tc": {"OKC": round(raw_totals["OKC"] * PLAYOFF_MULT),
                    "LAL": round(raw_totals["LAL"] * PLAYOFF_MULT)},
        "market_total": market_total,
        "all_picks": picks,
        "qualified_picks": qualified,
        "top_parlay": best,
        "total_decimal": round(total_dec, 3),
        "payout": payout,
        "net": net,
        "tc_weights": CONS_PLAYER,
        "gaps": GAP,
        "playoff_mult": PLAYOFF_MULT
    }

def print_report(r):
    abbr_h = r["home"]; abbr_a = r["away"]
    print(f"\n{'='*88}")
    print(f"  🏀 TC NBA PIPELINE — {abbr_a} @ {abbr_h}")
    print(f"  Source: SportsGameOdds API | TC: pts×0.85 | reb×0.80 | ast×0.75 | 3pm×0.70")
    print(f"  Gaps: pts=-3.0 | reb=-1.5 | ast=-1.0 | 3pm=-0.8 | Playoff ×1.18")
    print(f"  Market Total: {r['market_total']} | Game TC: {abbr_a}={r['game_tc'][abbr_a]} | {abbr_h}={r['game_tc'][abbr_h]}")
    print(f"{'='*88}")

    q = r["qualified_picks"]
    print(f"\n  QUALIFIED PICKS: {len(q)} (U:{sum(1 for p in q if p['pick']=='UNDER')} | O:{sum(1 for p in q if p['pick']=='OVER')})")
    print(f"  {'Player':<22} {'T':<4} {'St':<4} {'Ln':>5} {'Odds':>6} {'TC':>5} {'EstLn':>6} {'Edge':>7} {'Kelly':>7} {'Pick':<6}")
    print(f"  {'-'*88}")
    for p in sorted(q, key=lambda x: x["kelly"], reverse=True):
        print(f"  {p['player']:<22} {p['team']:<4} {p['stat']:<4} {p['market_line']:>5} {p['odds']:>6} {p['tc_raw']:>5.1f} {p['tc_est']:>6.1f} {p['edge']:>+7.1f} {p['kelly']:>7.2f} {p['pick']:<6}")

    best = r["top_parlay"]
    print(f"\n  TOP PARLAY — {len(best)} LEGS")
    print(f"  {'-'*88}")
    for i, p in enumerate(best, 1):
        b = abs(p["mkt_odds"]) / 100 if p["mkt_odds"] > 0 else 100 / abs(p["mkt_odds"])
        dec = round((1 + b) if p["mkt_odds"] < 0 else (1 + 100 / abs(p["mkt_odds"])), 3)
        print(f"  {i}. {p['player']} {p['pick']} {p['market_line']} | {p['team']} {p['stat'].upper()}")
        print(f"     TC={p['tc_raw']:.1f} | EstLn={p['tc_est']:.1f} | Edge={p['edge']:+.1f} | Odds={p['odds']} | Kelly=${p['kelly']:.2f}")

    print(f"\n  Stake: ${10*len(best):.2f} | Dec: {r['total_decimal']}x | Payout: ${r['payout']:.2f} | Net: ${r['net']:.2f}")
    print(f"{'='*88}\n")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--game", default="OKC @ LAL")
    args = parser.parse_args()

    parts = args.game.replace("@", " ").split()
    away, home = parts[0].upper(), parts[1].upper()
    result = run_game(home, away)
    if "error" in result:
        print(f"❌ {result['error']}")
    else:
        print_report(result)
        with open(f"/home/workspace/scrapes/{away}_vs_{home}_live.json", "w") as f:
            json.dump(result, f, indent=2, default=str)
        print(f"  ✅ Saved: /home/workspace/scrapes/{away}_vs_{home}_live.json")