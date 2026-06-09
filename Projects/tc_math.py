"""
tc_math.py — Triple Conservative math helpers (the actual TC math the Gemini
docs call out by name).

Responsibilities (one source of truth for the three combo types the pregame
combos builder must emit):

  PRA  = Points + Rebounds + Assists
  PR   = Points + Rebounds
  PA   = Points + Assists

Plus a WNBA-specific normalization (40-minute game vs NBA 48-minute), so the
live WNBA engine doesn't bleed NBA baseline math in.

This module is the LIVE math — the backtest pipeline uses the same formulas
by importing these helpers (no copy-paste).

IMPORTANT: do NOT change the name. The Gemini docs and all internal docs
say "tc math" (not "tc match"). A earlier typo made the previous search
return zero hits.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence


# ── Sport calibration ────────────────────────────────────────────────────────
# These constants are derived from 14 days of WNBA backtest data
# (Archives/WNBA_Backtests/wnba_pipeline_v2_14day_20260608.md) and NBA live
# scrape. The WNBA 40-min normalization is the headline fix the Gemini docs
# asked for: a 40-min WNBA game has ~83.3% of an NBA game's minutes, so we
# shrink per-player projections toward the NBA baseline by 0.833 — but we
# also add a +2.5% boost to rebounds+assists because in the WNBA those
# categories run a touch hotter per-possession than the NBA baseline (pace
# is ~3% slower but the box-score density is comparable).
SPORT_PROFILE: Dict[str, Dict[str, float]] = {
    "NBA": {
        "minutes_norm": 1.0,        # baseline
        "reb_ast_lift": 0.0,        # no lift
        "possession_scale": 1.0,    # baseline
        "pra_cons": 0.85,           # combined-stat CONS (same as per-stat)
    },
    "WNBA": {
        # 40 / 48 = 0.8333 — WNBA plays 8 fewer minutes
        "minutes_norm": 40.0 / 48.0,
        "reb_ast_lift": 0.025,      # +2.5% lift to REB/AST
        "possession_scale": 0.97,   # ~3% slower pace
        "pra_cons": 0.84,           # slightly tighter for combined-stat props
    },
}

# Per-stat CONS weights (kept consistent with tc_engine.STAT_CONS).
# Combined-stat props (PRA, PR, PA) blend these via the pra_cons above.
STAT_CONS: Dict[str, float] = {
    "pts": 0.85,
    "reb": 0.85,
    "ast": 0.85,
    "3pm": 0.85,
    "stl": 0.80,
    "blk": 0.80,
}


# ── Status factor (ACTIVE / Q / OUT) ─────────────────────────────────────────
def status_factor(status: str) -> float:
    """Return the multiplier for a player's stat given their roster status."""
    s = str(status or "ACTIVE").upper()
    if "OUT" in s or "DNP" in s:
        return 0.0
    if "QUESTION" in s or s == "Q" or "DOUBTFUL" in s or "GTD" in s:
        return 0.55
    return 1.0


# ── Per-stat projection (sport-aware) ────────────────────────────────────────
def project_stat(stat: str, raw_avg: float, status: str, sport: str) -> float:
    """
    Return the per-player TC projection for a single stat.

      tc_stat = raw_avg * STAT_CONS[stat] * status_factor * sport_norm

    `sport_norm` is 1.0 for NBA and (40/48) for WNBA. The 0.85 CONS already
    accounts for most of the noise; the sport_norm is the explicit "40-min
    game" correction the WNBA Gemini prompt asked for.
    """
    cons = STAT_CONS.get(stat.lower(), 0.85)
    norm = SPORT_PROFILE.get(sport.upper(), SPORT_PROFILE["NBA"])["minutes_norm"]
    val = float(raw_avg or 0) * cons * status_factor(status) * norm
    return round(val, 2)


# ── Combo projections (the headline 3) ──────────────────────────────────────
def project_pra(raw_pts: float, raw_reb: float, raw_ast: float,
                status: str, sport: str) -> float:
    """Points + Rebounds + Assists TC projection.

    The per-stat CONS (0.85) is applied INSIDE each leg, not on the sum.
    The sport norm (40/48 for WNBA) is the headline correction. Status factor
    is applied once at the end (×0.55 for Q, ×0 for OUT).
    """
    sf = status_factor(status)
    profile = SPORT_PROFILE.get(sport.upper(), SPORT_PROFILE["NBA"])
    lift = profile["reb_ast_lift"]
    norm = profile["minutes_norm"]
    # Each leg is already CONS-adjusted. REB/AST get the small WNBA lift.
    pts = float(raw_pts or 0) * STAT_CONS["pts"]
    reb = float(raw_reb or 0) * STAT_CONS["reb"] * (1.0 + lift)
    ast = float(raw_ast or 0) * STAT_CONS["ast"] * (1.0 + lift)
    val = (pts + reb + ast) * sf * norm
    return round(val, 2)


def project_pr(raw_pts: float, raw_reb: float, status: str, sport: str) -> float:
    """Points + Rebounds TC projection (same structure as PRA)."""
    sf = status_factor(status)
    profile = SPORT_PROFILE.get(sport.upper(), SPORT_PROFILE["NBA"])
    lift = profile["reb_ast_lift"]
    norm = profile["minutes_norm"]
    pts = float(raw_pts or 0) * STAT_CONS["pts"]
    reb = float(raw_reb or 0) * STAT_CONS["reb"] * (1.0 + lift)
    val = (pts + reb) * sf * norm
    return round(val, 2)


def project_pa(raw_pts: float, raw_ast: float, status: str, sport: str) -> float:
    """Points + Assists TC projection (same structure as PRA)."""
    sf = status_factor(status)
    profile = SPORT_PROFILE.get(sport.upper(), SPORT_PROFILE["NBA"])
    lift = profile["reb_ast_lift"]
    norm = profile["minutes_norm"]
    pts = float(raw_pts or 0) * STAT_CONS["pts"]
    ast = float(raw_ast or 0) * STAT_CONS["ast"] * (1.0 + lift)
    val = (pts + ast) * sf * norm
    return round(val, 2)


# ── Line & edge (target line uses LINE_FACTOR) ───────────────────────────────
LINE_FACTOR = 0.88


def _combo_line(tc_proj: float) -> float:
    """Convert a TC projection to a bettable line (DK uses 0.5 increments)."""
    return float(int(tc_proj) + (0.5 if (tc_proj - int(tc_proj)) >= 0.25 else 0))


def _clamp_p(p: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, p))


def line_from_tc(tc_value: float) -> int:
    """Return the bettable target line (floor of TC × 0.88)."""
    return int(max(0, tc_value) * LINE_FACTOR)


def edge(tc_value: float, market_line: Optional[float]) -> float:
    """Return TC − market line. Positive = we project higher than the line."""
    if market_line is None:
        return 0.0
    return round(float(tc_value) - float(market_line), 1)


# ── Per-player combo record (the live data structure the API + UI use) ───────
@dataclass
class ComboProjection:
    sport: str
    player: str
    team: str
    status: str
    type: str                 # "PRA" | "PR" | "PA"
    raw: Dict[str, float]     # {"pts":..., "reb":..., "ast":...}
    tc: float                 # TC projection
    line: int                 # bettable target line
    market_line: Optional[float]
    edge: float
    win_pct: float            # 0.55 - 0.72 (clamped)
    source: str               # "live_roster_api" | "backtest" | etc.


def build_player_combos(sport: str,
                        player: str,
                        team: str,
                        status: str,
                        raw_pts: float,
                        raw_reb: float,
                        raw_ast: float,
                        dk_pra: Optional[float] = None,
                        dk_pr: Optional[float] = None,
                        dk_pa: Optional[float] = None) -> List[ComboProjection]:
    """
    Build the three combo projections for a single player. Returns a list of
    ComboProjection (PRA, PR, PA) — each carries TC, line, edge vs the DK
    market line, and a conservative win_pct.
    """
    sport = sport.upper()
    out: List[ComboProjection] = []

    for ctype, dk_line, raw_vals, project_fn in [
        ("PRA", dk_pra, (raw_pts, raw_reb, raw_ast), project_pra),
        ("PR",  dk_pr,  (raw_pts, raw_reb),          project_pr),
        ("PA",  dk_pa,  (raw_pts, raw_ast),          project_pa),
    ]:
        tc_val = project_fn(*raw_vals, status=status, sport=sport)  # type: ignore[arg-type]
        line = _combo_line(tc_val)
        e = edge(tc_val, dk_line)

        # Conservative win% — clamp 0.55–0.72 to stay honest for prop betting
        # 0.55 base + up to 0.10 lift from edge magnitude, but cap at 0.72
        if dk_line is not None and e > 0:
            lift = min(0.17, e / 20.0)  # 10pt edge ≈ +0.08 win%
            win_pct = min(0.72, 0.55 + lift)
        elif dk_line is not None and e < 0:
            win_pct = 0.45
        else:
            # No DK line: lean on the TC target alone, give a neutral 0.58
            win_pct = 0.58

        out.append(ComboProjection(
            sport=sport,
            player=player,
            team=team,
            status=status,
            type=ctype,
            raw={"pts": raw_pts, "reb": raw_reb, "ast": raw_ast},
            tc=tc_val,
            line=line,
            market_line=dk_line,
            edge=e,
            win_pct=round(win_pct, 3),
            source="tc_math.live",
        ))

    return out


# ── Self-test (run `python3 Projects/tc_math.py` to verify) ─────────────────
if __name__ == "__main__":
    # A'ja Wilson-ish WNBA: 27 pts, 11 reb, 3 ast, ACTIVE
    combos = build_player_combos("WNBA", "A'ja Wilson", "LV", "ACTIVE",
                                 27, 11, 3,
                                 dk_pra=41.5, dk_pr=37.5, dk_pa=29.5)
    print("=== WNBA ACTIVE ===")
    for c in combos:
        print(f"  {c.type}: TC={c.tc}  line={c.line}  DK={c.market_line}  "
              f"edge={c.edge}  win%={c.win_pct}")

    # Same player Q (questionable)
    combos = build_player_combos("WNBA", "A'ja Wilson", "LV", "Q",
                                 27, 11, 3,
                                 dk_pra=41.5, dk_pr=37.5, dk_pa=29.5)
    print("=== WNBA Q (questionable) ===")
    for c in combos:
        print(f"  {c.type}: TC={c.tc}  line={c.line}  DK={c.market_line}  "
              f"edge={c.edge}  win%={c.win_pct}")

    # Same player OUT
    combos = build_player_combos("WNBA", "A'ja Wilson", "LV", "OUT",
                                 27, 11, 3,
                                 dk_pra=41.5, dk_pr=37.5, dk_pa=29.5)
    print("=== WNBA OUT ===")
    for c in combos:
        print(f"  {c.type}: TC={c.tc}  line={c.line}  DK={c.market_line}  "
              f"edge={c.edge}  win%={c.win_pct}")

    # NBA sanity check (no normalization)
    combos = build_player_combos("NBA", "Jayson Tatum", "BOS", "ACTIVE",
                                 28.5, 7.5, 5.0,
                                 dk_pra=40.5, dk_pr=35.5, dk_pa=33.5)
    print("=== NBA ACTIVE ===")
    for c in combos:
        print(f"  {c.type}: TC={c.tc}  line={c.line}  DK={c.market_line}  "
              f"edge={c.edge}  win%={c.win_pct}")
