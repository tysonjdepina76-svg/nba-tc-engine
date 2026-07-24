# SYSTEM GAP LIST — 2026-07-21
## Why each gap exists + what blocks it

### 1. SERPAPI — MONTHLY QUOTA MAXED
- Status: 0/50 remaining per run, 253/250 daily cap exceeded
- Why: Monthly quota exhausted. No real market lines from DraftKings/BetMGM/FanDuel.
- What blocks: Needs new key or billing cycle reset. Resets ~8/1.
- Impact: ALL picks are SELF_EDGE (no external line comparables).

### 2. ODDS API — BUSINESS TIER MAXED
- Status: 401 on /odds/ and /props/ endpoints
- Why: Business tier quota fully consumed. Events endpoint /events/ still works.
- What blocks: Needs higher tier plan or new billing cycle.
- Impact: No DK/BetMGM/PointsBet lines for World Cup, MLB, WNBA.

### 3. SDIO — DEAD KEY
- Status: 401 on all odds endpoints
- Why: Unauthorized. Key is expired or invalid. Not our key to refresh.
- What blocks: Needs valid key from SportsDataIO account owner.
- Impact: No SDIO odds feed.

### 4. FANGRAPHS (pybaseball) — 403 IP-BLOCKED
- Status: 403 from fangraphs.com/leaders-legacy.aspx
- Why: Fangraphs instituted IP blocking on scrape endpoints.
- What blocks: statsapi still works (MLB live stats). pybaseball team/player lookups work but player-specific stat pages blocked.
- Impact: Can't scrape Fangraphs advanced metrics. Using statsapi fallback.

### 5. nba_api / WNBA LIVE STATS — NO GAMES TODAY
- Status: nba_api installed and wired. WNBA feed returns 0 games.
- Why: Tuesday 7/21 — no WNBA games scheduled.
- What blocks: Competitions resume when games scheduled.
- Impact: WNBA live enrichment path exists but idle until next game day.

### 6. ESPN FREE API — NO PLAYER PROPS
- Status: Working. Spread/O/U per game enriched from DraftKings provider 100.
- Why: Free ESPN API only exposes game-level lines (spread, total). No individual player props.
- What blocks: Player props require paid API or scrape source.
- Impact: 774/810 enriched with game context but no player-specific market lines.

### 7. WORLD CUP — 0 MATCHES
- Status: ESPN API returns no matches.
- Why: Competition not active on current date. No fixtures.
- Impact: WC pipeline generates 0 picks.

### 8. EMAIL AUTO-DELIVERY — SMTP NOT CONFIGURED
- Status: Gmail OAuth connected for manual sends. No SMTP in daily_picks.py.
- Why: daily_picks.py email section needs SMTP creds (server, port, user, pass).
- What blocks: Can be configured with a Gmail app password or SendGrid key.
- Impact: Manual emails work via send_email_to_user. Automation emails (daily_picks auto-send) don't.

### 9. WORLD CUP ODDS — DEPENDS ON GAP 2
- Status: Depends on Odds API (gap 2 above).
- Impact: WC picks remain SELF_EDGE until Odds API quota resets or new source wired.

---

## WHAT'S WORKING (FREE)
| Source | Status | Coverage |
|--------|--------|----------|
| ESPN v2 API | LIVE | Game spread/O/U (MLB) |
| statsapi (MLB) | LIVE | Player stats, lineups |
| nba_api (WNBA) | WIRED | Waiting for games |
| pybaseball (MLB) | PARTIAL | Teams/players, Fangraphs blocked |
| SerpAPI | EXHAUSTED | Resets ~8/1 |

## WHAT I DID TODAY (7/21)
- Wired free_api_aggregator into daily_picks.py import chain
- Health check runs on every pipeline execution
- statsapi + nba_api + pybaseball live stat path ready
- Pipeline tested: 810 picks, 774 ESPN-enriched, 25 combos
- AGENTS.md updated
