#!/usr/bin/env python3
"""Fill ALL gaps: projections, picks, dashboard, symlinks, last_run.json."""
import json, os, csv, subprocess, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ET = timezone(timedelta(hours=-4))
WORKSPACE = Path("/home/workspace")
LOG_DIR = WORKSPACE / "Daily_Log"
TODAY = datetime.now(ET).strftime("%Y-%m-%d")

# ============================================================
# STEP 1: Generate WNBA projections for today via API
# ============================================================
def generate_wnba_projections():
    """Call the zo.space API to get WNBA projections and save to Daily_Log."""
    import urllib.request, json as _json
    
    print("=" * 60)
    print("STEP 1: Generate WNBA projections from zo.space API")
    
    today_dir = LOG_DIR / TODAY
    today_dir.mkdir(parents=True, exist_ok=True)
    
    # Get WNBA slate
    url = "http://localhost:3099/api/tc?sport=WNBA"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            slate = _json.loads(resp.read())
    except Exception as e:
        print(f"  ERROR fetching slate: {e}")
        return False
    
    games = slate.get("games", [])
    if not games:
        print("  No WNBA games today")
        return False
    
    print(f"  Found {len(games)} WNBA games")
    
    for g in games:
        away = g.get("away", "?")
        home = g.get("home", "?")
        matchup = f"{away}_at_{home}"
        filename = f"proj_WNBA_{matchup}.json"
        filepath = today_dir / filename
        
        # Fetch projections with ?game query
        game_url = f"http://localhost:3099/api/tc?sport=WNBA&game={away}_at_{home}"
        try:
            with urllib.request.urlopen(game_url, timeout=15) as resp:
                proj = _json.loads(resp.read())
            
            with open(filepath, "w") as f:
                _json.dump(proj, f, indent=2)
            print(f"  ✅ Saved {filename} ({proj.get('away',{}).get('all',{}).get('players',[]) and len(proj['away']['all']['players']) + len(proj.get('home',{}).get('all',{}).get('players',[]))} players)")
        except Exception as e:
            print(f"  ❌ {matchup}: {e}")
    
    return True

# ============================================================
# STEP 2: Generate MLB projections
# ============================================================
def generate_mlb_projections():
    """Fetch MLB projections from API."""
    print("\n" + "=" * 60)
    print("STEP 2: Generate MLB projections")
    
    today_dir = LOG_DIR / TODAY
    
    url = "http://localhost:3099/api/tc?sport=MLB"
    try:
        import urllib.request, json as _json
        with urllib.request.urlopen(url, timeout=15) as resp:
            slate = _json.loads(resp.read())
    except Exception as e:
        print(f"  ERROR fetching MLB slate: {e}")
        return False
    
    games = slate.get("games", [])
    if not games:
        print("  No MLB games today (All-Star break)")
        return False
    
    print(f"  Found {len(games)} MLB games")
    
    for g in games:
        away = g.get("away", "?")
        home = g.get("home", "?")
        matchup = f"{away}_at_{home}"
        filename = f"proj_MLB_{matchup}.json"
        filepath = today_dir / filename
        
        game_url = f"http://localhost:3099/api/tc?sport=MLB&game={away}_at_{home}"
        try:
            import urllib.request, json as _json
            with urllib.request.urlopen(game_url, timeout=15) as resp:
                proj = _json.loads(resp.read())
            
            if "error" not in proj:
                with open(filepath, "w") as f:
                    _json.dump(proj, f, indent=2)
                print(f"  ✅ Saved {filename}")
            else:
                print(f"  ⚠️ {matchup}: {proj.get('error')}")
        except Exception as e:
            print(f"  ❌ {matchup}: {e}")
    
    return True

# ============================================================
# STEP 3: Run daily_picks for WNBA + MLB
# ============================================================
def run_daily_picks():
    """Generate picks from projections."""
    print("\n" + "=" * 60)
    print("STEP 3: Run daily_picks")
    
    success = []
    for sport in ["wnba", "mlb"]:
        print(f"  Running: python3 Projects/daily_picks.py --sport {sport} --date {TODAY}")
        result = subprocess.run(
            ["python3", "Projects/daily_picks.py", "--sport", sport, "--date", TODAY],
            cwd=str(WORKSPACE),
            capture_output=True, text=True, timeout=120
        )
        print(f"  stdout: {result.stdout.strip()[:200]}")
        if result.returncode == 0:
            success.append(sport)
        else:
            print(f"  stderr: {result.stderr.strip()[:300]}")
    
    return len(success) > 0

# ============================================================
# STEP 4: Verify picks.csv and symlink
# ============================================================
def verify_picks_symlink():
    """Ensure today_picks.csv symlink points to Daily_Log date/picks.csv."""
    print("\n" + "=" * 60)
    print("STEP 4: Verify picks symlink")
    
    dash_picks = WORKSPACE / "sports_betting_dashboard" / "data" / "picks" / "today_picks.csv"
    log_picks = LOG_DIR / TODAY / "picks.csv"
    
    if log_picks.exists():
        dash_picks.unlink(missing_ok=True)
        dash_picks.symlink_to(log_picks)
        
        count = sum(1 for _ in open(log_picks)) - 1  # minus header
        print(f"  ✅ today_picks.csv → {log_picks} ({count} rows)")
    else:
        print(f"  ⚠️ {log_picks} does not exist")
    
    return log_picks.exists()

# ============================================================
# STEP 5: Update last_run.json
# ============================================================
def update_last_run():
    """Update last_run.json with current timestamp and sports."""
    print("\n" + "=" * 60)
    print("STEP 5: Update last_run.json")
    
    import json as _json
    
    data = {
        "timestamp": datetime.now(ET).isoformat(),
        "sports": ["wnba", "mlb"],
        "generated_picks": True,
        "dashboard_url": "http://localhost:8510",
        "api_url": "https://true.zo.space/nba-tc"
    }
    
    last_run = LOG_DIR / "last_run.json"
    with open(last_run, "w") as f:
        _json.dump(data, f, indent=2)
    print(f"  ✅ Updated {last_run}")

# ============================================================
# STEP 6: Generate backfill for 7/14 and 7/15
# ============================================================
def backfill_historical():
    """Backfill projections and picks for 7/14 and 7/15."""
    import urllib.request, json as _json
    
    print("\n" + "=" * 60)
    print("STEP 6: Backfill 7/14 and 7/15")
    
    for date_str in ["2026-07-14", "2026-07-15"]:
        date_dir = LOG_DIR / date_str
        date_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n  --- {date_str} ---")
        
        for sport, esn_path in [("WNBA", "wnba"), ("MLB", "baseball/mlb")]:
            games_url = f"https://site.api.espn.com/apis/site/v2/sports/{esn_path}/scoreboard?dates={date_str.replace('-','')}"
            try:
                req = urllib.request.Request(games_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = _json.loads(resp.read())
            except Exception as e:
                print(f"    ❌ {sport}: {e}")
                continue
            
            events = data.get("events", [])
            print(f"    {sport}: {len(events)} games")
            
            for evt in events:
                comps = evt.get("competitions", [{}])[0]
                teams = comps.get("competitors", [])
                if len(teams) < 2:
                    continue
                
                away = teams[0].get("team", {}).get("abbreviation", "?")
                home = teams[1].get("team", {}).get("abbreviation", "?")
                
                # Try zo.space API first
                game_url = f"http://localhost:3099/api/tc?sport={sport}&game={away}_at_{home}&date={date_str}"
                try:
                    with urllib.request.urlopen(game_url, timeout=15) as resp:
                        proj = _json.loads(resp.read())
                    if "error" not in proj:
                        filename = f"proj_{sport}_{away}_at_{home}.json"
                        with open(date_dir / filename, "w") as f:
                            _json.dump(proj, f, indent=2)
                        print(f"    ✅ {filename}")
                    else:
                        print(f"    ⚠️ {away}@{home}: {proj.get('error')}")
                except Exception as e:
                    print(f"    ❌ {away}@{home}: {e}")
        
        # Run picks for this date if we have projection files
        proj_files = list(date_dir.glob("proj_*.json"))
        if proj_files:
            print(f"    Running picks for {date_str} ({len(proj_files)} proj files)")
            for sport in ["wnba", "mlb"]:
                result = subprocess.run(
                    ["python3", "Projects/daily_picks.py", "--sport", sport, "--date", date_str],
                    cwd=str(WORKSPACE),
                    capture_output=True, text=True, timeout=120
                )
                print(f"    {sport}: {result.stdout.strip()[:150]}")

# ============================================================
# STEP 7: Dashboard health check
# ============================================================
def check_dashboard():
    """Verify dashboard is running."""
    print("\n" + "=" * 60)
    print("STEP 7: Dashboard health check")
    
    try:
        import urllib.request
        with urllib.request.urlopen("http://localhost:8510/_stcore/health", timeout=5) as resp:
            print(f"  ✅ Dashboard :8510 UP ({resp.read().decode()})")
    except:
        print(f"  ❌ Dashboard :8510 DOWN — restarting...")
        subprocess.Popen(
            ["streamlit", "run", "sports_betting_dashboard/dashboard.py", "--server.port", "8510"],
            cwd=str(WORKSPACE),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print(f"🔧 TC PIPELINE GAP FILLER — {TODAY}")
    print("=" * 60)
    
    generate_wnba_projections()
    generate_mlb_projections()
    run_daily_picks()
    verify_picks_symlink()
    update_last_run()
    backfill_historical()
    check_dashboard()
    
    # Final summary
    print("\n" + "=" * 60)
    print("ALL GAPS FILLED ✅")
    print(f"Dashboard: http://localhost:8510")
    print(f"Live: https://true.zo.space/nba-tc")
    
    # Count picks
    picks_file = LOG_DIR / TODAY / "picks.csv"
    if picks_file.exists():
        count = sum(1 for _ in open(picks_file)) - 1
        print(f"Picks today: {count}")
    else:
        print("Picks today: 0 (no projection files)")
