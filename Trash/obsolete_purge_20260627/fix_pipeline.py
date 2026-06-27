#!/usr/bin/env python3
"""Auto-repair for the TC pipeline. Fixes common broken states."""

import json
import subprocess
import sys
import time
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

WORKSPACE = Path("/home/workspace")
LOG_DIR = WORKSPACE / "Daily_Log"
PROJ_DIR = WORKSPACE / "Projects"
DASH_DIR = WORKSPACE / "sports_betting_dashboard"
TODAY = (datetime.now(timezone.utc) - timedelta(hours=5)).strftime("%Y-%m-%d")

FIXES_APPLIED = []


def run(cmd, timeout=60):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout, cwd=str(WORKSPACE))
        return r.returncode == 0, r.stdout.strip()[-300:] + "\n" + r.stderr.strip()[-200:]
    except Exception as e:
        return False, str(e)


def hours_to_earliest_game():
    """Hours until earliest game today. Returns 999 if none found."""
    try:
        et = timezone(timedelta(hours=-5))
        now = datetime.now(et)
        earliest = None
        evdir = DASH_DIR / "data" / "events"
        for f in sorted(evdir.glob("*.json")):
            data = json.loads(f.read_text())
            for e in [data] if isinstance(data, dict) else data:
                start = e.get("start_time", e.get("commence_time", ""))
                if not start:
                    continue
                t = datetime.fromisoformat(start.replace("Z", "+00:00"))
                t_et = t.astimezone(et)
                diff_h = (t_et - now).total_seconds() / 3600
                if diff_h > -3 and (earliest is None or diff_h < earliest):
                    earliest = diff_h
        return round(earliest, 1) if earliest is not None else 999
    except Exception:
        return 999


def fix_no_picks_today():
    picks_path = LOG_DIR / TODAY / "picks.json"
    if picks_path.exists():
        try:
            data = json.loads(picks_path.read_text())
            count = len(data) if isinstance(data, list) else 0
            if count > 0:
                return False, f"Already {count} picks"
        except:
            pass

    ok, out = run("python3 Projects/daily_picks.py WNBA MLB 'WORLD CUP'", timeout=120)
    FIXES_APPLIED.append("Ran daily_picks.py")
    picks_path = LOG_DIR / TODAY / "picks.json"
    if picks_path.exists():
        data = json.loads(picks_path.read_text())
        count = len(data) if isinstance(data, list) else 0
        return True, f"Generated {count} picks"
    return ok, out


def fix_streamlit_down():
    ok, _ = run("curl -sf --max-time 3 http://localhost:8510", timeout=5)
    if ok:
        return False, "Streamlit already running"

    run("pkill -f 'streamlit run.*dashboard' 2>/dev/null || true", timeout=5)
    time.sleep(1)
    ok, _ = run(
        "nohup streamlit run sports_betting_dashboard/dashboard.py --server.port 8510 --server.headless true > /dev/shm/streamlit_8510.log 2>&1 &",
        timeout=5,
    )
    time.sleep(3)
    ok2, _ = run("curl -sf --max-time 3 http://localhost:8510", timeout=5)
    FIXES_APPLIED.append("Restarted Streamlit")
    return ok2, "Streamlit restarted" if ok2 else "Streamlit failed to start"


def fix_missing_projs():
    missing = []
    picks_path = LOG_DIR / TODAY / "picks.json"
    if picks_path.exists():
        data = json.loads(picks_path.read_text())
        picks = data if isinstance(data, list) else []
        seen = set()
        for p in picks:
            if isinstance(p, dict):
                league = p.get("league", "")
                matchup = p.get("matchup", "")
                if league and matchup and matchup not in seen:
                    seen.add(matchup)
                    proj_path = LOG_DIR / TODAY / f"proj_{league}_{matchup.replace('@','_at_')}.json"
                    if not proj_path.exists():
                        missing.append(str(proj_path))

    if missing:
        ok, out = run("python3 Projects/daily_picks.py WNBA MLB 'WORLD CUP'", timeout=120)
        FIXES_APPLIED.append(f"Regenerated {len(missing)} missing projection files")
        return True, f"Regenerated projections, {len(missing)} were missing"
    return False, "No missing projection files"


def fix_odds_cache():
    odds_dir = DASH_DIR / "data" / "odds"
    if not odds_dir.exists():
        return False, "No odds data dir"

    hours_to_game = hours_to_earliest_game()
    stale = list(odds_dir.glob("*.json"))
    fresh = [f for f in stale if (time.time() - f.stat().st_mtime) < 7200]

    # Only refresh if within 3h of games and no fresh files — conserve API
    if hours_to_game < 3.0 and not fresh and stale:
        ok, out = run("python3 sports_betting_dashboard/scripts/odds_api_scraper.py", timeout=60)
        FIXES_APPLIED.append(f"Refreshed odds cache (game in {hours_to_game}h)")
        return True, f"Refreshed odds ({hours_to_game}h to game)"
    elif hours_to_game >= 3.0:
        return False, f"Cache OK — {len(stale)} files from today, game in {hours_to_game}h (gate not active)"
    elif fresh:
        return False, f"Cache OK — {len(fresh)} fresh files"
    else:
        return False, "No odds files to refresh"


def fix_empty_consensus():
    cons_path = LOG_DIR / TODAY / "consensus.json"
    if not cons_path.exists():
        ok, out = run("python3 Projects/consensus_engine.py", timeout=60)
        FIXES_APPLIED.append("Ran consensus engine")
        return ok, "Consensus generated"
    try:
        data = json.loads(cons_path.read_text())
        count = len(data) if isinstance(data, list) else data.get("total", 0)
        if count == 0:
            ok, out = run("python3 Projects/consensus_engine.py", timeout=60)
            FIXES_APPLIED.append("Re-ran consensus (was empty)")
            return ok, "Consensus regenerated"
    except:
        pass
    return False, "Consensus already populated"


def fix_api_limits():
    status_path = DASH_DIR / "data" / "account" / "status.json"
    if status_path.exists():
        d = json.loads(status_path.read_text()).get("data", {})
        used = d.get("requests_today", 0)
        limit = d.get("daily_limit", 6667)
        remaining = d.get("remaining", 0)
        pct = used * 100 // limit if limit else 0
        if pct > 80:
            FIXES_APPLIED.append(f"API budget at {pct}% — deferring heavy calls")
            return True, f"API budget {pct}% ({used}/{limit}, {remaining} remaining) — defer heavy ops"
        return False, f"API budget OK: {used}/{limit} ({pct}%, {remaining} remaining)"
    return False, "No API budget tracking file"


def fix_nba_offseason():
    nba_events = DASH_DIR / "data" / "events" / "basketball_nba.json"
    if nba_events.exists():
        nba_events.unlink()
        FIXES_APPLIED.append("Purged NBA events (off-season)")
        return True, "Purged stale NBA events file"
    return False, "NBA events already clean"


def fix_empty_logs():
    """Purge truly empty log files that were never written to."""
    removed = []
    for logfile in [DASH_DIR / "logs" / "daily.log", DASH_DIR / "logs" / "api.log"]:
        if logfile.exists() and logfile.stat().st_size == 0:
            logfile.unlink()
            removed.append(str(logfile.name))
    if removed:
        FIXES_APPLIED.append(f"Purged {len(removed)} empty log files: {', '.join(removed)}")
        return True, f"Purged empty logs: {', '.join(removed)}"
    return False, "No empty log files"


def fix_stale_symlinks():
    """Update symlinks in data dir to point to today."""
    import os
    picks_link = DASH_DIR / "data" / "picks" / "today_picks.csv"
    today_csv = LOG_DIR / TODAY / "picks.csv"
    if picks_link.exists() or picks_link.is_symlink():
        if picks_link.is_symlink():
            target = os.readlink(str(picks_link))
            today_str = f"Daily_Log/{TODAY}/picks.csv"
            if today_str in target:
                return False, f"Symlink already points to {TODAY}"
        picks_link.unlink(missing_ok=True)
    if today_csv.exists():
        os.symlink(str(today_csv), str(picks_link))
        FIXES_APPLIED.append(f"Updated today_picks.csv symlink → {TODAY}")
        return True, f"Symlink updated to {TODAY}"
    return False, "No today picks.csv to link"


# ─── Report ────────────────────────────────────────────────────────────

FIXES = [
    ("NBA Off-Season", fix_nba_offseason),
    ("Empty Logs", fix_empty_logs),
    ("API Budget", fix_api_limits),
    ("Picks Today", fix_no_picks_today),
    ("Streamlit Down", fix_streamlit_down),
    ("Missing Projections", fix_missing_projs),
    ("Stale Odds Cache", fix_odds_cache),
    ("Empty Consensus", fix_empty_consensus),
    ("Stale Symlinks", fix_stale_symlinks),
]

results = []
for name, fn in FIXES:
    applied, detail = fn()
    results.append({"check": name, "fix_applied": applied, "detail": detail})

report = {
    "timestamp": datetime.now().isoformat(),
    "date": TODAY,
    "fixes_applied": FIXES_APPLIED,
    "results": results,
    "total_fixes": len([r for r in results if r["fix_applied"]]),
}

output_path = DASH_DIR / "data" / "fix_report.json"
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(json.dumps(report, indent=2))

print(json.dumps(report, indent=2))
