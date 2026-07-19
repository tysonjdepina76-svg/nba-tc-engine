# Pipeline Gaps — Full Thread List
# 2026-07-19 · Compiled from SMS conversation

## 1. Combo banner crosses/spills across dashboard window (nba-tc game cards)
Status: FIXED — reduced to compact inline pills, no glow/shadow, muted border

## 2. WC live stats dashboard generates nothing (live game stats tab blank for WC)
Status: FIXED — added WC_COLS (G,A,SH,SOT,PAS,TKL,YC) + rendering blocks for soccer in /nba-tc

## 3. WC picks not generating (pipeline skipping World Cup)
Status: FIXED — projections now generate for WC; pipeline runs wc alongside wnba/mlb

## 4. 19 dead/obsolete API endpoints cluttering main.py
Status: FIXED — purged 19 endpoints, 11 clean live endpoints remaining (all return 200)

## 5. Combos button on /dashboard not working (all other 4 buttons work)
Status: FIXED — /dashboard now fetches /api/v1/combos instead of old /api/combos/precomputed; field name c.label fixed to c.combo_label

## 6. Combo endpoint returning Internal Server Error after purge
Status: FIXED — _build_combos_from_db() and COMBO_DEFS deleted accidentally during purge; restored both

## 7. SerpAPI quota burned through — no cap was enforced in enrich_lines_via_serpapi()
Status: FIXED — Added SERPAPI_DAILY_MAX=250, SERPAPI_PER_RUN=8 with daily tracking file (serpapi_usage.json); picks sorted by edge before search

## 8. SDIO API key dead (401 on all odds endpoints)
Status: UNRESOLVED — needs new API key or different tier

## 9. Odds API Business tier quota maxed
Status: UNRESOLVED — Business tier exhausted; WC has no market data

## 10. All 721 projections are SELF_EDGE (zero real lines flowing)
Status: UNRESOLVED — cascading failure from SDIO dead + SerpAPI exhausted + Odds API maxed. Pipeline infrastructure correct, needs working keys

## 11. daily_picks.py had merged import on line 26 (correct_wc_teamfrom serp_odds_scraper)
Status: FIXED — split into two separate imports

## 12. Projections generating fake/identical lines across sports
Status: FIXED — generate_projections.py now sets line=0 for all sports, letting SerpAPI enrich (when quota available)

## 13. Signal not propagating from SerpAPI-enriched picks to DB
Status: FIXED — signal=SERPAPI now flows through to picks.db

## 14. WC combo definitions missing (only WNBA had combos)
Status: FIXED — 6 WC combo types added: G+A, S+PS, S+SOT, T+S, T+P, S+T

## 15. Combo API returning mixed dates (not filtering by today)
Status: FIXED — /api/v1/combos now filters WHERE date = today's date

## 16. Workspace cluttered — empty dirs, .bak files, stale node_modules
Status: FIXED — cleaned, committed, pushed

## 17. Streamlit dashboard not reflecting latest fixes
Status: FIXED — service restarted after each batch of changes

## SUMMARY
- Fixed: 14 gaps
- Unresolved: 3 gaps (all external API keys — SDIO dead, Odds API maxed, SerpAPI exhausted)
- Pipeline dead until SerpAPI monthly reset (~29 days) OR new API keys purchased
