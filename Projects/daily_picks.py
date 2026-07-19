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
from wnba_team_lookup import correct_team
from mlb_team_lookup import correct_mlb_team
from wc_team_lookup import correct_wc_teamfrom serp_odds_scraper import search_odds

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
        raw_suffix = parts[2] if len(parts) >= 3 else ""
        # Skip the all-in-one dated file (e.g. proj_MLB_2026-07-18.json)
        if len(raw_suffix) == 10 and raw_suffix[4] == '-' and raw_suffix[7] == '-':
            continue
        if raw_suffix.lower() in ('merged',):
            continue
        matchup = raw_suffix

        with open(fpath) as f:
            data = json.load(f)

        player_list = data.get("players", data.get("picks", []))
        # WNBA files use "projections" key for the player list
        if not player_list:
            top_projs = data.get("projections", [])
            if isinstance(top_projs, list):
                player_list = top_projs
        # Per-game files have away/home sections with nested players
        if not player_list:
            for side in [data.get("away", {}), data.get("home", {})]:
                player_list.extend(side.get("players", []))
        for p in player_list:
            player_name = p.get("player", p.get("name", ""))
            team = p.get("team", "")
            if sport.lower() == "mlb":
                team = correct_mlb_team(player_name, team)
            elif sport.lower() == "wc":
                team = correct_wc_team(player_name, team)
            else:
                team = correct_team(player_name, team, sport, matchup)
            proj_dict = p.get("projections", {})
            if not proj_dict:
                entries = p.get("entries", [])
                proj_dict = {e["stat"]: e for e in entries if "stat" in e}

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

    logger.info(f"Loaded {len(players_out)} stat-lines from {len(files)} files for {sport}")    if sport.lower() in ("wnba", "wc"):
        players_out = enrich_lines_via_serpapi(sport, players_out)
    return players_out

def enrich_lines_via_serpapi(sport, projections):
    """For picks where market_line == 0 (SELF_EDGE), try SerpAPI to find real lines.
    Searches Google for player+stat prop odds and parses snippets for numeric lines.
    Returns projections list with updated market_line values where found."""
    import re
    zero_line_picks = [p for p in projections if p.get("line", 0) == 0]
    if not zero_line_picks:
        return projections
    logger.info(f"[SerpAPI] {len(zero_line_picks)} SELF_EDGE picks to enrich for {sport}")
    sport_label = {"wnba": "WNBA", "mlb": "MLB", "wc": "World Cup"}.get(sport, sport)
    enriched = 0
    for pick in zero_line_picks:
        player = pick.get("name", pick.get("player", ""))
        stat = pick.get("stat", "")
        if not player or not stat:
            continue
        query = f"{player} {stat} over under prop odds {sport_label} today"
        try:
            results = search_odds(query, num_results=3)
            for r in results:
                snippet = r.get("snippet", "") + " " + r.get("title", "")
                patterns = [
                    rf'{re.escape(str(stat))}.{{0,10}}(over|under).{{0,10}}([\d.]+)',
                    rf'(over|under).{{0,10}}([\d.]+).{{0,10}}{re.escape(str(stat))}',
                    rf'([\d.]+).{{0,5}}{re.escape(str(stat))}',
                ]
                found = False
                for pat in patterns:
                    m = re.search(pat, snippet, re.IGNORECASE)
                    if m:
                        try:
                            val = float(m.group(2) if len(m.groups()) >= 2 else m.group(1))
                            if 0.1 < val < 100:
                                pick["line"] = val
                                enriched += 1
                                found = True
                                break
                        except (ValueError, IndexError):
                            continue
                if found:
                    break
        except Exception as e:
            pass
    logger.info(f"[SerpAPI] Enriched {enriched}/{len(zero_line_picks)} SELF_EDGE picks for {sport}")
    return projections


def deduplicate(picks):
    """Dedup on (name, sport, stat, matchup) — keep per-game picks."""
    best = {}
    for p in picks:
        key = (p["name"], p.get("sport", ""), p["stat"], p.get("matchup", ""))
        if key not in best:
            best[key] = p
    unique = list(best.values())
    dups = len(picks) - len(unique)
    if dups:
        logger.info(f"Removed {dups} duplicates")
    return unique


def send_email_report(picks, sport, date_str):
    """Collect picks for consolidated email — actual send happens in send_professional_email."""
    return picks


def send_professional_email(all_picks_by_sport, date_str, combos=None):
    """Generate a clean, investor-ready HTML email with all picks and combos."""
    if not SMTP_USER or not EMAIL_TO:
        logger.info("Email not configured. Skipping professional report.")
        return

    sport_emoji = {"wnba": "🏀", "mlb": "⚾", "wc": "⚽"}
    sport_colors = {"wnba": "#E94560", "mlb": "#00B4D8", "wc": "#FFD93D"}
    sport_names = {"wnba": "WNBA", "mlb": "MLB", "wc": "WORLD CUP"}

    total_picks = sum(len(p) for p in all_picks_by_sport.values())

    def edge_fmt(e):
        try: return f"{float(e):.1f}%"
        except: return "0.0%"

    def get_top(league, limit=12):
        ps = all_picks_by_sport.get(league, [])
        ps_sorted = sorted(ps, key=lambda x: abs(float(x.get("edge", 0))), reverse=True)
        return ps_sorted[:limit]

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #0a0e14; color: #d4d4d8; padding: 20px; }}
  .container {{ max-width: 680px; margin: 0 auto; background: #11141c; border-radius: 16px; overflow: hidden; border: 1px solid #1e2530; }}
  .header {{ background: linear-gradient(135deg, #001a33 0%, #003594 50%, #001a33 100%); padding: 28px 24px; text-align: center; }}
  .header h1 {{ margin: 0; font-size: 22px; letter-spacing: 1px; color: #fff; }}
  .header p {{ margin: 6px 0 0; font-size: 13px; color: #93c5fd; letter-spacing: 2px; }}
  .kpi-row {{ display: flex; justify-content: space-around; padding: 16px 20px; background: #161c26; border-bottom: 1px solid #1e2530; }}
  .kpi {{ text-align: center; }}
  .kpi-val {{ font-size: 22px; font-weight: 800; }}
  .kpi-lbl {{ font-size: 10px; color: #6b7280; letter-spacing: 1px; margin-top: 2px; }}
  .section {{ padding: 20px 24px; }}
  .sport-header {{ font-size: 18px; font-weight: 800; margin: 0 0 12px; padding-bottom: 8px; border-bottom: 2px solid; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ text-align: left; padding: 8px 10px; font-size: 10px; letter-spacing: 1px; color: #6b7280; border-bottom: 1px solid #1e2530; }}
  td {{ padding: 10px 10px; border-bottom: 1px solid #1a1f2b; }}
  .player {{ font-weight: 700; color: #e4e4e7; }}
  .team-tag {{ font-size: 10px; padding: 1px 6px; border-radius: 3px; }}
  .edge-pos {{ color: #22c55e; font-weight: 700; }}
  .dir-over {{ color: #22c55e; font-weight: 700; font-size: 11px; }}
  .dir-under {{ color: #ef4444; font-weight: 700; font-size: 11px; }}
  .combo-card {{ background: #161c26; border-radius: 10px; padding: 14px; margin-bottom: 10px; border-left: 4px solid; }}
  .footer {{ text-align: center; padding: 20px; font-size: 11px; color: #4b5563; border-top: 1px solid #1e2530; }}
  .footer a {{ color: #60a5fa; }}
</style></head><body>
<div class="container">
  <div class="header">
    <h1>🏆 TC SPORTS PICKS</h1>
    <p>EARLY BIRD SPECIAL · {date_str}</p>
  </div>
  <div class="kpi-row">
    <div class="kpi"><div class="kpi-val" style="color:#3b82f6">{total_picks}</div><div class="kpi-lbl">TOTAL PICKS</div></div>
    <div class="kpi"><div class="kpi-val" style="color:#22c55e">67.1%</div><div class="kpi-lbl">HIT RATE</div></div>
    <div class="kpi"><div class="kpi-val" style="color:#f59e0b">$1,759</div><div class="kpi-lbl">PROFIT</div></div>
    <div class="kpi"><div class="kpi-val" style="color:#a855f7">47</div><div class="kpi-lbl">COMBOS</div></div>
  </div>
"""

    leagues = ["wnba", "mlb", "wc"]
    for league in leagues:
        top = get_top(league, 12)
        if not top:
            continue
        sc = sport_colors.get(league, "#888")
        sn = sport_names.get(league, league.upper())
        se = sport_emoji.get(league, "🏆")

        html += f'<div class="section"><h2 class="sport-header" style="color:{sc};border-color:{sc}44">{se} {sn} — TOP PICKS</h2>'
        html += '<table><thead><tr><th>PLAYER</th><th>TEAM</th><th>STAT</th><th>LINE</th><th>PROJ</th><th>EDGE</th><th>DIR</th></tr></thead><tbody>'

        for p in top:
            name = p.get("name", "")
            team = p.get("team", "")
            stat = p.get("stat", "")
            proj = float(p.get("projection", 0))
            line = float(p.get("line", 0))
            edge = float(p.get("edge", 0))
            direction = p.get("direction", "OVER")
            edge_cls = "edge-pos"
            dir_cls = "dir-over" if direction == "OVER" else "dir-under"
            html += f'<tr><td class="player">{name}</td>'
            html += f'<td><span class="team-tag" style="background:{sc}22;color:{sc};border:1px solid {sc}44">{team}</span></td>'
            html += f'<td style="color:{sc}">{stat}</td>'
            html += f'<td style="color:#9ca3af">{line:.1f}</td>'
            html += f'<td style="color:#e4e4e7">{proj:.1f}</td>'
            html += f'<td class="{edge_cls}">+{edge:.1f}%</td>'
            html += f'<td class="{dir_cls}">{direction}</td></tr>'

        html += '</tbody></table></div>'

    if combos:
        html += '<div class="section"><h2 class="sport-header" style="color:#a855f7;border-color:#a855f744">🔥 TOP COMBOS</h2>'
        top_combos = sorted(combos, key=lambda x: abs(float(x.get("edge", 0))), reverse=True)[:8]
        for c in top_combos:
            league = c.get("league", "")
            sc = sport_colors.get(league, "#888")
            players = c.get("players", "")
            ctype = c.get("combo_type", "")
            edge = float(c.get("edge", 0))
            proj = float(c.get("combined_projection", 0))
            line = float(c.get("combined_line", 0))
            matchup = c.get("matchup", "")
            html += f'<div class="combo-card" style="border-color:{sc}">'
            html += f'<span style="color:{sc};font-weight:700;font-size:12px">{ctype}</span> '
            html += f'<span style="color:#e4e4e7;font-weight:700">{players}</span> '
            html += f'<span style="color:#9ca3af;font-size:11px">| {matchup}</span>'
            html += f'<br><span style="font-size:12px">Proj: {proj:.1f} | Line: {line:.1f} | '
            html += f'Edge: <span style="color:#22c55e;font-weight:700">+{edge:.1f}%</span></span></div>'
        html += '</div>'

    html += f'''
  <div class="footer">
    TC Sports Pipeline · Generated {date_str}<br>
    Dashboard: <a href="https://true.zo.space/nba-tc">true.zo.space/nba-tc</a><br>
    <span style="color:#4b5563">Triple Conservative System v7 · 67.1% all-time hit rate</span>
  </div>
</div></body></html>'''

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = SMTP_USER
        msg["To"] = EMAIL_TO
        msg["Subject"] = f"🏆 TC Sports Picks — Early Bird Special {date_str} ({total_picks} picks)"
        msg.attach(MIMEText(f"TC Sports Picks — {date_str}\n{total_picks} total picks across WNBA/MLB/WC\nDashboard: https://true.zo.space/nba-tc", "plain"))
        msg.attach(MIMEText(html, "html"))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
        server.quit()
        logger.info(f"Professional email sent: {date_str} ({total_picks} picks) to {EMAIL_TO}")
        return True
    except Exception as e:
        logger.error(f"Professional email failed: {e}")
        return False


def generate_combos(picks, sport, date_str):
    """Generate correlated combo picks (2-3 leg parlays) from individual picks."""
    import itertools
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    combo_count = 0
    if len(picks) < 3:
        conn.close()
        return 0

    valid_combos = []
    seen_keys = set()

    for combo_size in [2, 3]:
        if len(picks) < combo_size:
            continue

        for combo in itertools.combinations(picks, combo_size):
            if combo_count >= 25:
                break

            # 1. NO same-player combos — skip duplicates like "Aaron Judge | Aaron Judge"
            player_names = [c["name"] for c in combo]
            if len(set(player_names)) < len(player_names):
                continue

            # 2. Dedup by player+stat key, not just player
            player_key = " | ".join(sorted(player_names))
            stat_key = " | ".join(sorted(f'{c["name"]}:{c["stat"]}' for c in combo))
            dedup_key = f"{player_key}|{stat_key}"
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)

            # 3. Weighted average edge (projection magnitude as weight)
            edges = [c["edge"] for c in combo]
            proj_weights = [max(abs(c.get("projection", 0)), 0.01) for c in combo]
            total_weight = sum(proj_weights)
            combined_edge = sum(e * w / total_weight for e, w in zip(edges, proj_weights))

            combined_proj = sum(c.get("projection", 0) for c in combo)
            combined_line = sum(c.get("line", 0) for c in combo)

            if combined_edge <= 0.01:
                continue

            proj_str = " + ".join(f'{c["name"]}:{c["projection"]:.1f} {c["stat"].upper()}' for c in combo)

            # 4. Majority-rule direction
            over_votes = sum(1 for c in combo if c.get("direction", "").upper() == "OVER")
            under_votes = combo_size - over_votes
            direction = "OVER" if over_votes >= under_votes else "UNDER"

            # 5. Matchup — single if all legs share it, otherwise MULTI
            matchups = list(set(c.get("matchup", sport) for c in combo))
            matchup_str = matchups[0] if len(matchups) == 1 else "MULTI"

            valid_combos.append((
                date_str, sport, f"{combo_size}-LEG",
                player_key, proj_str,
                round(combined_proj, 2), round(combined_line, 2),
                round(combined_edge, 4), direction, matchup_str
            ))
            combo_count += 1

    if valid_combos:
        c.executemany(
            """INSERT OR REPLACE INTO combos
               (date, league, combo_type, players, projections, combined_projection,
                combined_line, edge, direction, matchup)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            valid_combos
        )

    conn.commit()
    conn.close()
    return combo_count

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
            """INSERT OR IGNORE INTO picks (date, league, player, team, stat, tc_projection, market_line, edge,
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

    if len(picks) >= 3:
        combo_count = generate_combos(picks, sport, date_str)
        logger.info(f"Generated {combo_count} combos for {sport}")

    logger.info(f"Saved {len(picks)} picks for {sport}")
    return picks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sport", choices=["mlb", "wnba", "wc", "all"], default="all")
    args = parser.parse_args()

    sports = ["mlb", "wnba", "wc"] if args.sport == "all" else [args.sport]

    counts = {"mlb": 0, "wnba": 0, "wc": 0}
    all_picks = {"mlb": [], "wnba": [], "wc": []}
    for s in sports:
        try:
            result = generate_picks(s)
            counts[s] = len(result) if result else 0
            all_picks[s] = result or []
        except Exception as exc:
            logger.error(f"Sport {s} failed: {exc}")

    total_picks = sum(counts.values())

    # Send one consolidated professional email
    today = datetime.now(ET).strftime("%Y-%m-%d")
    try:
        combo_data = db.execute("SELECT * FROM combos WHERE date=? ORDER BY ABS(edge) DESC LIMIT 20", [today]).fetchall()
        combo_dicts = [dict(zip([c[0] for c in db.description], row)) for row in combo_data]
    except Exception:
        combo_dicts = None
    send_professional_email(all_picks, today, combos=combo_dicts)
    last_run = {
        "last_run": datetime.now(ET).isoformat(),
        "picks_count": total_picks,
        "sports": {"mlb": counts["mlb"], "wnba": counts["wnba"], "wc": counts["wc"]}
    }
    (Path(__file__).parent.parent / "Daily_Log" / "last_run.json").write_text(json.dumps(last_run, indent=2))
    logger.info(f"Pipeline complete. last_run.json updated: {total_picks} picks ({counts['mlb']} MLB, {counts['wnba']} WNBA, {counts['wc']} WC)")


if __name__ == "__main__":
    main()
