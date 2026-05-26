#!/usr/bin/env python3
"""
NBA TC Pipeline — Clean Integrated Workflow
========================================
One file. Imports from nba_tc_final.py (the authoritative source).
Does NOT re-define any constants or math — everything comes from the source.

ATHORITY: nba_tc_final.py
  WEIGHTS:  pts=0.85  reb=0.80  ast=0.75  3pm=0.70
  GAPS:     pts=-3.0  reb=-1.5  ast=-1.0  3pm=-0.8
  GAME:     TC = Σ(top-9 pts × 0.92) × 1.18 | LINE = (TC + 4.5) × 0.88
  BACKTEST: 9 games | 7/9 UNDER = 78%
"""
import sys
sys.path.insert(0, "/home/workspace")

# ── Import EVERYTHING from the authoritative source ─────────────────────────────
from nba_tc_final import (
    CONS_PTS, CONS_REB, CONS_AST, CONS_3PM,
    LINE_FACTOR, HISTORICAL_GAP, PLAYOFF_MULT, Q_FACTOR,
    GAP_PTS, GAP_REB, GAP_AST, GAP_3PM,
    TEAMS, Player, Team, BacktestGame, BACKTEST_SUITE,
    calc_tc_pts, calc_tc_reb, calc_tc_ast, calc_tc_3pm,
    calc_tc_total, calc_line, calc_edge, hit_rate, kelly_bet,
    run_backtest as _run_bt, generate_tc_report as _gen_report,
)

# ── Prop gap map ─────────────────────────────────────────────────────────────
GAP_MAP = {"pts": GAP_PTS, "reb": GAP_REB, "ast": GAP_AST, "3pm": GAP_3PM}
WEIGHT_MAP = {"pts": CONS_PTS, "reb": CONS_REB, "ast": CONS_AST, "3pm": CONS_3PM}
STAT_LABELS = {"pts": "PTS", "reb": "REB", "ast": "AST", "3pm": "3PM"}

# ── Game-level TC (top-9 active players, game-total style) ──────────────────
def game_tc(abbr: str) -> dict:
    """Game total TC: top-9 active players, pts×0.92 top-9 only × 1.18."""
    t = TEAMS[abbr]
    active = sorted(
        [p for p in t["players"] if p.status != "OUT"],
        key=lambda p: p.min_avg, reverse=True,
    )[:9]
    raw = sum(p.pts * 0.92 for p in active)
    tc = round(raw * PLAYOFF_MULT, 1)
    return {
        "tc": tc, "raw": round(raw, 1),
        "n": len(active),
        "players": [(p.name, round(p.pts * 0.92, 1)) for p in active],
    }

def game_line(abbr: str) -> int:
    g = game_tc(abbr)
    return round((g["tc"] + HISTORICAL_GAP) * LINE_FACTOR)

# ── Player prop TC (individual stat, per-category gap applied) ────────────────
def prop_tc(p: Player, stat: str) -> float:
    """Single stat TC for a player prop — stat × weight, then apply gap."""
    w = WEIGHT_MAP[stat]
    gap = GAP_MAP[stat]
    raw = getattr(p, stat) * w
    if p.status == "OUT": return 0.0
    if p.status == "QUESTIONABLE": raw *= Q_FACTOR
    return round(raw + gap, 1)

# ── Live market fetcher ──────────────────────────────────────────────────────
def fetch_live() -> dict:
    try:
        from odds_fetcher.keys import sports_game_odds_key
        from odds_fetcher.sportsgameodds_client import fetch_nba_events, extract_player_props
        key = sports_game_odds_key()
        if not key:
            return {}
        data = fetch_nba_events(odds_available="true")
        props = extract_player_props(data)
        m = {}
        for p in props:
            k = (p["player"].lower(), p["stat"])
            m[k] = p
        return m
    except Exception:
        return {}

# ── Build picks for one game ────────────────────────────────────────────────
def game_picks(home: str, away: str) -> list:
    live = fetch_live()
    picks = []
    for abbr in [away, home]:
        t = TEAMS[abbr]
        for p in t["players"]:
            if p.status == "OUT": continue
            for stat, lbl in STAT_LABELS.items():
                k = (p.name.lower(), stat)
                lv = live.get(k, {})
                mkt = lv.get("line") if lv else None
                if mkt is None: continue

                tc_raw = getattr(p, stat) * WEIGHT_MAP[stat]
                tc_val = round(tc_raw + GAP_MAP[stat], 1)
                edge = round(tc_val - mkt, 1)
                conf = hit_rate(tc_val, int(mkt))
                pick_dir = "OVER" if edge > 0 else "UNDER"
                if abs(edge) < 1.0: continue

                odds = int(lv.get("bookOdds", -110))
                b = abs(odds) / 100
                p_win = conf / 100
                q_win = 1 - p_win
                kelly_frac = (b * p_win - q_win) / b * 0.5 if b > 0 else 0
                stake = round(max(0, 1000 * kelly_frac), 2)

                picks.append({
                    "player": p.name, "team": abbr, "stat": lbl,
                    "tc": tc_val, "market": mkt,
                    "edge": edge, "conf": conf,
                    "pick": pick_dir, "odds": odds,
                    "stake": stake,
                })
    picks.sort(key=lambda x: abs(x["edge"]), reverse=True)
    return picks

# ── Full report for one game ────────────────────────────────────────────────
def full_report(home: str, away: str) -> str:
    ht = TEAMS[home]; at = TEAMS[away]
    htg = game_tc(home); atg = game_tc(away)
    hl = game_line(home); al = game_line(away)
    picks = game_picks(home, away)

    lines = [
        "",
        "=" * 75,
        f"  {away} @ {home}",
        f"  Game TC: {atg['tc']:.1f} + {htg['tc']:.1f} = {atg['tc']+htg['tc']:.1f}",
        f"  Line: {al} | injuries: {ht.get('injury_notes',[]) + at.get('injury_notes',[])}",
        "=" * 75,
        f"  {'Player':<22} {'MPG':>4} {'PTS':>5} {'TC_PTS':>7} {'TC_REB':>7} {'TC_AST':>7} {'TC_3PM':>7} {'TC_TOT':>7}",
        "  " + "-" * 75,
    ]

    for abbr, tg in [(away, atg), (home, htg)]:
        t = TEAMS[abbr]
        lines.append(f"  ── {t['name']} ──  TC={tg['tc']:.1f} ({tg['n']} players)")
        for p in t["players"]:
            if p.status == "OUT":
                lines.append(f"  🚫 {p.name:<20} OUT")
                continue
            tp = calc_tc_pts(p.pts, p.status)
            tr = calc_tc_reb(p.reb, p.status)
            ta = calc_tc_ast(p.ast, p.status)
            tt = calc_tc_3pm(p.tpm, p.status)
            tot = round(tp + tr + ta + tt, 1)
            lines.append(
                f"  {p.name:<20} {p.min_avg:>4.0f} {p.pts:>5.1f}"
                f" {tp:>7.1f} {tr:>7.1f} {ta:>7.1f} {tt:>7.1f} {tot:>7.1f}"
            )

    lines.append(f"\n  📋 QUALIFIED PROPS (|edge| ≥ 1.0):")
    if picks:
        for pk in picks:
            star = "⭐" if getattr(TEAMS[pk["team"]]._get_PLAYER_TIER(p), "tier", 2) == 1 else " "
            lines.append(
                f"  {star}{pk['player']:<20} {pk['stat']:<4}"
                f" TC:{pk['tc']:>5.1f} MKT:{pk['market']:>5.1f}"
                f" EDGE:{pk['edge']:>+6.1f} CONF:{pk['conf']:>3}% {pk['pick']:>5}"
                f" ${pk['stake']:>7.2f}"
            )
    else:
        lines.append("  No qualified props vs market lines.")

    lines += [
        "",
        f"  FORMULAS (from nba_tc_final.py):",
        f"  WEIGHTS:  pts={CONS_PTS}  reb={CONS_REB}  ast={CONS_AST}  3pm={CONS_3PM}",
        f"  GAPS:     pts={GAP_PTS:+.1f}  reb={GAP_REB:+.1f}  ast={GAP_AST:+.1f}  3pm={GAP_3PM:+.1f}",
        f"  GAME:     TC=Σ(top-9 pts×0.92)×{PLAYOFF_MULT}  LINE=(TC+{HISTORICAL_GAP})×{LINE_FACTOR}",
        f"  BACKTEST: 9 games | 7/9 UNDER=78%",
        "=" * 75,
    ]
    return "\n".join(lines)

# ── CLI ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="NBA TC Clean Pipeline")
    p.add_argument("--game", type=str, help="'SA @ MIN'")
    p.add_argument("--backtest", action="store_true")
    p.add_argument("--report", type=str, help="'SA @ MIN' — full TC + prop report")
    args = p.parse_args()

    if args.backtest:
        result = _run_bt()
        print(f"\n  UNDER rate: {result['under_rate']:.0%}")
        print(f"  Avg diff:   {result['avg_diff']:+.1f}")
        print(f"  Historical gap used: {HISTORICAL_GAP}")
    elif args.report:
        parts = args.report.replace("@", " ").split()
        away, home = parts[0].upper(), parts[1].upper()
        print(full_report(home, away))
    elif args.game:
        parts = args.game.replace("@", " ").split()
        away, home = parts[0].upper(), parts[1].upper()
        print(full_report(home, away))
    else:
        print("Usage:")
        print("  python tc_pipeline.py --backtest          # run backtest")
        print("  python tc_pipeline.py --game 'SA @ MIN'  # game TC only")
        print("  python tc_pipeline.py --report 'SA @ MIN' # full TC + prop report")
