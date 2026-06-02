#!/usr/bin/env python3
"""
Sports TC Pipeline v7.0
=======================
Unified NBA + WNBA workflow for:
  - Full roster projections: starters + bench + injury notes
  - TC player-prop floors only: PTS, REB, AST, 3PM
  - Separate non-TC team/game totals: raw totals + optional model-adjusted totals
  - Optional model layers: NFRI, Pace, Home Court, Momentum
  - Backtest seed logging with unit sizing and ROI-ready fields

Hard rules
----------
1. TC is the core player-prop model only.
2. Team totals and game totals are never labeled TC totals.
3. Team/game totals live in a separate section: RAW + MODEL-ADJUSTED.
4. Prop recommendations require sportsbook lines; this tool produces floors/watchlists.

Usage
-----
  python3 tc_pipeline.py --sport NBA --game "BOS @ NYK"
  python3 tc_pipeline.py --sport WNBA --game "DAL @ ATL" --total 172.5 --model nfri
  python3 tc_pipeline.py --sport NBA --game "OKC @ SAS" --model full --save
  python3 tc_pipeline.py --diagnostics
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent
BASE_DIR = Path(__file__).resolve().parent
WORKSPACE = BASE_DIR.parents[1] if BASE_DIR.parts[-3:] == ("tc-workspace", "apps", "sports-tc") else Path("/home/workspace")
NBA_JSON = WORKSPACE / "rosters" / "wnba_rosters" / "NBA_BACKTEST_ROSTERS.json"
WNBA_JSON = WORKSPACE / "rosters" / "wnba_rosters" / "WNBA_BACKTEST_ROSTERS.json"
REPORT_DIR = ROOT / "reports"
DATA_DIR = ROOT / "data"
MONITOR_DIR = ROOT / "monitor"
for p in (REPORT_DIR, DATA_DIR, MONITOR_DIR):
    p.mkdir(exist_ok=True)

TC_FACTORS = {"pts": 0.85, "reb": 0.80, "ast": 0.75, "tpm": 0.70}
Q_FACTOR = 0.55
OUT_FACTOR = 0.0
LINE_FACTOR = 0.88
DEFAULT_PROP_EDGE = {"pts": 3.0, "reb": 2.0, "ast": 1.5, "tpm": 0.5}
MAX_UNIT_SIZE = 3.0

TEAM_ALIASES = {
    "NY": "NYK", "NYK": "NYK",
    "LV": "LVA", "LVA": "LVA",
    "LA": "LAS", "LAS": "LAS", "LAC": "LAC", "LAL": "LAL",
    "GS": "GSW", "GSW": "GSW",
    "SA": "SAS", "SAS": "SAS",
    "BK": "BKN", "BKN": "BKN",
    "NO": "NOP", "NOP": "NOP",
    "UTH": "UTA", "UTA": "UTA",
}

PACE_INDEX = {
    "NBA": {"OKC": 1.025, "SAS": 1.018, "NYK": 0.982, "CLE": 0.990, "BOS": 0.995, "PHI": 0.985, "MIN": 0.988, "DEN": 0.990, "LAL": 1.000, "GSW": 1.012, "LAC": 0.992},
    "WNBA": {"GS": 1.035, "IND": 1.025, "DAL": 1.018, "ATL": 1.006, "PHX": 1.010, "TOR": 0.990, "NY": 0.995, "POR": 0.985, "MIN": 0.988, "SEA": 1.000, "LVA": 0.998, "CON": 0.982, "WAS": 0.990, "CHI": 1.012, "LAS": 1.006},
}

HOME_COURT = {"NBA": 1.018, "WNBA": 1.015}
AWAY_DISCOUNT = {"NBA": 0.992, "WNBA": 0.994}
MOMENTUM_INDEX = {
    "NBA": {"OKC": 1.020, "SAS": 1.015, "NYK": 1.010, "CLE": 1.000},
    "WNBA": {"PHX": 1.018, "TOR": 1.006, "DAL": 1.004, "ATL": 1.000, "NY": 1.015, "POR": 0.995, "GS": 1.012, "IND": 1.010},
}


def norm_code(code: str) -> str:
    clean = code.strip().upper()
    return TEAM_ALIASES.get(clean, clean)


def safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def _load_json_roster(json_path: Path, sport_label: str) -> Dict[str, Dict[str, Any]]:
    if not json_path.exists():
        raise FileNotFoundError(f"{sport_label} roster JSON not found: {json_path}")
    data = json.loads(json_path.read_text())
    teams = data.get("teams", {})
    if not teams:
        raise ValueError(f"{json_path} contains no teams.")
    return teams


def player_from_dict(item: Dict[str, Any], role: str) -> "PlayerProjection":
    return PlayerProjection(
        name=str(item.get("name", "Unknown")),
        pos=str(item.get("pos", "")),
        ht=str(item.get("ht", "")),
        ppg=safe_float(item.get("ppg", item.get("pts", 0))),
        rpg=safe_float(item.get("rpg", item.get("reb", 0))),
        apg=safe_float(item.get("apg", item.get("ast", 0))),
        tpm=safe_float(item.get("tpm", item.get("3pm", 0))),
        status=str(item.get("status", "ACTIVE")).upper(),
        role=role,
    )


def load_team_from_json(code: str, sport: str, json_path: Path) -> "TeamProjection":
    code = norm_code(code)
    teams = _load_json_roster(json_path, sport.upper())
    if code not in teams:
        raise KeyError(f"{sport} team '{code}' not found. Available: {', '.join(sorted(teams))}")
    team = teams[code]
    raw_notes = team.get("injury_notes", [])
    injury_notes = [raw_notes] if isinstance(raw_notes, str) and raw_notes else list(raw_notes or [])
    return TeamProjection(
        code=code,
        name=team.get("team_name", code),
        starters=[player_from_dict(p, "STARTER") for p in team.get("starters", [])],
        bench=[player_from_dict(p, "BENCH") for p in team.get("bench", [])],
        injury_notes=injury_notes,
    )


def load_team(sport: str, code: str) -> "TeamProjection":
    sport = sport.upper()
    return load_team_from_json(code, sport, WNBA_JSON if sport == "WNBA" else NBA_JSON)


def list_available_teams(sport: str) -> List[Tuple[str, str]]:
    sport = sport.upper()
    teams = _load_json_roster(WNBA_JSON if sport == "WNBA" else NBA_JSON, sport)
    return sorted((code, info.get("team_name", code)) for code, info in teams.items())


@dataclass
class PlayerProjection:
    name: str
    pos: str
    ht: str
    ppg: float
    rpg: float
    apg: float
    tpm: float
    status: str = "ACTIVE"
    role: str = "BENCH"

    def status_factor(self) -> float:
        s = self.status.upper()
        if s == "OUT":
            return OUT_FACTOR
        if s in {"Q", "QUESTIONABLE", "DOUBTFUL", "DAY-TO-DAY"}:
            return Q_FACTOR
        return 1.0

    def status_icon(self) -> str:
        if self.status == "OUT":
            return "❌"
        if self.status in {"Q", "QUESTIONABLE", "DOUBTFUL", "DAY-TO-DAY"}:
            return "⚠️"
        return "✅"

    def raw(self) -> Dict[str, float]:
        return {"pts": round(self.ppg, 1), "reb": round(self.rpg, 1), "ast": round(self.apg, 1), "tpm": round(self.tpm, 1)}

    def tc(self) -> Dict[str, float]:
        f = self.status_factor()
        return {
            "pts": round(self.ppg * TC_FACTORS["pts"] * f, 1),
            "reb": round(self.rpg * TC_FACTORS["reb"] * f, 1),
            "ast": round(self.apg * TC_FACTORS["ast"] * f, 1),
            "tpm": round(self.tpm * TC_FACTORS["tpm"] * f, 1),
        }

    def prop_targets(self) -> Dict[str, int]:
        tc = self.tc()
        return {k: max(0, int(v)) for k, v in tc.items()}

    def nfri(self, rest_factor: float = 1.0, location_factor: float = 1.0, momentum_factor: float = 1.0) -> float:
        return round(self.tc()["pts"] * rest_factor * location_factor * momentum_factor, 2)


@dataclass
class TeamProjection:
    code: str
    name: str
    starters: List[PlayerProjection] = field(default_factory=list)
    bench: List[PlayerProjection] = field(default_factory=list)
    injury_notes: List[str] = field(default_factory=list)

    @property
    def players(self) -> List[PlayerProjection]:
        return self.starters + self.bench

    @property
    def active_players(self) -> List[PlayerProjection]:
        return [p for p in self.players if p.status != "OUT"]

    def raw_totals(self) -> Dict[str, float]:
        active = self.active_players
        return {
            "pts": round(sum(p.ppg for p in active), 1),
            "reb": round(sum(p.rpg for p in active), 1),
            "ast": round(sum(p.apg for p in active), 1),
            "tpm": round(sum(p.tpm for p in active), 1),
        }

    def tc_prop_totals(self) -> Dict[str, float]:
        totals = {"pts": 0.0, "reb": 0.0, "ast": 0.0, "tpm": 0.0}
        for player in self.players:
            tc = player.tc()
            for key in totals:
                totals[key] += tc[key]
        return {k: round(v, 1) for k, v in totals.items()}

    def injury_summary(self) -> Dict[str, List[PlayerProjection]]:
        return {
            "out": [p for p in self.players if p.status == "OUT"],
            "q": [p for p in self.players if p.status in {"Q", "QUESTIONABLE", "DOUBTFUL", "DAY-TO-DAY"}],
            "active": [p for p in self.players if p.status == "ACTIVE"],
        }


@dataclass
class GameProjection:
    away: TeamProjection
    home: TeamProjection
    sport: str
    market_total: Optional[float] = None
    market_spread: Optional[float] = None
    model: str = "tc"
    generated_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def raw_game_totals(self) -> Dict[str, float]:
        away = self.away.raw_totals()
        home = self.home.raw_totals()
        return {key: round(away[key] + home[key], 1) for key in away}

    def location_factor(self, team_code: str) -> float:
        if team_code == self.home.code:
            return HOME_COURT.get(self.sport, 1.0)
        return AWAY_DISCOUNT.get(self.sport, 1.0)

    def pace_factor(self) -> float:
        table = PACE_INDEX.get(self.sport, {})
        return round((table.get(self.away.code, 1.0) + table.get(self.home.code, 1.0)) / 2, 4)

    def momentum_factor(self, team_code: str) -> float:
        return MOMENTUM_INDEX.get(self.sport, {}).get(team_code, 1.0)

    def nfri_team_points(self, team: TeamProjection) -> float:
        loc = self.location_factor(team.code)
        mom = self.momentum_factor(team.code)
        return round(sum(p.nfri(location_factor=loc, momentum_factor=mom) for p in team.players), 1)

    def model_totals(self) -> Dict[str, Any]:
        raw_away = self.away.raw_totals()["pts"]
        raw_home = self.home.raw_totals()["pts"]
        raw_total = raw_away + raw_home
        nfri_away = self.nfri_team_points(self.away)
        nfri_home = self.nfri_team_points(self.home)
        nfri_total = round(nfri_away + nfri_home, 1)
        pace = self.pace_factor()
        pace_total = round(raw_total * pace, 1)
        full_away = round(nfri_away * pace, 1)
        full_home = round(nfri_home * pace, 1)
        full_total = round(full_away + full_home, 1)
        selected = self.model.lower()
        if selected == "nfri":
            chosen_total, chosen_away, chosen_home = nfri_total, nfri_away, nfri_home
        elif selected == "pace":
            chosen_total, chosen_away, chosen_home = pace_total, round(raw_away * pace, 1), round(raw_home * pace, 1)
        elif selected == "full":
            chosen_total, chosen_away, chosen_home = full_total, full_away, full_home
        else:
            chosen_total, chosen_away, chosen_home = raw_total, raw_away, raw_home
        edge = None if self.market_total is None else round(chosen_total - self.market_total, 1)
        lean = "NO MARKET"
        units = 0.0
        if edge is not None:
            if edge >= 7:
                lean, units = "OVER", min(MAX_UNIT_SIZE, round(edge / 7, 1))
            elif edge <= -7:
                lean, units = "UNDER", min(MAX_UNIT_SIZE, round(abs(edge) / 7, 1))
            else:
                lean, units = "NO PLAY", 0.0
        return {
            "rule": "Separate from TC player-prop floors. These are raw/model totals, not TC totals.",
            "selected_model": selected.upper(),
            "raw": {"away_pts": round(raw_away, 1), "home_pts": round(raw_home, 1), "game_pts": round(raw_total, 1)},
            "nfri": {"away_pts": nfri_away, "home_pts": nfri_home, "game_pts": nfri_total},
            "pace": {"factor": pace, "game_pts": pace_total},
            "full": {"away_pts": full_away, "home_pts": full_home, "game_pts": full_total},
            "selected": {"away_pts": chosen_away, "home_pts": chosen_home, "game_pts": chosen_total, "market_total": self.market_total, "edge": edge, "lean": lean, "unit_size": units},
        }

    def prop_candidates(self) -> List[Dict[str, Any]]:
        candidates: List[Dict[str, Any]] = []
        for team in (self.away, self.home):
            for player in team.players:
                if player.status == "OUT":
                    continue
                tc = player.tc()
                raw = player.raw()
                for stat in ("pts", "reb", "ast", "tpm"):
                    gap = round(raw[stat] - tc[stat], 1)
                    if gap >= DEFAULT_PROP_EDGE[stat] and tc[stat] > 0:
                        candidates.append({
                            "team": team.code,
                            "player": player.name,
                            "role": player.role,
                            "stat": stat.upper().replace("TPM", "3PM"),
                            "raw_projection": raw[stat],
                            "tc_floor": tc[stat],
                            "target_whole_number": player.prop_targets()[stat],
                            "gap": gap,
                            "status": player.status,
                        })
        return sorted(candidates, key=lambda x: (x["gap"], x["raw_projection"]), reverse=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "sport": self.sport,
            "market_total": self.market_total,
            "market_spread": self.market_spread,
            "model": self.model,
            "tc_rule": "TC applies only to player props. Team/game totals are separate raw/model outputs.",
            "away": serialize_team(self.away),
            "home": serialize_team(self.home),
            "raw_game_totals": self.raw_game_totals(),
            "model_totals": self.model_totals(),
            "prop_candidates": self.prop_candidates(),
        }


def serialize_player(player: PlayerProjection) -> Dict[str, Any]:
    return {"name": player.name, "role": player.role, "pos": player.pos, "ht": player.ht, "status": player.status, "raw": player.raw(), "tc_prop_floor": player.tc(), "prop_targets": player.prop_targets()}


def serialize_team(team: TeamProjection) -> Dict[str, Any]:
    return {"code": team.code, "name": team.name, "injury_notes": team.injury_notes, "raw_totals": team.raw_totals(), "tc_prop_totals": team.tc_prop_totals(), "starters": [serialize_player(p) for p in team.starters], "bench": [serialize_player(p) for p in team.bench]}


def format_player_table(players: Iterable[PlayerProjection]) -> List[str]:
    rows = [
        "| Role | Player | POS | HT | Status | Raw PTS | Raw REB | Raw AST | Raw 3PM | TC PTS | TC REB | TC AST | TC 3PM | Target PTS | Target REB | Target AST | Target 3PM |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for p in players:
        raw, tc, tgt = p.raw(), p.tc(), p.prop_targets()
        rows.append(f"| {p.role} | {p.name} | {p.pos} | {p.ht} | {p.status} | {raw['pts']:.1f} | {raw['reb']:.1f} | {raw['ast']:.1f} | {raw['tpm']:.1f} | {tc['pts']:.1f} | {tc['reb']:.1f} | {tc['ast']:.1f} | {tc['tpm']:.1f} | {tgt['pts']}+ | {tgt['reb']}+ | {tgt['ast']}+ | {tgt['tpm']}+ |")
    return rows


def format_team_section(team: TeamProjection) -> List[str]:
    lines = [f"## {team.code} — {team.name}", "", "### Injury Notes"]
    lines.extend([f"- {n}" for n in team.injury_notes] if team.injury_notes else ["- No injury notes available. Confirm pregame status before bet placement."])
    rt = team.raw_totals()
    lines.extend(["", "### Raw Team Totals — No TC Applied", "", "| PTS | REB | AST | 3PM |", "|---:|---:|---:|---:|", f"| {rt['pts']:.1f} | {rt['reb']:.1f} | {rt['ast']:.1f} | {rt['tpm']:.1f} |", "", "### TC Prop Floors — Full Roster", ""])
    lines.extend(format_player_table(team.players))
    lines.append("")
    return lines


def render_report(game: GameProjection) -> str:
    raw_game = game.raw_game_totals()
    mt = game.model_totals()
    lines = [
        f"# {game.sport} TC Report — {game.away.code} @ {game.home.code}",
        "",
        f"**Generated:** {game.generated_at}",
        "",
        "## Rules",
        "- TC is the core player-prop floor model only: PTS×0.85, REB×0.80, AST×0.75, 3PM×0.70.",
        "- Questionable players: TC result ×0.55. OUT players: 0.",
        "- Team/game totals are separate raw/model totals, never TC totals.",
        "",
        "## Separate Team/Game Totals — No TC Applied",
        "",
        "| Item | Value |",
        "|---|---:|",
        f"| Market Total | {game.market_total if game.market_total is not None else 'Not provided'} |",
        f"| {game.away.code} Raw Team Points | {game.away.raw_totals()['pts']:.1f} |",
        f"| {game.home.code} Raw Team Points | {game.home.raw_totals()['pts']:.1f} |",
        f"| Raw Game Points Total | {raw_game['pts']:.1f} |",
        f"| NFRI Game Points | {mt['nfri']['game_pts']:.1f} |",
        f"| Pace Factor | {mt['pace']['factor']:.4f} |",
        f"| Full Model Game Points | {mt['full']['game_pts']:.1f} |",
        f"| Selected Model | {mt['selected_model']} |",
        f"| Selected Model Total | {mt['selected']['game_pts']:.1f} |",
        f"| Edge vs Market | {mt['selected']['edge'] if mt['selected']['edge'] is not None else 'N/A'} |",
        f"| Lean | {mt['selected']['lean']} |",
        f"| Unit Size | {mt['selected']['unit_size']} |",
        "",
    ]
    lines.extend(format_team_section(game.away))
    lines.extend(format_team_section(game.home))
    lines.extend(["## Prop Candidate Watchlist", "", "| Team | Player | Role | Stat | Raw | TC Floor | Whole # | Gap | Status |", "|---|---|---|---:|---:|---:|---:|---:|---:|"])
    for c in game.prop_candidates()[:30]:
        lines.append(f"| {c['team']} | {c['player']} | {c['role']} | {c['stat']} | {c['raw_projection']:.1f} | {c['tc_floor']:.1f} | {c['target_whole_number']}+ | {c['gap']:.1f} | {c['status']} |")
    return "\n".join(lines) + "\n"


def print_console_report(game: GameProjection) -> None:
    print(render_report(game))


def save_game_outputs(game: GameProjection, stem: Optional[str] = None) -> Tuple[Path, Path]:
    stem = stem or f"{game.sport}_{game.away.code}_at_{game.home.code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    md_path = REPORT_DIR / f"{stem}.md"
    json_path = DATA_DIR / f"{stem}.json"
    md_path.write_text(render_report(game))
    json_path.write_text(json.dumps(game.to_dict(), indent=2))
    return md_path, json_path


def append_backtest_seed(game: GameProjection, md_path: Path, json_path: Path) -> Path:
    path = DATA_DIR / "backtest_seed_log.csv"
    exists = path.exists()
    mt = game.model_totals()
    with path.open("a", newline="") as f:
        fields = ["generated_at", "sport", "model", "away", "home", "away_raw_pts", "home_raw_pts", "raw_game_pts", "selected_model_total", "market_total", "edge", "lean", "unit_size", "actual_total", "result", "profit_units", "roi_ready", "report_md", "report_json"]
        w = csv.DictWriter(f, fieldnames=fields)
        if not exists:
            w.writeheader()
        w.writerow({
            "generated_at": game.generated_at,
            "sport": game.sport,
            "model": game.model,
            "away": game.away.code,
            "home": game.home.code,
            "away_raw_pts": game.away.raw_totals()["pts"],
            "home_raw_pts": game.home.raw_totals()["pts"],
            "raw_game_pts": game.raw_game_totals()["pts"],
            "selected_model_total": mt["selected"]["game_pts"],
            "market_total": game.market_total or "",
            "edge": mt["selected"]["edge"] if mt["selected"]["edge"] is not None else "",
            "lean": mt["selected"]["lean"],
            "unit_size": mt["selected"]["unit_size"],
            "actual_total": "",
            "result": "PENDING",
            "profit_units": "",
            "roi_ready": "YES_AFTER_ACTUAL",
            "report_md": str(md_path),
            "report_json": str(json_path),
        })
    return path


def run_diagnostics() -> str:
    checks: List[Tuple[str, bool]] = []
    checks.append(("NBA roster JSON exists", NBA_JSON.exists()))
    checks.append(("WNBA roster JSON exists", WNBA_JSON.exists()))
    try:
        nba_teams = _load_json_roster(NBA_JSON, "NBA")
        checks.append(("NBA teams loaded", len(nba_teams) >= 10))
        checks.append(("Every NBA team has starters", all(len(t.get("starters", [])) >= 5 for t in nba_teams.values())))
        checks.append(("Every NBA team has injury_notes", all("injury_notes" in t for t in nba_teams.values())))
    except Exception:
        checks.append(("NBA JSON parse", False))
    try:
        wnba_teams = _load_json_roster(WNBA_JSON, "WNBA")
        checks.append(("WNBA teams loaded", len(wnba_teams) >= 10))
        checks.append(("Every WNBA team has starters", all(len(t.get("starters", [])) >= 5 for t in wnba_teams.values())))
    except Exception:
        checks.append(("WNBA JSON parse", False))
    for sport, game in (("NBA", "BOS @ NYK"), ("WNBA", "DAL @ ATL")):
        try:
            gp = build_game(sport, game, 172.5 if sport == "WNBA" else 215.5, model="full")
            d = json.dumps(gp.to_dict()).lower()
            checks.append((f"Build {sport} {game}", True))
            checks.append((f"{sport} has model_totals section", "model_totals" in d))
            checks.append((f"{sport} no tc_game_total field", "tc_game_total" not in d))
            checks.append((f"{sport} prop candidates", len(gp.prop_candidates()) > 0))
        except Exception:
            checks.append((f"Build {sport} {game}", False))
    lines = ["# Sports TC Pipeline Diagnostics", "", f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "", "| Check | Status |", "|---|---:|"]
    lines.extend(f"| {label} | {'PASS' if ok else 'FAIL'} |" for label, ok in checks)
    lines.extend(["", "## Canonical Rules", "- TC is the primary player-prop model.", "- Raw/model team and game totals are separate and never labeled TC totals.", "- NFRI, Pace, Home Court, and Momentum are optional layers for model totals."])
    text = "\n".join(lines) + "\n"
    (REPORT_DIR / "PIPELINE_DIAGNOSTICS.md").write_text(text)
    return text


def build_game(sport: str, game: str, market_total: Optional[float] = None, market_spread: Optional[float] = None, model: str = "tc") -> GameProjection:
    if "@" not in game:
        raise ValueError("Game must be formatted like 'DAL @ ATL'")
    away_code, home_code = [norm_code(x) for x in game.split("@", 1)]
    return GameProjection(away=load_team(sport, away_code), home=load_team(sport, home_code), sport=sport.upper(), market_total=market_total, market_spread=market_spread, model=model)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sports TC Pipeline v7.0")
    parser.add_argument("--sport", choices=["NBA", "WNBA"], default="WNBA")
    parser.add_argument("--game", default="DAL @ ATL")
    parser.add_argument("--total", type=float, default=None)
    parser.add_argument("--spread", type=float, default=None)
    parser.add_argument("--model", choices=["tc", "nfri", "pace", "full"], default="tc")
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--diagnostics", action="store_true")
    parser.add_argument("--list-teams", action="store_true")
    args = parser.parse_args()
    if args.list_teams:
        print(f"\n{args.sport} Teams ({len(list_available_teams(args.sport))}):")
        for code, name in list_available_teams(args.sport):
            print(f"  {code}: {name}")
        return
    if args.diagnostics:
        print(run_diagnostics())
        return
    game = build_game(args.sport, args.game, args.total, args.spread, args.model)
    if args.json:
        print(json.dumps(game.to_dict(), indent=2))
        return
    print_console_report(game)
    if args.save:
        md_path, json_path = save_game_outputs(game)
        log_path = append_backtest_seed(game, md_path, json_path)
        print(f"Report saved: {md_path}")
        print(f"Data saved:   {json_path}")
        print(f"Seed log:     {log_path}")


if __name__ == "__main__":
    main()
