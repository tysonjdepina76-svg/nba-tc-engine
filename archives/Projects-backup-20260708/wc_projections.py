#!/usr/bin/env python3

# TC — Triple Conservative — Trademark June 2026 — All rights reserved.
"""WC Projections - apply wc_tc_math to live player prop data."""
import csv, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from wc_tc_math import wc_bayes_shrink, position_of_player, WC_LEAGUE_PRIOR, expected_hit_rate, is_playable

HISTORICAL = Path("/home/workspace/Reports/wc_historical_2010_2022.csv")
LIVE_PROPS = Path("/home/workspace/Daily_Log/worldcup/" + __import__("datetime").datetime.now().strftime("%Y%m%d") + "/props.json")

def load_history():
    rows = list(csv.DictReader(open(HISTORICAL)))
    for r in rows:
        for k in ["totalGoals","goalAssists","totalShots","shotsOnTarget","foulsCommitted","yellowCards","saves"]:
            r[k] = float(r.get(k) or 0)
        r["starter"] = int(r.get("starter") or 0)
    by_player = defaultdict(list)
    for r in rows:
        if r["starter"]:
            by_player[(r["player"], position_of_player(r.get("pos","")))].append(r)
    for k in by_player:
        by_player[k].sort(key=lambda x: x.get("date",""))
    return by_player

def project_player(player_name, pos_class, line, stat, by_player, n_games=3):
    history = by_player.get((player_name, pos_class), [])
    if len(history) < 1:
        return None, 0, "no_history"
    prior_games = history[-n_games:]
    sample = sum(p[stat] for p in prior_games) / len(prior_games)
    proj = wc_bayes_shrink(stat, sample, pos_class, n_games=len(prior_games))
    edge = (proj - line) / max(line, 0.5)
    return round(proj, 2), len(history), round(edge, 3)

def main():
    by_player = load_history()
    print(f"Loaded {sum(len(v) for v in by_player.values())} starter-rows for {len(by_player)} unique players")
    print()
    if not LIVE_PROPS.exists():
        print(f"No live props at {LIVE_PROPS}")
        return
    import json, csv
    picks_csv = LIVE_PROPS.parent / "picks.csv"
    picks = []
    if picks_csv.exists():
        with picks_csv.open() as f:
            for row in csv.DictReader(f):
                if row.get("player") and row.get("stat") and row.get("over_price"):
                    picks.append(row)
    print(f"Live WC picks (CSV): {len(picks)}")
    print()
    stats_to_keys = {"goals":"totalGoals","assists":"goalAssists","shots":"totalShots","shots_on_target":"shotsOnTarget","fouls":"foulsCommitted","cards":"yellowCards","saves":"saves"}
    enriched = []
    for p in picks:
        player = p.get("player","")
        stat_label = p.get("stat", "").lower()
        stat = stats_to_keys.get(stat_label)
        if not stat or not is_playable(stat):
            continue
        line = float(p.get("line", 0) or 0)
        proj, n_hist, edge = project_player(player, p.get("pos_class","UNK"), line, stat, by_player)
        if proj is None:
            continue
        playable = expected_hit_rate(stat)
        if abs(edge) < 0.02:
            continue  # not enough edge
        enriched.append({
            "player": player,
            "stat": stat_label,
            "line": line,
            "direction": p.get("direction","Over"),
            "tc_proj": proj,
            "n_hist": n_hist,
            "edge": edge,
            "exp_hr": playable,
            "odds": p.get("odds", p.get("over_price","—")),
        })
    enriched.sort(key=lambda x: -x["edge"])
    print(f"Enriched WC picks: {len(enriched)}")
    print()
    print(f"{"Player":25s} {"Stat":10s} {"Line":5s} {"Dir":5s} {"TC":5s} {"Edge":6s} {"ExpHR":5s} {"N":3s} {"Odds":6s}")
    print("-" * 90)
    for e in enriched[:50]:
        print(f"{e["player"]:25s} {e["stat"]:10s} {e["line"]:5.1f} {e["direction"]:5s} {e["tc_proj"]:5.2f} {e["edge"]:6.2f} {e["exp_hr"]:5.1%} {e["n_hist"]:3d} {str(e["odds"]):6s}")

    # Persist to CSV
    from datetime import datetime
    out_csv = Path("/home/workspace/Reports") / f"wc_tc_projections_{datetime.now().strftime('%Y%m%d')}.csv"
    with out_csv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(enriched[0].keys()))
        w.writeheader()
        w.writerows(enriched)
    print(f"Wrote: {out_csv}  ({len(enriched)} rows)")

if __name__ == "__main__":
    main()
