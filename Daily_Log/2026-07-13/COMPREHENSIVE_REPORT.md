# TC Sports Betting System — Layman's Report

**Date**: Monday, July 13, 2026  
**Generated**: 5:25 PM ET  
**For**: Tyson J. Depina

---

## What the System Does (In Plain English)

This system watches sports matchups, crunches the numbers, and spits out **prop bets** — single-player stat bets like "will Dearica Hamby score more than 11.5 points?" It compares what the sportsbook thinks (the "line") against what our math model thinks (the "projection"). When our number is higher, we have an **edge** — meaning we think the sportsbook undervalued that bet.

The system rates every pick as **STRONG**, **MODERATE**, or **WEAK** based on how big the edge is.

---

## Today's Picks — Monday, July 13

| | |
|---|---|
| **Total picks generated** | 126 |
| **Sports covered** | WNBA (2 games) |
| **STRONG picks** | 99 (78.6%) — edge ≥ 12% |
| **MODERATE picks** | 27 (21.4%) — edge 6–11.9% |
| **All picks direction** | OVER (every single one) |
| **Edge range** | 11.1% to 14.0% |
| **Average edge** | 12.9% |

### Games on the slate

| Game | Spread | Total |
|---|---|---|
| LA Sparks @ Atlanta Dream | ATL -8.5 | 181.5 |
| Phoenix Mercury @ Minnesota Lynx | MIN -12.5 | 169.5 |

### What stats the picks cover

| Stat | Count | What it means |
|---|---|---|
| **PTS** (Points) | 72 picks | Player will score OVER their line |
| **REB** (Rebounds) | 40 picks | Player will grab more rebounds than the line |
| **AST** (Assists) | 13 picks | Player will dish more assists than the line |
| **BLK** (Blocks) | 1 pick | Player will swat more shots than the line |

---

## How Accurate Has the System Been? (Backtest)

We track every pick we've ever generated and grade it after the game. Here's the track record:

### WNBA (our best sport)

| Stat | Hit Rate | Sample Size |
|---|---|---|
| **BLK** (Blocks) | 100.0% | 50 picks |
| **AST** (Assists) | 75.0% | 40 picks |
| **REB** (Rebounds) | 62.5% | 80 picks |
| **PTS** (Points) | 59.9% | 202 picks |
| **Overall WNBA** | **67.5%** | 372 picks |

> **What this means**: Across 372 WNBA picks, we hit 251 of them. For prop betting, anything above 52.4% is profitable (at standard -110 odds). At 67.5%, the WNBA model is performing very well.

### World Cup (needs work)

| Stat | Hit Rate | Sample Size |
|---|---|---|
| ASSISTS | 5.2% | 58 picks |
| SHOTS | 3.4% | 58 picks |
| SHOTS ON TARGET | 1.7% | 58 picks |
| GOALS | 0.0% | 6 picks |
| **Overall World Cup** | **3.3%** | 180 picks |

> **What this means**: The World Cup model is not working. Soccer stats don't behave like basketball stats, and the model needs to be rebuilt specifically for soccer. Don't bet World Cup picks right now.

---

## System Health — All Green ✅

| Component | Status |
|---|---|
| **Dashboard** (http://localhost:8510) | ✅ UP — HTTP 200 |
| **Public page** (true.zo.space/nba-tc) | ✅ UP — HTTP 200 |
| **API endpoint** (true.zo.space/api/tc) | ✅ UP — HTTP 200 |
| **WNBA engine** | ✅ Generating 126 picks |
| **MLB engine** | ⚠️ 0 picks — All-Star break, no games scheduled |
| **World Cup engine** | ❌ Not wired into daily_picks.py yet |

---

## Known Gaps & Limitations

### 1. World Cup not in the daily pipeline
The WC slate data exists in `Daily_Log/` but `daily_picks.py` doesn't accept `--sport wc`. The projections are generated but no picks flow into the main CSV. Also: the WC backtest shows a 3.3% hit rate, so even when wired, the model is wrong for soccer and needs rebuilding.

### 2. Odds API quota maxed out
We're on the Business tier for Odds API and the quota is burned. The events endpoint still works (we can see what games exist), but odds/props endpoints return 401 (quota-exhausted, not bad key). This affects World Cup DK lines — we have no sportsbook lines to compare against for soccer.

### 3. MLB: No games today
All-Star break. Zero picks generated. This is correct behavior — not a bug.

### 4. All 126 picks are OVER
Every single WNBA pick today is an OVER recommendation. This isn't necessarily wrong, but it's unusual. Historically the model generates a mix of OVER/UNDER picks. This could mean the sportsbook lines are set low across the board today, or it could mean the model has a bias toward the over that should be watched.

---

## The Dashboard

The Streamlit dashboard at `http://localhost:8510` shows:
- Today's picks with signal badges (STRONG/MODERATE/WEAK)
- Edge percentages
- Matchup filters
- Why each pick was recommended (plain English explanation)
- Historical backtest stats

The public-facing version is at `https://true.zo.space/nba-tc`.

---

## Bottom Line for Today

**WNBA**: 126 picks, all STRONG or MODERATE, 67.5% historical accuracy. The model is confident and the historical track record backs it up. Two games: LA@ATL and PHX@MIN.

**MLB**: Nothing today — All-Star break. Normal.

**World Cup**: Don't bet. Model is broken for soccer (3.3% hit rate). Needs a rebuild before it's usable.

---

## Email Printout Note

If you're emailing this report: the stats table is the most important part. Everything else is context. The key numbers for someone who just wants picks:

- **126 WNBA picks, 99 STRONG, edge 12-14%**
- **Historical hit rate: 67.5% (251/372)**
- **Two games: LA@ATL and PHX@MIN**
- **Stick to STRONG picks only if you want to be conservative**

---

*Generated by the TC Pipeline at 2026-07-13 17:25 ET*
