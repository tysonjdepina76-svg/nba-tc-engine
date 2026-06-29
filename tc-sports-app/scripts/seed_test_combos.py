# TC seed combo generator — synthetic WNBA + MLB projections to drive ComboQualifier.
# TC — Triple Conservative — Trademark June 2026.
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from domain.entities import Projection
from domain.combo_qualifier import ComboQualifier

# Real WNBA + MLB players today; tc_projection = season_avg * 1.1 (offensive boost),
# edge = tc_projection - line. Direction inferred from sign of edge.
WNBA_PLAYERS = [
    # (player, team, role, stat, season_avg, line)
    ("A'ja Wilson", "LV",  "F",  "PTS", 27.2, 25.5),
    ("A'ja Wilson", "LV",  "F",  "REB", 11.8,  9.5),
    ("A'ja Wilson", "LV",  "F",  "BLK",  1.7,  0.5),
    ("Kelsey Plum", "LV",  "G",  "PTS", 20.4, 18.5),
    ("Kelsey Plum", "LV",  "G",  "AST",  4.6,  3.5),
    ("Kelsey Plum", "LV",  "G",  "3PM",  3.1,  2.5),
    ("Jackie Young", "LV", "G",  "AST",  5.2,  4.5),
    ("Jackie Young", "LV", "G",  "3PM",  2.4,  1.5),
    ("Alyssa Thompson", "LV", "G", "PTS", 14.1, 12.5),
    ("Caitlin Clark", "IND", "G", "PTS", 22.8, 19.5),
    ("Caitlin Clark", "IND", "G", "AST",  8.4,  7.5),
    ("Caitlin Clark", "IND", "G", "3PM",  3.6,  2.5),
    ("Aliyah Boston", "IND", "C", "REB",  9.8,  8.5),
    ("Aliyah Boston", "IND", "C", "BLK",  1.3,  0.5),
    ("Kelsey Mitchell", "IND", "G", "PTS", 18.7, 17.5),
    ("NaLyssa Smith", "IND", "F", "REB",  7.2,  6.5),
]

MLB_PLAYERS = [
    ("Aaron Judge", "NYY", "OF", "HITS", 1.8,  1.5),
    ("Aaron Judge", "NYY", "OF", "HR",    0.7,  0.5),
    ("Aaron Judge", "NYY", "OF", "RBI",   1.4,  1.5),
    ("Juan Soto",   "NYY", "OF", "HITS", 1.6,  1.5),
    ("Juan Soto",   "NYY", "OF", "BB",    1.2,  0.5),
    ("Giancarlo Stanton", "NYY", "DH", "RBI", 1.1, 0.5),
    ("Shohei Ohtani", "LAD", "DH", "HITS", 1.7,  1.5),
    ("Shohei Ohtani", "LAD", "DH", "HR",    0.6,  0.5),
    ("Mookie Betts", "LAD", "OF", "HITS", 1.5,  1.5),
    ("Mookie Betts", "LAD", "OF", "BB",    0.9,  0.5),
    ("Freddie Freeman", "LAD", "1B", "HITS", 1.6, 1.5),
]

def make_projections(players, sport, game_id):
    out = []
    for player, team, role, stat, sa, line in players:
        tc_proj = round(sa * 1.1, 2)
        edge = round(tc_proj - line, 2)
        direction = "OVER" if edge > 0 else "UNDER"
        out.append(Projection(
            player=player, team=team, role=role, status="ACTIVE",
            stat=stat, tc_projection=tc_proj, line=line,
            edge=edge, direction=direction, valid=True,
        ))
    return out

def main():
    wnba_proj = make_projections(WNBA_PLAYERS, "WNBA", "LV@IND")
    mlb_proj  = make_projections(MLB_PLAYERS,   "MLB",  "NYY@LAD")

    by_sport = {"WNBA": (wnba_proj, "LV@IND"), "MLB": (mlb_proj, "NYY@LAD")}

    all_combos = []
    all_reports = {}
    for sport, (projs, gid) in by_sport.items():
        cq = ComboQualifier(sport)
        combos, report = cq.qualify(projs)
        # tag game_id onto each combo's first leg
        for c in combos:
            c.game_id = gid
        all_combos.extend(combos)
        all_reports[sport] = report.to_dict()
        print(f"[{sport}] {len(projs)} projections → {len(combos)} combos, "
              f"{report.to_dict()['filtered_count']} filtered")

    out_path = Path("/home/workspace/tc-sports-app/data/seeded_combos.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": "2026-06-29",
        "sport_coverage": ["WNBA", "MLB"],
        "combo_count": len(all_combos),
        "projections": {
            "WNBA": [p.to_dict() for p in wnba_proj],
            "MLB":  [p.to_dict() for p in mlb_proj],
        },
        "combos": [c.to_dict() for c in all_combos[:6]],
        "filter_reports": all_reports,
        "thresholds": {
            "WNBA":   ComboQualifier("WNBA").criteria,
            "MLB":    ComboQualifier("MLB").criteria,
        },
    }
    out_path.write_text(json.dumps(payload, indent=2))
    print(f"\nWrote {out_path} — {len(all_combos)} total, {len(payload['combos'])} in payload")
    print(f"Top combo: {payload['combos'][0]['legs'][0]['player']} "
          f"+ {payload['combos'][0]['legs'][1]['player'] if len(payload['combos'][0]['legs'])>1 else ''}")
    print(f"  hit_prob={payload['combos'][0]['hit_probability']:.3f}, "
          f"avg_edge={payload['combos'][0]['avg_edge']:.2f}")

if __name__ == "__main__":
    main()
