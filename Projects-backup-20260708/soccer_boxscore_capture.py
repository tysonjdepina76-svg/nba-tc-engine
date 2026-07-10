#!/usr/bin/env python3
"""
World Cup Soccer Boxscore Capture — Final scores + player stats from ESPN plays.

Captures:
  - Final scores
  - Player-level stats (goals, assists, shots, SOT, cards, fouls, saves, tackles, passes)
  - Halftime scores
  - Team aggregate stats

Usage:
  python3 soccer_boxscore_capture.py                    # today's games
  python3 soccer_boxscore_capture.py --event 760435      # specific event
  python3 soccer_boxscore_capture.py --mode halftime     # halftimes only
  python3 soccer_boxscore_capture.py --mode final        # finals only
"""

import json, requests, re, sys, argparse
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path("/home/workspace")
BOX_DIR = WORKSPACE / "Daily_Log" / "wc_boxscores"
REG_PATH = WORKSPACE / "Daily_Log" / "wc_boxscore_registry.json"
WC_SPATH = "soccer/fifa.world"
BOX_DIR.mkdir(parents=True, exist_ok=True)

# ─── registry ────────────────────────────────────────────────
def _loadreg():
    try:
        data = json.loads(REG_PATH.read_text()) if REG_PATH.exists() else {}
        if isinstance(data, list):
            return {str(eid): 0 for eid in data}
        return data
    except:
        return {}

def _savereg(r):
    REG_PATH.write_text(json.dumps(r, indent=2))

def already_saved(eid):
    reg = _loadreg()
    if eid in reg: return True
    for f in BOX_DIR.glob(f"*{eid}*.json"):
        reg[eid] = f.stat().st_mtime
        _savereg(reg)
        return True
    return False

def mark_saved(eid, info):
    reg = _loadreg()
    reg[eid] = info
    _savereg(reg)

# ─── ESPN API ────────────────────────────────────────────────
def _sum(eid):
    r = requests.get(
        f"https://site.api.espn.com/apis/site/v2/sports/{WC_SPATH}/summary",
        params={"event": eid}, timeout=20)
    return r.json() if r.status_code == 200 else None

def _plays(eid, page=1, limit=500):
    r = requests.get(
        f"https://sports.core.api.espn.com/v2/sports/soccer/leagues/fifa.world/events/{eid}/competitions/{eid}/plays",
        params={"limit": limit, "page": page}, timeout=20)
    return r.json() if r.status_code == 200 else {"items": [], "pageCount": 0}

def _sb(dstr):
    r = requests.get(
        f"https://site.api.espn.com/apis/site/v2/sports/{WC_SPATH}/scoreboard",
        params={"dates": dstr}, timeout=15)
    return r.json() if r.status_code == 200 else {}

# ─── stat parsing from plays ─────────────────────────────────
STAT_MAP = {
    "Goal": "goals",
    "Goal - Header": "goals",
    "Assist": "assists",
    "Shot On Target": "shots_on_target",
    "Shot Off Target": "shots",
    "Shot Blocked": "shots",
    "Yellow Card": "yellow_cards",
    "Red Card": "red_cards",
    "Foul": "fouls_committed",
    "Save": "saves",
    "Tackle": "tackles",
    "Pass": "passes",
    "Assists Shot": "shots",  # the assisted shot also counts as a shot for the shooter
}

def parse_player_from_text(text):
    """Extract player name from play text: 'Cristiano Ronaldo (Portugal) Pass at 1''"""
    if not text: return None
    m = re.match(r'^(.+?)\s+\(', text)
    if m: return m.group(1).strip().rstrip(' ')
    return None

def parse_player_from_participant(participants):
    """Try to get player from participant array."""
    if not participants: return None
    for p in participants:
        ath = p.get("athlete", {}) or {}
        name = ath.get("displayName", "") or ath.get("shortName", "")
        if name and name != "?":
            return name
    return None

def get_player_name(play):
    """Get player name from play, trying participant first, then text."""
    participants = play.get("participants", [])
    name = parse_player_from_participant(participants)
    if name and name != "?":
        return name
    text = play.get("text", "")
    return parse_player_from_text(text)

def build_stats_from_plays(eid):
    """Fetch all plays and build player stats dict."""
    all_plays = []
    page = 1
    while True:
        data = _plays(eid, page=page)
        items = data.get("items", [])
        all_plays.extend(items)
        if page >= data.get("pageCount", 1):
            break
        page += 1
    
    players = defaultdict(lambda: {
        "goals": 0, "assists": 0, "shots": 0, "shots_on_target": 0,
        "yellow_cards": 0, "red_cards": 0, "fouls_committed": 0,
        "saves": 0, "tackles": 0, "passes": 0
    })
    
    for play in all_plays:
        text = play.get("text", "")
        if not text:
            continue
        
        ptype = play["type"]["text"]
        
        # Extract player name from text (format: "Player Name (Team) Action at minute'")
        # Need to handle prefixes like "Goal! ...", "Attempt missed. ", etc.
        clean_text = text
        # Strip common play-by-play prefixes
        for prefix in [
            "Goal! ", "Goal!  ", 
            "Attempt missed. ", "Attempt missed.  ",
            "Attempt saved. ", "Attempt saved.  ",
            "Attempt blocked. ", "Attempt blocked.  ",
        ]:
            if clean_text.startswith(prefix):
                clean_text = clean_text[len(prefix):]
                break
        # Also strip "Team 1, Team 0. " from goal announcements
        if not clean_text.startswith("Goal!") and not clean_text[:1].isupper():
            # Try finding the first uppercase letter after a period
            dot_idx = clean_text.find(". ")
            if dot_idx >= 0:
                candidate = clean_text[dot_idx+2:]
                if candidate and candidate[:1].isupper():
                    clean_text = candidate
        
        if " (" not in clean_text:
            continue
        
        name = clean_text.split(" (")[0].strip()
        # Fix double spaces
        name = " ".join(name.split())
        if not name:
            continue
        
        ptype = play.get("type", {}).get("text", "")
        stat = STAT_MAP.get(ptype)
        if not stat:
            continue
        
        players[name][stat] += 1
        # Special: Shot On Target also counts as a shot
        if ptype == "Shot On Target":
            players[name]["shots"] += 1
    
    return dict(players), all_plays

def get_halftime_from_plays(all_plays):
    """Find halftime score from plays."""
    for play in all_plays:
        if play.get("type", {}).get("text") == "Halftime":
            return {
                "away": play.get("awayScore", 0) or 0,
                "home": play.get("homeScore", 0) or 0
            }
    return None

def get_final_from_plays(all_plays):
    """Get final score from last play."""
    if not all_plays:
        return None
    last = all_plays[-1]
    return {
        "away": last.get("awayScore", 0) or 0,
        "home": last.get("homeScore", 0) or 0
    }

# ─── capture ─────────────────────────────────────────────────
def capture_event(eid, matchup_label="?"):
    """Capture a single event's boxscore."""
    if already_saved(eid):
        print(f"  [{eid}] Already captured — skip")
        return None
    
    summary = _sum(eid)
    if not summary:
        print(f"  [{eid}] No summary data")
        return None
    
    # Get team info
    header = summary.get("header", {})
    comp = (header.get("competitions") or [{}])[0]
    teams = {}
    team_display = {}
    for c in comp.get("competitors", []):
        ha = c.get("homeAway", "")
        t = c.get("team", {})
        teams[ha] = t.get("abbreviation", "?")
        team_display[ha] = t.get("displayName", "?")
    
    # Get player stats from plays
    player_stats, all_plays = build_stats_from_plays(eid)
    
    if not player_stats:
        print(f"  [{eid}] No play data — game may not be finished")
        return None
    
    # Get scores
    final_score = get_final_from_plays(all_plays)
    halftime_score = get_halftime_from_plays(all_plays)
    
    # Get roster to map players to teams
    roster_team = {}
    for ros in summary.get("rosters", []):
        team_dname = ros.get("team", {}).get("displayName", "?")
        for player in ros.get("roster", []):
            if player.get("athlete"):
                name = player["athlete"].get("displayName", "")
                if name:
                    roster_team[name] = team_dname
    
    # Assign teams to players
    team_players = defaultdict(dict)
    unknowns = 0
    for pname, stats in player_stats.items():
        t = roster_team.get(pname, "Unknown")
        if t == "Unknown":
            unknowns += 1
        team_players[t][pname] = stats
    
    boxscore = {
        "event_id": eid,
        "matchup": matchup_label,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "away": {
            "team": team_display.get("away", "?"),
            "abbr": teams.get("away", "?"),
            "score": final_score["away"] if final_score else 0,
            "halftime_score": halftime_score["away"] if halftime_score else None,
        },
        "home": {
            "team": team_display.get("home", "?"),
            "abbr": teams.get("home", "?"),
            "score": final_score["home"] if final_score else 0,
            "halftime_score": halftime_score["home"] if halftime_score else None,
        },
        "players": team_players,
        "total_players": sum(len(v) for v in team_players.values()),
        "unknown_players": unknowns,
        "status": (summary.get("header", {}).get("competitions", [{}])[0].get("status", {}).get("type", {}).get("state", "?")),
        "total_plays": len(all_plays),
    }
    
    # Save
    safe = f"{teams.get('away','?')}_at_{teams.get('home','?')}".replace(" ", "_")
    fn = f"wc_{safe}_{eid}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    fp = BOX_DIR / fn
    fp.write_text(json.dumps(boxscore, indent=2, ensure_ascii=False))
    
    reg_info = {
        "matchup": matchup_label,
        "date": datetime.now(timezone.utc).isoformat(),
        "away": f"{team_display.get('away', '?')} ({final_score['away'] if final_score else '?'})",
        "home": f"{team_display.get('home', '?')} ({final_score['home'] if final_score else '?'})",
        "score": f"{final_score['away'] if final_score else '?'}-{final_score['home'] if final_score else '?'}",
        "players_captured": sum(len(v) for v in team_players.values()),
    }
    mark_saved(eid, reg_info)
    
    print(f"  [{eid}] Captured: {team_display.get('away','?')} {final_score['away'] if final_score else '?'}-{final_score['home'] if final_score else '?'} {team_display.get('home','?')} ({sum(len(v) for v in team_players.values())} players, {unknowns} unknown)")
    return boxscore

# ─── scan day ────────────────────────────────────────────────
def scan_and_capture(mode="final"):
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    sb = _sb(today)
    events = sb.get("events", [])
    
    if not events:
        print(f"No events on {today}")
        return
    
    saved = 0
    for ev in events:
        eid = str(ev.get("id", ""))
        if not eid:
            continue
        
        status = (ev.get("status") or {}).get("type") or {}
        state = status.get("state", "")
        
        comp = (ev.get("competitions") or [{}])[0]
        cs = comp.get("competitors", [])
        away = (cs[0].get("team", {}).get("abbreviation", "?") if len(cs) > 0 else "?")
        home = (cs[1].get("team", {}).get("abbreviation", "?") if len(cs) > 1 else "?")
        
        if mode == "final" and state != "post":
            print(f"  [{eid}] {away}@{home} — not final ({state}), skip")
            continue
        
        if capture_event(eid, f"{away}@{home}"):
            saved += 1
    
    print(f"\nCaptured: {saved} events")

def main():
    ap = argparse.ArgumentParser(description="World Cup Soccer Boxscore Capture")
    ap.add_argument("--event", default=None, help="Specific event ID")
    ap.add_argument("--mode", choices=["final", "halftime", "all"], default="final")
    args = ap.parse_args()
    
    if args.event:
        capture_event(args.event, f"Event {args.event}")
    else:
        scan_and_capture(mode=args.mode)

if __name__ == "__main__":
    main()
