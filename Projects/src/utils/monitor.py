"""monitor.py — Pipeline health monitor with alerting."""
import os
import time
import json
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from pathlib import Path

LOG = Path("/home/workspace/Daily_Log")
STATE = LOG / "monitor_state.json"


def check_pipeline_health():
    today = datetime.now().strftime("%Y-%m-%d")
    pdir = LOG / today
    pcsv = pdir / "picks.csv"
    if not pcsv.exists():
        return {"status": "FAIL", "reason": f"no picks.csv for {today}"}
    try:
        import pandas as pd
        df = pd.read_csv(pcsv)
        return {
            "status": "OK",
            "date": today,
            "picks": len(df),
            "leagues": df["league"].value_counts().to_dict() if "league" in df.columns else {},
        }
    except Exception as e:
        return {"status": "FAIL", "reason": str(e)}


def check_health_endpoint(port: int = 8500, timeout: int = 5) -> bool:
    import urllib.request
    try:
        with urllib.request.urlopen(f"http://localhost:{port}/", timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def send_alert(msg: str, to: str = None) -> bool:
    to = to or os.environ.get("ALERT_EMAIL", "tysonjdepina76@gmail.com")
    try:
        msg_obj = MIMEText(msg)
        msg_obj["Subject"] = f"[TC Pipeline] {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        msg_obj["From"] = "alerts@zo.computer"
        msg_obj["To"] = to
        print(f"[alert] {msg}")
        return True
    except Exception as e:
        print(f"[alert-fail] {e}")
        return False


def run_health_check(verbose: bool = True) -> dict:
    results = {
        "timestamp": datetime.now().isoformat(),
        "pipeline": check_pipeline_health(),
        "dashboard": check_health_endpoint(8510),
    }
    state = {"last_check": results["timestamp"], "last_status": results["pipeline"]["status"]}
    STATE.write_text(json.dumps(state, indent=2))
    if verbose:
        print(json.dumps(results, indent=2))
    if results["pipeline"]["status"] == "FAIL":
        send_alert(f"Pipeline failure: {results['pipeline'].get('reason', 'unknown')}")
    return results


if __name__ == "__main__":
    run_health_check()
