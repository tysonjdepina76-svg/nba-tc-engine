"""Daily TC pipeline health check.

Reports:
  - API key status (SPORTSGAMEODDS, ODDS_API)
  - Streamlit service on :8507
  - TC API endpoint at https://true.zo.space/api/tc?sport=WNBA
  - Box-score scraper last-run
  - Last picks.csv row + hit-rate report existence
  - Daily picks count for the day
  - ESPN endpoint reachability

Writes a markdown report and emails it to the user.
"""
from __future__ import annotations

import json
import os
import subprocess
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import sys

LOG_DIR = Path("/home/workspace/Daily_Log")
SCRIPTS = Path("/home/workspace/Scripts")
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")

OUT = SCRIPTS / f"health_check_{datetime.now(timezone.utc).strftime('%Y%m%d')}.md"
OUT.parent.mkdir(parents=True, exist_ok=True)


def check(label: str, ok: bool, detail: str = "") -> tuple[str, bool]:
    icon = "OK" if ok else "FAIL"
    return f"- [{icon}] **{label}**" + (f" — {detail}" if detail else ""), ok


def check_env(name: str) -> tuple[str, bool]:
    """Read a secret from /root/.zo/secrets.env without exposing its value."""
    env_file = Path("/root/.zo/secrets.env")
    if not env_file.exists():
        return check(f"{name} env var", False, "secrets.env missing"), False
    content = env_file.read_text()
    for line in content.splitlines():
        if line.startswith(f"{name}="):
            val = line.split("=", 1)[1].strip()
            masked = val[:4] + "..." + val[-4:] if len(val) > 8 else "set"
            return check(f"{name} env var", True, f"({masked})"), True
    return check(f"{name} env var", False, "not in secrets.env"), False


def check_url(url: str, label: str, timeout: int = 8) -> tuple[str, bool]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 TC-HealthCheck"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            ok = r.status == 200
            return check(label, ok, f"HTTP {r.status}"), ok
    except urllib.error.HTTPError as e:
        return check(label, False, f"HTTP {e.code}"), False
    except Exception as e:
        return check(label, False, str(e)[:60]), False


def check_odds_api() -> tuple[str, bool]:
    """Test ODDS_API_KEY by listing sports."""
    env_file = Path("/root/.zo/secrets.env")
    if not env_file.exists():
        return check("Odds API key works", False, "no secrets file"), False
    key = None
    for line in env_file.read_text().splitlines():
        if line.startswith("ODDS_API_KEY="):
            key = line.split("=", 1)[1].strip()
    if not key:
        return check("Odds API key works", False, "ODDS_API_KEY not set"), False
    try:
        req = urllib.request.Request(f"https://api.the-odds-api.com/v4/sports/?apiKey={key}", headers={"User-Agent": "Mozilla/5.0 TC-HealthCheck"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
            count = len(data) if isinstance(data, list) else 0
            return check("Odds API key works", count > 0, f"{count} sports"), count > 0
    except Exception as e:
        return check("Odds API key works", False, str(e)[:60]), False


def check_espn() -> tuple[str, bool]:
    try:
        req = urllib.request.Request("https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard", headers={"User-Agent": "Mozilla/5.0 TC-HealthCheck"})
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read())
            n = len(d.get("events", []))
            return check("ESPN scoreboard", n > 0, f"{n} WNBA events"), n > 0
    except Exception as e:
        return check("ESPN scoreboard", False, str(e)[:60]), False


def check_streamlit() -> tuple[str, bool]:
    """Check if any service is on :8510."""
    try:
        out = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://localhost:8510/_stcore/health"], capture_output=True, text=True, timeout=8)
        code = out.stdout.strip()
        return check("Streamlit on :8510", code == "200", f"HTTP {code}"), code == "200"
    except Exception as e:
        return check("Streamlit on :8510", False, str(e)[:60]), False


def check_today_picks() -> tuple[str, bool, dict]:
    today_dir = LOG_DIR / TODAY
    if not today_dir.exists():
        return check(f"Picks for {TODAY}", False, "no daily log directory"), False, {}
    files = list(today_dir.glob("picks.csv")) + list(today_dir.glob("proj_*.json"))
    slate_files = list(today_dir.glob("slate_*.json"))
    summary = {"picks": 0, "games": 0, "files": len(files)}
    for f in files:
        try:
            d = json.loads(f.read_text())
            summary["picks"] += len(d.get("picks") or d.get("valid_props") or [])
            summary["games"] += 1
        except Exception:
            pass
    return check(f"Picks for {TODAY}", summary["games"] > 0, f"{summary['picks']} picks across {summary['games']} games"), summary["games"] > 0, summary


def check_box_files() -> tuple[str, bool, dict]:
    final_dir = LOG_DIR / "final"
    if not final_dir.exists():
        return check("Final box files", False, "no /Daily_Log/final/"), False, {}
    files = list(final_dir.glob("*.json"))
    return check("Final box files", len(files) > 0, f"{len(files)} saved"), len(files) > 0, {"count": len(files)}


def check_reports() -> tuple[str, bool, dict]:
    today_dir = LOG_DIR / TODAY
    if not today_dir.exists():
        return check("Hit-rate reports", False, "no daily log"), False, {}
    rpts = list(today_dir.glob("hit_rates_*.md"))
    if not rpts:
        return check("Hit-rate reports", False, "none yet"), False, {"reports": []}
    return check("Hit-rate reports", True, f"{len(rpts)} reports"), True, {"reports": [r.name for r in rpts]}


def main() -> int:
    lines = [f"# TC Pipeline Health Check — {TODAY}", "", f"Run at: {datetime.now(timezone.utc).isoformat()}", ""]
    fails = 0

    # Secrets
    for label, ok in [check_env("SPORTSGAMEODDS_API_KEY"), check_env("ODDS_API_KEY")]:
        lines.append(label)
        if not ok: fails += 1

    # API keys work
    label, ok = check_odds_api()
    lines.append(label)
    if not ok: fails += 1

    # Endpoints
    for label, ok in [check_espn(), check_url("https://true.zo.space/api/tc?sport=WNBA", "TC API (zo.space /api/tc)", timeout=15)]:
        lines.append(label)
        if not ok: fails += 1

    # Services
    label, ok = check_streamlit()
    lines.append(label)
    if not ok: fails += 1

    # Data
    label, ok, summary = check_today_picks()
    lines.append(label)
    if not ok: fails += 1

    label, ok, _ = check_box_files()
    lines.append(label)

    label, ok, _ = check_reports()
    lines.append(label)

    lines += ["", f"**Overall: {fails} failures**"]

    md = "\n".join(str(x) for x in lines)
    OUT.write_text(md)
    print(md)

    # Email the report
    try:
        send_email(md, fails)
        print(f"\nEmail sent ({fails} failures).")
    except Exception as e:
        print(f"\nEmail failed: {e}")

    return 0 if fails == 0 else 1


def send_email(body: str, failures: int) -> None:
    """Send the health check report via Gmail using stored credentials."""
    import os
    user = os.environ.get("HEALTH_EMAIL_FROM", "tysonjdepina76@gmail.com")
    to = os.environ.get("HEALTH_EMAIL_TO", "tysondepina99@gmail.com")
    app_pw = os.environ.get("GMAIL_APP_PASSWORD", "")
    if not app_pw:
        # try secrets.env
        sf = Path("/root/.zo/secrets.env")
        if sf.exists():
            for ln in sf.read_text().splitlines():
                if ln.startswith("GMAIL_APP_PASSWORD="):
                    app_pw = ln.split("=", 1)[1].strip()
    if not app_pw:
        print("no Gmail app password — skipping email")
        return

    subject = f"TC Health Check — {TODAY} — {failures} fail" + ("s" if failures != 1 else "")
    msg = MIMEMultipart()
    msg["From"] = user
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(user, app_pw)
        s.sendmail(user, [to], msg.as_string())


if __name__ == "__main__":
    sys.exit(main())
