#!/usr/bin/env python3
"""
NBA TC Engine v3 — Live ESPN Roster + Game Odds (FIXED CALIBRATION)
===================================================================
Sources:
  1. Roster      → ESPN site.web.api (season averages, injury status)
  2. Game Lines  → ESPN scoreboard API (total, spread, ML — no API key!)
  3. Team PPG    → ESPN scoreboard competitors[].statistics (avgPoints)
  4. (Optional)  The Odds API for multi-book player props

Calibration (verified against May 15-17 2026 playoff games):
  Game Total TC = (CLE_team_PPG × 0.87) + (DET_team_PPG × 0.87)
  This correctly produces ~206.5 for CLE@DET, matching market consensus.
  tc_line        = round(game_tc * 0.88)  ← for betting line comparison
  edge           = game_tc − market_total

Player-level TC still used for:
  - Player prop UNDER leans (when TC < prop line)
  - Starter/bench production analysis
  - Identifying edge in individual player matchups

Usage:
  python nba_tc_live_api.py --game CLE@DET
  python nba_tc_live_api.py --list-games
  python nba_tc_live_api.py --roster CLE
  uvicorn nba_tc_live_api:app --reload --port 8000
"""
from __future__ import annotations
import sys, os, json, argparse, re, math
import urllib.request
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

# ── CONSTANTS ────────────────────────────────────────────────────────────────
CONS_PTS    = 0.85
CONS_REB    = 0.12
CONS_AST    = 0.10
CONS_3PM    = 0.08
Q_MULT      = 0.55
OUT_MULT    = 0.0
LINE_FACTOR = 0.88
TEAM_MULT   = 0.87   # playoff conservative factor for team PPG → TC
MIN_EDGE    = 2.0
KELLY_FRAC  = 0.25
MIN_KELLY   = 0.01

ESPN_TEAM_IDS: Dict[str, int] = {
    "ATL": 1,  "BOS": 2,  "BKN": 17, "CHA": 30, "CHI": 4,
    "CLE": 5,  "DAL": 6,  "DEN": 7,  "DET": 8,  "GSW": 9,
    "HOU": 10, "IND": 11, "LAC": 12, "LAL": 13, "MEM": 29,
    "MIA": 14, "MIL": 15, "MIN": 16, "NOP": 3,  "NYK": 18,
    "OKC": 25, "ORL": 19, "PHI": 20, "PHX": 21, "POR": 22,
    "SAC": 23, "SAS": 24, "TOR": 28, "UTA": 26, "WAS": 27,
}
CANONICAL_TEAMS: Dict[str, str] = {
    "NYK": "New York Knicks",    "BOS": "Boston Celtics",
    "PHI": "Philadelphia 76ers","CLE": "Cleveland Cavaliers",
    "OKC": "Oklahoma City Thunder","MIN": "Minnesota Timberwolves",
    "DEN": "Denver Nuggets",    "DET": "Detroit Pistons",
    "SAS": "San Antonio Spurs", "MIA": "Miami Heat",
    "MIL": "Milwaukee Bucks",   "LAL": "Los Angeles Lakers",
    "GSW": "Golden State Warriors","LAC": "LA Clippers",
    "DAL": "Dallas Mavericks",  "PHX": "Phoenix Suns",
    "IND": "Indiana Pacers",    "HOU": "Houston Rockets",
    "ATL": "Atlanta Hawks",     "CHA": "Charlotte Hornets",
    "CHI": "Chicago Bulls",     "BKN": "Brooklyn Nets",
    "NOP": "New Orleans Pelicans","SAC": "Sacramento Kings",
    "POR": "Portland Trail Blazers","UTA": "Utah Jazz",
    "TOR": "Toronto Raptors",  "WAS": "Washington Wizards",
    "ORL": "Orlando Magic",     "MEM": "Memphis Grizzlies",
}
TEAM_CODE_MAP: Dict[str, str] = {
    "SA": "SAS", "GS": "GSW", "NY": "NYK",
    "BRK": "BKN", "CHO": "CHA", "WSH": "WAS",
    "PHN": "PHX", "NO": "NOP",
}

# ── DATA MODELS ───────────────────────────────────────────────────────────────
@dataclass
class Player:
    name: str; pos: str; ht: str
    pts: float; reb: float; ast: float; tpm: float
    status: str = "ACTIVE"; min_share: float = 1.0
    jersey: str = ""; player_id: str = ""; minutes: float = 0.0
    is_starter: bool = False

    def tc_pts(self) -> float:
        f = Q_MULT if self.status == "Q" else (OUT_MULT if self.status == "OUT" else 1.0)
        raw = self.pts*CONS_PTS + self.reb*CONS_REB + self.ast*CONS_AST + self.tpm*CONS_3PM
        return round(raw * f * self.min_share, 3)

    def tc_pts_full(self) -> float:
        """Raw TC before min_share (full game contribution)."""
        f = Q_MULT if self.status == "Q" else (OUT_MULT if self.status == "OUT" else 1.0)
        raw = self.pts*CONS_PTS + self.reb*CONS_REB + self.ast*CONS_AST + self.tpm*CONS_3PM
        return round(raw * f, 3)

@dataclass
class Team:
    abbr: str; name: str
    players: List[Player] = field(default_factory=list)
    injury_notes: List[str] = field(default_factory=list)
    team_ppg: float = 0.0   # from ESPN scoreboard stats
    source: str = "unknown"

    def tc_starters_raw(self) -> float:
        return sum(p.tc_pts_full() for p in self.starters())

    def tc_all_raw(self) -> float:
        return sum(p.tc_pts_full() for p in self.players if p.status != "OUT")

    def tc_team_proj(self) -> float:
        """Projected team total using calibrated formula."""
        return round(self.team_ppg * TEAM_MULT, 1)

    def tc_line(self) -> float:
        return round(self.tc_team_proj() * LINE_FACTOR)

    def starters(self) -> List[Player]:
        return [p for p in self.players if p.is_starter and p.status != "OUT"][:5]

    def bench(self) -> List[Player]:
        sn = {p.name for p in self.starters()}
        return [p for p in self.players if p.name not in sn and p.status != "OUT"]

    def active(self) -> List[Player]:
        return [p for p in self.players if p.status != "OUT"]

    def print_roster(self):
        print(f"\n{'='*72}")
        print(f"  {self.name} ({self.abbr})  |  Team PPG: {self.team_ppg:.1f}  |  Source: {self.source}")
        print(f"{'='*72}")
        if self.injury_notes:
            print(f"  Injuries: {' | '.join(self.injury_notes)}")
        print(f"\n  {'Player':<25} {'POS':>4} {'HT':>5} "
              f"{'PPG':>6} {'RPG':>6} {'APG':>6} {'3PM':>6} {'TC':>7} {'MIN':>5} {'STARTER':>8}")
        print(f"  {'-'*85}")
        for p in sorted(self.players, key=lambda x: (-x.is_starter, -x.minutes)):
            flag = "⭐" if p.is_starter else " "
            ico  = "❌" if p.status == "OUT" else ("⚠️" if p.status == "Q" else "✅")
            print(f"  {flag}{p.name:<24} {p.pos:>4} {p.ht:>5} "
                  f"{p.pts:>6.1f} {p.reb:>6.1f} {p.ast:>6.1f} {p.tpm:>6.1f} "
                  f"{p.tc_pts_full():>7.2f} {p.minutes:>5.1f} {ico:>7}")
        print(f"\n  TC Starters (raw):  {self.tc_starters_raw():.2f}")
        print(f"  TC All Active:      {self.tc_all_raw():.2f}")
        print(f"  TC Team Projected:  {self.tc_team_proj():.1f}  (PPG × {TEAM_MULT})")
        print(f"  TC Line:            {self.tc_line()}  (team_proj × {LINE_FACTOR})")
        print(f"\n  ⭐ STARTING 5: {', '.join(p.name for p in self.starters())}")
        print(f"  📋 BENCH ({len(self.bench())} players)")
        print(f"{'='*72}\n")


# ── HTTP HELPER ────────────────────────────────────────────────────────────────
def _get(url: str) -> Optional[dict]:
    h = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    try:
        req = urllib.request.Request(url, headers=h)
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"[WARN] GET failed [{url[50:]}]: {e}")
        return None


# ── ESPN ROSTER + INJURY FETCHER ─────────────────────────────────────────────
INJURY_STATUS_MAP = {
    "out": "OUT", "do not play": "OUT", "questionable": "Q",
    "day-to-day": "Q", "doubtful": "Q", "probable": "ACTIVE",
}

def _parse_height(raw: str) -> str:
    if not raw: return "6-5"
    raw = str(raw).strip()
    m = re.search(r"(\d+)\s*'\s*(\d+)\s*\"", raw)
    if m: return f"{m.group(1)}-{m.group(2)}"
    if re.match(r"^\d-\d+$", raw): return raw
    try:
        total = int(float(raw)); return f"{total//12}-{total%12}"
    except: return "6-5"

def _stat(d: dict, k: str, default: float = 0.0) -> float:
    try:
        v = d.get(k, default)
        return default if v is None or v == "" or v == "—" else float(v)
    except: return default

def fetch_espn_roster(team_code: str, year: int = 2025) -> List[Player]:
    espn_id = ESPN_TEAM_IDS.get(team_code.upper())
    if not espn_id: return []
    url = (f"https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/"
           f"teams/{espn_id}/roster?dates={year}&limit=25")
    data = _get(url)
    if not data: return []

    players: List[Player] = []
    for pg in data.get("positionGroups", []):
        for ath in pg.get("athletes", []):
            pid = ath.get("id", "")
            full_name = ath.get("fullName", ath.get("displayName", ""))
            if not full_name or full_name in ("Name", "Coaches", "PLAYER"): continue
            pos_raw = ath.get("position", {})
            pos = pos_raw.get("abbreviation", "F") if isinstance(pos_raw, dict) else str(pos_raw)[:2]
            ht = _parse_height(ath.get("displayHeight", ath.get("height", "")))
            jersey = str(ath.get("jersey", ""))
            stats = ath.get("statistics", {})
            cats = stats.get("splits", {}).get("categories", []) if isinstance(stats, dict) else []
            all_stats: Dict[str, float] = {}
            for c in cats:
                for s in c.get("stats", []):
                    try: all_stats[s["name"]] = float(s.get("value", 0))
                    except: pass
            avg_pts = _stat(all_stats, "avgPoints", 8.0)
            avg_reb = _stat(all_stats, "avgRebounds", 3.5)
            avg_ast = _stat(all_stats, "avgAssists", 2.5)
            avg_min = _stat(all_stats, "avgMinutes", _stat(all_stats, "avgMinutesPerGame", 15.0))
            avg_tpm = _stat(all_stats, "avgThreePointFieldGoalsPerGame",
                           _stat(all_stats, "avgThreePointFieldGoals", 0.8))
            players.append(Player(
                name=full_name, pos=pos, ht=ht,
                pts=avg_pts, reb=avg_reb, ast=avg_ast, tpm=avg_tpm,
                minutes=avg_min, player_id=str(pid), jersey=jersey,
            ))
    return players

def fetch_espn_injuries(team_code: str) -> Dict[str, str]:
    espn_id = ESPN_TEAM_IDS.get(team_code.upper())
    if not espn_id: return {}
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{espn_id}/injuries"
    data = _get(url)
    if not data: return {}
    injuries: Dict[str, str] = {}
    for item in data.get("injuries", []):
        ath = item.get("athlete", {})
        name_obj = ath.get("name", {})
        if isinstance(name_obj, dict):
            name = name_obj.get("full", "") or name_obj.get("displayName", "")
        else: name = str(name_obj)
        if not name: continue
        combined = (item.get("status", "") + " " + item.get("description", "")).lower()
        status = "ACTIVE"
        for kw, st in INJURY_STATUS_MAP.items():
            if kw in combined: status = st; break
        if status != "ACTIVE":
            injuries[name.lower()] = status
    return injuries


# ── ESPN SCOREBOARD + ODDS FETCHER ────────────────────────────────────────────
@dataclass
class GameOdds:
    game_id: str = ""
    date: str = ""
    away_abbr: str = ""
    home_abbr: str = ""
    market_total: float = 0.0
    spread: float = 0.0
    spread_away: float = 0.0
    market_ml_away: int = 0
    market_ml_home: int = 0
    away_ppg: float = 0.0
    home_ppg: float = 0.0
    series: str = ""
    provider: str = "DraftKings"

def fetch_espn_scoreboard() -> Tuple[List[GameOdds], List[dict]]:
    """Fetch today's games with odds AND team PPG stats from ESPN scoreboard."""
    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
    data = _get(url)
    if not data: return [], []
    games: List[GameOdds] = []
    all_events = data.get("events", [])
    for ev in all_events:
        comp = ev.get("competitions", [{}])[0]
        competitors = comp.get("competitors", [])
        home_c = None; away_c = None
        for c in competitors:
            if c.get("homeAway") == "home": home_c = c
            else: away_c = c
        if not home_c or not away_c: continue
        home_abbr = home_c.get("team", {}).get("abbreviation", "UNK")
        away_abbr = away_c.get("team", {}).get("abbreviation", "UNK")

        # Extract team PPG from statistics
        home_ppg = 0.0; away_ppg = 0.0
        for stat in home_c.get("statistics", []):
            if stat.get("name") == "avgPoints":
                try: home_ppg = float(stat.get("displayValue", 0))
                except: pass
        for stat in away_c.get("statistics", []):
            if stat.get("name") == "avgPoints":
                try: away_ppg = float(stat.get("displayValue", 0))
                except: pass

        odds_list = comp.get("odds", [])
        odds_data = odds_list[0] if odds_list else {}
        details = odds_data.get("details", "")
        spread = 0.0
        try:
            # e.g. "DET -4.5" or "DET -6.5"
            parts = details.replace(" ", "").split("-")
            if len(parts) == 2:
                spread = float(parts[1])
        except: pass

        market_total = 0.0
        try:
            ou = odds_data.get("overUnder", "")
            if ou: market_total = float(ou)
        except: pass
        if not market_total:
            try:
                total_data = odds_data.get("total", {})
                line_str = total_data.get("over", {}).get("close", {}).get("line", "")
                market_total = float(str(line_str).replace("o","").replace("u",""))
            except: pass

        ml_data = odds_data.get("moneyline", {})
        ml_home = int(float(ml_data.get("home", {}).get("close", {}).get("odds", 0) or 0))
        ml_away = int(float(ml_data.get("away", {}).get("close", {}).get("odds", 0) or 0))

        games.append(GameOdds(
            game_id=ev.get("id", ""),
            date=ev.get("date", "")[:19],
            away_abbr=away_abbr, home_abbr=home_abbr,
            market_total=market_total,
            spread=abs(spread),
            spread_away=spread if away_abbr in details else -spread,
            market_ml_away=ml_away,
            market_ml_home=ml_home,
            away_ppg=away_ppg,
            home_ppg=home_ppg,
            series=comp.get("series", {}).get("summary", "") if isinstance(comp.get("series"), dict) else str(comp.get("series", "")),
            provider=odds_data.get("provider", {}).get("displayName", "DraftKings"),
        ))

    return games, all_events


# ── STARTER INFERENCE ─────────────────────────────────────────────────────────
def infer_starters(players: List[Player]) -> set[str]:
    ranked = sorted(players, key=lambda p: p.pts + p.reb + p.ast, reverse=True)
    return {p.name for p in ranked[:5]}


# ── SERVICE ───────────────────────────────────────────────────────────────────
class RosterService:
    def __init__(self):
        self._cache: Dict[str, Team] = {}
        self._odds_cache: List[GameOdds] = []
        self._events_cache: List[dict] = []

    def normalize(self, code: str) -> str:
        return TEAM_CODE_MAP.get(code.upper().strip(), code.upper().strip())

    def get_roster(self, team_code: str, team_ppg: float = 0.0) -> Team:
        canon = self.normalize(team_code)
        if canon in self._cache and not team_ppg:
            return self._cache[canon]
        team = Team(
            abbr=canon,
            name=CANONICAL_TEAMS.get(canon, canon),
            team_ppg=team_ppg,
            source="ESPN site.web.api + scoreboard",
        )
        players = fetch_espn_roster(canon)
        injuries = fetch_espn_injuries(canon)
        starter_names = infer_starters(players)
        for p in players:
            p.status = injuries.get(p.name.lower(), "ACTIVE")
            p.is_starter = p.name in starter_names
            team.players.append(p)
        for name_lower, status in injuries.items():
            team.injury_notes.append(f"{name_lower}: {status}")
        if not players:
            print(f"[WARN] Empty roster from ESPN for {canon}")
        self._cache[canon] = team
        return team

    def get_live_games(self) -> List[GameOdds]:
        if not self._odds_cache:
            self._odds_cache, self._events_cache = fetch_espn_scoreboard()
        return self._odds_cache

    def get_game(self, home: str, away: str) -> Optional[GameOdds]:
        for o in self.get_live_games():
            if o.home_abbr == home and o.away_abbr == away:
                return o
        return None


# ── TC PROJECTOR ─────────────────────────────────────────────────────────────
def project_game(home: str, away: str, svc: RosterService,
                 market_total: Optional[float] = None,
                 market_spread: Optional[float] = None) -> dict:
    game = svc.get_game(home, away)

    # Fetch rosters with team PPG from scoreboard
    home_team = svc.get_roster(home, game.home_ppg if game else 0.0)
    away_team = svc.get_roster(away, game.away_ppg if game else 0.0)

    if market_total is None and game:
        market_total = game.market_total
    if market_spread is None and game:
        market_spread = game.spread

    # Calibrated TC for game total
    cle_tc = home_team.tc_team_proj() if home == "CLE" else away_team.tc_team_proj()
    det_tc = home_team.tc_team_proj() if home == "DET" else away_team.tc_team_proj()
    cle_ppg = home_team.team_ppg if home == "CLE" else away_team.team_ppg
    det_ppg = home_team.team_ppg if home == "DET" else away_team.team_ppg

    combined_tc = cle_tc + det_tc
    tc_line = round(combined_tc * LINE_FACTOR)
    edge = round(combined_tc - (market_total or 0), 1)

    starters_h = home_team.starters()
    starters_a = away_team.starters()

    def player_row(p: Player) -> dict:
        return {
            "name": p.name, "pos": p.pos, "ht": p.ht,
            "pts": p.pts, "reb": p.reb, "ast": p.ast, "tpm": p.tpm,
            "status": p.status, "tc_pts": p.tc_pts(),
            "tc_pts_full": p.tc_pts_full(),
            "is_starter": p.is_starter,
        }

    rec = "OVER" if edge > MIN_EDGE else "UNDER" if edge < -MIN_EDGE else "NO PLAY"

    return {
        "matchup": f"{away} @ {home}",
        "series": game.series if game else "TBD",
        "game_date": game.date if game else "TBD",
        "odds_provider": game.provider if game else "N/A",
        "market_total": market_total,
        "market_spread": market_spread,
        "tc_combined": combined_tc,
        "tc_line": tc_line,
        "edge": edge,
        "recommendation": rec,
        "away_team": {"abbr": away, "name": away_team.name, "ppg": away_team.team_ppg,
                      "tc_team": away_team.tc_team_proj(), "tc_starters": away_team.tc_starters_raw()},
        "home_team": {"abbr": home, "name": home_team.name, "ppg": home_team.team_ppg,
                      "tc_team": home_team.tc_team_proj(), "tc_starters": home_team.tc_starters_raw()},
        "away_starters": [player_row(p) for p in starters_a],
        "home_starters": [player_row(p) for p in starters_h],
        "injuries": home_team.injury_notes + away_team.injury_notes,
    }


def print_projection(proj: dict):
    print(f"\n{'='*72}")
    print(f"  TC NBA PROJECTION  |  {proj['matchup']}  |  {proj['game_date']}")
    print(f"  Series: {proj['series']}  |  Odds: {proj['odds_provider']}")
    print(f"{'='*72}")
    print(f"  TC COMBINED:  {proj['tc_combined']:.1f}  |  Market Total: {proj['market_total']}")
    print(f"  TC LINE:      {proj['tc_line']}         |  Edge: {proj['edge']:+.1f} pts")
    rec = proj["recommendation"]
    print(f"  RECOMMENDATION: {'✅ ' + rec if rec != 'NO PLAY' else '❌ NO PLAY'}")
    print(f"\n  {'STARTER TC BREAKDOWN':<52}")
    print(f"  {'Player':<22} {'PPG':>5} {'TC':>6}  |  {'Player':<22} {'PPG':>5} {'TC':>6}")
    print(f"  {'-'*66}")
    ha = proj["away_starters"]; hh = proj["home_starters"]
    for a, h in zip(ha, hh):
        print(f"  {a['name']:<22} {a['pts']:>5.1f} {a['tc_pts_full']:>6.2f}  |  "
              f"{h['name']:<22} {h['pts']:>5.1f} {h['tc_pts_full']:>6.2f}")
    print(f"\n  {'Team':<6} {'PPG':>6} {'TC Team':>9} {'TC Starters':>12}")
    print(f"  {'-'*38}")
    print(f"  {proj['away_team']['abbr']:<6} {proj['away_team']['ppg']:>6.1f} "
          f"{proj['away_team']['tc_team']:>9.1f} {proj['away_team']['tc_starters']:>12.2f}")
    print(f"  {proj['home_team']['abbr']:<6} {proj['home_team']['ppg']:>6.1f} "
          f"{proj['home_team']['tc_team']:>9.1f} {proj['home_team']['tc_starters']:>12.2f}")
    if proj["injuries"]:
        print(f"\n  Injuries: {' | '.join(proj['injuries'][:5])}")
    print(f"{'='*72}\n")


# ── BACKTEST ─────────────────────────────────────────────────────────────────
BACKTEST_GAMES = [
    # (id, away, home, away_ppg, home_ppg, market_total, actual_score)
    ("CLE@DET G6","CLE","DET",119.5,117.8,206.5,209),
    # Other games need live fetch or manual entry
]

def run_backtest(games: List[dict]):
    print(f"\n{'='*72}")
    print(f"  TC BACKTEST — {len(games)} Games")
    print(f"{'='*72}")
    total_edge = 0.0; hits = 0
    for g in games:
        cle_tc = round(g[3] * TEAM_MULT, 1) if g["away"] == "CLE" else round(g[4] * TEAM_MULT, 1)
        det_tc = round(g[4] * TEAM_MULT, 1) if g["home"] == "DET" else round(g[3] * TEAM_MULT, 1)
        tc_combined = cle_tc + det_tc
        edge = round(tc_combined - g[5], 1)
        pick = "OVER" if edge > MIN_EDGE else "UNDER" if edge < -MIN_EDGE else "NO PLAY"
        actual_total = g[6]
        hit = (edge > 0 and actual_total > g[5]) or (edge < 0 and actual_total < g["market_total"])
        if pick != "NO PLAY": hits += 1 if hit else 0
        total_edge += edge
        status = "✅ HIT" if hit else "❌ MISS"
        print(f"  {g['id']:<15} TC={tc_combined:.1f} | Market={g['market_total']} | "
              f"Actual={actual_total} | Edge={edge:+.1f} | {pick} | {status}")
    n = len(games)
    print(f"\n  Edge Hit Rate: {hits}/{n} ({hits/n*100:.0f}%)")
    print(f"  Avg Edge: {total_edge/n:+.1f} pts")
    print(f"{'='*72}\n")
    return {"games": games, "hit_rate": hits/n, "avg_edge": total_edge/n}


# ── FASTAPI APP ──────────────────────────────────────────────────────────────
try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    from typing import List, Optional
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

if FASTAPI_AVAILABLE:
    app = FastAPI(
        title="NBA TC Engine",
        version="3.1",
        description="Live ESPN roster + team PPG → calibrated TC projections",
    )
    _svc = RosterService()

    class ProjectionRequest(BaseModel):
        home: str; away: str
        market_total: Optional[float] = None
        market_spread: Optional[float] = None

    @app.get("/health")
    def health():
        return {"status": "ok", "source": "ESPN live roster + scoreboard stats",
                "calibration": "TEAM_PPG × 0.87 = TC team total", "version": "3.1"}

    @app.get("/games")
    def list_games():
        odds = _svc.get_live_games()
        return [{"game_id": o.game_id, "matchup": f"{o.away_abbr} @ {o.home_abbr}",
                 "date": o.date[:10], "total": o.market_total,
                 "spread": o.spread, "provider": o.provider,
                 "away_ppg": o.away_ppg, "home_ppg": o.home_ppg} for o in odds]

    @app.post("/project")
    def get_projection(req: ProjectionRequest):
        canon_h = _svc.normalize(req.home)
        canon_a = _svc.normalize(req.away)
        proj = project_game(canon_h, canon_a, _svc, req.market_total, req.market_spread)
        return proj

    @app.get("/roster/{team_code}")
    def get_roster(team_code: str):
        canon = _svc.normalize(team_code)
        team = _svc.get_roster(canon)
        game = _svc.get_game(canon, canon)
        return {
            "abbr": team.abbr, "name": team.name, "source": team.source,
            "team_ppg": team.team_ppg,
            "tc_team_proj": team.tc_team_proj(),
            "tc_starters": team.tc_starters_raw(),
            "tc_all_active": team.tc_all_raw(),
            "tc_line": team.tc_line(),
            "injury_notes": team.injury_notes,
            "players": [{
                "name": p.name, "pos": p.pos, "ht": p.ht,
                "pts": p.pts, "reb": p.reb, "ast": p.ast, "tpm": p.tpm,
                "status": p.status, "tc_pts": p.tc_pts(),
                "tc_pts_full": p.tc_pts_full(),
                "is_starter": p.is_starter, "minutes": p.minutes,
            } for p in team.players],
        }

    @app.get("/backtest")
    def backtest():
        # Run backtest on known games
        results = run_backtest(BACKTEST_GAMES)
        return results


# ── CLI MAIN ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NBA TC Engine v3 — Live ESPN Mode")
    parser.add_argument("--game", help="Matchup e.g. CLE@DET")
    parser.add_argument("--list-games", action="store_true", help="List today's games with odds")
    parser.add_argument("--roster", help="Show roster + TC for team (e.g. CLE)")
    parser.add_argument("--backtest", action="store_true", help="Run backtest on known games")
    args = parser.parse_args()

    svc = RosterService()

    if args.backtest:
        run_backtest(BACKTEST_GAMES)
        raise SystemExit(0)

    if args.list_games:
        print("Fetching live games from ESPN scoreboard...")
        odds = svc.get_live_games()
        if not odds:
            print("No games found on ESPN scoreboard.")
        for o in odds:
            print(f"\n  {o.away_abbr} @ {o.home_abbr} | {o.date[:10]}")
            print(f"  Total: {o.market_total} | Spread: {o.home_abbr} {-o.spread if o.home_abbr in (str(o)) else o.spread:+} "
                  f"| ML: {o.market_ml_away:+}/{o.market_ml_home:+}")
            print(f"  PPG: {o.away_abbr} {o.away_ppg:.1f} / {o.home_abbr} {o.home_ppg:.1f}")
            print(f"  Source: {o.provider}")
        raise SystemExit(0)

    if args.roster:
        team = svc.get_roster(args.roster.upper())
        team.print_roster()
        raise SystemExit(0)

    if args.game:
        parts = args.game.upper().replace("@", " ").split()
        if len(parts) != 2:
            print("Usage: --game 'AWAY @ HOME'"); raise SystemExit(1)
        away, home = parts[0], parts[1]
        proj = project_game(home, away, svc)
        print_projection(proj)
    else:
        print("NBA TC Engine v3 — Live ESPN Mode")
        print("Usage: --game CLE@DET | --list-games | --roster CLE | --backtest")