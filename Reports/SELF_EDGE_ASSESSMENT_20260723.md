# TC Self-Edge Backtest Assessment — 2026-07-23
**Professor's Report | Target: Positive Expected Value**

---

## 1. WHAT WE ACTUALLY HAVE (Not What We Wish We Had)

### WNBA Self-Edge: 84 Picks, One Day, One Direction

| Metric | Value |
|---|---|
| Total picks | 84 |
| Hits | 51 |
| Misses | 33 |
| **Hit Rate** | **60.7%** |
| Profit (flat $1/unit) | **+$18.00** |
| ROI | **+21.4%** |
| Direction | 100% UNDER |

### By Stat Category

| Stat | Picks | Hit Rate | Profit |
|---|---|---|---|
| PTS | 21 | **66.7%** | +$7 |
| P+R | 21 | **66.7%** | +$7 |
| P+A | 21 | 57.1% | +$3 |
| P+R+A | 21 | 52.4% | +$1 |

### The Player Split Is Brutal

**11 players went 4-for-4 (100%)**: Cheyenne Parker, Diamond DeShields, Brionna Jones, Diana Taurasi, Marina Mabrey, Kelsey Plum, Lexie Brown, Natasha Howard, Satou Sabally, Skylar Diggins-Smith, Teaira McCowan

**7 players went 0-for-4 (0%)**: Allisha Gray, Brittney Griner, DeWanna Bonner, Kahleah Copper, Arike Ogunbowale, Azura Stevens, Dearica Hamby

**2 players split 2-2 (50%)**: Alyssa Thomas, Jordin Canada

**1 player went 3-1 (75%)**: Rhyne Howard

---

## 2. THE UNCOMFORTABLE TRUTHS

### Truth #1: One Day Is Not A Backtest
84 picks from a single day. That's a snapshot, not a track record. The model looks great against Chicago and Phoenix on July 19th. We have no idea what it does against Las Vegas, New York, or Minnesota. Zero data.

### Truth #2: You Can't Only Bet UNDERS
Every single pick was UNDER. The self-edge math is generating projections below the line for every player-stat combination. That's a broken distribution — in a fair model, you'd see a mix of OVER and UNDER signals. This isn't insight; it's a systematic bias toward projecting low. If the model can't find a single OVER worth betting, it's not seeing the full picture.

### Truth #3: The Superstar Problem
The seven 0-for-4 players are the league's elite: Arike Ogunbowale, Kahleah Copper, Brittney Griner, DeWanna Bonner. The model projected them UNDER, and they all went OVER. The self-edge math doesn't distinguish between role players and All-Stars. It treats Cheyenne Parker the same as Arike Ogunbowale, and that's why it gets crushed on the stars.

### Truth #4: Marginal Edges
Every edge is between 0.7 and 1.1 points. That's thin. Professional betting models target edges of 3%+ of the line. A 0.7-point edge on a 14.2-point line is ~4.9% — borderline. The model is finding value, but it's not finding a lot of it.

### Truth #5: MLB Is Dead
Zero MLB picks have actual outcomes matched to non-zero lines. Without a working odds source, the MLB pipeline produces picks with market_line=0, and those can't be backtested. The Odds API Business tier is maxed out. SportsDataIO key is dead. ESPN doesn't give player props on the free tier.

---

## 3. CAN YOU BEAT THEM?

Short answer: **60.7% on a single day is promising, but it's not proof.**

Long answer: Here's what has to be true for this to work at scale:

1. **The 60.7% needs to hold across 500+ picks.** If it drops to 55% with real volume, you're still profitable (breakeven on standard -110 odds is ~52.4%), but the edge shrinks dramatically.

2. **Direction balance needs to exist.** A model that only bets UNDER is a model that doesn't understand offense. You need OVER candidates too.

3. **The star-player adjustment needs to be built.** The 0-for-4 players aren't random misses — they're a systematic failure mode. Fix that and the hit rate jumps from 60.7% to ~70%+.

4. **You need more sports working.** WNBA alone isn't enough volume. MLB was supposed to be the volume driver.

---

## 4. THE GAME PLAN: BUILD THE DESTINATION

You sent a blueprint that's fundamentally right. Here's what it looks like applied to what we actually have:

### Phase 1: Stabilize The Engine (This Week)

**Fix the UNDER-only bias.** The `tc_math.py` self-edge function needs to generate projections that can land on either side of the line. Right now every projection is below the market line. That's a math bug, not a market insight.

**Grade the MLB picks we can grade.** Even without live odds, we have some picks where actuals are available. Let's identify which ones are gradeable and get real numbers.

**Build the second data point.** The next WNBA game day, run the pipeline and capture results. One day is a snapshot. Two days is a trend.

### Phase 2: Generate Insights, Not Just Picks (Next 2 Weeks)

This is where your blueprint shines. Instead of outputting "Arike Ogunbowale UNDER 20.5 PTS," output:

> "Arike Ogunbowale has gone OVER her points line in 9 of her last 11 games. The TC model projects 18.2 — a 12% edge to the UNDER. But the trend is screaming OVER. This is a high-risk fade."

That's content. That's what keeps people coming back — the tension between what the model says and what the trend shows.

**Add a daily written report.** One markdown file per day. Picks, context, reasoning in plain English. This becomes your publication.

**Track streaks, not just picks.** "Jordin Canada has gone UNDER in 6 straight P+A lines" is much stickier than "Jordin Canada UNDER 18.5 P+A (Edge: 5%)."

### Phase 3: The Zero-Friction Web Presence (Month 1)

**Static site on Vercel (free).** GitHub Actions runs daily_picks.py, generates a static HTML report, commits it to the repo, Vercel deploys automatically. Zero server cost.

**No sign-ups, no accounts.** A simple page with today's picks, yesterday's results, all-time stats. People bookmark it and check it daily.

**"Community Consensus" widget.** Let people vote OVER/UNDER on each pick. Aggregate the votes. Now you have a data flywheel — you can compare your model against the crowd.

### Phase 4: Expand Volume (When Odds API Resets)

When you get a working odds source back:
- MLB player props (the volume driver — 10+ games/day, 100+ props)
- WNBA daily (4-8 games/day during season)
- NBA when season starts (October)

---

## 5. THE HONEST ANSWER ABOUT GITHUB SOURCES

The free API aggregator (`free_api_aggregator.py`) uses:
- **statsapi.mlb.com** — MLB stats (no props, no lines)
- **pybaseball** — MLB stats library (no props, no lines)
- **nba_api** — NBA stats (off-season)

None of these provide betting lines or player props. That's the whole problem. **Player prop odds are a paid product.** ESPN gives game lines for free but not player props. DraftKings/FanDuel don't have public APIs. The Odds API is the cheapest option at ~$99/month for the tier that includes player props.

**The self-edge approach IS the GitHub-source solution.** When you can't get market lines, you generate your own projections and compare them against your own edge thresholds. That's exactly what the 60.7% backtest represents — a self-contained system that doesn't need external odds.

---

## 6. BOTTOM LINE

| Question | Answer |
|---|---|
| Is 60.7% real? | Yes, on 84 picks from one day. |
| Is it sustainable? | Unknown. Needs 500+ picks across multiple days. |
| Can you beat the market? | Too early to tell. The math is promising but the sample is tiny and the UNDER-only bias is a red flag. |
| Should you build the media destination? | Yes. The blueprint you sent is smarter than trying to compete on betting infrastructure. |
| What's the single biggest fix? | Fix the direction bias. A model that only bets UNDER isn't a model — it's a systematic lowball. |

---

*Generated: 2026-07-23 22:45 ET | TC Pipeline Professor's Assessment*
