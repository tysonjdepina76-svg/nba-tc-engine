#!/usr/bin/env python3
"""
SportsData.io NFL engine v3 — comprehensive pull across ALL available sources.

═══════════════════════════════════════════════════════════════════════════
TIER: Discovery Lab — Odds ($99/mo or $599/yr)
KEY:  SPORTS_DATA_API_KEY (self-serve purchase at discoverylab.sportsdata.io)
═══════════════════════════════════════════════════════════════════════════

WORKING ENDPOINTS (Discovery Lab — Odds tier):
  ✅ GameOddsByWeek         — spreads, totals, ML per game
  ✅ PlayerPropsByWeek      — 15 prop markets across books
  ✅ LiveGameOddsByWeek     — live in-game odds snapshot
  ✅ Teams                  — 32 teams with full metadata
  ✅ Stadiums               — 60 stadiums with capacity
  ✅ AllTeams               — all-team entities (including All-Pros)
  ✅ AreAnyGamesInProgress  — boolean ticker
  ✅ News                   — 11+ player news items

NOT AVAILABLE (requires Leagues API — commercial, contact sales):
  🔒 Schedules      (401)   🔒 TeamSeasonStats      (401)
  🔒 PlayerSeasonStats (401) 🔒 PlayerGameProjections (401)
  🔒 FantasyDefenseByGame(401)

NOT AVAILABLE (endpoints don't exist at v3/nfl):
  ❌ ByeWeeks, TeamDefenseByGame, Injuries, DVOA, LineMovement

═══════════════════════════════════════════════════════════════════════════
PROP MARKETS AVAILABLE (15 categories):
═══════════════════════════════════════════════════════════════════════════
  Fantasy Points             Rushing Attempts          Passing Completions
  Fantasy Points PPR         Total Touchdowns          Passing Yards
  Total Yards                Passing Attempts          Passing Touchdowns
  Receptions                                           Passing Interceptions
  Receiving Yards            Rushing Yards             Rushing Touchdowns
                                                       Receiving Touchdowns

═══════════════════════════════════════════════════════════════════════════
PAID TIERS (sportsdata.io):
═══════════════════════════════════════════════════════════════════════════
  Free Trial      Free        Scrambled data, all endpoints, low call limit
  Replay          Free        Real historical data, live-feed simulation
  Dev Key         Sales       Scrambled, unlimited calls (integration dev)
  Discovery Lab   $99-149/mo  Real data, next-day delayed, 8 sports
    ├─ Fantasy     $99/mo      Scores, stats, projections
    ├─ Odds        $99/mo      Live odds, player props, betting data
    └─ F+O         $149/mo     Both combined
  Leagues API     Sales       Real-time live, unlimited calls, 13 sports
  Global API      Sales       Schedules/scores, 100+ sports worldwide
  Vault           Sales       10+ years historical data for backtesting

═══════════════════════════════════════════════════════════════════════════
SUPPLEMENTARY SOURCES:
═══════════════════════════════════════════════════════════════════════════
  The Odds API ($25/mo)     — NFL game odds (75 events), limited props
  ESPN API (free)           — NFL games, boxscores with player stats
  BALLDONTLIE NFL (paid)    — Season stats, game stats, advanced passing

  DEFENSIVE STATS:   Only via Leagues API (commercial) or ESPN boxscores
  DVOA:              Proprietary — requires FO+ subscription or scraping
  HISTORICAL:        Vault tier ($contact) or The Odds API historical closing lines

Auth per source:
  SportsData.io:  Ocp-Apim-Subscription-Key header
  The Odds API:   apiKey query param
  ESPN:           No auth (public API)
"""

import json, os, re, requests, sys
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter

SD = "https://api.sportsdata.io/v3/nfl"
TOA = "https://api.the-odds-api.com/v4"
ESPN_NFL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"

SECRETS = Path("/root/.zo/secrets.env")
secrets_text = SECRETS.read_text()
SD_KEY = re.search(r"^SPORTS_DATA_API_KEY=(\S+)", secrets_text, re.MULTILINE)
ODDS_KEY = re.search(r"^ODDS_API_KEY=(\S+)", secrets_text, re.MULTILINE)
SD_HEADERS = {"Ocp-Apim-Subscription-Key": SD_KEY.group(1) if SD_KEY else ""}

# ── PROP MARKET REFERENCE ───────────────────────────────────────────────
PROP_MARKETS = [
    "Fantasy Points", "Fantasy Points PPR", "Total Yards",
    "Receptions", "Receiving Yards", "Rushing Yards",
    "Rushing Attempts", "Total Touchdowns", "Passing Attempts",
    "Passing Completions", "Passing Yards", "Passing Touchdowns",
    "Passing Interceptions", "Rushing Touchdowns", "Receiving Touchdowns",
]


def pull_sportsdata(season: str, week: int) -> dict:
    """Pull all working SportsData.io NFL endpoints."""
    data = {
        "source": "sportsdata.io",
        "tier": "Discovery Lab — Odds ($99/mo)",
        "season": season, "week": week,
        "pulled_at": datetime.now(timezone.utc).isoformat(),
    }

    def fetch(label, url):
        try:
            r = requests.get(url, headers=SD_HEADERS, timeout=20)
            r.raise_for_status()
            data[label] = r.json()
            print(f"  ✅ SD {label}: {len(data[label])} items")
        except Exception as e:
            data[label] = {"error": str(e)}
            print(f"  ❌ SD {label}: {e}")

    fetch("games",       f"{SD}/odds/json/GameOddsByWeek/{season}/{week}")
    fetch("props",       f"{SD}/odds/json/PlayerPropsByWeek/{season}/{week}")
    fetch("live_odds",   f"{SD}/odds/json/LiveGameOddsByWeek/{season}/{week}")
    fetch("teams",       f"{SD}/scores/json/Teams")
    fetch("stadiums",    f"{SD}/scores/json/Stadiums")
    fetch("all_teams",   f"{SD}/scores/json/AllTeams")
    fetch("in_progress", f"{SD}/scores/json/AreAnyGamesInProgress")
    fetch("news",        f"{SD}/scores/json/News")

    return data


def pull_oddsapi() -> dict:
    """Pull The Odds API NFL data (supplementary odds)."""
    if not ODDS_KEY:
        return {"error": "ODDS_API_KEY not found in secrets"}
    key = ODDS_KEY.group(1)
    data = {"source": "the-odds-api.com", "tier": "Paid ($25/mo)"}
    try:
        r = requests.get(
            f"{TOA}/sports/americanfootball_nfl/odds/",
            params={"apiKey": key, "regions": "us",
                    "markets": "h2h,spreads,totals"},
            timeout=20,
        )
        r.raise_for_status()
        games = r.json()
        data["games"] = games
        print(f"  ✅ OddsAPI NFL: {len(games)} events with odds")
    except Exception as e:
        data["error"] = str(e)
        print(f"  ❌ OddsAPI NFL: {e}")
    return data


def pull_espn() -> dict:
    """Pull ESPN NFL scoreboard (free, no auth)."""
    data = {"source": "espn.com", "tier": "Free public API"}
    try:
        r = requests.get(f"{ESPN_NFL}/scoreboard", timeout=15)
        r.raise_for_status()
        events = r.json().get("events", [])
        data["events"] = events
        print(f"  ✅ ESPN NFL scoreboard: {len(events)} events")
    except Exception as e:
        data["error"] = str(e)
        print(f"  ❌ ESPN NFL: {e}")
    return data


def summarize(data: dict) -> str:
    """Generate comprehensive summary across all sources."""
    sd = data.get("sportsdata", {})
    games = sd.get("games", [])
    props = sd.get("props", [])
    live = sd.get("live_odds", [])
    teams = sd.get("teams", [])
    stadiums = sd.get("stadiums", [])
    news = sd.get("news", [])
    in_progress = sd.get("in_progress", False)
    all_teams = sd.get("all_teams", [])

    oa = data.get("oddsapi", {})
    oa_games = oa.get("games", [])

    espn = data.get("espn", {})
    espn_events = espn.get("events", [])

    lines = [
        "═══════════════════════════════════════════════════════════════",
        f"  NFL PULL — Week {sd.get('week','?')} {sd.get('season','?')}",
        f"  Pulled: {sd.get('pulled_at','?')}",
        "═══════════════════════════════════════════════════════════════",
        "",
        "── SportsData.io (Discovery Lab Odds $99/mo) ──",
        f"  Games: {len(games)} | Props: {len(props)} | Live odds: {len(live)}",
        f"  Teams: {len(teams)} | All teams: {len(all_teams)} | Stadiums: {len(stadiums)}",
        f"  News: {len(news) if isinstance(news, list) else 'N/A'} | In progress: {in_progress if isinstance(in_progress, bool) else 'N/A'}")
        "",
    ]

    # Prop market breakdown
    if props:
        markets = Counter(p.get("Description", "?") for p in props)
        covered = set(markets.keys())
        missing = [m for m in PROP_MARKETS if m not in covered]
        lines.append(f"  Prop markets ({len(covered)}/15):")
        for market, count in markets.most_common():
            lines.append(f"    {market}: {count}")
        if missing:
            lines.append(f"  ⚠ Missing markets: {', '.join(missing)}")

    # Game synopsis
    lines.append("\n── Games ──")
    for g in games[:16]:
        away = g.get("AwayTeamName", "?")
        home = g.get("HomeTeamName", "?")
        dt = g.get("DateTime", "?")[:19] if g.get("DateTime") else "?"
        sid = g.get("ScoreId")
        pregame = g.get("PregameOdds", [])
        if pregame:
            o = pregame[0]
            spr = f"H{o.get('HomePointSpread', '?')}"
            tot = o.get("OverUnder", "?")
        else:
            spr = tot = "?"
        prop_count = sum(1 for p in props if p.get("ScoreID") == sid)
        lines.append(f"  {away} @ {home}  {dt}  Spr {spr}  O/U {tot}  {prop_count} props")

    # Supplementary sources
    lines.append(f"\n── The Odds API (Supplementary) ──")
    if isinstance(oa_games, list):
        w1 = [g for g in oa_games if "2026-09-" in g.get("commence_time", "")]
        lines.append(f"  All events: {len(oa_games)} | Week 1: {len(w1)}")
    elif oa.get("error"):
        lines.append(f"  ERROR: {oa['error']}")

    lines.append(f"\n── ESPN (Free) ──")
    if isinstance(espn_events, list):
        lines.append(f"  Scoreboard events: {len(espn_events)}")

    # Tier notes
    lines.append(f"\n── LIMITATIONS (this tier) ──")
    lines.append("  🔒 Unavailable: Schedules, TeamSeasonStats, PlayerSeasonStats")
    lines.append("  🔒 Unavailable: PlayerGameProjections, FantasyDefenseByGame")
    lines.append("  ❌ N/A: ByeWeeks, TeamDefenseByGame, Injuries, DVOA")
    lines.append("")
    lines.append("  💡 Defensive stats → ESPN boxscores (post-game) or Leagues API")
    lines.append("  💡 DVOA → Football Outsiders FO+ subscription or scraping")
    lines.append("  💡 Historical → Vault tier (contact sales) or The Odds API closing lines")

    return "\n".join(lines)


if __name__ == "__main__":
    season = sys.argv[1] if len(sys.argv) > 1 else "2026REG"
    week = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    all_sources = bool(sys.argv[3]) if len(sys.argv) > 3 else True

    print(f"\n🏈 NFL Pull — {season} Week {week}\n")

    data = {"season": season, "week": week, "pulled_at": datetime.now(timezone.utc).isoformat()}

    data["sportsdata"] = pull_sportsdata(season, week)

    if all_sources:
        print()
        data["oddsapi"] = pull_oddsapi()
        print()
        data["espn"] = pull_espn()

    # Save
    out_dir = Path("/home/workspace/Daily_Log")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_dir_today = out_dir / today
    out_dir_today.mkdir(parents=True, exist_ok=True)
    out_path = out_dir_today / f"nfl_full_{season}_W{week}.json"
    out_path.write_text(json.dumps(data, indent=2, default=str))

    print(f"\n{summarize(data)}")
    print(f"\n📁 Saved → {out_path}")
    print(f"   Size: {len(json.dumps(data)):,.0f} bytes")
