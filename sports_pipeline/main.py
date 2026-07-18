#!/usr/bin/env python3
"""
Unified CLI - run pipeline, health check, or dashboard.
"""
import sys
import subprocess
import argparse
from pathlib import Path

Path("logs").mkdir(exist_ok=True)

def run_pipeline():
    subprocess.run([sys.executable, "run_pipeline.py"])

def run_health():
    subprocess.run([sys.executable, "health_check.py"])

def run_dashboard():
    subprocess.run(["streamlit", "run", "dashboard_enhanced.py"])

def main():
    parser = argparse.ArgumentParser(description="Sports Pipeline CLI")
    parser.add_argument("command", choices=["run", "health", "dashboard", "all"],
                        help="Command to execute")
    args = parser.parse_args()
    if args.command == "run":
        run_pipeline()
    elif args.command == "health":
        run_health()
    elif args.command == "dashboard":
        run_dashboard()
    elif args.command == "all":
        run_pipeline()
        run_health()
        run_dashboard()

if __name__ == "__main__":
    main()
