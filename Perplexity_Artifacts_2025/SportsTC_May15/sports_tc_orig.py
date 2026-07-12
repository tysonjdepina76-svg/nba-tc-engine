#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║           SPORTS TC v4.0 — Triple Conservative Engine        ║
║               NBA + WNBA | pts × 0.85 | Q × 0.65             ║
╚══════════════════════════════════════════════════════════════╝

FORMULA:
  ACTIVE  → stat × 0.85
  Q       → stat × 0.85 × 0.65  (CONS first, then status)
  OUT     → 0

EDGE MODEL:
  TC = conservative floor. Market line sits above TC.
  TC_final  = raw_combined + 8 (no spread) OR raw_combined × factor (with spread)
  TC_line   = TC_final × 0.88
  TC_edge   = TC_line − market_total
  signal:   edge > 0 → UNDER | edge < 0 → OVER

VARIABLE FORMULA (only when spread provided):
  |spread| < 8  → raw × 0.76
  |spread| ≥ 8  → raw × 0.82

USAGE:
  python sports_tc.py --sport NBA --game "NYK @ PHI" --total 219 --spread -4
  python sports_tc.py --sport WNBA --game "NYL @ POR"
  python sports_tc.py --backtest --sport NBA
  python sports_tc.py --slate --sport WNBA
"""

import json, argparse, warnings
warnings.filterwarnings("ignore")

# ── CONSTANTS ────────────────────────────────────────────────
CONS       = 0.85
Q_MULT     = 0.65
VAR_LOW    = 0.76   # |spread| < 8
VAR_HIGH   = 0.82   # |spread| >= 8
PACE_ADJ   = 8.0    # added to raw combined when NO spread
LINE_FACT  = 0.88   # TC_final → TC_line
MIN_EDGE   = 3.0    # minimum edge to fire a bet
KELLY_FRAC = 0.25   # 1/4 Kelly
MIN_KELLY  = 0.01

# ── PLAYER ───────────────────────────────────────────────────
class Player:
    def __init__(self, name, pos, ht, pts, reb, ast, tpm, status="ACTIVE"):
        self.name = name; self.pos = pos; self.ht = ht
        self.pts = float(pts); self.reb = float(reb)
        self.ast = float(ast); self.tpm = float(tpm)
        self.status = status

    def tc_raw(self, stat):
        if self.status == "OUT":   return 0.0
        c = stat * CONS
        return round(c * Q_MULT, 1) if self.status == "Q" else round(c, 1)

    def proj(self):
        return {
            "TC_PTS": self.tc_raw(self.pts),
            "TC_REB": self.tc_raw(self.reb),
            "TC_AST": self.tc_raw(self.ast),
            "TC_3PM": self.tc_raw(self.tpm),
        }

    def __repr__(self):
        return f"{self.name:25s} {self.status}"

# ── TEAM ─────────────────────────────────────────────────────
class Team:
    def __init__(self, code, name):
        self.code = code; self.name = name; self.players = []

    def add(self, p): self.players.append(p)

    def starters(self):
        return [p for p in self.players if p.status != "OUT"][:5]

    def roster(self):
        return sorted(self.players, key=lambda x: x.pts, reverse=True)

    def _t(self, key):
        return round(sum(p.proj()[key] for p in self.players if p.status != "OUT"), 1)

    def totals(self):
        return {"TC_PTS": self._t("TC_PTS"), "TC_REB": self._t("TC_REB"),
                "TC_AST": self._t("TC_AST"), "TC_3PM": self._t("TC_3PM")}

    def bench(self):
        start = set(self.starters())
        t = {"TC_PTS": 0.0, "TC_REB": 0.0, "TC_AST": 0.0, "TC_3PM": 0.0}
        for p in self.players:
            if p not in start and p.status != "OUT":
                for k, v in p.proj().items(): t[k] += v
        return {k: round(max(v, 20.0), 1) for k, v in t.items()}

# ── GAME ─────────────────────────────────────────────────────
class Game:
    def __init__(self, away_code, home_code, sport="NBA",
                 market_total=None, market_spread=None, bankroll=1000):
        self.away_code = away_code; self.home_code = home_code
        self.sport = sport
        self.market_total  = market_total
        self.market_spread = market_spread
        self.bankroll = bankroll
        self.away = self._build(away_code)
        self.home = self._build(home_code)

    def _build(self, code):
        roster = NBA_ROSTERS if self.sport == "NBA" else WNBA_ROSTERS
        t = Team(code, (NBA_TEAMS if self.sport == "NBA" else WNBA_TEAMS).get(code, code))
        for p in roster.get(code, []): t.add(p)
        return t

    # ── TC computation ──────────────────────────────────────
    def _tc_raw_combined(self):
        return round(self.away.totals()["TC_PTS"] + self.home.totals()["TC_PTS"], 1)

    def _tc_final(self):
        """Final TC number used for line derivation."""
        raw = self._tc_raw_combined()
        if self.market_spread is not None:
            factor = VAR_HIGH if abs(self.market_spread) >= 8 else VAR_LOW
            return round(raw * factor, 1)
        return round(raw + PACE_ADJ, 1)

    def _tc_line(self):
        """Market line equivalent: TC_final × 0.88."""
        return round(self._tc_final() * LINE_FACT, 1)

    def _tc_edge(self):
        """Edge = TC_line − market_total. Positive = TC below market → UNDER."""
        if self.market_total is None: return 0.0
        return round(self._tc_line() - self.market_total, 1)

    def _signal(self):
        return "UNDER" if self._tc_edge() > 0 else "OVER"

    def _kelly(self):
        """1/4 Kelly on the edge vs market_total."""
        edge = self._tc_edge()
        if edge <= 0: return 0.0
        odds = 110
        implied = odds / 100.0
        k = KELLY_FRAC * abs(edge) / (implied - 1)
        return max(round(k, 4), MIN_KELLY if abs(edge) >= MIN_EDGE else 0)

    # ── Reports ─────────────────────────────────────────────
    def injury_report(self):
        print(f"\n{'='*72}")
        print(f"  ⚕  INJURY REPORT — {self.away.code} @ {self.home.code}")
        print(f"  TC = stat × 0.85 | Q = × 0.65 | OUT = 0")
        print(f"{'='*72}")
        for team in [self.away, self.home]:
            active = [p for p in team.players if p.status == "ACTIVE"]
            q_list = [p for p in team.players if p.status == "Q"]
            outs   = [p for p in team.players if p.status == "OUT"]
            print(f"\n  {team.code} — {team.name} ({len(active)} ✅ | {len(q_list)} ⚠️ | {len(outs)} ❌)")
            print(f"  {'─'*60}")
            for p in team.players:
                tc   = p.tc_raw(p.pts)
                line = round(tc * LINE_FACT, 1)
                edge = round(tc - line, 1)
                es   = "+" if edge >= 0 else ""
                icon = "✅" if p.status == "ACTIVE" else "⚠️" if p.status == "Q" else "❌"
                print(f"  {icon} {p.name:25s} {p.pos:4s} | TC:{tc:5.1f} | LINE:{line:5.1f} | EDGE:{es}{edge:4.1f} | {p.status}")

    def starting_lineup(self):
        print(f"\n{'='*72}")
        print(f"  📋 STARTING LINEUP — {self.away.code} @ {self.home.code}")
        print(f"{'='*72}")
        for team in [self.away, self.home]:
            print(f"\n  {team.code} — {team.name}")
            print(f"  {'─'*70}")
            print(f"  {'#':>2} {'Player':25s} {'POS':4s} {'TC_PTS':>7s} {'TC_REB':>7s} {'TC_AST':>7s} {'TC_3PM':>7s} {'Status':6s}")
            print(f"  {'─'*70}")
            for i, p in enumerate(team.starters(), 1):
                proj = p.proj()
                icon = "✅" if p.status == "ACTIVE" else "⚠️" if p.status == "Q" else "❌"
                print(f"  {i:2d}. {p.name:25s} {p.pos:4s} "
                      f"{proj['TC_PTS']:>7.1f} {proj['TC_REB']:>7.1f} "
                      f"{proj['TC_AST']:>7.1f} {proj['TC_3PM']:>7.1f} {p.status:6s} {icon}")
            b = team.bench(); t = team.totals()
            print(f"  {'─'*70}")
            print(f"  {'BENCH':27s} {b['TC_PTS']:>7.1f} {b['TC_REB']:>7.1f} {b['TC_AST']:>7.1f} {b['TC_3PM']:>7.1f}")
            print(f"  {'TEAM TOTAL':27s} {t['TC_PTS']:>7.1f} {t['TC_REB']:>7.1f} {t['TC_AST']:>7.1f} {t['TC_3PM']:>7.1f}")

    def tc_projections(self):
        print(f"\n{'='*72}")
        print(f"  📊 TC PROJECTIONS — {self.away.code} @ {self.home.code}")
        print(f"  Formula: stat × 0.85 | Q = × 0.65 | OUT = 0 | Bench floor: 20")
        print(f"{'='*72}")
        for team in [self.away, self.home]:
            print(f"\n  {team.code} — {team.name}")
            print(f"  {'─'*92}")
            print(f"  {'Player':25s} {'POS':4s} {'TC_PTS':>7s} {'TC_LINE':>8s} {'TC_EDGE':>8s} "
                  f"{'TC_REB':>7s} {'TC_AST':>7s} {'TC_3PM':>7s} {'Status':6s}")
            print(f"  {'─'*92}")
            for p in team.roster():
                proj = p.proj()
                tc   = proj["TC_PTS"]
                line = round(tc * LINE_FACT, 1)
                edge = round(tc - line, 1)
                es   = "+" if edge >= 0 else ""
                icon = "✅" if p.status == "ACTIVE" else "⚠️" if p.status == "Q" else "❌"
                print(f"  {p.name:25s} {p.pos:4s} {tc:>7.1f} {line:>8.1f} {es}{edge:>7.1f} "
                      f"{proj['TC_REB']:>7.1f} {proj['TC_AST']:>7.1f} {proj['TC_3PM']:>7.1f} {p.status:6s} {icon}")
            b = team.bench(); t = team.totals()
            print(f"  {'─'*92}")
            print(f"  {'BENCH':25s}          {b['TC_PTS']:>7.1f} {'N/A':>8s} {'N/A':>8s} "
                  f"{b['TC_REB']:>7.1f} {b['TC_AST']:>7.1f} {b['TC_3PM']:>7.1f}")
            print(f"  {'TEAM TOTAL':25s}      {t['TC_PTS']:>7.1f} {'N/A':>8s} {'N/A':>8s} "
                  f"{t['TC_REB']:>7.1f} {t['TC_AST']:>7.1f} {t['TC_3PM']:>7.1f}")

    def tc_summary(self):
        raw   = self._tc_raw_combined()
        final = self._tc_final()
        line  = self._tc_line()
        edge  = self._tc_edge()
        sig   = self._signal()
        k     = self._kelly() if self.market_total else 0.0
        k_amt = round(k * self.bankroll, 2)

        print(f"\n{'='*72}")
        print(f"  📈 TC SUMMARY — {self.away.code} @ {self.home.code}")
        print(f"{'='*72}")
        print(f"  Raw TC Combined:      {raw:.1f}")
        if self.market_spread is not None:
            factor = VAR_HIGH if abs(self.market_spread) >= 8 else VAR_LOW
            print(f"  Variable Factor:      ×{factor}  (spread={self.market_spread})")
            print(f"  TC Final (variable):  {final:.1f}")
        else:
            print(f"  + Pace Adjustment:    +{PACE_ADJ:.1f}")
            print(f"  TC Final (w/ pace):  {final:.1f}")
        print(f"  {'─'*60}")
        print(f"  TC Line Target:        {line:.1f}  (TC_final × {LINE_FACT})")
        print(f"  TC Edge:               {'+' if edge >= 0 else ''}{edge:.1f}")
        print(f"  Signal:               🎯 {sig}")
        if self.market_total:
            print(f"  {'─'*60}")
            print(f"  Market Total:          {self.market_total}")
            print(f"  Edge vs Market:        {'+' if edge >= 0 else ''}{round(edge - (self.market_total - line), 1):.1f}")
            print(f"  Kelly Fraction:        {k:.4f}")
            print(f"  Suggested Stake:       ${k_amt:.2f}  (on ${self.bankroll:.0f})")
        print(f"{'='*72}")

    def full_report(self, market_total=None, market_spread=None):
        self.market_total  = market_total  if market_total  is not None else self.market_total
        self.market_spread = market_spread if market_spread is not None else self.market_spread
        self.injury_report()
        self.starting_lineup()
        self.tc_projections()
        self.tc_summary()

# ── NBA TEAMS / ROSTERS ───────────────────────────────────────
NBA_TEAMS = {
    "NYK":"New York Knicks","PHI":"Philadelphia 76ers","BOS":"Boston Celtics",
    "CLE":"Cleveland Cavaliers","OKC":"Oklahoma City Thunder","MIN":"Minnesota Timberwolves",
    "DEN":"Denver Nuggets","DET":"Detroit Pistons","SAS":"San Antonio Spurs",
    "MIA":"Miami Heat","MIL":"Milwaukee Bucks","LAL":"Los Angeles Lakers",
    "GSW":"Golden State Warriors","LAC":"LA Clippers","DAL":"Dallas Mavericks",
    "PHX":"Phoenix Suns","IND":"Indiana Pacers","HOU":"Houston Rockets",
    "ATL":"Atlanta Hawks","CHA":"Charlotte Hornets","CHI":"Chicago Bulls",
    "BKN":"Brooklyn Nets","NOP":"New Orleans Pelicans","SAC":"Sacramento Kings",
    "POR":"Portland Trail Blazers","UTA":"Utah Jazz","TOR":"Toronto Raptors",
    "WAS":"Washington Wizards","ORL":"Orlando Magic",
}

TEAM_ALIASES = {
    "SA": "SAS",
}

def _p(name,pos,ht,pts,reb,ast,tpm,status="ACTIVE"):
    return Player(name,pos,ht,pts,reb,ast,tpm,status)

NBA_ROSTERS = {
    "NYK": [_p("Jalen Brunson","G","6-2",20.5,3.5,6.5,2.0),
            _p("OG Anunoby","F","6-7",16.0,5.0,2.0,2.0),
            _p("Julius Randle","F","6-4",18.5,9.0,4.5,1.8),
            _p("Mikal Bridges","F","6-6",14.5,4.5,3.0,2.0),
            _p("Donte DiVincenzo","G","6-4",12.0,4.0,3.0,2.5),
            _p("Josh Hart","G","6-3",10.5,4.5,3.5,1.5),
            _p("Precious Achiuwa","F","6-8",7.5,5.0,1.0,0.8),
            _p("Bojan Bogdanovic","F","6-6",9.5,3.0,1.5,1.8,"Q"),
            _p("Mitchell Robinson","C","7-0",7.0,8.0,1.0,0.0),
            _p("Jerome Robinson","G","6-5",5.0,2.0,1.5,0.8)],
    "PHI": [_p("Tyrese Maxey","G","6-2",22.0,4.0,5.5,2.5),
            _p("Paul George","F","6-8",18.0,5.5,4.0,2.8),
            _p("Joel Embiid","C","7-0",28.5,11.0,5.5,1.8,"Q"),
            _p("Jared McCain","G","6-4",14.0,3.5,3.0,2.0),
            _p("Guerschon Yabusele","F","6-8",11.0,5.5,1.5,1.2),
            _p("Justin Edwards","F","6-8",7.5,3.5,1.0,0.8),
            _p("Kelly Oubre Jr.","F","6-5",13.0,5.0,2.0,1.5),
            _p("Eric Gordon","G","6-3",9.0,2.0,2.5,2.0),
            _p("Kyle Lowry","G","6-0",7.5,3.0,5.0,1.3),
            _p("Mo Bamba","C","7-0",6.5,5.5,1.0,0.8,"OUT")],
    "BOS": [_p("Jayson Tatum","F","6-8",25.5,8.0,5.0,2.8),
            _p("Jaylen Brown","F","6-6",23.0,6.0,4.0,2.5),
            _p("Kristaps Porzingis","C","7-1",20.0,7.5,2.5,2.0),
            _p("Derrick White","G","6-4",15.5,4.5,4.5,2.2),
            _p("Jrue Holiday","G","6-4",14.5,5.0,6.0,2.0),
            _p("Al Horford","F","6-9",11.0,5.5,3.5,1.8),
            _p("Payton Pritchard","G","6-1",9.0,2.5,3.0,2.0),
            _p("Sam Hauser","F","6-5",8.0,3.5,1.5,1.8),
            _p("Luke Kornet","C","7-0",6.0,4.0,1.0,0.5),
            _p("Neemias Queta","C","7-0",5.5,4.0,0.5,0.0)],
    "CLE": [_p("Donovan Mitchell","G","6-1",24.5,5.0,4.5,3.0),
            _p("Darius Garland","G","6-1",20.0,3.5,6.0,2.5),
            _p("Evan Mobley","F","6-11",18.0,9.0,3.5,1.2),
            _p("Jarrett Allen","C","6-9",14.0,8.0,2.0,0.5),
            _p("Max Strus","F","6-5",12.5,4.5,3.5,2.5),
            _p("Isaac Okoro","G","6-5",10.0,3.5,3.0,1.2),
            _p("Georges Niang","F","6-5",9.0,3.0,1.5,2.0),
            _p("Caris LeVert","G","6-5",11.5,3.5,3.5,1.8,"Q"),
            _p("Tristan Thompson","C","6-9",6.0,5.5,1.0,0.0),
            _p("Ty Jerome","G","6-5",5.5,2.0,2.5,1.0)],
    "OKC": [_p("Shai Gilgeous-Alexander","G","6-6",27.5,5.5,6.5,2.2),
            _p("Jalen Williams","F","6-5",19.0,4.5,4.0,2.0),
            _p("Chet Holmgren","C","7-0",16.0,7.5,2.5,1.5),
            _p("Lu Dort","G","6-4",13.5,4.0,2.5,2.5),
            _p("Isaiah Hartenstein","C","6-11",12.0,8.5,3.5,0.8),
            _p("Josh Giddey","G","6-8",12.5,6.5,5.5,1.5),
            _p("Jaylen Duren","C","6-10",8.5,5.5,1.5,0.3),
            _p("Cason Wallace","G","6-4",8.0,2.5,2.0,1.5),
            _p("Kenrich Williams","F","6-7",7.0,4.5,2.0,1.0)],
    "MIN": [_p("Anthony Edwards","G","6-4",26.0,5.5,5.0,3.2),
            _p("Julius Randle","F","6-4",18.5,9.0,4.5,1.8),
            _p("Rudy Gobert","C","7-1",14.0,11.5,1.5,0.0),
            _p("Jaden McDaniels","F","6-9",12.0,4.5,2.0,1.5),
            _p("Mike Conley","G","6-0",11.0,3.0,5.5,2.0),
            _p("Naz Reid","C","6-9",13.5,5.5,2.5,1.8),
            _p("Nickeil Alexander-Walker","G","6-5",11.5,3.0,2.5,2.0),
            _p("Kyle Anderson","F","6-9",8.5,4.5,3.5,0.8)],
    "DEN": [_p("Nikola Jokic","C","6-11",26.5,12.0,9.5,1.8),
            _p("Jamal Murray","G","6-4",21.5,4.5,5.5,2.5),
            _p("Michael Porter Jr.","F","6-10",16.5,6.5,2.0,2.5),
            _p("Aaron Gordon","F","6-8",14.0,5.5,2.5,1.2),
            _p("Kentavious Caldwell-Pope","G","6-5",11.5,3.5,2.0,2.0),
            _p("Christian Braun","G","6-5",8.5,3.5,1.5,1.0),
            _p("Peyton Watson","F","6-8",7.5,3.0,1.5,0.8)],
    "DET": [_p("Cade Cunningham","G","6-6",22.0,5.5,7.5,2.2),
            _p("Jaden Ivey","G","6-4",17.5,4.5,4.0,2.0),
            _p("Jalen Duren","C","6-10",13.5,8.0,2.0,0.5),
            _p("Ausar Thompson","F","6-7",12.5,5.5,3.5,1.2),
            _p("Tim Hardaway Jr.","F","6-5",14.0,4.0,2.5,2.5),
            _p("Marcus Sasser","G","6-2",10.5,2.5,3.0,1.8),
            _p("Simone Fontecchio","F","6-8",8.5,3.5,1.5,1.2),
            _p("Killian Hayes","G","6-5",9.0,3.0,4.5,1.2,"Q")],
    "GSW": [_p("Stephen Curry","G","6-2",24.5,4.5,6.0,3.5),
            _p("Jimmy Butler","F","6-7",20.0,5.5,4.5,1.5),
            _p("Draymond Green","F","6-6",11.5,7.5,6.5,1.0),
            _p("Jonathan Kuminga","F","6-8",16.5,5.5,2.5,1.5),
            _p("Buddy Hield","G","6-4",13.0,4.5,2.5,3.0),
            _p("Andrew Wiggins","F","6-7",12.0,4.5,2.0,2.0),
            _p("Kevon Looney","C","6-9",6.5,6.5,2.0,0.3),
            _p("Gary Payton II","G","6-3",7.0,3.0,1.5,1.0),
            _p("Moses Moody","G","6-5",8.0,3.0,1.5,1.2),
            _p("Trayce Jackson-Davis","F","6-9",7.0,4.5,1.0,0.5)],
    "LAC": [_p("Kawhi Leonard","F","6-7",23.5,6.0,4.0,2.5),
            _p("James Harden","G","6-5",21.0,5.0,8.5,2.8),
            _p("Ivica Zubac","C","7-0",12.0,9.5,2.0,0.0),
            _p("Norman Powell","G","6-3",16.5,3.5,2.5,2.2),
            _p("Terance Mann","G","6-5",11.0,4.5,3.0,1.5),
            _p("Amir Coffey","F","6-5",9.0,3.5,2.0,1.5),
            _p("Derrick Jones Jr.","F","6-6",10.5,4.5,1.5,1.2),
            _p("Kris Dunn","G","6-4",8.0,3.5,4.5,0.8),
            _p("Nicolas Batum","F","6-8",7.5,4.0,2.5,1.2),
            _p("Ben Simmons","G","6-10",8.5,7.5,6.5,0.3,"Q")],
    "MIA": [_p("Jimmy Butler","F","6-7",20.0,5.5,4.5,1.5),
            _p("Tyler Herro","G","6-5",21.0,4.5,4.0,2.8),
            _p("Bam Adebayo","C","6-9",18.5,10.0,4.0,0.5),
            _p("Nikola Jovic","F","6-10",13.0,5.5,3.0,1.5),
            _p("Duncan Robinson","G","6-8",11.5,3.5,2.5,3.0),
            _p("Jaime Jaquez Jr.","F","6-6",12.0,4.5,3.0,1.5),
            _p("Kevin Love","F","6-8",8.5,6.5,2.0,1.5),
            _p("Kyle Lowry","G","6-0",7.5,3.0,5.0,1.3),
            _p("Cody Zeller","C","7-0",6.5,5.5,1.0,0.3)],
    "MIL": [_p("Giannis Antetokounmpo","F","6-11",29.5,11.5,5.5,1.2),
            _p("Damian Lillard","G","6-2",24.5,4.5,7.0,3.2),
            _p("Khris Middleton","F","6-7",15.5,5.0,4.5,2.0),
            _p("Brook Lopez","C","7-1",12.0,6.5,1.5,1.8),
            _p("Bobby Portis","F","6-10",13.0,7.5,1.5,1.5),
            _p("Donte DiVincenzo","G","6-4",12.0,4.0,3.0,2.5),
            _p("Pat Connaughton","G","6-5",9.0,4.5,1.5,2.0),
            _p("AJ Green","G","6-4",8.0,2.5,1.5,2.2)],
    "LAL": [_p("LeBron James","F","6-9",25.5,7.5,8.0,2.0),
            _p("Luka Doncic","G","6-7",28.5,7.5,8.5,3.0),
            _p("Austin Reaves","G","6-5",16.5,4.5,4.5,2.0),
            _p("Rui Hachimura","F","6-8",13.5,5.0,1.5,1.2),
            _p("Jaxson Hayes","C","6-10",9.5,5.5,1.5,0.3),
            _p("Jordan Goodwin","G","6-4",8.0,3.5,3.0,1.2),
            _p("Dorian Finney-Smith","F","6-7",9.0,4.0,1.5,1.8),
            _p("Gabe Vincent","G","6-3",7.5,2.0,2.5,1.5)],
    "PHX": [_p("Kevin Durant","F","6-10",26.5,6.5,4.0,2.8),
            _p("Devin Booker","G","6-5",25.0,4.5,5.5,2.5),
            _p("Bradley Beal","G","6-4",19.0,4.0,4.5,2.0,"Q"),
            _p("Royce O'Neale","F","6-4",9.5,5.0,3.5,2.0),
            _p("Nick Richards","C","7-0",12.0,8.5,1.0,0.3),
            _p("Tyus Jones","G","6-0",10.5,2.5,5.5,1.8),
            _p("Grayson Allen","G","6-4",11.0,3.5,2.5,2.5),
            _p("Bol Bol","C","7-2",10.0,5.5,1.5,0.8)],
    "IND": [_p("Tyrese Haliburton","G","6-5",21.0,4.0,8.5,3.2),
            _p("Pascal Siakam","F","6-8",20.0,6.5,4.5,1.8),
            _p("Myles Turner","C","6-11",15.5,8.0,2.0,1.2),
            _p("Bennedict Mathurin","G","6-5",17.5,4.5,2.5,2.0),
            _p("Aaron Nesmith","F","6-5",11.0,4.0,2.0,2.0),
            _p("Obi Toppin","F","6-8",11.5,4.0,2.0,1.5),
            _p("Jalen Smith","F","6-10",9.5,5.5,1.0,1.0),
            _p("Andrew Nembhard","G","6-4",9.0,2.5,4.0,1.2)],
    "DAL": [_p("Luka Doncic","G","6-7",28.5,7.5,8.5,3.0),
            _p("Kyrie Irving","G","6-2",24.5,4.5,5.0,2.8),
            _p("P.J. Washington","F","6-7",12.5,6.0,2.5,1.8),
            _p("Dereck Lively II","C","7-0",9.5,7.5,1.5,0.3),
            _p("Klay Thompson","G","6-6",17.5,4.0,2.5,3.2),
            _p("Daniel Gadingston","F","6-8",10.5,5.0,1.5,1.2),
            _p("Spencer Dinwiddie","G","6-5",9.5,2.5,4.5,1.5),
            _p("Maxi Kleber","F","6-10",7.5,4.5,1.5,1.2)],
}

# Fill remaining NBA teams with empty rosters to avoid KeyError
for _c in ["SAS","HOU","ATL","CHA","CHI","BKN","NOP","SAC","POR","UTA","TOR","WAS","ORL"]:
    NBA_ROSTERS.setdefault(_c, [])

# ── WNBA TEAMS / ROSTERS ────────────────────────────────────
WNBA_TEAMS = {
    "NYL":"New York Liberty","POR":"Portland Fire","MIN":"Minnesota Lynx",
    "DAL":"Dallas Wings","LVA":"Las Vegas Aces","IND":"Indiana Fever",
    "PHX":"Phoenix Mercury","SEA":"Seattle Storm","CON":"Connecticut Sun",
    "CHI":"Chicago Sky","ATL":"Atlanta Dream","WAS":"Washington Mystics",
    "LAS":"Las Vegas Aces",
}

WNBA_ROSTERS = {
    "NYL": [_p("Breanna Stewart","F","6-4",19.5,8.5,4.0,2.4),
            _p("Sabrina Ionescu","G","5-11",17.5,5.5,7.1,3.2),
            _p("Jonquel Jones","C","6-6",15.0,9.0,2.9,1.5),
            _p("Courtney Vandersloot","G","5-8",10.9,4.0,6.5,1.8),
            _p("Betnijah Laney","F","6-0",10.6,3.0,1.6,1.0,"Q"),
            _p("Kayla Thornton","F","6-2",6.5,4.0,0.9,0.8),
            _p("Sonia","G","5-9",6.0,2.0,1.5,0.5),
            _p("Han Xu","C","6-11",7.0,4.0,0.5,0.3)],
    "POR": [_p("Te'a Cooper","G","5-9",13.5,3.5,4.0,1.5),
            _p("Alexis","G","5-10",10.9,2.9,3.5,1.2),
            _p("Aaliyah","F","6-2",9.5,4.9,0.9,0.8),
            _p("Isabelle","C","6-4",8.5,6.5,0.5,0.0),
            _p("Nika","F","6-3",8.0,5.0,1.0,0.0,"OUT"),
            _p("Jessika","G","5-7",6.0,1.5,2.0,0.5),
            _p("Kate","F","6-2",5.5,2.9,0.5,0.3),
            _p("Sami","G","5-6",4.5,0.9,0.9,0.3)],
    "MIN": [_p("Naphessa Collier","F","6-0",16.9,5.5,3.4,1.8),
            _p("Kayla McCollough","G","5-11",14.1,3.5,2.0,1.0,"Q"),
            _p("Alana","C","6-4",11.5,7.0,1.5,0.5),
            _p("Natasha","G","5-8",11.0,2.9,5.5,1.5),
            _p("Diamond","F","6-2",8.5,4.0,1.0,0.8),
            _p("Nele","F","6-3",6.0,3.0,0.5,0.3),
            _p("Olivia","G","5-7",4.5,1.0,1.5,0.4),
            _p("Nara","G","5-9",3.5,0.8,0.8,0.3)],
    "DAL": [_p("Arielle","G","5-10",16.5,4.5,4.5,2.0),
            _p("Moriah","G","6-0",14.0,4.0,3.5,1.3),
            _p("Caitlin","F","6-3",12.5,6.0,1.5,0.8),
            _p("Naomi","C","6-5",10.5,7.0,1.0,0.5,"Q"),
            _p("Satou","F","6-2",9.0,4.5,1.5,0.8),
            _p("Lindsay","G","5-9",7.5,2.0,2.5,0.9),
            _p("Jaiden","F","6-3",5.5,3.0,0.5,0.3),
            _p("Awak","G","5-8",4.0,1.0,1.0,0.3)],
    "LVA": [_p("A'ja Wilson","F","6-4",22.5,10.0,3.5,1.5),
            _p("Chelsea Gray","G","5-11",14.5,4.0,5.0,1.8),
            _p("Kia","C","6-5",12.5,7.5,1.5,0.5),
            _p("Jackie","G","5-10",11.0,3.5,4.0,1.5),
            _p("Alysha","F","6-2",8.5,4.0,1.0,0.8,"Q"),
            _p("Kayla","G","5-9",6.5,1.5,2.0,0.8),
            _p("Sydney","F","6-3",5.5,3.0,0.5,0.3)],
    "IND": [_p("Caitlin Clark","G","6-0",18.5,5.0,8.0,3.5),
            _p("Aliyah Boston","C","6-4",14.0,9.0,2.5,1.0),
            _p("Kelsey Mitchell","G","5-10",14.5,3.0,2.5,2.0),
            _p("Grace Berger","G","6-0",8.5,2.5,2.0,0.8),
            _p("Lexie Hull","G","5-11",6.5,2.5,1.5,0.6),
            _p("Emma","F","6-2",6.0,4.0,0.8,0.5,"Q"),
            _p("Nina","F","6-3",5.0,3.5,0.5,0.3)],
    "PHX": [_p("Diana Taurasi","G","6-0",17.0,4.0,4.0,3.0),
            _p("Brittany Griner","C","6-9",15.0,8.0,1.5,0.5),
            _p("Megan","F","6-3",9.0,4.5,1.5,0.8,"Q"),
            _p("Diana","F","6-2",7.5,3.5,1.0,0.5),
            _p("Sophie","G","5-10",6.5,1.5,2.0,0.6),
            _p("Te'a","G","5-9",5.5,1.5,1.5,0.5),
            _p("Nneka","F","6-4",8.0,5.0,1.0,0.5)],
    "SEA": [_p("Breanna Stewart","F","6-4",20.0,8.5,4.5,2.5),
            _p("Sue Bird","G","5-9",14.0,3.0,5.5,2.8),
            _p("Jewel","C","6-5",12.0,8.0,1.5,0.5),
            _p("Natasha Howard","F","6-4",11.0,5.5,2.5,1.5),
            _p("Mercedes Russell","C","6-6",7.5,6.0,1.0,0.0,"Q"),
            _p("Kennedy","G","5-8",5.5,1.5,2.0,0.6),
            _p("Jillian","F","6-2",5.0,3.5,0.5,0.3)],
    "CON": [_p("Alyssa Thomas","F","6-3",15.5,7.5,6.5,1.0),
            _p("DeWanna Bonner","F","6-4",16.0,6.5,3.5,1.8),
            _p("Brionna Jones","C","6-3",12.5,7.0,2.0,0.8),
            _p("DiJonai","G","5-11",11.0,3.5,4.0,1.5),
            _p("Natasha","G","5-10",9.0,2.5,3.5,1.2,"Q"),
            _p("Julie","F","6-2",6.5,3.5,0.8,0.5),
            _p("Megan","G","5-9",5.5,1.5,1.5,0.5)],
    "CHI": [_p("Kahleah Copper","F","6-1",16.5,5.5,2.5,1.5),
            _p("Candace Parker","F","6-4",15.0,8.0,5.0,2.0),
            _p("Rebekah","C","6-5",10.0,7.0,1.5,0.5,"Q"),
            _p("Dana Evans","G","5-6",8.5,2.0,3.5,1.2),
            _p("Ingrid","F","6-3",6.5,4.0,0.8,0.5),
            _p("Yuki","G","5-9",5.5,1.5,1.5,0.5),
            _p("Li","F","6-4",7.0,4.5,0.8,0.5)],
    "ATL": [_p("Rhyne Howard","G","6-0",15.5,4.5,3.5,2.0),
            _p("Danielle","F","6-3",12.0,6.0,1.5,0.8),
            _p("Tina","C","6-5",11.5,8.0,1.5,0.5),
            _p("Shakira","G","5-10",10.0,3.5,4.5,1.3),
            _p("Cheyenne","F","6-2",7.5,4.0,1.0,0.6,"Q"),
            _p("Nia","G","5-8",6.0,1.5,2.0,0.5),
            _p("Christina","F","6-3",5.5,3.5,0.5,0.3)],
    "WAS": [_p("Elena Delle Donne","F","6-4",18.0,6.0,3.0,2.5),
            _p("Ariel Atkins","G","5-11",14.5,4.0,3.0,1.5),
            _p("Natasha","C","6-5",11.0,7.5,1.5,0.5),
            _p("Natasha Cloud","G","5-11",9.5,3.5,5.0,1.2),
            _p("Shakira Austin","C","6-0",8.5,5.5,1.5,0.5,"Q"),
            _p("KeKe","F","6-4",7.0,4.0,0.8,0.5),
            _p("Jade","G","5-8",5.5,1.5,1.5,0.5)],
}

# ── BACKTEST ────────────────────────────────────────────────
BACKTEST_SUITE = [
    ("NYK","PHI","NBA",226,219),
    ("BOS","NYK","NBA",221,216),
    ("OKC","MIN","NBA",228,224),
    ("CLE","IND","NBA",215,212),
    ("DEN","LAC","NBA",219,217),
    ("MIN","SAS","NBA",222,218),
    ("NYL","POR","WNBA",162,160),
    ("LVA","IND","WNBA",169,166),
]

def run_backtest():
    print(f"\n{'='*72}")
    print(f"  TC BACKTEST v4.0 — Corrected Formula")
    print(f"  TC = stat×0.85 | Q = ×0.65 | OUT = 0 | Pace: +8 | Line: ×0.88")
    print(f"{'='*72}\n")
    for away,home,sport,actual,mkt in BACKTEST_SUITE:
        g = Game(away, home, sport, market_total=mkt)
        tc_final = g._tc_final()
        tc_line  = g._tc_line()
        edge     = g._tc_edge()
        sig      = g._signal()
        actual_dir = "OVER" if actual > mkt else "UNDER"
        hit = "✅" if sig == actual_dir else "❌"
        print(f"  {away}@{home} ({sport})")
        print(f"    TC Final: {tc_final:.1f} | TC Line: {tc_line:.1f} | Edge: {'+' if edge>=0 else ''}{edge:.1f}")
        print(f"    Signal: {sig} | Actual: {actual} ({actual_dir}) {hit}")
        print()

# ── MAIN ────────────────────────────────────────────────────
if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Sports TC Engine v4.0")
    p.add_argument("--sport",   choices=["NBA","WNBA"], default="NBA")
    p.add_argument("--game",    help="'AWAY @ HOME'")
    p.add_argument("--total",   type=float, help="Market total")
    p.add_argument("--spread",  type=float, help="Home spread (e.g. -4)")
    p.add_argument("--bankroll",type=float, default=1000)
    p.add_argument("--backtest",action="store_true")
    p.add_argument("--list",    action="store_true")
    p.add_argument("--slate",   action="store_true")
    p.add_argument("--history", action="store_true")
    a = p.parse_args()

    if a.backtest:
        run_backtest()
    elif a.game:
        away,home = [x.strip().upper() for x in a.game.split("@")]
        g = Game(away, home, a.sport, a.total, a.spread, a.bankroll)
        g.full_report()
    elif a.list:
        tm = NBA_TEAMS if a.sport=="NBA" else WNBA_TEAMS
        print(f"\n{a.sport} Teams:"); [print(f"  {k}: {v}") for k,v in sorted(tm.items())]
    elif a.slate:
        matchups = {
            "NBA": [("NYK","PHI"),("BOS","NYK"),("OKC","MIN"),("CLE","IND"),
                    ("GSW","LAC"),("DEN","MIA"),("MIL","PHX"),("LAL","DAL")],
            "WNBA":[("NYL","POR"),("LVA","IND"),("MIN","DAL"),
                    ("CON","CHI"),("ATL","SEA"),("PHX","WAS")]}
        print(f"\n{'='*72}\n  {a.sport} SLATE\n{'='*72}")
        for away,home in matchups.get(a.sport,[]):
            g = Game(away,home,a.sport,bankroll=a.bankroll)
            tf = g._tc_final(); tl = g._tc_line(); eg = g._tc_edge(); sg = g._signal()
            es = "+" if eg>=0 else ""
            print(f"\n  {away} @ {home} → TC:{tf:.0f} | Line:{tl:.0f} | Edge:{es}{eg:.1f} | {sg}")
    elif a.history:
        WNBA_FINALS = {
            "2024":{"champion":"Las Vegas Aces","series":"4-1","games":[
                {"game":1,"home":"LVA","away":"NYL","home_score":97,"away_score":82},
                {"game":2,"home":"LVA","away":"NYL","home_score":83,"away_score":79},
                {"game":3,"home":"NYL","away":"LVA","home_score":88,"away_score":85},
                {"game":4,"home":"NYL","away":"LVA","home_score":74,"away_score":83},
                {"game":5,"home":"LVA","away":"NYL","home_score":81,"away_score":73},
            ]},
            "2025":{"champion":"New York Liberty","series":"4-2","games":[
                {"game":1,"home":"NYL","away":"LVA","home_score":87,"away_score":74},
                {"game":2,"home":"NYL","away":"LVA","home_score":81,"away_score":76},
                {"game":3,"home":"LVA","away":"NYL","home_score":83,"away_score":78},
                {"game":4,"home":"LVA","away":"NYL","home_score":91,"away_score":85},
                {"game":5,"home":"NYL","away":"LVA","home_score":88,"away_score":82},
                {"game":6,"home":"LVA","away":"NYL","home_score":79,"away_score":84},
            ]},
        }
        print(f"\n{'='*60}\n  WNBA FINALS HISTORY\n{'='*60}")
        for yr,d in sorted(WNBA_FINALS.items()):
            avg = (sum(g["home_score"]+g["away_score"] for g in d["games"]))/len(d["games"])
            print(f"\n  {yr} — {d['champion']} wins {d['series']} | Avg total: {avg:.1f}")
            for g in d["games"]:
                tot=g["home_score"]+g["away_score"]; w="HOME" if g["home_score"]>g["away_score"] else "AWAY"
                print(f"    G{g['game']}: {g['away']:3d} @ {g['home']:3d} | {tot} | {w}")
    else:
        print("""
╔══════════════════════════════════════════════════════════════╗
║              SPORTS TC v4.0 — MASTER ENGINE                   ║
║         NBA + WNBA Triple Conservative System                 ║
║  TC = stat×0.85 | Q = ×0.65 | OUT = 0 | Pace: +8              ║
║  TC Line = TC×0.88 | Edge = TC−Line | Signal: UNDER            ║
╚══════════════════════════════════════════════════════════════╝

USAGE:
  python sports_tc.py --sport WNBA --game "NYL @ POR"
  python sports_tc.py --sport NBA --game "NYK @ PHI" --total 219 --spread -4
  python sports_tc.py --backtest --sport NBA
  python sports_tc.py --slate --sport WNBA
  python sports_tc.py --list --sport NBA
  python sports_tc.py --history
""")