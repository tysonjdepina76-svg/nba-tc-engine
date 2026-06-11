"""Reconcile TC picks against ESPN final box scores and write back hit/miss results.

Reads:
  - /home/workspace/Daily_Log/<YYYY-MM-DD>/proj_<SPORT>_<AWAY>_at_<HOME>.json (TC picks)
  - /home/workspace/Daily_Log/final/<sport>_<AWAY>_at_<HOME>_final_<eventid>_<ts>.json (ESPN final box)

Writes:
  - Updates each pick with `actual` and `result` (HIT / MISS / VOID)
  - /home/workspace/Daily_Log/<YYYY-MM-DD>/hit_rates_<sport>_<away>_at_<home>.md
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

LOG_DIR = Path("/home/workspace/Daily_Log")
FINAL_DIR = LOG_DIR / "final"

STAT_KEYS = {
    "PTS": "points",
    "REB": "rebounds",
    "AST": "assists",
    "3PM": "threepointfieldgoalsmade",
    "STL": "steals",
    "BLK": "blocks",
}


def load_box(path: Path) -> tuple[dict, str, str]:
    """Return ({player_lower: {stat: val}}, sport, matchup_key) from a final box file.

    Handles two shapes:
      - new scraper: teams[].roster[] with name+points+rebounds+...
      - old direct call: box.players[].statistics[].athletes[] with raw stats arrays
    """
    d = json.loads(path.read_text())
    sport = (d.get("sport") or "").upper()

    # derive away/home from name (e.g. "Atlanta Dream at Chicago Sky")
    name = d.get("name") or d.get("matchup") or ""
    if " at " in name:
        away_full, home_full = name.split(" at ", 1)
    else:
        # fall back to filename: wnba_AtlantaDream_AT_ChicagoSky_final_...
        stem = path.stem
        m = re.search(r"_(?P<a>[A-Za-z]+)_AT_(?P<h>[A-Za-z]+)_", stem)
        if m:
            away_full, home_full = m.group("a"), m.group("h")
        else:
            away_full = home_full = ""
    away = re.sub(r"[^A-Za-z]", "", away_full)[:3].upper() if away_full else ""
    home = re.sub(r"[^A-Za-z]", "", home_full)[:3].upper() if home_full else ""
    matchup_key = f"{away}_at_{home}"

    players: dict[str, dict] = {}

    # shape A: new scraper -> teams[].players[]
    team_blocks = d.get("teams") or []
    if isinstance(team_blocks, list) and team_blocks and isinstance(team_blocks[0], dict) and "players" in team_blocks[0]:
        for t in team_blocks:
            team_code = (t.get("code") or t.get("team_code") or "").upper()
            for a in t.get("players", []):
                nm = a.get("name") or ""
                if not nm:
                    continue
                players[nm.lower()] = {
                    "team": team_code or a.get("team", ""),
                    "minutes": a.get("minutes", ""),
                    "points": int(a.get("points") or 0),
                    "rebounds": int(a.get("rebounds") or 0),
                    "assists": int(a.get("assists") or 0),
                    "steals": int(a.get("steals") or 0),
                    "blocks": int(a.get("blocks") or 0),
                    "threepointfieldgoalsmade": int(a.get("threePointMade") or a.get("threepointfieldgoalsmade") or 0),
                    "turnovers": int(a.get("turnovers") or 0),
                    "fouls": int(a.get("fouls") or 0),
                }
        return players, sport, matchup_key

    # shape B: old direct call -> box.players[].statistics[].athletes[]
    if "box" in d:
        for t in d["box"].get("players", []):
            team_code = (t.get("team", {}) or {}).get("abbreviation", "").upper()
            for grp in t.get("statistics", []):
                keys = [k.lower() for k in grp.get("keys", [])]
                if not keys or "points" not in keys:
                    continue
                idx = {k: i for i, k in enumerate(keys)}
                for a in grp.get("athletes", []):
                    ath = a.get("athlete", {}) or {}
                    nm = ath.get("displayName") or ath.get("shortName") or ath.get("name", "")
                    if not nm:
                        continue
                    vals = a.get("stats", [])
                    row = {k: vals[i] if i < len(vals) else "" for k, i in idx.items()}
                    # try to coerce numerics, leave X-Y composite as-is
                    parsed = {"team": team_code}
                    for k, v in row.items():
                        try:
                            parsed[k] = int(v)
                        except (TypeError, ValueError):
                            parsed[k] = v
                    players[nm.lower()] = parsed
    return players, sport, matchup_key


def find_picks_file(sport: str, matchup_key: str) -> Path | None:
    """Search last 3 days for proj_<SPORT>_<AWAY>_at_<HOME>.json."""
    for offset in range(4):
        d = LOG_DIR / (datetime.utcnow() - timedelta(days=offset)).strftime("%Y-%m-%d")
        if not d.exists():
            continue
        cand = d / f"proj_{sport}_{matchup_key}.json"
        if cand.exists():
            return cand
    return None


def lookup_actual(player: str, stat: str, box: dict) -> tuple[int | None, str]:
    """Fuzzy-match player name + return (actual_value, team_code) from box."""
    if not player:
        return None, ""
    box_key = STAT_KEYS.get(stat.upper())
    if not box_key:
        return None, ""
    needle_last = player.split()[-1].lower() if player else ""
    needle_first = player.split()[0].lower() if player else ""
    # 1) exact full-name match
    if player.lower() in box:
        return int(box[player.lower()].get(box_key) or 0), box[player.lower()].get("team", "")
    # 2) startswith last name
    for nm, row in box.items():
        if nm.startswith(needle_last + " ") or nm.startswith(needle_last):
            return int(row.get(box_key) or 0), row.get("team", "")
    # 3) contains last name
    for nm, row in box.items():
        if needle_last and needle_last in nm:
            return int(row.get(box_key) or 0), row.get("team", "")
    return None, ""


def reconcile(picks_file: Path, box: dict, sport: str, matchup_key: str) -> dict:
    data = json.loads(picks_file.read_text())
    picks = data.get("picks") or data.get("valid_props") or data.get("projections") or []
    n_hit = n_miss = n_void = 0
    hits_over = hits_under = 0
    by_stat: dict[str, dict] = {}
    enriched = []
    for p in picks:
        player = p.get("player", "")
        stat = (p.get("stat") or "").upper()
        direction = (p.get("direction") or "").upper()
        line = p.get("market_line") or p.get("dk_line") or p.get("line")
        tc = p.get("tc_projection") or p.get("tc_target")
        actual, team = lookup_actual(player, stat, box)
        if actual is None:
            result = "VOID"
            n_void += 1
        else:
            p["actual"] = actual
            p["result_team"] = team
            if direction == "OVER":
                if line is not None and actual > line:
                    result = "HIT"; n_hit += 1; hits_over += 1
                else:
                    result = "MISS"; n_miss += 1
            elif direction == "UNDER":
                if line is not None and actual < line:
                    result = "HIT"; n_hit += 1; hits_under += 1
                else:
                    result = "MISS"; n_miss += 1
            else:
                result = "VOID"; n_void += 1
        p["result"] = result
        p["actual"] = actual
        enriched.append(p)
        by_stat.setdefault(stat, {"hit": 0, "miss": 0, "void": 0})
        if result == "HIT": by_stat[stat]["hit"] += 1
        elif result == "MISS": by_stat[stat]["miss"] += 1
        else: by_stat[stat]["void"] += 1

    data["picks"] = enriched
    data["reconciled_at"] = datetime.utcnow().isoformat() + "Z"
    picks_file.write_text(json.dumps(data, indent=2))

    return {
        "picks_file": str(picks_file),
        "matchup": matchup_key,
        "sport": sport,
        "n_picks": len(picks),
        "n_hit": n_hit,
        "n_miss": n_miss,
        "n_void": n_void,
        "hit_rate": round(n_hit / max(1, n_hit + n_miss) * 100, 1),
        "over_hits": hits_over,
        "under_hits": hits_under,
        "by_stat": by_stat,
    }


def write_report(result: dict, out_path: Path) -> None:
    md = []
    md.append(f"# Hit Rate Report — {result['sport']} {result['matchup']}")
    md.append("")
    md.append(f"- Picks file: `{result['picks_file']}`")
    md.append(f"- Total picks: {result['n_picks']}")
    md.append(f"- HIT: {result['n_hit']}")
    md.append(f"- MISS: {result['n_miss']}")
    md.append(f"- VOID: {result['n_void']}")
    md.append(f"- **Hit rate (graded)**: {result['hit_rate']}%")
    md.append(f"- OVER hits: {result['over_hits']}  |  UNDER hits: {result['under_hits']}")
    md.append("")
    md.append("## By stat")
    md.append("")
    md.append("| Stat | Hit | Miss | Void | HR |")
    md.append("|---|---|---|---|---|")
    for stat, c in sorted(result["by_stat"].items()):
        graded = c["hit"] + c["miss"]
        hr = round(c["hit"] / graded * 100, 1) if graded else 0.0
        md.append(f"| {stat} | {c['hit']} | {c['miss']} | {c['void']} | {hr}% |")
    out_path.write_text("\n".join(md))


def main() -> int:
    sport_filter = sys.argv[1].upper() if len(sys.argv) > 1 else None
    box_files = sorted(FINAL_DIR.glob("*.json"))
    if not box_files:
        print("no final boxes to reconcile")
        return 0
    total_picks = total_hit = total_miss = 0
    for bf in box_files:
        box, sport, matchup_key = load_box(bf)
        if sport_filter and sport != sport_filter:
            continue
        if not matchup_key or matchup_key == "_at_":
            print(f"[skip] {bf.name}: could not derive matchup key")
            continue
        picks_file = find_picks_file(sport, matchup_key)
        if not picks_file:
            print(f"[skip] {bf.name}: no TC picks file for {sport} {matchup_key}")
            continue
        result = reconcile(picks_file, box, sport, matchup_key)
        report_path = picks_file.parent / f"hit_rates_{sport}_{matchup_key}.md"
        write_report(result, report_path)
        print(f"[ok] {sport} {matchup_key}: {result['n_hit']}H / {result['n_miss']}M / {result['n_void']}V -> {result['hit_rate']}%  (report: {report_path})")
        total_picks += result["n_hit"] + result["n_miss"]
        total_hit += result["n_hit"]
        total_miss += result["n_miss"]
    if total_picks:
        overall = round(total_hit / total_picks * 100, 1)
        print(f"\nOverall: {total_hit}/{total_picks} = {overall}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
