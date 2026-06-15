"""
NBA TC ENGINE — BLOWOUT + GARBAGE TIME UPGRADE v2
===============================================
Key data from CLE@NYK 3-game series (ESPN summary API):
  G1: CLOSE  | margin=11 | CLE starters=35.5min, bench=18.6min
  G2: BLOWOUT| margin=16 | CLE starters=31.6min, bench=9.1min  (-9.5 min bench)
  G3: CLOSE  | margin=13 | CLE starters=37.6min, bench=11.5min

Blowout adjustments:
  Starters: -4.0 min in blowout → ~8% production loss
  Bench:    -9.5 min in blowout → ~51% production loss
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import json, argparse

CONS_PTS    = 0.85
CONS_REB    = 0.12
CONS_AST    = 0.10
CONS_3PM    = 0.08
LINE_FACTOR = 0.88
Q_FACTOR    = 0.55
OUT_FACTOR  = 0.0
MIN_EDGE    = 1.0

# Blowout tuning from CLE@NYK real series data
BLOWOUT_MARGIN           = 15
STARTER_BLOWOUT_PENALTY  = 4.0
BENCH_BLOWOUT_PENALTY    = 9.5
BENCH_BLOWOUT_FACTOR     = 0.49

@dataclass
class Player:
    name:   str
    pos:     str
    ht:      str
    pts:    float
    reb:    float
    ast:    float
    tpm:    float
    stl:    float = 0.3
    blk:    float = 0.3
    status: str   = "ACTIVE"

    def tc(self, stat: str) -> float:
        if self.status == "OUT": return 0.0
        factor = Q_FACTOR if self.status == "QUESTIONABLE" else 1.0
        return getattr(self, stat, 0.0) * factor

    def tc_pts(self) -> float: return self.tc("pts") * CONS_PTS
    def tc_reb(self) -> float: return self.tc("reb") * CONS_REB
    def tc_ast(self) -> float: return self.tc("ast") * CONS_AST
    def tc_3pm(self) -> float: return self.tc("tpm") * CONS_3PM
    def tc_stl(self) -> float: return self.tc("stl") * CONS_PTS
    def tc_blk(self) -> float: return self.tc("blk") * CONS_PTS

    def line(self, stat: str) -> float:
        method = "tc_3pm" if stat == "tpm" else f"tc_{stat}"
        tc = getattr(self, method)()
        if stat == "tpm":
            return tc
        return round(tc * LINE_FACTOR)

    @property
    def edge_pts(self) -> float:
        return round(self.tc_pts() - self.line("pts"), 1)

@dataclass
class Team:
    abbr:         str
    name:         str
    players:      List[Player]
    injury_notes: List[str] = field(default_factory=list)

    def starters(self) -> List[Player]:
        active = [p for p in self.players if p.status != "OUT"]
        return active[:5]

    def bench(self) -> List[Player]:
        active = [p for p in self.players if p.status != "OUT"]
        return active[5:]

    def total(self, stat: str) -> float:
        return sum(getattr(p, f"tc_{stat}")() for p in self.players if p.status != "OUT")


def calc_blowout_adjustment(team: Team, margin: float, is_blowout: bool) -> Dict[str, Dict[str, float]]:
    """
    Returns {player_name: {stat: negative_adjustment}} for blowout games.
    Bench players are hit hardest: -9.5 min AND 49% factor on top.
    """
    adjustments = {}
    if not is_blowout:
        return adjustments

    for p in team.starters():
        ppm = p.pts / 48.0
        adjustments[p.name] = {
            "pts": -(ppm * STARTER_BLOWOUT_PENALTY),
            "reb": -((p.reb / 48.0) * STARTER_BLOWOUT_PENALTY),
            "ast": -((p.ast / 48.0) * STARTER_BLOWOUT_PENALTY),
            "tpm": -((p.tpm / 48.0) * STARTER_BLOWOUT_PENALTY),
        }

    for p in team.bench():
        ppm = p.pts / 48.0
        # Lost bench min + extra 49% factor (they barely play even in close games)
        total_penalty = BENCH_BLOWOUT_PENALTY * (1 + BENCH_BLOWOUT_FACTOR)
        adjustments[p.name] = {
            "pts": -(ppm * total_penalty),
            "reb": -((p.reb / 48.0) * total_penalty),
            "ast": -((p.ast / 48.0) * total_penalty),
            "tpm": -((p.tpm / 48.0) * total_penalty),
        }
    return adjustments


def apply_tc_adjustments(rows: List[dict], adjustments: Dict[str, Dict[str, float]]) -> List[dict]:
    """Subtract blowout losses from each player's TC."""
    new_rows = []
    for r in rows:
        name = r["name"]
        if name in adjustments:
            r = {**r}
            for stat in ["pts", "reb", "ast", "3pm"]:
                key = f"tc_{stat}"
                adj_key = "tpm" if stat == "3pm" else stat
                if key in r and adj_key in adjustments[name]:
                    r[key] = max(0, r[key] + adjustments[name][adj_key])
        new_rows.append(r)
    return new_rows


def find_garbage_time_candidates(team: Team, margin: float, threshold_tc_pts: float = 9.0) -> List[dict]:
    """
    Scan bench players for live blowout prop plays.
    Two categories:
    - STRONG UNDER: even 8 garbage min won't reach line
    - LEAN OVER:   projected garbage min could fill a low line
    """
    candidates = []
    for p in team.bench():
        tc_pts  = round(p.tc_pts(), 1)
        tc_3pm  = round(p.tc_3pm(), 1)
        ppm     = p.pts / 48.0
        tpmm    = p.tpm / 48.0

        garbage_min   = min(8.0, BENCH_BLOWOUT_PENALTY)
        garbage_pts   = ppm * garbage_min * CONS_PTS
        garbage_3pm   = tpmm * garbage_min * CONS_3PM

        if tc_pts < threshold_tc_pts and tc_pts > 4.0:
            # Marginal under candidate
            over = garbage_pts >= p.line("pts") * 0.8
            candidates.append({
                "player":          p.name,
                "pos":            p.pos,
                "tc_pts":         tc_pts,
                "line_pts":       p.line("pts"),
                "garbage_proj_pts": round(garbage_pts, 1),
                "tc_3pm":         tc_3pm,
                "line_3pm":       p.line("tpm"),
                "garbage_proj_3pm": round(garbage_3pm, 1),
                "verdict":        ("LEAN OVER (garbage fills line)" if over
                                   else "LEAN UNDER (TC too high for garbage)"),
                "play":           "OVER" if over else "UNDER",
            })
        elif tc_pts >= threshold_tc_pts or tc_3pm >= 1.5:
            # Strong under — can't fill even with max garbage
            candidates.append({
                "player":          p.name,
                "pos":            p.pos,
                "tc_pts":         tc_pts,
                "line_pts":       p.line("pts"),
                "garbage_proj_pts": round(garbage_pts, 1),
                "tc_3pm":         tc_3pm,
                "line_3pm":       p.line("tpm"),
                "garbage_proj_3pm": round(garbage_3pm, 1),
                "verdict":        "STRONG UNDER (garbage insufficient)",
                "play":           "UNDER",
            })
    return candidates


def update_props_for_blowout(
    market_total: float,
    margin:        float,
    away_rows:     List[dict],
    home_rows:     List[dict],
    away_adj:      Dict[str, Dict[str, float]],
    home_adj:      Dict[str, Dict[str, float]],
) -> dict:
    """
    Live 4-6 leg UNDER parlay for bench players in a blowout.
    Only includes bench players whose lines moved DOWN (adj.min > 0).
    Max 6 legs, sorted by edge (biggest mover first).
    """
    legs = []
    for team_rows, team_adj in [(away_rows, away_adj), (home_rows, home_adj)]:
        for r in team_rows:
            name = r["name"]
            if name not in team_adj:
                continue
            Delta_pts = team_adj[name].get("pts", 0)
            if abs(Delta_pts) < 0.5:
                continue
            orig_line = r.get("line_pts", 0)
            new_line = round(max(0, r.get("tc_pts", 0) + Delta_pts) * LINE_FACTOR)
            if new_line >= orig_line:
                continue
            legs.append({
                "player":   name,
                "stat":     "pts",
                "old_line": orig_line,
                "new_line": new_line,
                "verdict":  "UNDER",
                "edge":     orig_line - new_line,
            })
    legs.sort(key=lambda x: x["edge"], reverse=True)
    return {"legs": legs[:6], "total_legs": len(legs)}


SERIES_BACKTEST = [
    ("CLE@NYK G1", "CLE", "NYK", 11, False, 219.0),
    ("CLE@NYK G2", "CLE", "NYK", 16, True,  202.0),
    ("NYK@CLE G3", "NYK", "CLE", 13, False, 229.0),
]

def run_series_backtest() -> None:
    print("\n=== CLE@NYK SERIES BACKTEST ===")
    print(f"BLOWOUT_M={BLOWOUT_MARGIN}  BENCH_F={BENCH_BLOWOUT_FACTOR}")
    hits = 0
    for game_key, away, home, margin, is_blowout, actual in SERIES_BACKTEST:
        proj = project_game_v2(home_abbr=home, away_abbr=away, margin=margin)
        tc   = proj["tc_combined"]
        sig  = proj["signal"]
        diff = actual - proj["market_total"]
        ok   = (diff > 0 and "OVER" in sig) or (diff < 0 and "UNDER" in sig)
        hit  = "Y" if ok else "N"
        if ok: hits += 1
        tag   = "BLOWOUT" if is_blowout else "CLOSE"
        print(f"  {game_key} [{tag}] m={margin:2d} TC={tc:5.1f} "
              f"mkt={proj['market_total']:5.1f} actual={actual:5.1f} "
              f"diff={diff:+4.1f} sig={sig:10s} {hit}")
    print(f"\n  Hit Rate: {hits}/{len(SERIES_BACKTEST)} "
          f"({100*hits/len(SERIES_BACKTEST):.0f}%)\n")


def project_game_v2(
    home_abbr:    str,
    away_abbr:    str,
    margin:        float = 0.0,
    market_total: Optional[float] = None,
    blowout_mode: bool = False,
) -> dict:
    away_team = TEAMS.get(away_abbr)
    home_team = TEAMS.get(home_abbr)
    if not away_team or not home_team:
        raise ValueError(f"Unknown: {away_abbr}/{home_abbr}")

    is_blowout = blowout_mode or (margin >= BLOWOUT_MARGIN and margin > 0)

    def team_rows(team: Team) -> List[dict]:
        rows = []
        for p in team.players:
            rows.append({
                "name":     p.name,
                "pos":      p.pos,
                "ht":       p.ht,
                "tc_pts":   round(p.tc_pts(), 1),
                "line_pts": p.line("pts"),
                "edge_pts": round(p.tc_pts() - p.line("pts"), 1),
                "tc_reb":   round(p.tc_reb(), 1),
                "line_reb": p.line("reb"),
                "edge_reb": round(p.tc_reb() - p.line("reb"), 1),
                "tc_ast":   round(p.tc_ast(), 1),
                "line_ast": p.line("ast"),
                "edge_ast": round(p.tc_ast() - p.line("ast"), 1),
                "tc_3pm":   round(p.tc_3pm(), 1),
                "line_3pm": p.line("tpm"),
                "edge_3pm": round(p.tc_3pm() - p.line("tpm"), 1),
                "tc_stl":   round(p.tc_stl(), 1),
                "tc_blk":   round(p.tc_blk(), 1),
                "status":   p.status,
            })
        return rows

    away_rows = team_rows(away_team)
    home_rows = team_rows(home_team)
    away_adj  = calc_blowout_adjustment(away_team, margin, is_blowout)
    home_adj  = calc_blowout_adjustment(home_team, margin, is_blowout)

    if is_blowout and (away_adj or home_adj):
        away_rows = apply_tc_adjustments(away_rows, away_adj)
        home_rows = apply_tc_adjustments(home_rows, home_adj)

    tc_combined = round((sum(r["tc_pts"] for r in away_rows)
                       + sum(r["tc_pts"] for r in home_rows)) * 1.05, 1)
    market_val  = market_total or tc_combined
    tc_line     = round(tc_combined * LINE_FACTOR)
    edge        = round(tc_line - market_val, 1)

    if edge > 0:
        signal = ("STRONG OVER" if edge >= 6 else
                 "LEAN OVER"  if edge >= 3 else "WEAK OVER")
    elif edge < 0:
        signal = ("STRONG UNDER" if edge <= -6 else
                 "LEAN UNDER"  if edge <= -3 else "WEAK UNDER")
    else:
        signal = "FLAT"

    result = {
        "away_team":   away_abbr,
        "home_team":   home_abbr,
        "margin":      margin,
        "is_blowout":  is_blowout,
        "tc_combined": tc_combined,
        "tc_line":     tc_line,
        "market_total": market_val,
        "edge":        edge,
        "signal":      signal,
        "source":      "hardcoded+v2-blowout",
        "away":        {"players": away_rows,
                        "adjustments": away_adj,
                        "injuries": away_team.injury_notes},
        "home":        {"players": home_rows,
                        "adjustments": home_adj,
                        "injuries": home_team.injury_notes},
    }
    if is_blowout:
        result["live_blowout_props"] = update_props_for_blowout(
            market_val, margin, away_rows, home_rows, away_adj, home_adj)
    return result


TEAMS: Dict[str, Team] = {}

def build_teams():
    global TEAMS
    TEAMS = {
        "CLE": Team("CLE", "Cleveland Cavaliers", [
            Player("Donovan Mitchell", "GT", "6-1",  21.0, 4.5, 5.0, 2.4, 1.2, 0.3),
            Player("Darius Garland",  "G",  "6-1",  19.0, 2.5, 6.5, 2.8, 1.2, 0.2),
            Player("Evan Mobley",     "C",  "7-0",  16.5, 9.0, 3.0, 1.2, 0.7, 1.7),
            Player("Jarrett Allen",   "C",  "6-9",  13.5, 7.5, 2.5, 0.5, 0.6, 1.2),
            Player("Max Strus",      "SF", "6-5",  11.0, 4.0, 3.5, 2.0, 0.5, 0.3),
            Player("Dean Wade",      "PF", "6-9",   5.3, 3.6, 1.1, 1.2, 0.6, 0.4),
            Player("Isaac Okoro",    "SG", "6-5",   7.0, 2.5, 1.5, 0.5, 0.5, 0.2),
            Player("Ty Jerome",      "SG", "6-5",   7.5, 2.0, 3.0, 1.5, 0.4, 0.1),
            Player("Sam Merrill",    "SG", "6-4",   5.0, 1.5, 1.0, 1.5, 0.2, 0.1),
            Player("Tacko Fall",     "C",  "7-5",   2.5, 2.5, 0.0, 0.0, 0.1, 0.4),
            Player("Luke Travers",   "SF", "6-7",   1.5, 1.5, 0.5, 0.3, 0.1, 0.1),
            Player("Tristan Enaruna","PF", "6-8",   1.0, 1.0, 0.5, 0.2, 0.1, 0.1),
            Player("Jaylon Tyson",   "SG", "6-5",   3.0, 1.5, 1.0, 0.8, 0.2, 0.1),
            Player("Riley Minix",   "F",  "6-7",   2.0, 1.5, 0.5, 0.3, 0.1, 0.1),
            Player("Larry Nance Jr.","F",  "6-7",   7.0, 4.5, 2.0, 1.0, 0.8, 0.4),
        ], ["Ty Jerome OUT (ankle)"]),
        "NYK": Team("NYK", "New York Knicks", [
            Player("Jalen Brunson",    "PG", "6-2",  27.5, 3.0, 6.5, 2.2, 1.0, 0.2),
            Player("Mikal Bridges",     "SG", "6-6",  14.5, 4.0, 3.0, 2.0, 1.0, 0.3),
            Player("Josh Hart",         "SF", "6-5",  14.0, 5.0, 4.0, 1.5, 0.9, 0.2),
            Player("OG Anunoby",        "SF", "6-7",  16.0, 4.5, 2.0, 2.2, 1.3, 0.5),
            Player("Karl-Anthony Towns","C",  "7-0",  22.0, 8.0, 3.0, 2.0, 0.6, 1.3),
            Player("Miles McBride",     "PG", "6-2",   8.0, 2.0, 2.5, 2.0, 0.7, 0.2),
            Player("Precious Achiuwa", "PF", "6-8",   7.5, 5.0, 2.0, 0.8, 0.4, 0.6),
            Player("Jacob Topp",        "F",  "6-8",   3.0, 2.0, 0.5, 0.5, 0.2, 0.2),
            Player("Matt Creamer",      "C",  "6-10",  2.0, 1.5, 0.5, 0.2, 0.1, 0.3),
            Player("Jordan Crawford",   "SG", "6-3",   9.0, 2.5, 3.0, 2.0, 0.6, 0.2),
            Player("Landry Shamet",     "SG", "6-5",   6.0, 1.5, 1.5, 1.8, 0.3, 0.1),
            Player("Sean Manaea",       "C",  "6-10",  4.0, 3.0, 1.0, 0.3, 0.2, 0.6),
            Player("Julius Randle",     "PF", "6-8",   9.0, 5.0, 3.0, 1.5, 0.4, 0.3),
        ], ["Julius Randle OUT (ankle)"]),
    }


if __name__ == "__main__":
    build_teams()

    parser = argparse.ArgumentParser(description="NBA TC — Blowout Engine")
    parser.add_argument("--backtest",   action="store_true")
    parser.add_argument("--game",       help="'AWAY @ HOME'")
    parser.add_argument("--margi",      type=float, default=0)
    parser.add_argument("--blowout-mode", action="store_true")
    parser.add_argument("--candidates", help="Team to scan (CLE or NYK)")
    args = parser.parse_args()

    if args.backtest:
        run_series_backtest()

    elif args.candidates:
        team = TEAMS.get(args.candidates.upper())
        if not team:
            print(f"Unknown: {args.candidates}")
            raise SystemExit(1)
        margin = args.margi or 0
        cands = find_garbage_time_candidates(team, margin)
        print(f"\n=== {args.candidates.upper()} Garbage Prop Candidates ===")
        for c in cands:
            print(f"  {c['player']:22s} {c['pos']} | "
                  f"TC={c['tc_pts']:4.1f} line={c['line_pts']:3.0f} | "
                  f"proj={c['garbage_proj_pts']:4.1f} | {c['verdict']}")

    elif args.game:
        parts = args.game.split("@")
        if len(parts) < 2:
            print("Usage: --game 'AWAY @ HOME'")
            raise SystemExit(1)
        away_key = parts[0].strip().upper()
        home_key = parts[1].strip().upper()
        proj = project_game_v2(
            home_abbr=home_key, away_abbr=away_key,
            margin=args.margi, blowout_mode=args.blowout_mode)
        print(json.dumps(proj, indent=2))
