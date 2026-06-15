#!/usr/bin/env python3
"""
TC Engine CLI Launcher v8.0
==========================
Unified entry point for the TC engine.

Usage:
    python run_tc.py --help
    python run_tc.py --sport NBA --game "SAS @ OKC" --total 218.5
    python run_tc.py --sport NBA --backtest
    python run_tc.py --sport WNBA --list-teams
    python run_tc.py --dashboard     # launch Streamlit
    python run_tc.py --api           # start FastAPI server
"""

import sys, subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ENGINE = BASE_DIR / "tc_pipeline_clean" / "tc_engine.py"

def run_engine():
    sys.path.insert(0, str(BASE_DIR / "tc_pipeline_clean"))
    import importlib.util, argparse, json

    # Load tc_engine
    spec = importlib.util.spec_from_file_location("tc_engine", str(ENGINE))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    parser = argparse.ArgumentParser(description="Sports TC v8 Engine")
    parser.add_argument("--sport", default="NBA", choices=["NBA", "WNBA"])
    parser.add_argument("--backtest", action="store_true")
    parser.add_argument("--game", type=str, help="'AWAY @ HOME'")
    parser.add_argument("--total", type=float, default=210.5)
    parser.add_argument("--spread", type=float, default=-5.0)
    parser.add_argument("--bankroll", type=float, default=1000.0)
    parser.add_argument("--list-teams", action="store_true")
    args = parser.parse_args()

    if args.backtest:
        result = mod.run_backtest(args.sport)
        print(json.dumps(result, indent=2))
    elif args.list_teams:
        for abbr, team in mod.get_teams(args.sport).items():
            print(f"{abbr}: {team.name}")
            for n in team.injury_notes:
                print(f"   {n}")
    elif args.game:
        parts = args.game.split("@")
        if len(parts) < 2:
            print("Usage: --game 'AWAY @ HOME'")
            raise SystemExit(1)
        away = parts[0].strip().upper()
        home = parts[1].strip().upper()
        result = mod.project_game(home, away, args.total, args.spread,
                                  series="CLI", game_time="CLI",
                                  bankroll=args.bankroll, sport=args.sport)
        print(json.dumps(result, indent=2))
    else:
        print("Options: --backtest | --game 'AWAY @ HOME' | --list-teams")
        print("Dashboard: python run_tc.py --dashboard")
        print("API:       python run_tc.py --api")

def run_dashboard():
    subprocess.run([sys.executable, "-m", "streamlit", "run",
                    str(BASE_DIR / "tc_pipeline_clean" / "nba_tc_streamlit.py")])

def run_api():
    import uvicorn
    port = int(os.environ.get("PORT", 3456))
    print(f"Starting Sports TC v8 API on port {port}...")
    uvicorn.run(f"tc_pipeline_clean.tc_engine:app",
                host="0.0.0.0", port=port, reload=False)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--dashboard":
        run_dashboard()
    elif len(sys.argv) > 1 and sys.argv[1] == "--api":
        run_api()
    elif len(sys.argv) > 1 and sys.argv[1] == "--help":
        print(__doc__)
    else:
        run_engine()