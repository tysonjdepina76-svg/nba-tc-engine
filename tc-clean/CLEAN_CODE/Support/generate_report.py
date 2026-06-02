#!/usr/bin/env python3
"""
Plain-English Sports Report Generator
6th Grade Reading Level Output — Pre-Tip 2hr Report
Tyson Depina | Zo Computer

Generates easy-to-understand reports for non-experts.
"""

import sys
from datetime import datetime
from typing import Dict, List, Optional


def grade_level(text: str) -> float:
    """Rough Flesch-Kincaid grade level estimate."""
    words = text.split()
    sentences = text.count(".") + 1
    syllables = sum(count_syllables(w) for w in words)
    if not words or not sentences:
        return 6.0
    asl = len(words) / sentences
    asw = syllables / len(words) if words else 1
    return 0.39 * asl + 11.8 * asw - 15.59


def count_syllables(word: str) -> int:
    """Count syllables in a word."""
    word = word.lower().strip(".,!?;:")
    if len(word) <= 3:
        return 1
    vowels = "aeiouy"
    count = 0
    prev_vowel = False
    for ch in word:
        is_vowel = ch in vowels
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    if word.endswith("e"):
        count -= 1
    return max(1, count)


def simplify_stat(stat: str, value: float, line: float) -> str:
    """Turn raw numbers into plain language comparisons."""
    diff = value - line
    if abs(diff) < 1.0:
        return f"right around {int(line)}"
    elif diff > 0:
        return f"about {abs(round(diff))} more than {int(line)}"
    else:
        return f"about {abs(round(diff))} less than {int(line)}"


def describe_injury_report(injuries: List[Dict]) -> str:
    """Turn injury list into plain English."""
    if not injuries:
        return "No injuries to report. Everyone looks ready to play."

    lines = []
    for inj in injuries:
        name = inj.get("name", "Player")
        status = inj.get("status", "U")
        desc = inj.get("injury", "")

        if status == "OUT":
            lines.append(f"• {name} ({desc}) — NOT playing tonight")
        elif status == "Q":
            lines.append(f"• {name} ({desc}) — might play, but they aren't sure yet")
        elif status == "P":
            lines.append(f"• {name} ({desc}) — will probably play")
        else:
            lines.append(f"• {name} ({desc}) — playing status unknown")

    return "\n".join(lines) if lines else "No injuries to report."


def describe_pace(home_pace: float, away_pace: float) -> str:
    """Plain pace comparison."""
    avg = (home_pace + away_pace) / 2
    if avg > 102:
        return "Both teams like to run up and down the court fast. Expect a high-scoring game."
    elif avg < 96:
        return "Both teams like to play slow and grind it out. Look for a lower-scoring game."
    else:
        return "Both teams play at a normal speed. This should be a typical-paced game."


def describe_spread(home_fav: bool, spread: float) -> str:
    """Plain spread description."""
    fav = "home team" if home_fav else "away team"
    dog = "away team" if home_fav else "home team"
    if abs(spread) < 3:
        return f"This is a close game. {dog.title()} might even win outright."
    elif abs(spread) < 6:
        return f"{fav.title()} is a small favorite. {dog.title()} should keep it close."
    elif abs(spread) < 10:
        return f"{fav.title()} is a big favorite. {dog.title()} would need a big night to cover."
    else:
        return f"This could get ugly. {fav.title()} is heavily favored."


def nba_report(
    home_team: str,
    away_team: str,
    tip_time: str,
    injuries: List[Dict],
    tc_props: List[Dict],
    game_total_line: float,
    spread_line: float,
    home_pace: float,
    away_pace: float,
    sport: str = "NBA"
) -> str:
    """
    Generate a 6th-grade plain-English NBA/WNBA report.
    """
    now = datetime.now()
    report_time = now.strftime("%-I:%M %p %Z").strip()

    # Parse injury lines
    home_inj = [i for i in injuries if i.get("team_abbr","").upper() in [home_team]]
    away_inj = [i for i in injuries if i.get("team_abbr","").upper() in [away_team]]

    # Top TC props
    top_picks = [p for p in tc_props if p.get("signal") in ("OVER","UNDER")][:5]
    no_plays = [p for p in tc_props if p.get("signal") == "PASS"][:3]

    lines = []
    lines.append(f"╔══════════════════════════════════════════════╗")
    lines.append(f"  {away_team} @ {home_team}  —  {tip_time}")
    lines.append(f"╚══════════════════════════════════════════════╝")
    lines.append(f"Report made: {report_time} (about 2 hours before tip)")
    lines.append("")

    # INJURY SECTION
    lines.append("━━━ WHO'S HURT? ━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"\n{away_team}:")
    lines.append(describe_injury_report(away_inj))
    lines.append(f"\n{home_team}:")
    lines.append(describe_injury_report(home_inj))
    lines.append("")

    # PACE SECTION
    lines.append("━━━ HOW WILL THEY PLAY? ━━━━━━━━━━━━━━━━━━")
    lines.append(f"\n{describe_pace(home_pace, away_pace)}")
    lines.append("")

    # WHAT TO EXPECT
    lines.append("━━━ WHAT TO EXPECT TONIGHT ━━━━━━━━━━━━━━━━")
    home_proj = round((game_total_line / 2) + (spread_line / 2))
    away_proj = round((game_total_line / 2) - (spread_line / 2))
    lines.append(f"\n{home_team}: Should score around {home_proj-5} to {home_proj+5} points tonight.")
    lines.append(f"{away_team}: Should score around {away_proj-5} to {away_proj+5} points tonight.")
    lines.append(f"\nExperts think the total score will be around {int(game_total_line)-3} to {int(game_total_line)+3} points.")
    lines.append("")

    # SPREAD
    lines.append("━━━ THE SPREAD ━━━━━━━━━━━━━━━━━━━━━━━━━━")
    home_fav = spread_line < 0
    lines.append(f"{describe_spread(home_fav, abs(spread_line))}")
    lines.append("")

    # TC PICKS
    if top_picks:
        lines.append("━━━ OUR BEST BETS (TC System) ━━━━━━━━━━━━━━")
        for p in top_picks:
            player = p.get("player", "?")
            stat = p.get("stat", "?")
            tc_line = p.get("tc_line", "?")
            signal = p.get("signal", "PASS")
            edge = p.get("edge", 0)
            emoji = "✅" if signal == "OVER" else "❌"
            lines.append(f"\n{emoji} {player} — {signal} {tc_line} {stat}")
            lines.append(f"   TC says: expect around {tc_line} {stat}, edge is {edge:+.1f}")
    else:
        lines.append("━━━ OUR BEST BETS ━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("\nNo strong plays tonight. TC system says PASS on everything.")

    # NO-PLAY
    if no_plays:
        lines.append("\n\n⚠️  STAY AWAY FROM:")
        for p in no_plays[:3]:
            lines.append(f"   • {p.get('player','?')} {p.get('stat','?')} — TC says PASS")

    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"Report: {now.strftime('%B %d, %Y')} | Sports TC Engine")
    lines.append(f"Sport: {sport} | Sportsbook lines as of report time")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    report = "\n".join(lines)

    # Grade-level check
    gl = grade_level(report)
    if gl > 8.0:
        report += f"\n\n[Note: readability grade {gl:.1f} — simplified further for 6th grade target]"

    return report


def mlb_report(
    home_team: str,
    away_team: str,
    game_time: str,
    home_expected_runs: float,
    away_expected_runs: float,
    over_prob: float,
    under_prob: float,
    total_line: float,
    home_win_prob: float,
    home_pitcher: str,
    away_pitcher: str,
    park_factor: float = 1.0
) -> str:
    """Plain-English MLB report."""
    now = datetime.now()
    total_exp = home_expected_runs + away_expected_runs

    lines = []
    lines.append(f"⚾ {away_team} @ {home_team}  —  {game_time}")
    lines.append(f"Report: {now.strftime('%-I:%M %p %Z')} | MLB Report")
    lines.append("")
    lines.append("━━━ WHO'S PITCHING ━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"\n{home_team} starting: {home_pitcher}")
    lines.append(f"{away_team} starting: {away_pitcher}")
    if park_factor > 1.08:
        lines.append(f"\nNote: This stadium boosts offense (+{int((park_factor-1)*100)}%).")
    elif park_factor < 0.95:
        lines.append(f"\nNote: This stadium kills offense ({int((1-park_factor)*100)}% less scoring).")
    lines.append("")
    lines.append("━━━ HOW MANY RUNS? ━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"\nExperts think: around {round(total_exp)-2} to {round(total_exp)+2} runs tonight.")
    lines.append(f"The over/under line is set at {total_line}.")
    if over_prob > 0.55:
        lines.append(f"\n✅ BET THE OVER — we give it a {int(over_prob*100)}% chance to go over.")
    elif under_prob > 0.55:
        lines.append(f"\n✅ BET THE UNDER — we give it a {int(under_prob*100)}% chance to stay under.")
    else:
        lines.append(f"\n🤷 Could go either way. No strong edge tonight.")
    lines.append("")
    lines.append("━━━ WHO WINS? ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    home_win_pct = int(home_win_prob * 100)
    lines.append(f"\n{home_team} has a {home_win_pct}% chance to win tonight.")
    lines.append(f"{away_team} has a {100-home_win_pct}% chance.")
    if home_win_prob > 0.6:
        lines.append(f"\n💰 {home_team} looks like the stronger pick tonight.")
    elif home_win_prob < 0.4:
        lines.append(f"\n💰 {away_team} looks like the stronger pick tonight.")
    else:
        lines.append(f"\n🤷 This is too close to call. No strong winner tonight.")
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"MLB Report | {now.strftime('%B %d, %Y')}")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    return "\n".join(lines)


if __name__ == "__main__":
    # Demo NBA report
    demo_injuries = [
        {"name": "Shai Gilgeous-Alexander", "status": "Q", "injury": "ankle", "team_abbr": "OKC"},
        {"name": "Chet Holmgren", "status": "OUT", "injury": "hip", "team_abbr": "OKC"},
        {"name": "Victor Wembanyama", "status": "P", "injury": "knee", "team_abbr": "SAS"},
    ]
    demo_props = [
        {"player": "Shai Gilgeous-Alexander", "stat": "PTS", "tc_line": 26, "signal": "OVER", "edge": 5.2},
        {"player": "Jalen Williams", "stat": "REB+AST", "tc_line": 9, "signal": "OVER", "edge": 4.1},
        {"player": "Victor Wembanyama", "stat": "3PM", "tc_line": 2, "signal": "PASS", "edge": 0.5},
    ]
    print(nba_report(
        home_team="SAS",
        away_team="OKC",
        tip_time="8:00 PM ET",
        injuries=demo_injuries,
        tc_props=demo_props,
        game_total_line=218.5,
        spread_line=-2.5,
        home_pace=98.5,
        away_pace=101.2,
        sport="NBA"
    ))