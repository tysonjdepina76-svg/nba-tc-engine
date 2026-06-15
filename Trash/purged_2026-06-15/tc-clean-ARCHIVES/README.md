# WNBA TC MODULE

## Overview
The WNBA TC module handles Triple Conservative projections for WNBA games.

## Files
- `wnba/scraper.py` — Live ESPN scraper (WNBA-specific)
- `wnba/engine.py` — TC calculation engine (same formula as NBA)
- `wnba/backtest.py` — Backtest suite
- `wnba/rosters.py` — Full WNBA roster data (13 teams)

## TC Formula
- TC = stat × 0.85
- Questionable = stat × 0.55
- OUT = 0

## Teams
| Code | Name |
|------|------|
| ATL | Atlanta Dream |
| CHI | Chicago Sky |
| CON | Connecticut Sun |
| DAL | Dallas Wings |
| IND | Indiana Fever |
| LVA | Las Vegas Aces |
| MIN | Minnesota Lynx |
| NYL | New York Liberty |
| PHX | Phoenix Mercury |
| POR | Portland Fire |
| SEA | Seattle Storm |
| WAS | Washington Mystics |

## Usage
```bash
python sports_tc.py --sport WNBA --game "MIN @ DAL"
python sports_tc.py --sport WNBA --list
python sports_tc.py --sport WNBA --dashboard
```