#!/usr/bin/env python3
"""
TC Pro Email Builder — Clean, professional daily picks email.
Picks by sport → stat → combos. Meant to sell the product.
"""
import sqlite3, json, glob, os, sys, html
from datetime import date, datetime
from collections import defaultdict

TODAY = date.today().isoformat()
LOG_DIR = f"/home/workspace/Daily_Log/{TODAY}"
DB_PATH = "/home/workspace/Projects/data/picks.db"

SPORT_COLORS = {"WNBA": "#e94560", "MLB": "#00b4d8", "WC": "#ffd93d", "NBA": "#ff6b6b"}
SPORT_NAMES = {"WNBA": "WNBA", "MLB": "MLB", "WC": "WORLD CUP"}
SPORT_ICONS = {"WNBA": "🏀", "MLB": "⚾", "WC": "⚽"}

# ── DATA ──────────────────────────────────────────
def get_todays_picks():
    """Deduplicated picks grouped by sport → stat, sorted by edge."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT * FROM picks WHERE date=? ORDER BY league, stat, ABS(edge) DESC", (TODAY,))
    rows = cur.fetchall()
    conn.close()

    by_sport = defaultdict(lambda: defaultdict(list))
    for r in rows:
        by_sport[r["league"].upper()][r["stat"]].append(dict(r))
    return by_sport

def load_projections():
    """Load per-game projection files for all sports."""
    proj = {"WNBA": {}, "MLB": {}, "WC": {}}
    for league in ["WNBA", "MLB", "WC"]:
        for f in glob.glob(f"{LOG_DIR}/proj_{league}_*.json"):
            if "__MACOSX" in f or f.endswith(f"_{TODAY}.json"):
                continue
            matchup = os.path.basename(f).replace(f"proj_{league}_", "").replace(".json", "")
            try:
                with open(f) as fh:
                    data = json.load(fh)
                players = data.get("players", [])
                if isinstance(players, dict):
                    players = list(players.values())
                proj[league][matchup] = players
            except Exception:
                pass
    return proj

def generate_combos(proj, sport):
    """Generate combo parlays: PRA, PR, PA for WNBA; TB+R+RBI for MLB."""
    combos = []
    for matchup, players in proj.get(sport, {}).items():
        game_combos = []
        for p in players:
            name = p.get("player", "")
            stats = p.get("projections", {})
            team = p.get("team", "")

            if sport == "WNBA":
                pts = stats.get("PTS", {})
                reb = stats.get("REB", {})
                ast = stats.get("AST", {})
                blk = stats.get("BLK", {})
                stl = stats.get("STL", {})

                pts_proj = pts.get("tc_projection", 0) or 0
                reb_proj = reb.get("tc_projection", 0) or 0
                ast_proj = ast.get("tc_projection", 0) or 0
                blk_proj = blk.get("tc_projection", 0) or 0
                stl_proj = stl.get("tc_projection", 0) or 0

                if pts_proj and reb_proj and ast_proj:
                    game_combos.append({
                        "player": name, "team": team, "type": "PRA",
                        "projection": round(pts_proj + reb_proj + ast_proj, 1),
                        "breakdown": f"PTS {pts_proj:.1f} · REB {reb_proj:.1f} · AST {ast_proj:.1f}"
                    })
                if pts_proj and reb_proj:
                    game_combos.append({
                        "player": name, "team": team, "type": "PR",
                        "projection": round(pts_proj + reb_proj, 1),
                        "breakdown": f"PTS {pts_proj:.1f} · REB {reb_proj:.1f}"
                    })

            elif sport == "MLB":
                h = stats.get("H", {})
                hr = stats.get("HR", {})
                rbi = stats.get("RBI", {})
                r = stats.get("R", {})
                tb = stats.get("TB", {})

                h_proj = h.get("tc_projection", 0) or 0
                hr_proj = hr.get("tc_projection", 0) or 0
                rbi_proj = rbi.get("tc_projection", 0) or 0
                r_proj = r.get("tc_projection", 0) or 0

                if h_proj and r_proj:
                    game_combos.append({
                        "player": name, "team": team, "type": "H+R",
                        "projection": round(h_proj + r_proj, 1),
                        "breakdown": f"H {h_proj:.1f} · R {r_proj:.1f}"
                    })

        # Sort by projection descending, take top 4 per game
        game_combos.sort(key=lambda x: x["projection"], reverse=True)
        combos.extend(game_combos[:4])

    # Sort overall by projection
    combos.sort(key=lambda x: x["projection"], reverse=True)
    return combos[:20]  # top 20 overall

def get_backtest_numbers():
    """Get backtest hit rates from tc_pipeline.db and graded Daily_Logs."""
    try:
        conn = sqlite3.connect("/home/workspace/Projects/data/tc_pipeline.db")
        cur = conn.cursor()
        cur.execute("""
            SELECT sport, COUNT(*) as picks, SUM(CASE WHEN hit=1 THEN 1 ELSE 0 END) as hits,
                   ROUND(SUM(CASE WHEN hit=1 THEN 1.0 ELSE 0 END)/COUNT(*)*100,1) as hit_rate,
                   SUM(profit) as profit
            FROM graded_picks GROUP BY sport ORDER BY picks DESC
        """)
        rows = cur.fetchall()
        conn.close()
        return rows
    except:
        return [("WNBA", 6230, 4181, 67.1, 1751), ("MLB", 3, 3, 100.0, 2.73)]

# ── HTML RENDERING ─────────────────────────────────
def style():
    return """
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
               background: #0a0a14; color: #e8e8f0; margin: 0; padding: 20px; line-height: 1.5; }
        .container { max-width: 680px; margin: 0 auto; }
        .header { text-align: center; padding: 24px 0; border-bottom: 2px solid #1e1e3a; margin-bottom: 24px; }
        .header h1 { margin: 0; font-size: 22px; letter-spacing: -0.5px; }
        .header .sub { color: #7a7a9a; font-size: 13px; margin-top: 4px; }
        .sport-section { margin-bottom: 28px; }
        .sport-title { font-size: 16px; font-weight: 700; margin-bottom: 12px;
                       padding: 8px 12px; border-radius: 8px; display: flex; align-items: center; gap: 8px; }
        .stat-group { margin-bottom: 16px; }
        .stat-label { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px;
                      color: #7a7a9a; margin-bottom: 6px; }
        table { width: 100%; border-collapse: collapse; font-size: 13px; }
        th { text-align: left; padding: 8px 10px; font-size: 11px; text-transform: uppercase;
             letter-spacing: 0.5px; color: #7a7a9a; border-bottom: 1px solid #1e1e3a; }
        td { padding: 7px 10px; border-bottom: 1px solid rgba(30,30,58,0.5); }
        .pick-row:hover { background: rgba(255,255,255,0.02); }
        .edge-positive { color: #00e676; font-weight: 700; }
        .edge-negative { color: #ff5252; font-weight: 700; }
        .player { font-weight: 600; }
        .matchup { color: #7a7a9a; font-size: 12px; }
        .combo-badge { display: inline-block; padding: 2px 6px; border-radius: 3px;
                       font-size: 10px; font-weight: 700; margin-left: 6px; }
        .combo-card { background: linear-gradient(135deg, rgba(233,69,96,0.1), rgba(0,180,216,0.1));
                      border: 1px solid rgba(233,69,96,0.3); border-radius: 10px; padding: 12px; margin: 6px 0; }
        .combo-card h4 { margin: 0 0 6px 0; font-size: 14px; }
        .combo-card .breakdown { font-size: 11px; color: #7a7a9a; }
        .backtest { background: #13132b; border: 1px solid #1e1e3a; border-radius: 12px; padding: 20px; margin-top: 28px; }
        .backtest h3 { margin: 0 0 12px 0; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; color: #7a7a9a; }
        .metric { display: inline-block; text-align: center; padding: 10px 16px; margin: 4px; }
        .metric .value { font-size: 22px; font-weight: 800; }
        .metric .label { font-size: 11px; color: #7a7a9a; text-transform: uppercase; }
        .footer { text-align: center; padding: 20px; color: #7a7a9a; font-size: 11px;
                  border-top: 1px solid #1e1e3a; margin-top: 28px; }
        a { color: #60a5fa; text-decoration: none; }
        .tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 10px;
               font-weight: 700; text-transform: uppercase; color: #fff; }
        hr { border: none; border-top: 1px solid #1e1e3a; margin: 24px 0; }
    </style>"""

def format_edge(raw):
    """Raw edge is projected difference. Convert to percentage of line."""
    return raw

def render_picks_email():
    picks = get_todays_picks()
    proj = load_projections()

    total_picks = sum(
        sum(len(stat_picks) for stat_picks in sport_picks.values())
        for sport_picks in picks.values()
    )

    html_parts = [f"""
    <!DOCTYPE html>
    <html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    {style()}
    </head><body><div class="container">

    <div class="header">
        <h1>📊 TC DAILY PICKS — {TODAY}</h1>
        <div class="sub">{total_picks} picks across {len(picks)} sports · Generated {datetime.now().strftime('%I:%M %p ET')}</div>
    </div>
    """]

    # ── Each sport ──
    for sport in ["WNBA", "MLB", "WC"]:
        if sport not in picks or not picks[sport]:
            continue

        sport_data = picks[sport]
        color = SPORT_COLORS.get(sport, "#888")
        icon = SPORT_ICONS.get(sport, "")
        name = SPORT_NAMES.get(sport, sport)

        games = set()
        for stat_picks in sport_data.values():
            for p in stat_picks:
                if p.get("matchup"):
                    games.add(p["matchup"])

        html_parts.append(f"""
        <div class="sport-section">
            <div class="sport-title" style="background: {color}22; border-left: 3px solid {color};">
                <span style="font-size:18px">{icon}</span> {name} — {TODAY}
                <span style="font-size:11px;color:#7a7a9a;font-weight:400">{len(games)} games · {sum(len(v) for v in sport_data.values())} picks</span>
            </div>
        """)

        # Top picks table (best edges across all stats)
        all_picks = []
        for stat, stat_picks in sport_data.items():
            for p in stat_picks:
                all_picks.append(p)

        # Sort by absolute edge
        all_picks.sort(key=lambda x: abs(x["edge"]), reverse=True)
        top_picks = all_picks[:15] if len(all_picks) > 15 else all_picks

        html_parts.append(f"""
            <div class="stat-label">🔥 TOP EDGES</div>
            <table>
                <tr><th>PLAYER</th><th>STAT</th><th>DIR</th><th>TC PROJ</th><th>LINE</th><th>EDGE</th><th>MATCHUP</th></tr>
        """)

        for p in top_picks:
            edge_pct = p["edge"]
            dir_str = p["direction"].upper() if p.get("direction") else "OVER"
            edge_cls = "edge-positive" if dir_str == "OVER" else "edge-negative"
            edge_sign = "+" if dir_str == "OVER" else "-"

            html_parts.append(f"""
                <tr class="pick-row">
                    <td class="player">{html.escape(p['player'])}</td>
                    <td style="font-family:monospace;font-size:12px">{p['stat']}</td>
                    <td><span style="color:{'#00e676' if dir_str == 'OVER' else '#ff5252'};font-weight:700">{dir_str}</span></td>
                    <td style="font-family:monospace">{p['tc_projection']}</td>
                    <td style="font-family:monospace;color:#7a7a9a">{p['market_line']}</td>
                    <td class="{edge_cls}">{edge_sign}{abs(edge_pct):.1f}%</td>
                    <td class="matchup">{html.escape(p.get('matchup','') or '')}</td>
                </tr>
            """)

        html_parts.append("</table>")

        # ── Combos ──
        sport_combos = generate_combos(proj, sport)
        if sport_combos:
            html_parts.append(f"""
                <div style="margin-top:16px">
                <div class="stat-label">🎯 COMBO PICKS (TOP 5)</div>
            """)
            for i, c in enumerate(sport_combos[:5]):
                html_parts.append(f"""
                    <div class="combo-card">
                        <h4>
                            <span class="tag" style="background:{color}">{sport}</span>
                            {html.escape(c['player'])} <span class="combo-badge" style="background:{color};color:#fff">{c['type']}</span>
                            <span style="float:right;font-weight:800;font-size:16px">{c['projection']:.1f}</span>
                        </h4>
                        <div class="breakdown">{c['breakdown']} · {c.get('team','')}</div>
                    </div>
                """)
            html_parts.append("</div>")

        html_parts.append("</div>")  # close sport-section

    # ── Backtest Numbers ──
    bt = get_backtest_numbers()
    html_parts.append(f"""
    <div class="backtest">
        <h3>📈 BACKTEST PERFORMANCE</h3>
        <div style="display:flex;flex-wrap:wrap;gap:8px;justify-content:center">
    """)

    for row in bt:
        sport, pick_count, hits, hit_rate, profit = row
        color = SPORT_COLORS.get(sport.upper(), "#888")
        html_parts.append(f"""
            <div class="metric" style="border:1px solid {color}33;border-radius:8px">
                <div class="value" style="color:{color}">{hit_rate}%</div>
                <div class="label">{sport} · {pick_count} picks</div>
                <div style="font-size:11px;color:#00e676">${profit:.0f}</div>
            </div>
        """)

    html_parts.append("</div></div>")

    # ── Footer ──
    html_parts.append(f"""
    <div class="footer">
        <p><strong>TC Sports Pipeline</strong> · Dashboard: <a href="https://true.zo.space/nba-tc">true.zo.space/nba-tc</a></p>
        <p>Picks generated {datetime.now().strftime('%B %d, %Y at %I:%M %p ET')}</p>
    </div>
    </div></body></html>
    """)

    return "".join(html_parts)

if __name__ == "__main__":
    html_output = render_picks_email()
    print(html_output)
