#!/usr/bin/env python3
"""Auto-repair for the TC pipeline. Fixes common broken states."""

import json
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

WORKSPACE = Path("/home/workspace")
LOG_DIR = WORKSPACE / "Daily_Log"
PROJ_DIR = WORKSPACE / "Projects"
TODAY = (datetime.now(timezone.utc) - timedelta(hours=5)).strftime("%Y-%m-%d")

FIXES_APPLIED = []


def run(cmd, timeout=60):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout, cwd=str(WORKSPACE))
        return r.returncode == 0, r.stdout.strip()[-300:] + "\n" + r.stderr.strip()[-200:]
    except Exception as e:
        return False, str(e)


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
        "nohup streamlit run Projects/dashboard.py --server.port 8510 --server.headless true > /dev/shm/streamlit_8510.log 2>&1 &",
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
    cache_dir = Path("/tmp/tc_cache/odds")
    if not cache_dir.exists():
        return False, "No odds cache dir"
    stale = list(cache_dir.glob("*.json"))
    fresh = [f for f in stale if (time.time() - f.stat().st_mtime) < 7200]
    if not fresh and stale:
        ok, out = run("python3 Projects/daily_picks.py WNBA MLB 'WORLD CUP'", timeout=120)
        FIXES_APPLIED.append("Refreshed stale odds cache")
        return True, "Refreshed odds"
    return False, f"{len(fresh)} fresh, {len(stale)} total"


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


# ─── Report ────────────────────────────────────────────────────────────

FIXES = [
    ("Picks Today", fix_no_picks_today),
    ("Streamlit Down", fix_streamlit_down),
    ("Missing Projections", fix_missing_projs),
    ("Stale Odds Cache", fix_odds_cache),
    ("Empty Consensus", fix_empty_consensus),
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

output_path = WORKSPACE / "sports_betting_dashboard" / "data" / "fix_report.json"
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(json.dumps(report, indent=2))

print(json.dumps(report, indent=2))
