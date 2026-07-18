#!/usr/bin/env python3
"""TC Sports Pipeline — daily_picks.py
Reads projection files from Daily_Log/YYYY-MM-DD/, generates picks, saves to DB + CSV,
applies enhancer, sends email report, updates last_run.json.
"""

import sys, os, csv, json, argparse, sqlite3, smtplib, glob
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

ET = ZoneInfo("America/New_York")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.explanation_engine import generate_explanation
from src.adapters.schedule_fetcher import has_games_today
from src.enhancer import apply_enhancements
from src.utils.logging import get_logger

logger = get_logger(__name__)

PROJ_DIR = Path(__file__).parent.parent / "Daily_Log"
DATA_DIR = Path(__file__).parent.parent / "data"
PICKS_DIR = DATA_DIR / "picks"
DB_PATH = Path(__file__).parent / "data" / "picks.db"

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
EMAIL_TO = os.getenv("EMAIL_TO", "")


def load_projections(sport):
    """Load projections from Daily_Log/YYYY-MM-DD/proj_SPORT_*.json"""
    today = datetime.now(ET).strftime("%Y-%m-%d")
    log_dir = PROJ_DIR / today
    if not log_dir.exists():
        logger.warning(f"No log dir {log_dir}")
        return []

    pattern = str(log_dir / f"proj_{sport.upper()}_*.json")
    files = sorted(glob.glob(pattern))
    if not files:
        logger.warning(f"No projection files for {sport} in {log_dir}")
        return []

    players_out = []
    for fpath in files:
        fname = Path(fpath).stem
        parts = fname.split("_", 2)
        matchup = parts[2] if len(parts) >= 3 and parts[2] != today else ""

        with open(fpath) as f:
            data = json.load(f)

        player_list = data.get("players", data.get("picks", []))
        for p in player_list:
            player_name = p.get("player", p.get("name", ""))
            team = p.get("team", "")
            proj_dict = p.get("projections", {})

            for stat, vals in proj_dict.items():
                tc_proj = vals.get("tc_projection", vals.get("projection", 0))
                line = vals.get("line", vals.get("market_line", 0))
                edge_val = vals.get("edge", tc_proj - line)
                direction = vals.get("direction", "OVER" if edge_val > 0 else "UNDER")

                players_out.append({
                    "name": player_name,
                    "team": team,
                    "matchup": matchup,
                    "stat": stat.upper() if sport.upper() == "MLB" else stat,
                    "projection": tc_proj,
                    "line": line,
                    "edge": edge_val,
                    "direction": direction,
                })

    logger.info(f"Loaded {len(players_out)} stat-lines from {len(files)} files for {sport}")
    return players_out


def deduplicate(picks):
    """Dedup on (name, sport, stat, matchup)."""
    seen = set()
    unique = []
    dups = 0
    for p in picks:
        key = (p["name"], p.get("sport", ""), p["stat"], p.get("matchup", ""))
        if key not in seen:
            seen.add(key)
            unique.append(p)
        else:
            dups += 1
    if dups:
        logger.info(f"Removed {dups} duplicates")
    return unique


def send_email_report(picks, sport, date_str):
    """Send CSV picks report via SMTP."""
    if not SMTP_USER or not EMAIL_TO:
        logger.info(f"Email not configured. Skipping {sport} report.")
        return

    try:
        lines = ["player,team,sport,stat,projection,line,edge,direction,reason"]
        for p in picks:
            row = [
                p.get("name", ""),
                p.get("team", ""),
                p.get("sport", ""),
                p.get("stat", ""),
                f"{float(p.get('projection', 0)):.4f}",
                f"{float(p.get('line', 0)):.4f}",
                f"{float(p.get('edge', 0)):.4f}",
                p.get("direction", ""),
                p.get("reason", "").replace(",", ";"),
            ]
            lines.append(",".join(row))

        csv_body = "\n".join(lines)
        msg = MIMEMultipart()
        msg["From"] = SMTP_USER
        msg["To"] = EMAIL_TO
        msg["Subject"] = f"TC Sports Picks \u2013 {sport.upper()} {date_str}"
        msg.attach(MIMEText(csv_body, "plain"))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
        server.quit()
        logger.info(f"Email sent: {sport} {date_str} ({len(picks)} picks) to {EMAIL_TO}")
    except Exception as e:
        logger.error(f"Email failed for {sport}: {e}")


def generate_picks(sport: str):
    """Main pick generation for one sport."""
    logger.info(f"Generating picks for {sport}...")

    players = load_projections(sport)
    if not players:
        if not has_games_today(sport):
            logger.info(f"No projections and no games for {sport} today. Skipping.")
            return []
        logger.warning(f"No projections for {sport} (but games exist)")
        return []

    picks = []
    for p in players:
        proj = float(p["projection"])
        line = float(p["line"])
        edge = proj - line
        direction = "OVER" if edge > 0 else "UNDER"

        reason = generate_explanation(p["name"], sport, str(p["stat"]), proj, line, edge)

        picks.append({
            "name": p["name"],
            "team": p.get("team", ""),
            "sport": sport,
            "stat": str(p["stat"]),
            "matchup": p.get("matchup", ""),
            "projection": proj,
            "line": line,
            "edge": edge,
            "direction": direction,
            "reason": reason,
        })

    picks = deduplicate(picks)
    picks = apply_enhancements(picks, sport)

    date_str = datetime.now(ET).strftime("%Y-%m-%d")

    # Save CSV
    PICKS_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = PICKS_DIR / f"{sport}_{date_str}.csv"
    fieldnames = ["name", "team", "sport", "stat", "matchup", "projection", "line", "edge", "direction", "reason"]
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for p in picks:
            writer.writerow(p)

    # Save to DB
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    for p in picks:
        c.execute(
            """INSERT INTO picks (date, league, player, team, stat, tc_projection, market_line, edge,
                                  direction, reason, matchup, period, signal)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                date_str, p["sport"], p["name"], p["team"], p["stat"],
                p["projection"], p["line"], p["edge"], p["direction"],
                p.get("reason", ""), p.get("matchup", ""), "GAME", "SELF_EDGE",
            ),
        )
    conn.commit()
    conn.close()

    send_email_report(picks, sport, date_str)

    logger.info(f"Saved {len(picks)} picks for {sport}")
    return picks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sport", choices=["mlb", "wnba", "wc", "all"], default="all")
    args = parser.parse_args()

    sports = ["mlb", "wnba", "wc"] if args.sport == "all" else [args.sport]

    for s in sports:
        try:
            generate_picks(s)
        except Exception as exc:
            logger.error(f"Sport {s} failed: {exc}")

    # Update last_run
    last_run = {"last_run": datetime.now(ET).isoformat()}
    (Path(__file__).parent.parent / "Daily_Log" / "last_run.json").write_text(json.dumps(last_run, indent=2))
    logger.info(f"Pipeline complete. last_run.json updated.")


if __name__ == "__main__":
    main()
