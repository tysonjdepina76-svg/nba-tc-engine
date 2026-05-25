#!/usr/bin/env python3
"""
Sports TC — Streamlit Dashboard Launcher v8.0
=============================================
Runs the clean v8 Streamlit dashboard.
Dashboard includes TC Match (player props) + v8 Game Total (separate calibration).

Usage:
    python app.py                    # runs Streamlit on default port
    python app.py --port 8501        # specify port
    streamlit run tc_pipeline_clean/nba_tc_streamlit.py  # alternative
"""

import subprocess, sys, os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
STREAMLIT_FILE = BASE_DIR / "tc_pipeline_clean" / "nba_tc_streamlit.py"
PORT = 8507

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print(__doc__)
        raise SystemExit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "--port":
        PORT = int(sys.argv[2])

    print(f"Launching Sports TC v8 Dashboard on port {PORT}...")
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        str(STREAMLIT_FILE),
        "--server.port", str(PORT),
        "--browser.gatherUsageStats", "false",
    ])