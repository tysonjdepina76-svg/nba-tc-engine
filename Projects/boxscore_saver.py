#!/usr/bin/env python3
"""
Dedup-aware Halftime + Final Boxscore Saver for TC Backtests.

Saves halftime boxscores (when game reaches Q3+ / period >= 3) and
final boxscores (post-game). Uses event_id as dedup key via registry —
never saves the same event+type twice.

Usage:
    python3 Projects/boxscore_saver.py                    # today, all sports
    python3 Projects/boxscore_saver.py --sport WNBA        # WNBA only
    python3 Projects/boxscore_saver.py --mode final        # finals only
    python3 Projects/boxscore_saver.py --mode halftime     # halftimes only
    python3 Projects/boxscore_saver.py --purge-dupes        # clean duplicates
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import requests
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

WORKSPACE = Path("/home/workspace")
LOG_DIR = WORKSPACE / "Daily_Log"
HT_DIR = LOG_DIR / "halftime"
FIN_DIR = LOG_DIR / "final"
DUPE_DIR = LOG_DIR / "_dupes"
REG = LOG_DIR / "boxscore_registry.json"
MLB_DIR = LOG_DIR / "mlb_boxscores"

for d in [LOG_DIR, HT_DIR, FIN_DIR, MLB_DIR]:
    d.mkdir(parents=True, exist_ok=True)

LEAGUE = {"WNBA": "basketball/wnba", "NBA": "basketball/nba"}
MLB_LEAGUE = {"MLB": "baseball/mlb"}

# ══════ registry ═══════════════════════════════════════════════════════

def _loadreg() -> dict:
    try:
        return json.loads(REG.read_text()) if REG.exists() else {}
    except Exception:
        return {}

def _savereg(r: dict):
    REG.write_text(json.dumps(r, indent=2))

def already_saved(eid: str, boxtype: str, search_dir: Path | None = None) -> bool:
    reg = _loadreg()
    key = f"{eid}:{boxtype}"
    if key in reg:
        return True
    if search_dir is not None:
        dirs = [search_dir]
    else:
        dirs = [HT_DIR if boxtype == "halftime" else FIN_DIR]
    for tgt in dirs:
        for f in tgt.glob(f"*_{eid}_*.json"):
            reg[f"{eid}:{boxtype}"] = f.stat().st_mtime
            _savereg(reg)
            return True
    return False

def mark_saved(eid: str, boxtype: str):
    reg = _loadreg()
    reg[f"{eid}:{boxtype}"] = datetime.now(timezone.utc).isoformat()
    _savereg(reg)

# ══════ ESPN  ══════════════════════════════════════════════════════════

def _sb(spath: str, dstr: str) -> dict:
    try:
        r = requests.get(
            f"https://site.api.espn.com/apis/site/v2/sports/{spath}/scoreboard",
            params={"dates": dstr}, timeout=15)
        return r.json() if r.status_code == 200 else {}
    except Exception as e:
        print(f"  scoreboard err: {e}")
        return {}

def _sum(spath: str, eid: str) -> dict | None:
    try:
        r = requests.get(
            f"https://site.api.espn.com/apis/site/v2/sports/{spath}/summary",
            params={"event": eid}, timeout=20)
        return r.json() if r.status_code == 200 else None
    except Exception as e:
        print(f"  summary err {eid}: {e}")
        return None

# ══════ parse  ═════════════════════════════════════════════════════════

def _int(v, d=0):
    try:
        return int(str(v).replace(",", ""))
    except Exception:
        return d

def build_final(s: dict, eid: str, sport: str) -> dict | None:
    comp = (s.get("header") or {}).get("competitions", [{}])[0]
    cs = comp.get("competitors", [])
    teams = {}
    for c in cs:
        teams[c.get("homeAway", "")] = c.get("team", {}).get("displayName", "?")
    players = {}
    for grp in (s.get("boxscore") or {}).get("players", []):
        tn = grp.get("team", {}).get("displayName", "?")
        for sbh in grp.get("statistics", []):
            keys = sbh.get("keys", [])
            for ath in sbh.get("athletes", []):
                nm = ath.get("athlete", {}).get("displayName", "?")
                if not nm or nm == "?":
                    continue
                raw = ath.get("stats", [])
                row = {"name": nm, "team": tn}

                def _g(field, idx_key):
                    if idx_key in keys and keys.index(idx_key) < len(raw):
                        row[field] = _int(raw[keys.index(idx_key)])

                _g("pts", "points")
                _g("reb", "rebounds")
                _g("ast", "assists")
                _g("stl", "steals")
                _g("blk", "blocks")
                _g("to", "turnovers")
                _g("pf", "fouls")
                _g("oreb", "offensiveRebounds")
                _g("dreb", "defensiveRebounds")
                if "minutes" in keys and keys.index("minutes") < len(raw):
                    row["minutes"] = str(raw[keys.index("minutes")])
                t3k = "threePointFieldGoalsMade-threePointFieldGoalsAttempted"
                if t3k in keys and keys.index(t3k) < len(raw):
                    v = str(raw[keys.index(t3k)])
                    row["fg3m"] = _int(v.split("-")[0]) if "-" in v else _int(v)
                players[nm] = row

    if not players:
        return None

    return {
        "event_id": eid, "sport": sport,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "type": "final", "players": players,
        "score": {
            "away": _int(next((c.get("score") for c in cs if c.get("homeAway") == "away"), 0)),
            "home": _int(next((c.get("score") for c in cs if c.get("homeAway") == "home"), 0))
        },
        "away_team": teams.get("away", "?"), "home_team": teams.get("home", "?")
    }

def build_halftime(s: dict, final: dict) -> dict | None:
    plays = s.get("plays", [])
    if not plays:
        return None

    p1p2 = [p for p in plays if (p.get("period") or {}).get("number") in (1, 2)]
    if not p1p2:
        return None

    # find end-of-Q2 marker
    ht_play = None
    for p in p1p2:
        if ((p.get("clock") or {}).get("displayValue") == "0.0"
                and (p.get("period") or {}).get("number") == 2):
            ht_play = p
    if not ht_play:
        return None

    away_h = _int(ht_play.get("awayScore"))
    home_h = _int(ht_play.get("homeScore"))

    players = {}
    for p in [x for x in p1p2 if x.get("scoringPlay")]:
        pts = _int(p.get("scoreValue"))
        parts = p.get("participants") or []
        if not parts:
            continue
        nm = (parts[0].get("athlete") or {}).get("displayName", "")
        if not nm:
            continue
        row = players.setdefault(nm, {"name": nm, "pts": 0, "fg3m": 0, "ast": 0, "reb": 0, "stl": 0, "blk": 0})
        row["pts"] += pts
        txt = p.get("text", "").lower()
        if "three point" in txt or "3pt" in txt:
            row["fg3m"] += 1

    for p in p1p2:
        txt = p.get("text", "").lower()
        parts = p.get("participants") or []
        if not parts:
            continue
        nm = (parts[0].get("athlete") or {}).get("displayName", "")
        if not nm:
            continue
        if "rebound" in txt:
            r = players.setdefault(nm, {"name": nm, "pts": 0, "reb": 0, "ast": 0, "fg3m": 0, "stl": 0, "blk": 0})
            r["reb"] = r.get("reb", 0) + 1
        elif "steal" in txt:
            r = players.setdefault(nm, {"name": nm, "pts": 0, "reb": 0, "ast": 0, "fg3m": 0, "stl": 0, "blk": 0})
            r["stl"] = r.get("stl", 0) + 1
        elif "block" in txt:
            r = players.setdefault(nm, {"name": nm, "pts": 0, "reb": 0, "ast": 0, "fg3m": 0, "stl": 0, "blk": 0})
            r["blk"] = r.get("blk", 0) + 1
        elif "assist" in txt:
            r = players.setdefault(nm, {"name": nm, "pts": 0, "reb": 0, "ast": 0, "fg3m": 0, "stl": 0, "blk": 0})
            r["ast"] = r.get("ast", 0) + 1

    return {
        "event_id": final["event_id"], "sport": final["sport"],
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "type": "halftime", "players": players,
        "score": {"away": away_h, "home": home_h},
        "away_team": final["away_team"], "home_team": final["home_team"]
    }

# ══════ save / dedup  ══════════════════════════════════════════════════

def _save(box: dict, out_dir: Path) -> Path | None:
    safe = (box.get("away_team", "?") + "_at_" + box.get("home_team", "?")) \
        .replace(" ", "").replace(".", "")
    fn = f"{box['sport'].lower()}_{safe}_{box['type']}_{box['event_id']}" \
         f"_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    fp = out_dir / fn
    fp.write_text(json.dumps(box, indent=2))
    return fp

def save_box(box: dict, out_dir: Path) -> bool:
    """Save boxscore, mark registry. Returns True if saved."""
    try:
        fp = _save(box, out_dir)
        mark_saved(box["event_id"], box["type"])
        print(f"  ✅ {box['type']:8s} {box['away_team']} @ {box['home_team']} "
              f"(id={box['event_id']})")
        return True
    except Exception as e:
        print(f"  ❌ save error: {e}")
        return False

def purge_duplicates():
    """Remove older duplicate files, keep most recent per event_id+type."""
    DUPE_DIR.mkdir(parents=True, exist_ok=True)
    removed = 0
    for box_dir, label in [(HT_DIR, "halftime"), (FIN_DIR, "final")]:
        by_event = defaultdict(list)
        for f in box_dir.glob("*.json"):
            parts = f.stem.split("_")
            eid = None
            for p in parts:
                if p.isdigit() and len(p) == 9:
                    eid = p
                    break
            if not eid:
                continue
            by_event[eid].append(f)

        for eid, files in by_event.items():
            if len(files) <= 1:
                continue
            # keep newest
            files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            for old in files[1:]:
                dst = DUPE_DIR / f"{label}_{old.name}"
                try:
                    old.rename(dst)
                    removed += 1
                except Exception:
                    pass

    print(f"  🧹 Dupes moved to _dupes/: {removed} files")
    # rebuild registry from remaining files
    rebuild_registry()

def rebuild_registry():
    """Rebuild registry from filesystem."""
    reg = {}
    for box_dir, label in [(HT_DIR, "halftime"), (FIN_DIR, "final")]:
        for f in box_dir.glob("*.json"):
            parts = f.stem.split("_")
            eid = None
            for p in parts:
                if p.isdigit() and len(p) == 9:
                    eid = p
                    break
            if eid:
                reg[f"{eid}:{label}"] = f.stat().st_mtime
    _savereg(reg)
    print(f"  📋 Registry rebuilt: {len(reg)} entries")

# ══════ MLB  ══════════════════════════════════════════════════════════

def build_mlb_final(s: dict, eid: str, dstr: str) -> dict | None:
    comp = (s.get("header") or {}).get("competitions", [{}])[0]
    cs = comp.get("competitors", [])
    teams = {}
    for c in cs:
        teams[c.get("homeAway", "")] = c.get("team", {}).get("displayName", "?")
    batting = {}
    pitching = {}
    for grp in (s.get("boxscore") or {}).get("players", []):
        tn = grp.get("team", {}).get("displayName", "?")
        for sbh in grp.get("statistics", []):
            keys = sbh.get("keys", [])
            if not keys:
                continue
            is_pitching = "ERA" in keys or "fullInnings" in str(keys[0])
            target = pitching if is_pitching else batting
            for ath in sbh.get("athletes", []):
                nm = ath.get("athlete", {}).get("displayName", "?")
                if not nm or nm == "?":
                    continue
                raw = ath.get("stats", [])
                row = {"name": nm, "team": tn}
                if is_pitching:
                    def _gp(field, idx_key):
                        if idx_key in keys and keys.index(idx_key) < len(raw):
                            row[field] = str(raw[keys.index(idx_key)])
                    _gp("ip", "fullInnings.partInnings")
                    _gp("h", "hits")
                    _gp("r", "runs")
                    _gp("er", "earnedRuns")
                    _gp("bb", "walks")
                    _gp("so", "strikeouts")
                    _gp("hr", "homeRuns")
                    _gp("era", "ERA")
                    _gp("pitches", "pitches")
                else:
                    def _gb(field, idx_key):
                        if idx_key in keys and keys.index(idx_key) < len(raw):
                            row[field] = str(raw[keys.index(idx_key)])
                    _gb("ab", "atBats")
                    _gb("r", "runs")
                    _gb("h", "hits")
                    _gb("rbi", "RBIs")
                    _gb("hr", "homeRuns")
                    _gb("bb", "walks")
                    _gb("so", "strikeouts")
                    _gb("avg", "avg")
                target[nm] = row

    away = teams.get("away", "?")
    home = teams.get("home", "?")
    away_score = _int(next((c.get("score") for c in cs if c.get("homeAway") == "away"), 0))
    home_score = _int(next((c.get("score") for c in cs if c.get("homeAway") == "home"), 0))
    return {
        "event_id": eid, "sport": "mlb", "date": dstr,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "type": "final",
        "batting": batting, "pitching": pitching,
        "score": {"away": away_score, "home": home_score},
        "away_team": away, "home_team": home
    }

def scan_and_save_mlb(mode: str = "all"):
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    for sp, spath in MLB_LEAGUE.items():
        sb = _sb(spath, today)
        events = sb.get("events", [])
        if not events:
            print(f"  MLB: no events on {today}")
            continue
        print(f"  MLB: {len(events)} event(s) on {today}")
        saved = 0
        for ev in events:
            eid = str(ev.get("id", ""))
            if not eid:
                continue
            status = (ev.get("status") or {}).get("type") or {}
            state = status.get("state", "")
            away = (ev.get("competitions", [{}])[0].get("competitors", [{}])[0]
                    .get("team", {}).get("abbreviation", "?"))
            home = (ev.get("competitions", [{}])[0].get("competitors", [{}])[1]
                    .get("team", {}).get("abbreviation", "?"))
            if mode in ("all", "final") and state == "post":
                if not already_saved(eid, "final", MLB_DIR):
                    summary = _sum(spath, eid)
                    if summary:
                        bx = build_mlb_final(summary, eid, today)
                        if bx and save_box(bx, MLB_DIR):
                            saved += 1
                else:
                    print(f"    [{state}] {away}@{home} — already saved ✓")
        print(f"  MLB saved {saved} finals")

# ══════ soccer  ══════════════════════════════════════════════════════

def scan_and_save_soccer(mode: str = "final"):
    """Delegate WC capture to the soccer-specific boxscore saver."""
    import subprocess
    soccer_script = WORKSPACE / "Projects" / "soccer_boxscore_capture.py"
    cmd = [sys.executable, str(soccer_script)]
    if mode != "all":
        cmd.extend(["--mode", mode])
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

# ══════ main scanner  ══════════════════════════════════════════════════

def scan_and_save(sport: str | None = None, mode: str = "all"):
    if sport == "MLB":
        scan_and_save_mlb(mode=mode)
        return
    sports = [sport] if sport else list(LEAGUE)
    today = datetime.now(timezone.utc).strftime("%Y%m%d")

    saved_ht = saved_final = 0

    for sp in sports:
        if sp == "WORLD CUP":
            scan_and_save_soccer(mode=mode)
            continue
        
        if sp == "MLB":
            continue
        spath = LEAGUE[sp]
        sb = _sb(spath, today)
        events = sb.get("events", [])
        if not events:
            print(f"  {sp}: no events on {today}")
            continue

        print(f"  {sp}: {len(events)} event(s) on {today}")
        for ev in events:
            eid = str(ev.get("id", ""))
            if not eid:
                continue
            status = (ev.get("status") or {}).get("type") or {}
            state = status.get("state", "")
            detail = status.get("detail", "")
            period = status.get("period", 0)

            away = (ev.get("competitions", [{}])[0].get("competitors", [{}])[0]
                    .get("team", {}).get("abbreviation", "?"))
            home = (ev.get("competitions", [{}])[0].get("competitors", [{}])[1]
                    .get("team", {}).get("abbreviation", "?"))
            pref = f"    [{state}] {away}@{home} (id={eid})"

            # ── Halftime capture ──
            if mode in ("all", "halftime") and state == "in" and period >= 3:
                if not already_saved(eid, "halftime"):
                    summary = _sum(spath, eid)
                    if summary:
                        final = build_final(summary, eid, sp)
                        if final:
                            ht = build_halftime(summary, final)
                            if ht and save_box(ht, HT_DIR):
                                saved_ht += 1
                            else:
                                print(f"{pref} — halftime data not ready")
                else:
                    print(f"{pref} — halftime already saved ✓")

            # ── Final capture ──
            if mode in ("all", "final") and state == "post":
                if not already_saved(eid, "final"):
                    summary = _sum(spath, eid)
                    if summary:
                        bx = build_final(summary, eid, sp)
                        if bx and save_box(bx, FIN_DIR):
                            saved_final += 1
                else:
                    print(f"{pref} — final already saved ✓")

    # ── MLB capture ──
    if sport is None or sport == "MLB":
        saved_mlb = 0
        for sp, spath in MLB_LEAGUE.items():
            sb = _sb(spath, today)
            events = sb.get("events", [])
            if not events:
                continue
            for ev in events:
                eid = str(ev.get("id", ""))
                if not eid:
                    continue
                status = (ev.get("status") or {}).get("type") or {}
                state = status.get("state", "")
                if state == "post":
                    if not already_saved(eid, "final", MLB_DIR):
                        summary = _sum(spath, eid)
                        if summary:
                            bx = build_mlb_final(summary, eid, today)
                            if bx and save_box(bx, MLB_DIR):
                                saved_mlb += 1
        print(f"  MLB saved {saved_mlb} finals")

    print(f"\n📊 {saved_ht} new halftime, {saved_final} new final boxscores")

def main():
    ap = argparse.ArgumentParser(description="Dedup-aware boxscore saver")
    ap.add_argument("--sport", choices=list(LEAGUE) + ["MLB"], default=None)
    ap.add_argument("--mode", choices=["all", "halftime", "final"], default="all")
    ap.add_argument("--purge-dupes", action="store_true")
    args = ap.parse_args()

    print(f"📦 Boxscore Saver — {datetime.now(timezone.utc).isoformat()}")

    if args.purge_dupes:
        purge_duplicates()
        return

    scan_and_save(sport=args.sport, mode=args.mode)

if __name__ == "__main__":
    main()
