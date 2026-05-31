# SportsBet AI — Competitive Improvements & Market Plan
## Tyson Depina | Zo Computer
### Draft: 2026-05-31 | CONFIDENTIAL

---

## 📊 Market Landscape

### Who We're Up Against
| App | Strengths | Weaknesses |
|-----|-----------|-----------|
| **DraftKings** | Brand, odds depth, same-game parlays | No AI projections, generic public model |
| **FanDuel** | UX, betting promos | SameGame Parlay+ uses public injury data only |
| **PrizePicks** | Simple over/under props | No algorithmic model — pure public consensus |
| **Underdog Fantasy** | Progressive odds, player-focused | No NBA injury-adjusted TC model |
| **BetMGM** | Casino integration, brand trust | No prop projection engine |
| **Caesars** | Retail, market maker | Slow line movement, no AI |

### Our Gap: Nobody Is Doing Injury-Adjusted TC + Multi-Sport + Plain English in One Place

---

## 🏆 Competitive Advantages (Moat)

### 1. Triple Conservative (TC) Injury Adjustment — NBA/WNBA Only
- **What it does**: Automatically discounts projected stats when a key player is OUT or Q
- **Why it's a moat**: DraftKings/FanDuel show injury lists but don't automatically re-price props
- **How to protect**: Document the exact formula (already in `nba_tc_pipeline.py`)

### 2. Multi-Sport Coverage
- **MLB**: Poisson run expectancy + FIP-adjusted pitching
- **NCAAB/NCAAF**: Pomeroy + Massey + G-Elo
- **NHL**: 5v5 goal expectancy + xG
- **NFL**: Proprietary template (already owned by Tyson)
- **Competitor gap**: No single app covers all 6 sports with sport-specific algorithms

### 3. Plain English Reports — 6th Grade Level
- **What**: Auto-generated pre-game reports anyone can understand
- **Why it matters**: 60% of sports bettors don't understand prop lines
- **Competitor gap**: Nobody does this

### 4. No API Key Required — Scrapes Public Sources
- **What**: Uses ESPN public APIs + web scraping
- **Why**: Reduces friction to zero for new users

### 5. Edge Detection Signal — OVER/UNDER/PASS
- **What**: Clean 3-signal output (no analysis paralysis)
- **Why**: PrizePicks-style simplicity with algorithmic backing

---

## 🔧 Improvements by Priority

### P0 — Must Have (MVP)

#### P0.1: DK/FanDuel Prop Line Scraper
```
Problem: Currently no live odds scraping
Solution: Use The Odds API or scrape DK
Cost: $0-$50/month
ROI: Required for edge calculation
```
**Action**: Add `the-odds-api` key to [Settings > Advanced](/?t=settings&s=advanced)

#### P0.2: Injury Report Window (NBA + WNBA)
```
Problem: Injuries exist in roster data but no dedicated UI
Status: ✅ Built in this session (tab added)
Files: SportsTC_Streamlit_App.py, /nba-tc React page
```
**Action**: Test the new "🏥  Injury Report" tab in Streamlit

#### P0.3: Multi-Sport Engine Integration
```
Problem: NBA TC is ready but MLB/NHL/NCAAB/NCAAF not in pipeline
Status: ✅ Algorithms written in multi_sport_engine.py + college_models.py
Missing: Live data integration into dashboard
```
**Action**: Wire `multi_sport_engine.py` into the Streamlit sport selector

#### P0.4: Daily Automation — 2hr Before Tip
```
Problem: No scheduled automation
Status: ✅ Script written: daily_tip_report.py
Missing: Cron or Zo automation to trigger it
```
**Action**: Create Zo agent: "Every day at 4 PM ET, run daily_tip_report.py"

---

### P1 — Should Have (V1.1)

#### P1.1: xMins Engine — Expected Minutes Model
```
Status: ✅ Algorithm written: xmins_engine.py
Missing: Live minute data feed
Priority: High — xMins is the #1 input to prop accuracy
```
**Note**: 1-5-10 game lag weighting documented in research. Implement when
live box scores are available via ESPN or DK API.

#### P1.2: Plain English Report Generator
```
Status: ✅ Built: generate_report.py
Output: 6th grade reading level reports
```
**Action**: Integrate into daily_tip_report.py output

#### P1.3: NFL Template Integration
```
Problem: Tyson has an NFL template but it's not in the system
Status: ❌ Not yet integrated
Missing: The NFL template file
```
**Action**: Provide the NFL template file and I'll integrate it

#### P1.4: WNBA Roster Expansion (12 → 15 teams)
```
Status: ✅ WNBA teams exist but may be outdated
Note: WNBA expanded to 15 teams in 2025
```

---

### P2 — Nice to Have (V2.0)

#### P2.1: Twitter/X Sports Sentiment Integration
```
Use x_search to track public injury news and line movement
Correlation with prop edges
```

#### P2.2: Custom Odds API Key — Premium Tier
```
The Odds API Free: 500 calls/month
The Odds API Paid: $100/month for 50,000 calls
Priority: Upgrade when daily users > 100
```

#### P2.3: Push Notifications via Telegram
```
Alert when edge > 4.0 on a prop
Integrate with Zo Telegram bot
```

#### P2.4: MLP Prediction Engine
```
From research: Transformer + BCE achieves 0.847 AUC on NCAA predictions
Consider adding when more historical data is collected
```

#### P2.5: PrizePicks/Dabin Integration
```
Pull PrizePicks lines directly
Compare against TC projections
Show edge on PrizePicks-specific props
```

---

### P3 — Future (V3.0)

#### P3.1: Betting History Tracker
```
Log every bet placed
Track ROI by sport, bet type, algorithm version
Show win/loss dashboard
```

#### P3.2: Community Parlay Builder
```
Users share parlay cards
Vote on best cards
Track community record
```

#### P3.3: Subscription Model
```
Free tier: 3 props/day
Pro tier ($9.99/mo): Unlimited props, all sports
Sharp tier ($29.99/mo): Custom alerts, API access
```

---

## 📋 Implementation Roadmap

### Week 1 — Infrastructure (DONE ✅)
- [x] 13/13 diagnostic tests passing
- [x] BKN + DET added to NBA roster
- [x] DK override wired into dashboard
- [x] Injury Report tab built (Streamlit + React)
- [x] Automations cleared

### Week 2 — Live Data MVP
- [ ] Get The Odds API key → [Add to Zo secrets](/?t=settings&s=advanced)
- [ ] Wire injury_scraper.py into daily_tip_report.py
- [ ] Create daily automation: 4 PM ET, run daily_tip_report.py --all
- [ ] Test on real NBA game

### Week 3 — Multi-Sport
- [ ] Wire multi_sport_engine.py into Streamlit sport selector
- [ ] Add MLB Poisson calculator to dashboard
- [ ] Add NCAAB Massey calculator
- [ ] Test all 5 sports

### Week 4 — Report + Email
- [ ] Finish plain-English report integration
- [ ] Configure SendGrid for email delivery
- [ ] Test full email delivery to tysondepina99@gmail.com

### Week 5 — NFL + Polish
- [ ] Integrate Tyson

's NFL template
- [ ] WNBA roster update (verify 15 teams)
- [ ] Final UX polish on Streamlit

### Week 6 — Market Pitch
- [ ] One-page pitch deck (Google Slides)
- [ ] Demo video (Loom, 3 min)
- [ ] Investor deck PDF

---

## 📁 Key Files Reference

| File | Purpose |
|------|---------|
| `nba_tc_pipeline.py` | NBA/WNBA TC engine (1147 lines, 13/13 ✅) |
| `SportsTC_Streamlit_App.py` | Main dashboard (579 lines) |
| `multi_sport_engine.py` | MLB + NHL algorithms |
| `college_models.py` | NCAAB + NCAAF algorithms |
| `xmins_engine.py` | Expected minutes model |
| `injury_scraper.py` | Live injury data |
| `generate_report.py` | Plain-English report generator |
| `daily_tip_report.py` | Daily automation script |
| `SPORTS_MODEL_SPEC.md` | Full algorithm documentation |
| `/nba-tc` (zo.space) | Public React dashboard |

---

## 💰 Revenue Model

| Tier | Price | Features |
|------|-------|---------|
| Free | $0 | 3 NBA props/day, no multi-sport |
| Pro | $9.99/mo | Unlimited props, all sports, email reports |
| Sharp | $29.99/mo | API access, custom alerts, Telegram |
| B2B | $99/mo | White-label, 5 seats, data export |

---

## 🎯 What Tyson Needs to Provide

1. **NFL template file** → upload to workspace, I'll integrate
2. **The Odds API key** → add to [Zo secrets](/?t=settings&s=advanced) as `ODDS_API_KEY`
3. **SendGrid API key** → add as `SENDGRID_API_KEY` for email
4. **Which sport to prioritize first** → NBA or WNBA?

---

*This document is the source of truth for the SportsBet AI build.*
