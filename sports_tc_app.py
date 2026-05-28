"""
Sports TC — Integrated Production App v9.0
FastAPI + Streamlit + Live TC Engine for NBA + WNBA.
TC: PTS×0.85+GAP | REB×0.80+GAP | AST×0.75+GAP | 3PM×0.70+GAP
Line = TC×0.88 | Edge = TC−Line | Signal: OVER/UNDER/PASS
Game Total v8: raw×star_mult + bench_diff + home_court
Author: Tyson (Zo Computer)
"""
import asyncio, json, math, os, random, datetime, argparse, sys
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

LINE_FACTOR = 0.88
Q_FACTOR = 0.55
OUT_FACTOR = 0.0
EDGE_THRESH = 3.0
GAP = {"pts": -3.0, "reb": -1.5, "ast": -1.0, "3pm": -0.8}
STAR_MULT = 0.90
ALL_NBA_STARS = {
    "Shai Gilgeous-Alexander": 0.90, "Nikola Jokic": 0.90,
    "Victor Wembanyama": 0.90, "Luka Doncic": 0.90,
    "Jayson Tatum": 0.90, "Giannis Antetokounmpo": 0.90,
    "Donovan Mitchell": 0.87, "Jalen Brunson": 0.87,
    "Anthony Edwards": 0.87, "Kevin Durant": 0.87,
    "Jaylen Brown": 0.87, "Karl-Anthony Towns": 0.87,
}
BENCH_DIFF_THRESHOLD = 15.0
BENCH_DIFF_BONUS = 4.0
HOME_COURT_BONUS = 2.0
SERIES_BENCH_PTS: Dict[str, Dict[str, float]] = {
    "OKC": {"G1": 33.0, "G2": 45.0, "G3": 76.0, "G4": 23.0},
    "SAS": {"G1": 25.0, "G2": 19.0, "G3": 19.0, "G4": 23.0},
    "CLE": {"G1": 28.0, "G2": 31.0, "G3": 19.0, "G4": 22.0},
    "BOS": {"G1": 35.0, "G2": 29.0, "G3": 38.0, "G4": 19.0},
}

@dataclass
class Player:
    name: str; pos: str; ht: str; pts: float
    reb: float = 0.0; ast: float = 0.0; tpm: float = 0.0; status: str = "ACTIVE"

    def sf(self) -> float:
        s = self.status.upper()
        if s in ("OUT", "DNP"): return OUT_FACTOR
        if any(x in s for x in ("Q", "QUESTION", "DOUBTFUL", "GTD")): return Q_FACTOR
        return 1.0

    def tc_prop(self, stat: str) -> float:
        stat = stat.lower()
        cm = {"pts": 0.85, "reb": 0.80, "ast": 0.75, "3pm": 0.70, "tpm": 0.70}
        gm = {"pts": -3.0, "reb": -1.5, "ast": -1.0, "3pm": -0.8, "tpm": -0.8}
        if stat not in cm: raise ValueError(f"Unknown stat: {stat}")
        raw = getattr(self, stat if stat != "3pm" else "tpm", 0.0)
        return round(max(0.0, raw * cm[stat] * self.sf() + gm[stat]), 1)

    def tc_pts(self) -> float: return self.tc_prop("pts")
    def tc_reb(self) -> float: return self.tc_prop("reb")
    def tc_ast(self) -> float: return self.tc_prop("ast")
    def tc_3pm(self) -> float: return self.tc_prop("tpm")
    def tc_prop_total(self) -> float:
        return round(self.tc_pts() + self.tc_reb() + self.tc_ast() + self.tc_3pm(), 1)
    def raw_pts_for_total(self) -> float:
        base = self.pts * self.sf()
        if self.name in ALL_NBA_STARS: base *= ALL_NBA_STARS[self.name]
        return round(base, 1)
    def as_dict(self) -> dict:
        return {"name": self.name, "pos": self.pos, "ht": self.ht, "status": self.status,
                "pts": self.pts, "reb": self.reb, "ast": self.ast, "tpm": self.tpm,
                "sf": self.sf(), "tc_pts": self.tc_pts(), "tc_reb": self.tc_reb(),
                "tc_ast": self.tc_ast(), "tc_3pm": self.tc_3pm(),
                "tc_prop_total": self.tc_prop_total(), "raw_pts_for_total": self.raw_pts_for_total()}

@dataclass
class Team:
    abbr: str; name: str; players: List[Player] = field(default_factory=list)
    injury_notes: List[str] = field(default_factory=list)
    def prop_tc_totals(self) -> Dict[str, float]:
        return {"pts": round(sum(p.tc_pts() for p in self.players), 1),
                "reb": round(sum(p.tc_reb() for p in self.players), 1),
                "ast": round(sum(p.tc_ast() for p in self.players), 1),
                "3pm": round(sum(p.tc_3pm() for p in self.players), 1)}
    def tc_starters(self) -> float: return round(sum(p.tc_pts() for p in self.players[:5]), 1)
    def bench_tc(self) -> float: return round(sum(p.tc_pts() for p in self.players[5:]), 1)
    def raw_total(self) -> float: return round(sum(p.raw_pts_for_total() for p in self.players), 1)
    def raw_starters(self) -> float: return round(sum(p.raw_pts_for_total() for p in self.players[:5]), 1)
    def raw_bench(self) -> float: return round(sum(p.raw_pts_for_total() for p in self.players[5:]), 1)
    def tc_adjusted_total(self, is_home: bool = False, s_bench: Optional[float] = None,
                          opp_bench: Optional[float] = None) -> Dict[str, Any]:
        adj, total = [], 0.0
        for p in self.players: total += p.raw_pts_for_total()
        if is_home:
            total += HOME_COURT_BONUS; adj.append(f"+{HOME_COURT_BONUS} home_court")
        if s_bench is not None and opp_bench is not None:
            diff = s_bench - opp_bench
            if diff > BENCH_DIFF_THRESHOLD:
                total += BENCH_DIFF_BONUS; adj.append(f"+{BENCH_DIFF_BONUS:.1f} bench_diff ({diff:.1f})")
        return {"adjusted_total": round(total, 1), "raw_total": self.raw_total(), "adjustments": adj}
    def active(self) -> List[Player]: return [p for p in self.players if p.status != "OUT"]
    def as_dict(self) -> dict:
        return {"abbr": self.abbr, "name": self.name, "raw_total": self.raw_total(),
                "raw_starters": self.raw_starters(), "raw_bench": self.raw_bench(),
                "prop_tc_totals": self.prop_tc_totals(), "tc_starters": self.tc_starters(),
                "bench_tc": self.bench_tc(),
                "players": [p.as_dict() for p in self.players], "injury_notes": self.injury_notes}

def P(name, pos, ht, pts, reb=0.0, ast=0.0, tpm=0.0, status="ACTIVE") -> Player:
    return Player(name, pos, ht, pts, reb, ast, tpm, status)

# ── NBA ROSTERS ──────────────────────────────────────────────────────────────
NBA_TEAMS: Dict[str, Team] = {
    "NYK": Team("NYK", "New York Knicks", [
        P("Jalen Brunson","PG","6-2",26.0,3.5,6.5,2.5),
        P("Karl-Anthony Towns","C","6-11",24.5,10.5,3.0,2.0),
        P("Mikal Bridges","SG","6-6",19.0,4.5,3.5,2.2),
        P("OG Anunoby","SF","6-7",17.5,5.0,2.5,1.8),
        P("Josh Hart","PF","6-5",13.5,6.5,4.5,1.2),
        P("Miles McBride","PG","6-2",9.5,2.5,3.0,1.5),
        P("Precious Achiuwa","PF","6-8",7.5,5.5,1.0,0.5),
        P("Jordan Clarkson","G","6-4",16.5,3.5,4.5,1.8),
    ]),
    "PHI": Team("PHI", "Philadelphia 76ers", [
        P("Joel Embiid","C","7-0",28.5,10.5,5.5,1.8,"OUT"),
        P("Tyrese Maxey","PG","6-2",24.5,4.5,6.5,2.5),
        P("Paul George","SF","6-8",22.0,5.5,4.5,3.2),
        P("Kelly Oubre Jr.","F","6-7",18.5,5.0,1.5,2.1),
        P("Andre Drummond","C","6-9",10.0,10.0,2.0,0.0),
        P("Justin Edwards","F","6-6",8.0,3.0,1.0,0.8),
        P("VJ Edgecombe","G","6-5",15.0,3.5,2.5,1.2),
        P("Quentin Grimes","G","6-5",10.0,3.0,2.5,1.8),
    ], ["Joel Embiid OUT (knee)", "Paul George OUT (ankle)"]),
    "BOS": Team("BOS", "Boston Celtics", [
        P("Jayson Tatum","F","6-8",28.5,7.5,5.0,2.9),
        P("Jaylen Brown","G","6-6",23.0,6.0,3.5,2.2),
        P("Kristaps Porzingis","C","7-1",20.0,7.0,2.5,2.8,"Q"),
        P("Derrick White","G","6-4",16.0,4.2,4.8,2.8),
        P("Jrue Holiday","G","6-4",14.5,4.5,5.0,1.8),
        P("Al Horford","F","6-9",9.0,6.2,3.5,2.0),
        P("Payton Pritchard","G","6-2",8.0,2.8,3.0,1.5),
    ], ["Kristaps Porzingis Q (illness)"]),
    "CLE": Team("CLE", "Cleveland Cavaliers", [
        P("Donovan Mitchell","SG","6-1",27.0,4.5,5.0,2.5),
        P("Darius Garland","PG","6-1",20.0,3.0,7.0,2.2),
        P("Evan Mobley","PF","6-11",18.0,9.5,3.0,0.8),
        P("Jarrett Allen","C","6-9",15.0,10.0,2.0,0.0),
        P("Caris LeVert","SG","6-5",12.0,4.0,3.0,1.5),
        P("Isaac Okoro","SG","6-5",8.5,3.0,2.0,1.2),
        P("Max Strus","SF","6-5",9.0,4.0,3.0,2.0),
        P("Ty Jerome","PG","6-6",7.5,2.5,3.5,1.2),
    ]),
    "OKC": Team("OKC", "Oklahoma City Thunder", [
        P("Shai Gilgeous-Alexander","SG","6-5",32.0,5.0,6.5,2.8),
        P("Jalen Williams","SF","6-6",18.5,5.5,4.0,1.5),
        P("Chet Holmgren","C","7-0",16.0,8.0,2.5,1.0),
        P("Isaiah Hartenstein","C","6-11",8.0,7.5,2.5,0.2),
        P("Luguentz Dort","SG","6-4",9.5,3.5,1.2,2.0),
        P("Alex Caruso","G","6-4",6.0,2.5,2.0,1.2),
        P("Isaiah Joe","G","6-1",9.0,2.0,0.8,2.1),
        P("Cason Wallace","G","6-4",8.5,2.5,1.5,1.8),
    ]),
    "MIN": Team("MIN", "Minnesota Timberwolves", [
        P("Anthony Edwards","G","6-4",30.0,5.0,5.5,3.5),
        P("Julius Randle","PF","6-9",22.0,9.0,4.5,1.8),
        P("Rudy Gobert","C","7-1",14.0,12.0,1.5,0.2),
        P("Donte DiVincenzo","SG","6-4",10.0,4.0,3.0,2.0),
        P("Mike Conley","PG","6-1",11.0,3.0,5.5,2.0),
        P("Naz Reid","C","6-9",13.5,5.0,2.0,1.8),
        P("Kyle Anderson","F","6-9",8.5,5.0,4.0,0.8),
        P("Nickeil Alexander-Walker","SG","6-5",12.0,3.5,2.5,2.0),
    ]),
    "DEN": Team("DEN", "Denver Nuggets", [
        P("Nikola Jokic","C","6-11",29.0,12.5,10.0,2.0),
        P("Jamal Murray","G","6-4",22.0,4.5,6.5,2.2),
        P("Michael Porter Jr.","F","6-10",16.5,6.5,2.5,2.0),
        P("Aaron Gordon","F","6-9",14.0,6.5,3.0,1.5),
        P("Russell Westbrook","G","6-3",12.0,5.0,6.5,1.2),
        P("Christian Braun","G","6-6",8.5,3.5,2.0,1.2),
    ]),
    "LAC": Team("LAC", "LA Clippers", [
        P("James Harden","SG","6-4",21.0,5.5,8.5,2.5),
        P("Kawhi Leonard","SF","6-7",24.0,6.5,3.5,1.8,"Q"),
        P("Norman Powell","SG","6-5",21.0,3.5,2.5,2.8),
        P("Ivica Zubac","C","7-0",12.0,9.0,2.0,0.0),
        P("Amir Coffey","G","6-5",11.0,3.0,2.5,1.5),
        P("Nicolas Batum","F","6-8",8.5,4.5,2.5,1.5),
        P("Derrick Jones Jr.","F","6-6",9.0,3.5,1.5,1.0),
        P("Kris Dunn","G","6-4",7.5,3.0,4.0,0.8),
    ], ["Kawhi Leonard Q (knee)"]),
    "SAS": Team("SAS", "San Antonio Spurs", [
        P("Victor Wembanyama","F","7-4",28.0,10.5,4.5,2.5),
        P("De'Aaron Fox","G","6-4",26.5,4.5,6.5,2.0),
        P("Stephon Castle","G","6-5",14.0,4.0,4.0,0.8),
        P("Devin Vassell","G","6-7",12.0,3.5,2.5,1.8),
        P("Harrison Barnes","F","6-8",10.5,4.0,1.5,0.8),
        P("Keldon Johnson","F","6-5",14.0,5.0,2.0,1.5),
        P("Mason Plumlee","C","6-11",6.5,6.0,2.0,0.0),
        P("Julian Champagnie","F","6-6",8.5,3.0,1.0,1.5),
    ]),
    "POR": Team("POR", "Portland Trail Blazers", [
        P("Scoot Henderson","G","6-3",18.5,4.5,7.5,1.5),
        P("Anfernee Simons","G","6-5",21.5,3.5,4.5,3.0),
        P("Jerami Grant","F","6-8",18.0,5.0,2.5,2.2),
        P("Deandre Ayton","C","7-0",16.5,10.0,2.0,0.0),
        P("Toukam Saop","F","6-9",15.5,7.5,2.5,1.2),
        P("Shaedon Sharpe","G","6-6",15.0,4.0,2.5,2.0),
        P("Rayan Rupert","G","6-7",8.5,3.0,2.0,1.2),
        P("Kris Murray","F","6-8",8.0,3.5,1.5,0.8),
    ]),
    "ORL": Team("ORL", "Orlando Magic", [
        P("Paolo Banchero","F","6-10",28.5,7.5,5.5,1.5),
        P("Franz Wagner","F","6-10",22.0,5.0,4.0,1.8,"OUT"),
        P("Jalen Suggs","G","6-5",16.5,4.0,4.5,1.5),
        P("Wendell Carter Jr.","C","6-6",14.5,9.0,2.5,0.8),
        P("Cole Anthony","G","6-2",13.0,4.5,3.5,1.2),
        P("Goga Bitadze","C","6-11",10.5,6.0,2.0,0.5),
        P("Jonathan Isaac","F","6-10",6.5,4.0,1.0,0.5),
        P("Caleb Houstan","F","6-8",7.0,3.0,1.5,0.8),
    ], ["Franz Wagner OUT (calf)"]),
    "HOU": Team("HOU", "Houston Rockets", [
        P("Alperen Sengun","C","6-9",21.5,9.5,5.0,0.8),
        P("Jabari Smith Jr.","F","6-10",18.0,7.0,1.8,2.5),
        P("Tari Eason","F","6-8",14.5,7.0,2.0,1.2),
        P("Reed Sheppard","G","6-2",13.0,4.0,3.0,2.2),
        P("Amen Thompson","G","6-6",12.5,5.5,3.5,0.8),
        P("Cam Whitmore","G","6-4",11.0,4.0,1.5,1.5),
        P("Jalen Green","G","6-4",18.0,4.5,3.0,2.0),
        P("Dillon Brooks","F","6-6",12.0,4.0,2.0,1.5),
    ]),
    "TOR": Team("TOR", "Toronto Raptors", [
        P("Scottie Barnes","F","6-8",21.5,7.5,5.5,1.5),
        P("RJ Barrett","G","6-7",19.5,5.5,3.5,2.0),
        P("Immanuel Quickley","G","6-2",15.0,4.0,4.5,1.5),
        P("Jakob Poeltl","C","6-11",12.5,9.5,2.5,0.0),
        P("Jamal Shead","G","6-2",9.5,3.0,4.5,1.2),
        P("Ochai Agbaji","G","6-5",8.5,3.5,2.0,1.2),
        P("Collin Murray-Boyles","F","6-8",12.0,5.5,2.5,0.5),
    ]),
    "DET": Team("DET", "Detroit Pistons", [
        P("Cade Cunningham","PG","6-6",25.0,6.0,8.5,2.0),
        P("Jaden Ivey","SG","6-4",17.0,4.5,4.0,1.5),
        P("Ausar Thompson","G","6-5",14.0,5.0,4.0,1.2),
        P("Jalen Duren","C","6-10",13.5,9.0,2.5,0.5),
        P("Tobias Harris","F","6-8",14.0,5.5,3.0,1.5),
        P("Simone","F","6-8",10.0,5.0,2.0,0.8),
        P("Marcus Sasser","G","6-2",11.0,2.5,3.0,1.8),
        P("Ron Holland II","F","6-6",10.0,4.0,1.5,1.0),
    ]),
    "ATL": Team("ATL", "Atlanta Hawks", [
        P("Trae Young","PG","6-1",25.0,3.5,10.0,3.0),
        P("Jalen Johnson","F","6-9",20.0,7.5,4.5,1.5),
        P("Zach LaVine","G","6-5",24.0,4.5,4.0,3.5),
        P("Jabari Parker","F","6-8",15.0,6.5,2.5,1.5),
        P("Onyeka Okongwu","C","6-9",14.0,8.0,1.5,0.0),
        P("Dyson Daniels","G","6-6",12.0,4.5,3.5,1.2),
        P("Vit Krejci","F","6-8",9.0,4.0,3.0,1.0),
    ]),
    "PHX": Team("PHX", "Phoenix Suns", [
        P("Devin Booker","SG","6-5",27.0,4.5,6.5,2.8),
        P("Kevin Durant","SF","6-10",26.0,6.0,4.0,2.5),
        P("Bradley Beal","G","6-4",21.0,4.0,5.0,2.0),
        P("Jusuf Nurkic","C","7-0",14.0,11.0,3.0,0.5),
        P("Grayson Allen","G","6-4",13.0,4.0,3.0,2.5),
        P("Ryan Dunn","F","6-8",8.0,4.0,1.5,1.2),
        P("Oven Mykhail","G","6-3",7.5,2.5,3.5,1.0),
    ]),
    "MIA": Team("MIA", "Miami Heat", [
        P("Jimmy Butler","F","6-7",22.0,5.5,5.0,1.2),
        P("Bam Adebayo","C","6-9",20.0,10.0,4.5,0.5),
        P("Tyler Herro","G","6-5",24.0,4.5,4.0,3.0),
        P("Nikola Jovic","F","6-10",12.0,6.0,2.0,1.2),
        P("Jaime Jaquez Jr.","F","6-6",11.0,4.5,2.5,1.0),
        P("Duncan Robinson","G","6-5",10.0,3.0,2.5,2.5),
        P("Alec Burks","G","6-2",8.5,2.5,4.0,1.5),
    ], ["Jimmy Butler GTD (knee)"]),
    "NOP": Team("NOP", "New Orleans Pelicans", [
        P("Zion Williamson","F","6-6",24.0,7.0,5.0,0.8),
        P("Brandon Ingram","F","6-8",20.0,5.5,4.0,2.0),
        P("CJ McCollum","G","6-3",22.0,4.0,5.0,2.5),
        P("Jonas Valanciunas","C","7-0",16.0,10.5,2.5,0.8),
        P("Trey Murphy III","F","6-8",14.0,4.5,2.0,2.5),
        P("Herb Jones","F","6-8",11.0,4.5,2.5,1.0),
        P("De'Anthony Melton","G","6-3",10.0,3.5,3.0,1.5),
        P("Jordan Hawkins","G","6-4",12.0,3.0,1.5,2.8),
    ]),
    "MIL": Team("MIL", "Milwaukee Bucks", [
        P("Giannis Antetokounmpo","F","6-11",30.0,11.0,6.0,1.5),
        P("Damian Lillard","PG","6-2",24.0,4.0,7.0,3.0),
        P("Khris Middleton","F","6-7",15.0,5.0,4.5,2.0),
        P("Brook Lopez","C","7-1",12.0,7.0,1.5,1.5),
        P("Bobby Portis","F","6-10",14.0,7.5,2.0,1.2),
        P("Pat Connaughton","G","6-5",8.5,4.0,2.0,1.8),
    ]),
    "SAC": Team("SAC", "Sacramento Kings", [
        P("De'Aaron Fox","PG","6-4",26.0,4.5,6.5,2.5),
        P("Domantas Sabonis","F","6-10",20.0,10.0,6.5,0.8),
        P("Keegan Murray","F","6-8",15.0,5.5,2.0,2.5),
        P("Malik Monk","G","6-3",15.0,3.5,3.5,2.0),
        P("Kevin Huerter","G","6-7",12.0,4.0,2.5,2.5),
        P("Keon Ellis","G","6-3",7.5,2.5,2.0,1.5),
        P("Devin Carter","G","6-3",11.0,3.5,3.0,1.5),
    ]),
    "DAL": Team("DAL", "Dallas Mavericks", [
        P("Luka Doncic","PG","6-7",29.0,8.5,9.5,3.0),
        P("Kyrie Irving","PG","6-3",25.0,4.0,6.0,3.0),
        P("P.J. Washington","F","6-7",14.0,5.5,2.0,1.8),
        P("Daniel Gafford","C","6-11",12.0,7.5,1.5,0.5),
        P("Klay Thompson","G","6-6",18.0,4.0,2.5,3.2),
        P("Dereck Lively II","C","7-0",8.0,5.5,1.5,0.0),
        P("Naji Marshall","F","6-8",10.0,4.0,2.5,1.0),
        P("Spencer Dinwiddie","G","6-5",9.0,3.0,4.0,1.2),
    ]),
    "LAL": Team("LAL", "Los Angeles Lakers", [
        P("LeBron James","F","6-9",24.5,7.0,8.0,2.0),
        P("Luka Doncic","PG","6-7",29.0,8.5,9.5,3.0),
        P("Austin Reaves","G","6-5",16.0,4.0,4.0,1.8),
        P("Rui Hachimura","F","6-8",13.0,5.0,1.5,1.0),
        P("Jarred Vanderbilt","F","6-8",8.0,5.0,2.5,0.8),
        P("Gabe Vincent","G","6-4",7.0,2.5,2.0,1.5),
        P("Christian Wood","C","6-10",7.5,4.5,1.0,1.2),
        P("Dorian Finney-Smith","F","6-7",9.0,3.5,2.0,1.0),
    ]),
    "GSW": Team("GSW", "Golden State Warriors", [
        P("Stephen Curry","PG","6-2",24.5,4.5,6.0,3.5),
        P("Jimmy Butler","F","6-7",22.0,5.5,5.0,1.2),
        P("Buddy Hield","G","6-4",13.0,4.0,2.5,3.2),
        P("Draymond Green","F","6-6",8.0,6.0,6.5,1.0),
        P("Trayce Jackson-Davis","C","6-9",12.0,7.5,2.0,0.8),
        P("Gary Payton II","G","6-3",7.0,3.0,2.0,1.2),
        P("Jonathan Kuminga","F","6-8",14.0,5.0,2.0,1.0),
        P("Moses Moody","G","6-6",9.0,3.0,1.5,1.5),
    ]),
    "IND": Team("IND", "Indiana Pacers", [
        P("Tyrese Haliburton","PG","6-5",21.0,4.0,10.0,2.5),
        P("Pascal Siakam","F","6-8",20.0,6.5,4.5,1.5),
        P("Myles Turner","C","6-11",15.0,7.0,2.5,1.0),
        P("Aaron Nesmith","F","6-5",10.0,4.0,1.5,1.5),
        P("Jalen Smith","F","6-10",12.0,6.0,1.5,1.0),
        P("Andrew Nembhard","G","6-4",8.0,3.0,3.5,1.0),
        P("Ben Sheppard","G","6-6",7.5,3.0,2.0,1.5),
    ]),
    "CHO": Team("CHO", "Charlotte Hornets", [
        P("LaMelo Ball","PG","6-7",25.0,5.5,8.5,3.0),
        P("Miles Bridges","F","6-6",20.0,6.0,3.0,1.8),
        P("Brandon Miller","F","6-9",18.0,5.0,2.5,2.5),
        P("Mark Williams","C","7-1",15.0,9.0,1.5,0.0),
        P("Cody Martin","G","6-6",8.0,4.5,3.0,1.0),
        P("Josh Green","G","6-5",9.0,3.0,2.0,1.5),
        P("Nick Smith Jr.","G","6-5",12.0,2.5,2.0,1.8),
        P("JT Thor","F","6-10",7.0,3.5,1.0,1.0),
    ]),
    "BKN": Team("BKN", "Brooklyn Nets", [
        P("Cameron Thomas","G","6-4",24.0,3.5,3.0,2.5),
        P("Moses Brown","C","7-2",14.0,12.0,1.5,0.0),
        P("Nic Claxton","C","6-11",12.0,8.0,2.5,0.5),
        P("Dorian Finney-Smith","F","6-8",9.0,4.5,2.0,1.5),
        P("Ben Simmons","G","6-10",8.0,6.0,7.0,0.5),
        P("Dennis Schroder","G","6-1",13.0,3.0,6.0,1.5),
        P("Lonnie Walker IV","G","6-4",11.0,2.5,2.0,1.8),
    ]),
    "WAS": Team("WAS", "Washington Wizards", [
        P("Jordan Poole","G","6-4",22.0,3.5,4.5,3.0),
        P("Bilal Coulibaly","F","6-9",16.0,5.0,2.0,1.5),
        P("Alexandre Sarr","C","6-11",12.0,6.5,2.0,0.5),
        P("Kyle Kuzma","F","6-10",14.0,4.5,2.5,1.5),
        P("Richaun Holmes","C","6-10",10.0,6.0,1.5,0.8),
        P("Justin Champagnari","F","6-9",9.0,5.0,1.5,1.0),
        P("Bub Carrington","G","6-5",11.0,3.0,4.0,1.2),
    ]),
    "UTA": Team("UTA", "Utah Jazz", [
        P("Lauri Markkanen","F","6-9",23.0,7.0,2.0,2.8),
        P("Keyonte George","G","6-4",16.0,3.5,5.0,2.0),
        P("John Collins","F","6-9",15.0,7.5,2.0,1.2),
        P("Walker Kessler","C","7-0",12.0,7.5,1.0,0.0),
        P("Kris Dunn","G","6-4",7.5,3.0,4.0,0.8),
        P("Judahh","G","6-5",11.0,3.5,4.5,1.8),
        P("Brandon Logan","G","6-2",9.0,2.5,3.0,1.0),
        P("Oscar Clary","G","6-3",8.0,2.0,4.0,1.2),
    ]),
    "CHI": Team("CHI", "Chicago Bulls", [
        P("Zach LaVine","G","6-5",24.0,4.5,4.0,3.5),
        P("Nikola Vucevic","C","6-11",18.0,10.0,3.0,1.5),
        P("Patrick Williams","F","6-8",14.0,5.5,2.0,2.0),
        P("Coby White","G","6-4",20.0,4.0,5.0,2.8),
        P("Tony Bradley","C","7-0",6.0,6.0,1.0,0.0),
        P("Ayo Dosunmu","G","6-5",11.0,3.5,3.5,1.2),
    ]),
    "MEM": Team("MEM", "Memphis Grizzlies", [
        P("Ja Morant","PG","6-3",27.0,5.0,8.0,1.8),
        P("Desmond Bane","SG","6-6",22.0,4.5,4.0,2.8),
        P("Jaren Jackson Jr.","F","6-11",20.0,5.5,2.5,2.5),
        P("Marcus Smart","G","6-4",12.0,4.5,5.5,1.5),
        P("Ziaire Williams","F","6-8",12.0,4.0,2.0,1.8),
        P("Santi Aldama","F","6-11",11.0,5.5,2.5,1.0),
        P("Derrick Rose","G","6-3",8.0,2.5,4.0,0.8),
        P("Jake LaRavia","F","6-8",8.0,4.0,1.5,1.0),
    ]),
}

# ── WNBA ROSTERS ─────────────────────────────────────────────────────────────
WNBA_TEAMS: Dict[str, Team] = {
    "NYL": Team("NYL", "New York Liberty", [
        P("Breanna Stewart","F","6-4",23.0,9.0,4.0,2.5),
        P("Jonquel Jones","C","6-6",18.5,9.5,3.5,1.8),
        P("Sabrina Ionescu","G","5-11",20.5,5.0,7.5,3.2),
        P("Kayla Thornton","F","6-2",11.0,5.5,2.5,1.5),
        P("Svetlana Petrov","G","5-10",10.0,3.5,4.5,1.8),
        P("JiSu Park","C","6-5",10.5,7.0,1.5,0.5),
        P("Marine Johannès","G","6-0",11.5,3.0,4.0,2.2),
        P("Michele Taylor","F","6-3",7.5,4.0,1.5,1.0),
    ]),
    "MIN": Team("MIN", "Minnesota Lynx", [
        P("Napheesa Collier","F","6-2",20.0,6.5,3.5,1.8),
        P("Alana Smith","G","5-9",14.5,3.5,5.5,1.5,"Q"),
        P("Kayla McBride","G","5-11",16.0,4.0,4.0,2.8),
        P("Crystal Dangerfield","G","5-5",12.0,3.0,3.5,1.2),
        P("Natalie Achonwu","C","6-5",9.5,7.0,2.0,0.5),
        P("Olivia Olu","F","6-2",7.0,4.0,1.5,1.0),
        P("Tiffany Mitchell","G","5-10",9.0,2.5,3.0,1.2),
        P("Nizhoni Cowboy","F","6-3",6.5,4.0,1.0,0.8),
    ], ["Alana Smith Q (ankle)"]),
    "DAL": Team("DAL", "Dallas Wings", [
        P("Arielle Wiggins","F","6-4",17.0,6.0,2.5,1.2),
        P("Satou Sabally","F","6-4",18.5,7.5,4.0,2.0,"Q"),
        P("Odyssey Sims","G","5-8",15.0,3.5,6.0,1.5),
        P("Teaira McCowan","C","7-0",16.0,11.0,1.5,0.0),
        P("Crystal Dangerfield","G","5-5",11.5,2.5,3.5,1.0),
        P("Moriah Jefferson","G","5-7",10.0,2.0,5.5,1.2),
        P("Natasha Howard","F","6-4",14.0,6.5,2.0,1.0,"OUT"),
        P("Joyner Woods","G","5-10",8.5,2.5,3.0,1.2),
    ], ["Satou Sabally Q (hip)", "Natasha Howard OUT (knee)"]),
    "LVA": Team("LVA", "Las Vegas Aces", [
        P("A'ja Wilson","F","6-4",25.0,10.5,3.5,1.5),
        P("Chelsea Gray","G","5-11",17.5,4.0,6.5,2.0),
        P("Kia Wilson","G","5-8",15.0,3.5,5.0,2.5),
        P("Candace Parker","F","6-4",14.5,8.0,4.5,1.2),
        P("Dearica Hamby","F","6-2",13.0,7.5,3.0,1.5),
        P("Jasmine Thomas","G","5-8",9.5,2.5,5.0,1.8),
        P("Sydney Colson","G","5-8",6.0,2.0,4.0,1.0),
        P("Kamera Conrad","F","6-2",7.5,4.5,1.5,0.8),
    ]),
    "CON": Team("CON", "Connecticut Sun", [
        P("Alyssa Thomas","F","6-3",16.0,8.5,7.5,1.0),
        P("DeWanna Bonner","F","6-4",18.0,7.0,4.0,2.0),
        P("Brionna Jones","C","6-3",14.5,7.5,2.0,0.8),
        P("Natasha Cloud","G","5-11",12.0,3.5,6.0,1.5),
        P("Megan McKenna","G","5-10",10.5,2.5,4.5,2.0),
        P("Ellie","F","6-2",7.0,4.0,1.5,1.0),
        P("Lindsay Wisdom","C","6-5",8.5,5.5,1.5,0.5),
        P("Jasmine Nwajei","G","5-9",6.5,2.0,2.5,1.0),
    ]),
    "CHI": Team("CHI", "Chicago Sky", [
        P("Skylar Diggins","G","5-9",16.0,3.0,7.0,1.0),
        P("Rickea Jackson","F","6-1",13.0,3.0,1.0,1.0),
        P("Kamilla Cardoso","C","6-5",11.0,5.0,1.0,0.0),
        P("Azura Stevens","F","6-3",8.0,3.0,0.0,0.0),
        P("Gabriela Jaquez","G","5-11",10.0,4.0,0.0,0.0),
    ]),
    "SEA": Team("SEA", "Seattle Storm", [
        P("Jillian","F","6-3",22.0,8.0,4.5,1.8),
        P("Skylar Diggins-Smith","G","5-9",16.0,3.0,7.0,1.0),
        P("Nneka Ogwumike","F","6-3",18.0,8.0,3.0,1.5),
        P("J-Canada","G","5-6",12.0,4.0,5.0,2.0),
        P("Mercedes Russell","C","6-6",8.0,6.0,1.0,0.0),
        P("Joyner Holmes","F","6-3",6.0,4.0,1.0,0.5),
    ]),
    "ATL": Team("ATL", "Atlanta Dream", [
        P("Rhyne Howard","G","6-0",25.0,4.0,8.0,2.0),
        P("Allisha Gray","G","6-0",16.0,4.0,1.0,0.0),
        P("Angel Reese","F","6-3",15.0,9.0,2.0,0.0),
        P("Jordin Canada","G","5-8",9.0,5.0,6.0,1.0),
        P("Naz Hillmon","F","6-2",6.0,3.0,2.0,0.0),
    ]),
    "LAS": Team("LAS", "Los Angeles Sparks", [
        P("Nneka Ogwumike","F","6-3",18.0,8.0,3.0,1.5),
        P("Jillian","F","6-3",22.0,8.0,4.5,1.8),
        P("Lexie Brown","G","6-0",10.0,3.0,4.0,2.0),
        P("Emily","C","6-5",12.0,8.0,1.5,0.5),
        P("Layslo","G","5-9",11.0,2.5,4.5,1.0),
    ]),
    "PHX_W": Team("PHX_W", "Phoenix Mercury", [
        P("Diana Taurasi","G","6-0",22.0,5.0,4.5,3.2),
        P("Brittney Griner","C","7-1",20.0,10.0,2.0,0.8),
        P("Kahleah Copper","G","6-0",18.0,4.5,3.5,2.0),
        P("Moriah Jefferson","G","5-7",10.0,2.0,5.5,1.2),
    ]),
    "IND_W": Team("IND_W", "Indiana Fever", [
        P("Caitlin Clark","PG","6-0",22.0,5.0,8.0,3.5),
        P("Aliyah Boston","C","6-4",15.0,7.0,2.0,0.0),
        P("Katherine","F","6-2",14.0,6.5,3.0,1.2),
        P("Natalie Achonwu","C","6-5",9.5,7.0,2.0,0.5),
    ]),
    "WAS_W": Team("WAS_W", "Washington Mystics", [
        P("Ariel Atkins","G","5-11",16.0,4.0,3.0,1.5),
        P("Emily","F","6-3",14.0,6.0,2.5,1.2),
        P("Shakira","F","6-2",12.0,5.5,2.0,0.8),
        P("Naomi","G","5-9",11.0,3.0,4.5,1.8),
    ]),
}

# ── HELPERS ─────────────────────────────────────────────────────────────────
def get_team(abbr: str, sport: str = "NBA") -> Team:
    teams = NBA_TEAMS if sport == "NBA" else WNBA_TEAMS
    abbr = abbr.upper()
    if abbr in teams: return teams[abbr]
    for key, team in teams.items():
        if key == abbr or team.name.upper().startswith(abbr): return team
    raise ValueError(f"Team '{abbr}' not found in {sport}")

def get_teams(sport: str = "NBA") -> Dict[str, Team]:
    return NBA_TEAMS if sport == "NBA" else WNBA_TEAMS

def tc_line(val: float) -> int: return math.floor(float(val) * LINE_FACTOR)
def edge(tc_val: float, line_val: float) -> float: return round(tc_val - float(line_val), 2)
def signal_from_edge(e: float, thresh: float = EDGE_THRESH) -> str:
    return "OVER" if e > thresh else "UNDER" if e < -thresh else "PASS"

def team_tc(players: List[Player], half: float = 1.64) -> Dict[str, float]:
    active = [p for p in players if p.sf() > 0]
    out = {}
    for stat in ("pts", "reb", "ast", "3pm"):
        total = sum(getattr(p, f"tc_{stat}")() for p in active)
        out[f"tc_{stat}"] = round(total * half, 2)
    return out

# CORRECTED: half parameter correctly applies to combined totals
def team_tc_combined(away_players: List[Player], home_players: List[Player], half: float = 1.0) -> Dict[str, Any]:
    """Compute TC combined for game total with halftime scaling."""
    at = team_tc(away_players, half)
    ht = team_tc(home_players, half)
    tc_comb = round(at["tc_pts"] + ht["tc_pts"], 2)
    tc_ln = tc_line(tc_comb)
    tc_ed = edge(tc_comb, tc_ln)
    return {"tc_pts": tc_comb, "tc_line": tc_ln, "tc_edge": tc_ed,
            "at": at, "ht": ht, "signal": sig_from_edge(tc_ed)}

def calc_series_bench_avg(team_abbr: str, series_data: Dict[str, Dict[str, float]] = None) -> Optional[float]:
    series_data = series_data or SERIES_BENCH_PTS
    if team_abbr not in series_data: return None
    games = list(series_data[team_abbr].values())
    return round(sum(games) / len(games), 1) if games else None

def calc_game_total_v8(home: Team, away: Team, market_total: float,
                       series_bench: Dict[str, Dict[str, float]] = None) -> Dict[str, Any]:
    series_bench = series_bench or SERIES_BENCH_PTS
    h_bench = calc_series_bench_avg(home.abbr, series_bench)
    a_bench = calc_series_bench_avg(away.abbr, series_bench)
    h_adj = home.tc_adjusted_total(True, h_bench, a_bench)
    a_adj = away.tc_adjusted_total(False, a_bench, h_bench)
    combined = round(h_adj["adjusted_total"] + a_adj["adjusted_total"], 1)
    gap = round(combined - market_total, 1)
    lean = "UNDER" if gap < -5 else ("OVER" if gap > 5 else "NO EDGE")
    return {
        "home": {"abbr": home.abbr, "v8_total": h_adj["adjusted_total"],
                  "raw_total": h_adj["raw_total"], "adjustments": h_adj["adjustments"]},
        "away": {"abbr": away.abbr, "v8_total": a_adj["adjusted_total"],
                  "raw_total": a_adj["raw_total"], "adjustments": a_adj["adjustments"]},
        "v8_combined": combined, "market_total": market_total,
        "gap_vs_market": gap, "lean": lean,
        "model_type": "v8_game_total_calibration",
    }

def sig_from_edge(e: float) -> str: return signal_from_edge(e)

def calc_game(home: Team, away: Team, market_total: float, market_spread: float,
              sport: str = "NBA", series_bench: Dict[str, Dict[str, float]] = None) -> Dict[str, Any]:
    home_tc = home.prop_tc_totals()
    away_tc = away.prop_tc_totals()
    tc_combined = round(home_tc["pts"] + away_tc["pts"], 1)
    tc_ln = tc_line(tc_combined)
    tc_ed = edge(tc_combined, tc_ln)
    v8 = calc_game_total_v8(home, away, market_total, series_bench)
    spread_raw = round(home.raw_total() - away.raw_total(), 1)
    spread_abs = abs(market_spread)
    return {
        "home": home.as_dict(), "away": away.as_dict(),
        "tc_match": {"tc_combined_pts": tc_combined, "tc_line_pts": tc_ln,
                     "tc_edge": tc_ed, "tc_signal": signal_from_edge(tc_ed),
                     "prop_tc_totals": {"home": home_tc, "away": away_tc},
                     "rule": "TC Match = player props only (PTS/REB/AST/3PM)"},
        "game_total_v8": v8,
        "market_total": market_total,
        "spread": {"raw_points_spread": spread_raw, "market_spread": market_spread,
                   "lean": "HOME" if spread_raw > abs(market_spread) else (
                           "AWAY" if spread_raw < -abs(market_spread) else "PASS")},
    }

def project_game(home_abbr: str, away_abbr: str, market_total: float,
                 market_spread: float, series: str = "", game_time: str = "TBD",
                 bankroll: float = 1000.0, sport: str = "NBA") -> Dict[str, Any]:
    home = get_team(home_abbr, sport)
    away = get_team(away_abbr, sport)
    proj = calc_game(home, away, market_total, market_spread, sport)
    tc_edge = proj["tc_match"]["tc_edge"]
    return {
        "meta": {"home": home_abbr.upper(), "away": away_abbr.upper(),
                  "series": series, "game_time": game_time, "sport": sport},
        "tc_match": proj["tc_match"],
        "game_total_v8": proj["game_total_v8"],
        "market_total": market_total,
        "spread": proj["spread"],
        "players": {"home": proj["home"]["players"], "away": proj["away"]["players"]},
        "starters": {"home": proj["home"]["players"][:5], "away": proj["away"]["players"][:5]},
        "bench": {"home_raw": proj["home"]["raw_bench"], "away_raw": proj["away"]["raw_bench"]},
        "injuries": {"home": proj["home"]["injury_notes"], "away": proj["away"]["injury_notes"]},
        "bets": {"tc_signal": proj["tc_match"]["tc_signal"], "tc_edge": tc_edge,
                 "game_total_v8_lean": proj["game_total_v8"]["lean"],
                 "game_total_v8_gap": proj["game_total_v8"]["gap_vs_market"],
                 "bankroll": bankroll,
                 "note": "Two independent models: (1) TC Match for player props (2) v8 Game Total for game totals"},
    }

def run_backtest(sport: str = "NBA") -> Dict[str, Any]:
    teams = get_teams(sport)
    suite = (
        [{"home": "BOS", "away": "PHI", "date": "2026-04-19", "market_total": 208.5, "market_spread": -11.5, "actual_total": 216},
         {"home": "DEN", "away": "LAC", "date": "2026-04-19", "market_total": 216.5, "market_spread": -4.5, "actual_total": 222},
         {"home": "DET", "away": "ORL", "date": "2026-04-19", "market_total": 200.5, "market_spread": -5.5, "actual_total": 207},
         {"home": "SAS", "away": "POR", "date": "2026-04-19", "market_total": 206.5, "market_spread": -8.5, "actual_total": 226}]
        if sport == "NBA"
        else [{"home": "NYL", "away": "MIN", "date": "2025-10-10", "market_total": 161.5, "market_spread": -5.5, "actual_total": 161},
              {"home": "LVA", "away": "NYL", "date": "2025-10-13", "market_total": 162.5, "market_spread": -4.5, "actual_total": 162}]
    )
    results = []
    for g in suite:
        home_t, away_t = teams[g["home"]], teams[g["away"]]
        proj = calc_game(home_t, away_t, g["market_total"], g["market_spread"], sport)
        v8c = proj["game_total_v8"]["v8_combined"]
        v8g = proj["game_total_v8"]["gap_vs_market"]
        v8d = proj["game_total_v8"]["lean"]
        actual = g["actual_total"]
        actual_dir = "OVER" if actual > g["market_total"] else "UNDER"
        v8_hit = v8d == actual_dir
        tcc = proj["tc_match"]["tc_combined_pts"]
        tcl = proj["tc_match"]["tc_line_pts"]
        tce = proj["tc_match"]["tc_edge"]
        tcs = proj["tc_match"]["tc_signal"]
        results.append({"game": f"{g['away']}@{g['home']}", "date": g["date"],
                         "market_total": g["market_total"], "v8_combined": v8c,
                         "actual_total": actual, "v8_gap": v8g, "v8_lean": v8d,
                         "actual_lean": actual_dir, "v8_hit": v8_hit,
                         "tc_combined": tcc, "tc_line": tcl, "tc_edge": tce, "tc_signal": tcs})
    n = len(results)
    v8_hr = round(sum(r["v8_hit"] for r in results) / n * 100, 1) if n else 0
    return {"games": results, "summary": {"sport": sport, "n": n, "v8_hit_rate": v8_hr}}

# ── GLOBAL STATE ─────────────────────────────────────────────────────────────
SYSTEM_STATE = {
    "active_algorithm": "Arbitrage Maximizer (EV+)",
    "betting_wallet": {"fiat_balance": 10450.00, "active_exposure": 0.0, "total_pnl": 1240.50},
    "alert_logs": [],
    "backtest_results": {"status": "Idle", "total_trades": 0, "win_rate": 0.0,
                          "net_profit": 0.0, "historical_blowouts": 0, "sharp_triggers": 0},
}

LIVE_SPORTS = {
    "NBA": {"teams": {"home": "Lakers", "away": "Celtics"}, "score": {"home": 104, "away": 82},
             "minutes_remaining": 6.2, "injury_report": {"Anthony Davis": "Available"}},
    "WNBA": {"teams": {"home": "Liberty", "away": "Aces"}, "score": {"home": 74, "away": 72},
              "minutes_remaining": 2.1, "injury_report": {}},
    "NFL": {"teams": {"home": "Chiefs", "away": "49ers"}, "score": {"home": 14, "away": 17},
            "minutes_remaining": 11.5, "injury_report": {}},
    "SOCCER": {"teams": {"home": "Argentina", "away": "France"}, "score": {"home": 1, "away": 0},
               "minutes_remaining": 68.0, "injury_report": {}},
    "BASEBALL": {"teams": {"home": "Yankees", "away": "Red Sox"}, "score": {"home": 9, "away": 2},
                 "minutes_remaining": 3.0, "injury_report": {}},
}

HISTORICAL_DB = [  {"sport": "NBA", "score_diff": 22, "line_mov": 2.5, "win": True, "pra_total": 42},
    {"sport": "WNBA", "score_diff": 4, "line_mov": 3.0, "win": False, "pra_total": 35},
    {"sport": "NFL", "score_diff": 21, "line_mov": 0.5, "win": True, "pra_total": 0},
    {"sport": "BASEBALL", "score_diff": 8, "line_mov": 1.0, "win": True, "pra_total": 0},
    {"sport": "SOCCER", "score_diff": 1, "line_mov": 0.0, "win": False, "pra_total": 0},
] * 80

def run_live_betting_rules():
    for sport, data in LIVE_SPORTS.items():
        sd = abs(data["score"]["home"] - data["score"]["away"])
        if (sport in ("NBA", "WNBA") and sd > 20) or (sport == "NFL" and sd > 17) or (sport == "BASEBALL" and sd > 6):
            msg = f"⚠️ BLOWOUT WARN: {sport} diff {sd} pts"
            if not any(l["msg"] == msg for l in SYSTEM_STATE["alert_logs"]):
                SYSTEM_STATE["alert_logs"].insert(0, {"type": "BLOWOUT", "msg": msg})

# ── FASTAPI APP ──────────────────────────────────────────────────────────────
try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import StreamingResponse
    from pydantic import BaseModel
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

if FASTAPI_AVAILABLE:
    app = FastAPI(title="TC Sports App — Integrated v9",
                  description="TC Match + Game Total v8 + Live Streaming", version="9.0.0")

    class AlgoSelection(BaseModel):
        algorithm: str

    async def live_data_simulator():
        while True:
            try:
                for sport in LIVE_SPORTS:
                    if random.random() > 0.7:
                        LIVE_SPORTS[sport]["score"]["home"] += random.choice([-1, 0, 1])
                run_live_betting_rules()
                await asyncio.sleep(1.0)
            except Exception:
                await asyncio.sleep(1.0)

    async def execute_parallel_backtest(algorithm_name: str):
        SYSTEM_STATE["backtest_results"]["status"] = "Processing..."
        await asyncio.sleep(1.0)
        trades, wins, profit, blowouts, sharps = 0, 0, 0.0, 0, 0
        for match in HISTORICAL_DB:
            trigger = False
            if match["score_diff"] > 15: blowouts += 1
            if match["line_mov"] > 2.0: sharps += 1
            if algorithm_name == "Arbitrage Maximizer (EV+)" and match["line_mov"] > 1.5: trigger = True
            elif algorithm_name == "Blowout Under-Correlator" and match["score_diff"] > 18: trigger = True
            elif algorithm_name == "Sharp Steam Line Squeezer" and match["line_mov"] > 2.0: trigger = True
            elif algorithm_name == "High Volume Player Prop Arbitrage" and match["pra_total"] > 35: trigger = True
            if trigger:
                trades += 1
                if match["win"]: wins += 1; profit += 110.0
                else: profit -= 100.0
        wr = round((wins / trades * 100) if trades > 0 else 0.0, 2)
        SYSTEM_STATE["backtest_results"] = {"status": "Complete", "total_trades": trades,
            "win_rate": wr, "net_profit": round(profit, 2),
            "historical_blowouts": blowouts, "sharp_triggers": sharps}

    @app.on_event("startup")
    async def startup():
        os.makedirs("templates", exist_ok=True)
        asyncio.create_task(live_data_simulator())

    @app.post("/api/select_algo")
    async def select_algo(payload: AlgoSelection):
        SYSTEM_STATE["active_algorithm"] = payload.algorithm
        asyncio.create_task(execute_parallel_backtest(payload.algorithm))
        return {"status": "success", "active_algorithm": payload.algorithm}

    @app.get("/api/stream")
    async def stream_data(request: Request):
        async def event_gen():
            while True:
                if await request.is_disconnected(): break
                sc = dict(SYSTEM_STATE); sc["sports"] = LIVE_SPORTS
                yield f"data: {json.dumps(sc)}\n\n"
                await asyncio.sleep(1)
        return StreamingResponse(event_gen(), media_type="text/event-stream")

    @app.get("/api/state")
    async def get_state():
        sc = dict(SYSTEM_STATE); sc["sports"] = LIVE_SPORTS
        return sc

    @app.get("/api/project")
    async def api_project(home: str, away: str, market_total: float,
                          market_spread: float = 0.0, sport: str = "NBA"):
        try:
            return project_game(home.upper(), away.upper(), float(market_total),
                                float(market_spread), sport=sport.upper())
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.get("/api/backtest")
    async def api_backtest(sport: str = "NBA"):
        return run_backtest(sport.upper())

    @app.get("/")
    async def root():
        return {"message": "TC Sports App v9", "version": "9.0.0",
                "endpoints": ["/", "/api/state", "/api/stream", "/api/project", "/api/backtest"]}

# ── STREAMLIT DASHBOARD ─────────────────────────────────────────────────────
def run_streamlit():
    import streamlit as st
    st.set_page_config(page_title="Sports TC Dashboard v9", page_icon="🏀",
                        layout="wide", initial_sidebar_state="collapsed")
    st.markdown("""
    <style>
    :root { --bg:#0d1117; --surface:#161b22; --border:#30363d; --text:#e6edf3;
            --muted:#7d8590; --accent:#3fb950; --amber:#f0883e; --rose:#f85149; }
    html,body,.stApp { background:var(--bg) !important; color:var(--text) !important; }
    [data-testid="stMain"] { border:none !important; }
    .stTabs [data-baseweb="tab-list"] { gap:2px; background:#161b22; border-radius:8px; padding:4px; }
    .stTabs [data-baseweb="tab"] { border-radius:6px; font-weight:600; font-size:13px; color:#7d8590; }
    .stTabs [aria-selected="true"] { background:#21262d !important; color:#e6edf3 !important; }
    div[data-testid="stHorizontalBlock"]>div>div { background:#161b22; border:1px solid #30363d; border-radius:12px; padding:16px; margin-bottom:8px; }
    .stMetric { background:transparent !important; border:none !important; }
    footer,header { display:none !important; }
    </style>""", unsafe_allow_html=True)

    st.markdown("""
    <div style="padding:20px 24px;border-bottom:1px solid #30363d;margin-bottom:24px">
      <h1 style="color:#3fb950;margin:0;font-size:1.7rem;font-weight:900">
        🛡️ Sports TC Dashboard <span style="font-size:0.7rem;color:#7d8590">v9.0 INTEGRATED</span>
      </h1>
      <p style="color:#7d8590;margin:6px 0 0;font-size:0.78rem">
        TC Match: PTS×0.85+gap | Line=TC×0.88 | Edge=TC−Line | Signal: OVER if edge>+3 | UNDER if edge<−3 | PASS
        &nbsp;|&nbsp; Game Total v8: raw×0.90+bench_diff+home_court
      </p>
    </div>""", unsafe_allow_html=True)

    tabs = st.tabs(["📊 Project Game","📈 Backtest Run","📡 Live Monitor","📋 Game Slate","🧪 Diagnostic"])
    sport_opt = st.sidebar.selectbox("Sport", ["NBA","WNBA"], index=0, key="sport_sel")

    with tabs[0]:
        col1,col2,col3 = st.columns(3)
        team_list = list(get_teams(sport_opt).keys())
        away_sel = col1.selectbox("Away", team_list, index=0, key="away_sel")
        home_sel = col2.selectbox("Home", team_list, index=3, key="home_sel")
        market_in = col3.number_input("Market Total", value=215.0, step=0.5, key="market_in")
        spread_in = st.number_input("Market Spread", value=-3.5, step=0.5, key="spread_in")
        half_chk = st.checkbox("⚡ Halftime Mode (TC × 0.5)", value=False, key="half_chk")

        if st.button("🚀 Run TC Projection", type="primary", use_container_width=True):
            try:
                away_t = get_team(away_sel, sport_opt)
                home_t = get_team(home_sel, sport_opt)
                half = 0.5 if half_chk else 1.0
                at = team_tc(away_t.players, half)
                ht = team_tc(home_t.players, half)
                tc_comb = round(at["tc_pts"] + ht["tc_pts"], 2)
                tc_ln = tc_line(tc_comb)
                tc_ed = edge(tc_comb, tc_ln)
                sig = signal_from_edge(tc_ed)
                v8 = calc_game_total_v8(home_t, away_t, market_in)
                c1,c2,c3,c4 = st.columns(4)
                c1.metric("TC Combined PTS", f"{tc_comb}")
                c2.metric("TC Line", f"{tc_ln}")
                c3.metric("Edge", f"{tc_ed:+.2f}", delta=sig)
                c4.metric("Signal", sig, delta="OVER" if sig=="OVER" else ("UNDER" if sig=="UNDER" else "PASS"))
                v8c4,v8c2,v8c3 = st.columns(3)
                v8c4.metric("v8 Combined", f"{v8['v8_combined']}")
                v8c2.metric("v8 Gap vs Market", f"{v8['gap_vs_market']:+.1f}")
                v8c3.metric("v8 Lean", v8["lean"], delta=v8["lean"])
                st.markdown("#### 👥 Rosters — Full TC Breakdown")
                for label, team in [(f"{away_sel} (Away)", away_t), (f"{home_sel} (Home)", home_t)]:
                    with st.expander(f" {label}", expanded=True):
                        rows = [{"Player": p.name, "POS": p.pos, "TC PTS": p.tc_pts(),
                                  "Line": tc_line(p.tc_pts()), "Edge": f"{edge(p.tc_pts(), tc_line(p.tc_pts())):+.1f}",
                                  "TC REB": p.tc_reb(), "TC AST": p.tc_ast(), "TC 3PM": p.tc_3pm(), "Status": p.status}
                                 for p in team.players]
                        st.dataframe(rows, use_container_width=True, hide_index=True)
                st.markdown("#### 🎯 Prop Candidates (Edge ≥ 2.0)")
                cands = []
                for p in away_t.players + home_t.players:
                    if p.status == "OUT" or p.pts < 5: continue
                    e = edge(p.tc_pts(), tc_line(p.tc_pts()))
                    if abs(e) >= 2.0:
                        cands.append({"Player": p.name, "Team": away_sel if p in away_t.players else home_sel,
                                       "TC PTS": p.tc_pts(), "Line": tc_line(p.tc_pts()),
                                       "Edge": f"{e:+.1f}", "Direction": "OVER" if e > 0 else "UNDER"})
                cands.sort(key=lambda x: float(x["Edge"].replace("+","")), reverse=True)
                if cands: st.dataframe(cands, use_container_width=True, hide_index=True)
                else: st.info("No prop candidates with edge ≥ 2.0 detected.")
            except Exception as e: st.error(f"Error: {e}")

    with tabs[1]:
        bt_sport = st.selectbox("Sport", ["NBA","WNBA"], index=0, key="bt_sport")
        if st.button("▶️ Run Backtest Now", type="primary", use_container_width=True):
            with st.spinner("Running backtest..."):
                result = run_backtest(bt_sport)
            st.success(f"Done — {result['summary']['n']} games | v8 Hit Rate: {result['summary']['v8_hit_rate']}%")
            for g in result["games"]:
                g["tc_signal"] = g.get("tc_signal","N/A")
                g["tc_edge"] = g.get("tc_edge", 0)
                g["actual_total"] = g.get("actual_total", 0)
                g["market_total"] = g.get("market_total", 0)
            st.dataframe(result["games"], use_container_width=True, hide_index=True)
            col_a,col_b = st.columns(2)
            col_a.metric("v8 Hit Rate", f"{result['summary'].get('v8_hit_rate',0)}%")
            col_b.metric("Games Tested", result["summary"]["n"])

    with tabs[2]:
        st.markdown("#### 📡 Live Multi-Sport Feed (simulated)")
        for sport, data in LIVE_SPORTS.items():
            sd = abs(data["score"]["home"] - data["score"]["away"])
            blowout = (sport in ("NBA","WNBA") and sd > 20) or (sport == "NFL" and sd > 17)
            with st.container():
                cs, csc = st.columns([3, 1])
                cs.markdown(f"""
                <div style="background:#161b22;border:1px solid #30363d;border-radius:12px;padding:14px;margin-bottom:8px">
                  <div style="display:flex;justify-content:space-between;align-items:center">
                    <span style="background:#3fb950/10;color:#3fb950;font-weight:700;font-size:11px;padding:3px 8px;border-radius:6px;border:1px solid #3fb950/20">{sport}</span>
                    <span style="color:#7d8590;font-size:11px">⏱ {data['minutes_remaining']}m</span>
                  </div>
                  <div style="display:flex;justify-content:space-between;margin-top:8px">
                    <span style="font-weight:600">{data['teams']['away']} @ {data['teams']['home']}</span>
                    <span style="font-weight:900;font-size:1.3rem;color:#f0883e">{data['score']['away']} — {data['score']['home']}</span>
                  </div>
                </div>""", unsafe_allow_html=True)
                csc.metric("Score Diff", f"{sd} pts", delta="⚠️ BLOWOUT" if blowout else "OK")
        st.markdown("#### 🚨 Alert Ticker")
        run_live_betting_rules()
        if SYSTEM_STATE["alert_logs"]:
            for log in SYSTEM_STATE["alert_logs"][:10]:
                st.warning(f"`{log['type']}`: {log['msg']}")
        else: st.info("No active alerts — all systems nominal.")
        st.markdown("#### 🎒 Betting Wallet")
        w = SYSTEM_STATE["betting_wallet"]
        w1,w2,w3 = st.columns(3)
        w1.metric("Fiat Balance", f"${w['fiat_balance']:,.2f}")
        w2.metric("Total P&L", f"${w['total_pnl']:+.2f}", delta="+" if w["total_pnl"] > 0 else "")
        w3.metric("Active Exposure", f"${w['active_exposure']:,.2f}")

    with tabs[3]:
        st.markdown("#### 📋 Today's Slate — Quick Project")
        slate_sport = st.selectbox("Sport", ["NBA","WNBA"], index=0, key="slate_sport")
        team_opts = list(get_teams(slate_sport).keys())
        presets = team_opts[:6] if slate_sport == "NBA" else team_opts[:4]
        for i in range(0, min(len(presets)-1, 6), 2):
            away_p, home_p = presets[i], presets[i+1]
            if st.button(f"▶ {away_p} @ {home_p}", use_container_width=True):
                st.session_state["away_sel"] = away_p
                st.session_state["home_sel"] = home_p
                st.session_state["half_chk"] = False
                st.rerun()

    with tabs[4]:
        st.markdown("#### 🧪 In-Depth Diagnostic Test")
        st.markdown("""
        Tests: TC Formula · Halftime Scale · v8 Game Total · Status Factors
        · Signal Logic · Edge Math · Backtest Coverage · Roster Integrity
        """)
        diagnostics = []; all_ok = True

        def diag(name, expected, actual, ok):
            diagnostics.append({"test": name, "expected": expected, "actual": actual,
                                 "status": "✅ PASS" if ok else "❌ FAIL"})
            if not ok: all_ok = False

        # 1: TC Formula
        pts, actual = 20.0, P("Test","G","6-4",20.0,4.0,6.0,2.0,"ACTIVE").tc_pts()
        diag("TC Formula: PTS×0.85+GAP", round(20.0*0.85-3.0,1), actual, abs(actual-round(20.0*0.85-3.0,1))<0.2)

        # 2: Q status
        actual = P("Q","G","6-4",20.0,4.0,6.0,2.0,"Q").tc_pts()
        diag("Status Factor: Q → 0.55", round(20.0*0.85*0.55-3.0,1), actual, abs(actual-round(20.0*0.85*0.55-3.0,1))<0.2)

        # 3: OUT status
        actual = P("OUT","G","6-4",20.0,4.0,6.0,2.0,"OUT").tc_pts()
        diag("Status Factor: OUT → 0", 0.0, actual, actual == 0.0)

        # 4: TC Line
        tc_val = P("T","G","6-4",20.0).tc_pts()
        ln = tc_line(tc_val)
        diag("TC Line = floor(TC×0.88)", int(tc_val*LINE_FACTOR), ln, ln == int(tc_val*LINE_FACTOR))

        # 5: Edge
        tc_val = P("T","G","6-4",20.0).tc_pts()
        ln = tc_line(tc_val)
        ed_val = edge(tc_val, ln)
        diag("Edge = TC − Line", round(tc_val-ln,2), ed_val, abs(ed_val-(tc_val-ln))<0.01)

        # 6: Halftime Scaling
        away_p = get_team("NYK","NBA").players[:5]
        home_p = get_team("CLE","NBA").players[:5]
        at_half = team_tc(away_p, 0.5)["tc_pts"]
        ht_half = team_tc(home_p, 0.5)["tc_pts"]
        at_full = team_tc(away_p, 1.0)["tc_pts"]
        ht_full = team_tc(home_p, 1.0)["tc_pts"]
        half_comb = at_half + ht_half; full_comb = at_full + ht_full
        ratio = half_comb/full_comb if full_comb else 0
        diag("Halftime: TC_combined × 0.5", "ratio=0.5", f"ratio={ratio:.3f}", abs(ratio-0.5)<0.02)

        # 7: Signal Logic
        cases = [(5.0,"OVER"),(-5.0,"UNDER"),(0.0,"PASS"),(3.1,"PASS"),(-3.1,"PASS")]
        okc = sum(1 for v,e in cases if signal_from_edge(v)==e)
        diag("Signal: +4 OVER | −4 UNDER | 0 PASS", "5/5 correct", f"{okc}/{len(cases)} correct", okc==len(cases))

        # 8: v8 Game Total
        v8 = calc_game_total_v8(get_team("OKC","NBA"), get_team("SAS","NBA"), 218.5)
        ok = v8["v8_combined"] > 0 and v8["lean"] in ("OVER","UNDER","NO EDGE")
        diag("v8 Game Total", "v8_combined>0", f"v8={v8['v8_combined']}, lean={v8['lean']}", ok)

        # 9: Roster Count
        nba_ok = len(NBA_TEAMS) >= 24; wnba_ok = len(WNBA_TEAMS) >= 10
        ok = nba_ok and wnba_ok
        diag("Roster Count", "NBA≥24, WNBA≥10", f"NBA={len(NBA_TEAMS)}, WNBA={len(WNBA_TEAMS)}", ok)

        # 10: Backtest
        try:
            r_nba = run_backtest("NBA"); r_wnba = run_backtest("WNBA")
            ok = r_nba["summary"]["n"] >= 4 and r_wnba["summary"]["n"] >= 2
            diag("Backtest: NBA + WNBA", "NBA≥4, WNBA≥2", f"NBA={r_nba['summary']['n']}, WNBA={r_wnba['summary']['n']}", ok)
        except Exception as e:
            diag("Backtest", "-", str(e), False)

        st.dataframe(diagnostics, use_container_width=True, hide_index=True)
        passed = sum(1 for d in diagnostics if "PASS" in d["status"])
        failed = len(diagnostics) - passed
        col_d1,col_d2 = st.columns(2)
        col_d1.metric("Tests Passed", f"{passed}/{len(diagnostics)}", delta="ALL CLEAR 🚀" if all_ok else "FAILURES ⚠️")
        col_d2.metric("Tests Failed", f"{failed}/{len(diagnostics)}", delta="🔴 ISSUES" if failed > 0 else "✅ NONE")
        st.download_button("📥 Download Diagnostic Report (JSON)",
                           data=json.dumps({"diagnostics": diagnostics, "summary": {
                               "passed": passed, "failed": failed,
                               "timestamp": datetime.datetime.now().isoformat(), "version": "9.0.0"}}, indent=2),
                           file_name="tc_diagnostic_report.json", mime="application/json")

# ── CLI ──────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sports TC v9 Engine")
    parser.add_argument("--sport", default="NBA", choices=["NBA","WNBA"])
    parser.add_argument("--backtest", action="store_true")
    parser.add_argument("--game", type=str, help="'AWAY @ HOME'")
    parser.add_argument("--total", type=float, default=210.5)
    parser.add_argument("--spread", type=float, default=-5.0)
    parser.add_argument("--bankroll", type=float, default=1000.0)
    parser.add_argument("--list-teams", action="store_true")
    parser.add_argument("--streamlit", action="store_true", help="Launch Streamlit dashboard")
    args = parser.parse_args()
    if args.streamlit:
        sys.argv = ["streamlit","run",__file__,"--server.port","8501","--browser.gatherUsageStats=False"]
        sys.exit(0)
    if args.backtest:
        print(json.dumps(run_backtest(args.sport), indent=2))
    elif args.list_teams:
        for abbr, team in get_teams(args.sport).items():
            print(f"{abbr}: {team.name}")
            for n in team.injury_notes: print(f"   {n}")
    elif args.game:
        parts = args.game.split("@")
        if len(parts) < 2: print("Usage: --game 'AWAY @ HOME'"); raise SystemExit(1)
        away = parts[0].strip().upper(); home = parts[1].strip().upper()
        result = project_game(home, away, args.total, args.spread, series="CLI", game_time="CLI", bankroll=args.bankroll, sport=args.sport)
        print(json.dumps(result, indent=2))
    else:
        print("TC Sports App v9:")
        print("  python sports_tc_app.py --streamlit    Launch Streamlit dashboard")
        print("  python sports_tc_app.py --backtest     Run backtest")
        print("  python sports_tc_app.py --game 'A@H'  Project a game")
        print("  python sports_tc_app.py --list-teams   List teams")
