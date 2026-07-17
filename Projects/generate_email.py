#!/usr/bin/env python3
"""TC Daily Picks — SMS-friendly report generator with sport-specific lines, combos, and explanations."""

import sys, os, json, csv, shutil
from datetime import datetime
from collections import defaultdict
from zoneinfo import ZoneInfo
import subprocess

ET = ZoneInfo("America/New_York")
LOG_DIR = "/home/workspace/Daily_Log"
PROJ_DIR = "/home/workspace/Projects"
IMG_DIR = "/home/workspace/Images"

STAT_LABELS = {
    "PTS": "Points", "REB": "Rebounds", "AST": "Assists",
    "3PM": "3PM", "STL": "Steals", "BLK": "Blocks",
    "PRA": "Pts+Reb+Ast", "PR": "Pts+Reb", "PA": "Pts+Ast",
    "K": "Strikeouts", "HA": "Hits Allowed", "ER": "Earned Runs",
    "H": "Hits", "HR": "Home Runs", "RBI": "RBI", "SB": "SB",
    "Pts+Reb+Ast": "Pts+Reb+Ast", "Pts+Reb": "Pts+Reb", "Pts+Ast": "Pts+Ast",
}

def explain_combo(c):
    player = c.get("player","?")
    combo_label = c.get("combo_label","")
    stats = c.get("stats",[])
    tc_proj = float(c.get("tc_projection",0))
    market_line = float(c.get("market_line",0))
    ep = float(c.get("edge_pct",0))
    direction = c.get("direction","?")
    matchup = c.get("matchup","")
    parts = [STAT_LABELS.get(s,s) for s in stats]
    detail = " + ".join(parts)
    return (f"{player} projects {tc_proj:.1f} {combo_label} "
            f"({detail}) vs line {market_line:.1f} — {ep:.0f}% edge {direction} ({matchup})")

def explain_pick(p):
    player = p.get("player","?")
    stat = p.get("stat","?")
    direction = p.get("direction","?")
    tc_proj = float(p.get("tc_projection",0))
    market_line = float(p.get("market_line",0))
    edge_val = abs(float(p.get("edge",0)))
    ep = edge_val * 100
    matchup = p.get("matchup","")
    signal = p.get("signal","")
    label = STAT_LABELS.get(stat, stat)
    why = p.get("why","")
    if why:
        return f"{player} {label} {direction} {market_line:.1f} | TC: {tc_proj:.1f} | {ep:.0f}% | {matchup}\n   Why: {why}"
    return f"{player} {label} {direction} {market_line:.1f} | TC: {tc_proj:.1f} | {ep:.0f}% | {matchup}"

def load_picks(log_date):
    csv_path = os.path.join(LOG_DIR, log_date, "picks.csv")
    if not os.path.isfile(csv_path):
        return []
    with open(csv_path, "r") as f:
        return list(csv.DictReader(f))

def load_combos(log_date):
    json_path = os.path.join(LOG_DIR, log_date, "combos.json")
    if not os.path.isfile(json_path):
        return []
    with open(json_path, "r") as f:
        return json.load(f)

def build_report(log_date):
    picks = load_picks(log_date)
    combos = load_combos(log_date)
    now = datetime.now(ET).strftime("%I:%M %p ET")

    proj_only = [p for p in picks if p.get("signal","") == "PROJECTION ONLY"]
    real = [p for p in picks if p.get("signal","") not in ("PROJECTION ONLY","")]

    total = len(picks)
    body = f"TC DAILY — {log_date} {now}\n{total} picks | {len(combos)} combos\n\n"

    if combos:
        body += "🔥 TOP COMBOS\n"
        by_edge = sorted(combos, key=lambda c: abs(float(c.get("edge",0))), reverse=True)
        for i, c in enumerate(by_edge[:6], 1):
            player = c.get("player","?")
            lbl = c.get("combo_label","")
            d = c.get("direction","?")
            proj = float(c.get("tc_projection",0))
            ml = float(c.get("market_line",0))
            ep = float(c.get("edge_pct",0))
            mu = c.get("matchup","")
            body += f"{i}. {player} {lbl} {d} {ml:.1f} | TC:{proj:.1f} | +{ep:.0f}% | {mu}\n"
            body += f"   {explain_combo(c)}\n\n"

    by_sport = defaultdict(list)
    for p in picks:
        league = p.get("league", p.get("sport","?"))
        by_sport[league].append(p)

    for sport in ["WNBA","MLB","WC"]:
        sp = by_sport.get(sport, [])
        if not sp:
            continue
        emoji = {"WNBA":"🏀","MLB":"⚾","WC":"⚽"}.get(sport,"📊")
        body += f"---\n{emoji} {sport} — {len(sp)} picks\n\n"
        sp_sorted = sorted(sp, key=lambda p: abs(float(p.get("edge",0))), reverse=True)
        for p in sp_sorted[:10]:
            body += f"• {explain_pick(p)}\n"
        body += "\n"

    body += "---\n"
    body += "⚠️ ALL SELF-EDGE PROJECTIONS — no sportsbook lines available.\n"
    body += "WC: Odds API quota maxed. WNBA: DK posts late. MLB: quiet day.\n"
    body += f"Generated {now}"
    return body

def build_sms_report(log_date):
    picks = load_picks(log_date)
    combos = load_combos(log_date)
    now = datetime.now(ET).strftime("%I:%M%p ET")

    lines = [f"TC {log_date} {now}"]
    total = len(picks)
    lines.append(f"{total} picks | {len(combos)} combos")

    if combos:
        lines.append("")
        lines.append("🔥 TOP COMBOS:")
        by_edge = sorted(combos, key=lambda c: abs(float(c.get("edge",0))), reverse=True)
        for i, c in enumerate(by_edge[:3], 1):
            player = c.get("player","?")
            lbl = c.get("combo_label","")
            d = c.get("direction","?")
            ml = float(c.get("market_line",0))
            proj = float(c.get("tc_projection",0))
            mu = c.get("matchup","?")
            stats = c.get("stats",[])
            parts = "/".join([STAT_LABELS.get(s,s) for s in stats])
            lines.append(f"{i}. {player} {lbl} {d} {ml:.1f} TC:{proj:.1f} ({parts}) {mu}")

    by_sport = {}
    for p in picks:
        league = p.get("league", p.get("sport","?"))
        by_sport.setdefault(league, []).append(p)

    for sport in ["WNBA","MLB","WC"]:
        sp = by_sport.get(sport, [])
        if not sp:
            continue
        lines.append(f"\n🏀 {sport} top:")
        sp_sorted = sorted(sp, key=lambda p: abs(float(p.get("edge",0))), reverse=True)
        for p in sp_sorted[:4]:
            player = p.get("player","?")
            stat = p.get("stat","?")
            d = p.get("direction","?")
            ml = float(p.get("market_line",0))
            proj = float(p.get("tc_projection",0))
            line = f"{player} {stat} {d} {ml:.1f} TC:{proj:.1f}"
            lines.append(line)

    return "\n".join(lines)

def save_report(body, log_date):
    out_path = os.path.join(LOG_DIR, log_date, "email_report.md")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        f.write(body)
    print(f"Report saved: {out_path} ({len(body)} chars, {body.count(chr(10))} lines)")
    return out_path

def generate_images(log_date):
    picks = load_picks(log_date)
    combos = load_combos(log_date)
    os.makedirs(IMG_DIR, exist_ok=True)

    images = []
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        if combos:
            top = sorted(combos, key=lambda c: abs(float(c.get("edge",0))), reverse=True)[:3]
            fig, axes = plt.subplots(1, len(top), figsize=(5*len(top), 5))
            if len(top) == 1:
                axes = [axes]
            for ax, c in zip(axes, top):
                player = c.get("player","?")
                lbl = c.get("combo_label","")
                ml = float(c.get("market_line",0))
                proj = float(c.get("tc_projection",0))
                ax.bar(["Line","TC","Edge"],[ml, proj, proj-ml], color=["gray","green","gold"])
                ax.set_title(f"{player}\n{lbl}")
                ax.set_ylabel("Value")
            img_path = os.path.join(IMG_DIR, f"combos_{log_date}.png")
            plt.tight_layout()
            plt.savefig(img_path, dpi=100)
            plt.close()
            images.append(img_path)
            print(f"Image: {img_path}")
    except Exception as e:
        print(f"Images: SKIPPED ({e})")

    return images

def send_report(log_date):
    body = build_report(log_date)
    sms_body = build_sms_report(log_date)
    report_path = save_report(body, log_date)
    images = generate_images(log_date)

    print(f"\n--- REPORT READY ---")
    print(sms_body)
    print(f"--- {len(body)} chars ---")
    return report_path, sms_body, images

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None)
    ap.add_argument("--output", default=None)
    ap.add_argument("--send", action="store_true")
    ap.add_argument("--sms", action="store_true")
    args = ap.parse_args()

    log_date = args.date or datetime.now(ET).date().isoformat()

    if args.send or args.sms:
        report_path, sms_body, images = send_report(log_date)
        if args.sms:
            print(sms_body)
        return report_path

    body = build_report(log_date)
    out_path = args.output or os.path.join(LOG_DIR, log_date, "email_report.md")
    save_report(body, log_date)
    return out_path

if __name__ == "__main__":
    main()
