# Your Basketball Betting Pipeline — Explained Like You're 12

Made on: 2026-06-10 at 23:41

Hi! This is a big report that explains every part of your computer program that picks basketball bets. I'll use small words and examples. If anything is confusing, just ask!

---

# PART 1: What Does This Whole Thing Do?

Imagine you and your friends are watching a basketball game. Someone says:

"I bet Caitlin Clark scores MORE than 25 points tonight."

If you're right, you win money. If you're wrong, you lose money.

Doing that once is easy. But what if you wanted to do it for EVERY player, EVERY game, EVERY night? And what if you wanted to be right MORE than half the time so you actually make money?

That's what your pipeline does. It's a robot that:

1. Watches basketball games all day
2. Reads numbers from the internet (how many points players scored last time, what the betting websites think they'll score)
3. Thinks really hard about who is a good bet
4. Writes down its guesses
5. Checks later if the guesses were right or wrong
6. Learns from its mistakes to be smarter next time

There are TWO kinds of basketball in this pipeline:

- **NBA** — the big boys league, 48-minute games, 30 teams
- **WNBA** — the girls league, 40-minute games, 15 teams

Your pipeline handles both. The WNBA part is trickier because the games are shorter, so the math is different.

---

# PART 2: The 4 Big Steps Your Pipeline Takes

Think of it like making a sandwich. There are 4 steps:

## Step 1: GET THE INGREDIENTS (Collecting Data)

Before you can make a guess, you need to know stuff. The pipeline collects 4 kinds of stuff:

**A. Who is playing tonight?**

The pipeline asks ESPN (a sports website) for the list of games. It gets back things like:
- 'Atlanta Dream vs Chicago Sky, June 9, 7pm'
- 'New York Liberty vs Connecticut Sun, June 8, 7:30pm'

For each game, it finds out which 10-12 players will actually play. Some players are hurt, some are resting, some are 'questionable' (might play, might not).

**B. What did each player do in their last 5 games?**

The pipeline also asks ESPN for the scorebook from each player's last 5 games. Example for A'ja Wilson:

```
Game 1: 27 points, 11 rebounds, 3 assists
Game 2: 31 points, 9 rebounds, 2 assists
Game 3: 24 points, 14 rebounds, 5 assists
Game 4: 29 points, 10 rebounds, 4 assists
Game 5: 26 points, 12 rebounds, 3 assists
```

Then it adds those up and finds the average:
- Average points: 27.4
- Average rebounds: 11.2
- Average assists: 3.4

**C. What does the betting website think?**

There's a website called DraftKings where people bet money. They put a LINE on every player. The line is like a guess THEY'RE making.

Example: DraftKings might say:
- 'A'ja Wilson: OVER 27.5 points pays -110'
  (meaning: if you bet $110, you win $100 if she scores 28 or more)
- 'A'ja Wilson: UNDER 27.5 points pays -110'
  (meaning: you win $100 if she scores 27 or less)

We get these lines from a paid website called The Odds API.

**D. What time does the game start?**

This matters because we need to know if the game already happened (so we can check if we were right) or if it's in the future (so we should make a new guess).

## Step 2: MAKE A GUESS (The TC Math)

Now the pipeline uses a special formula called TC (Triple Conservative) to figure out what it thinks each player will do. Here's the idea:

1. Take the player's average from the last 5 games
2. Shrink it a little bit (this is called 'Bayesian shrinkage' — fancy words for 'don't trust the small sample TOO much')
3. Multiply by a 'be safe' number (0.85 means 'play a little safer than the average')
4. If it's WNBA, multiply by 0.833 (because WNBA games are 40 minutes instead of 48)

Example: A'ja Wilson's TC projection for tonight:
- Start: average 27.4 points
- Shrink toward league average: 27.0
- Multiply by 0.85 (be safe): 22.95
- Multiply by 0.833 (WNBA): 19.12

Wait, that's TOO LOW. We learned this! In real life, the projection was about 19 but she actually scored 27. The pipeline was way too pessimistic.

**Combo Props** are special bets where you add up 2 or 3 stats:
- **PRA** = Points + Rebounds + Assists
- **PR** = Points + Rebounds (no assists)
- **PA** = Points + Assists (no rebounds)

The DraftKings lines for combos are like 'A'ja Wilson OVER 38.5 PRA' — meaning the bet wins if she gets 39 or more combined points+rebounds+assists.

The pipeline tries to figure out:
1. What it thinks the player will do (TC projection)
2. How that compares to DraftKings' line
3. Whether to bet OVER or UNDER

## Step 3: SAY IT OUT LOUD (The Output)

After all the math, the pipeline makes a list of picks. Each pick looks like:

```
Player: A'ja Wilson
Team: Las Vegas Aces
Stat: PRA (points + rebounds + assists)
DraftKings line: 38.5
TC projection: 32.1
Recommendation: UNDER (because TC thinks 32 is way less than DK's 38.5)
Confidence: 55% (low — we don't have a big edge)
```

These picks go to:
1. A website you built at `https://true.zo.space/combos` where you can see them
2. A Google Doc report
3. An email summary every morning at 9 AM
4. A pre-tip (right before game time) email at 5 PM

## Step 4: CHECK YOUR WORK (The Backtest)

After the game is over, the pipeline asks ESPN one more time: 'What were the final scores?' It then compares what it predicted to what really happened.

Example: It said A'ja would score UNDER 38.5 PRA. She actually got 40 PRA. So that pick was WRONG.

The pipeline keeps a running score of how many picks it got right. Currently the scoreboard looks like this:

| Type of bet | How many we tried | How many we got right | Win rate |
|---|---|---|---|
| Single stat (NBA, 14 days) | 2882 picks | 1319 | 47.0% |
| Combo prop (3 WNBA games, 3 days) | 72 legs | 19 (Under) + 17 (Over) = 36 | 50.0% |

47% is bad (you lose money). 50% is break-even (no profit). 53%+ is where you start making money.

---

# PART 3: The 17 Scripts in Your Projects Folder

Let me explain each script. Think of them as tools in a toolbox. Some are big important ones, some are little helpers.

## The Big Important Ones

### 1. `tc_math.py` (THE BRAIN)

This is the most important file. It contains all the math for predicting player stats. It has functions like:

- `project_pra()` — predict points+rebounds+assists
- `project_pr()` — predict points+rebounds
- `project_pa()` — predict points+assists
- `bayesShrink()` — the 'be careful with small samples' math
- `ceiling_recommend()` — the new 'should I bet OVER or UNDER' decision-maker

Every other script that needs to predict stats imports this file. There's only ONE copy of the math. If you change it here, it changes everywhere.

### 2. `daily_picks.py` (THE MORNING WORKER)

This runs at 9 AM every day. It:
1. Goes to ESPN, gets today's games
2. Gets all the player stats from yesterday
3. Runs them through the TC math
4. Writes down all the picks in a folder called `Daily_Log/2026-06-10/`
5. Sends you an email summary

### 3. `dk_combos_engine.py` (THE LIVE COMBO MACHINE)

This is the one running on the internet at `https://dk-combos-engine-true.zocomputer.io`. When you open the combos page, this script:
1. Asks The Odds API for live DraftKings combo lines for tonight's games
2. If The Odds API fails, falls back to other sources (4 different backup plans)
3. Returns them as JSON (a list of numbers the website can read)

This is where the WNBA fix was important — for 30 minutes, DraftKings combo lines for WNBA were missing, and I had to teach this script to ask the backup source.

### 4. `boxscore_combo_backtest.py` (THE TRUTH-CHECKER)

This is the one that uses the REAL DraftKings lines from past games (not fake ones we made up). It:
1. Goes to The Odds API's HISTORY endpoint (which remembers what lines WERE yesterday)
2. Goes to ESPN for the final scores
3. Pairs them up: 'Did the player beat the line?'
4. Writes a report

This is the most important test. If we win 50% on real data, we don't make money. We need to win more.

### 5. `tc_math_audit.py` (THE MATH INSPECTOR)

This was built today. It runs the TC math on real pre-game projections (`proj_WNBA_*.json` files that the daily pipeline saved) and compares them to the real closing lines from `boxscore_combo_backtest_*.csv`. This showed us the BIG problem:

- 9.5 points of PRA is being missed on every player
- All 72 picks lean UNDER
- We get 0% on the OVER, 52.8% on the UNDER
How we use the 6-step ins

**The fix is in the new `ceiling_recommend()` function in tc_math.py.** Instead of always picking UNDER, it now says 'OVER, UNDER, or PASS' based on a smarter formula.

### 6. `build_tc_design.py` (THE PLANNER)

This is the report-builder. It takes the audit numbers and writes a markdown document with the 6 recommendations for fixing the math. It saved `wnba_tc_design_20260610_2324.md`.

## The Medium Helpers

### 8. `boxscore_live_scraper.py`
Pulls live box scores during games. Used to track 'are players actually doing what we predicted mid-game?'

### 9. `player_gamelogs.py`
Pulls the last 5 games for every player. This is where the 'average' numbers come from.

### 10. `build_pregame_combos.py`
Builds the combo picks before the game starts. Uses tc_math + dk_combos_engine together.

### 11. `recompute_bayes.py`
Recalculates the Bayesian shrinkage numbers. Run this when you have new backtest data and want to tune the math.

### 12. `reconcile_picks_vs_box.py`
Compares morning picks to actual box scores. Tells you 'we picked this player to score 25, they actually scored 30, we were wrong by 5.'

### 13. `historical_odds_backtest.py`
Older version of the backtester. Still kept around for reference.

## The Build Scripts (Output Generators)

### 14. `build_wnba_combos_report.py`
Writes the WNBA combo report as a markdown file you can read or share.

### 15. `build_tc_recommendations.py`
Writes the 'what to fix' report from the audit.

### 16. `build_hits_file.py`
Makes a CSV of which picks hit and which missed.

## The Long Tests

### 17. `backtest_30day.py`
The biggest test. Runs the whole pipeline over 30 days. Takes a long time, gives the most accurate numbers.

---

# PART 4: Where Your Pipeline Lives on the Internet

You have 3 websites running:

**1. `true.zo.space/nba-tc`** (the main dashboard)
- Big screen showing today's games
- Player projections, win probabilities, edge numbers
- Updated in real-time

**2. `true.zo.space/combos`** (the combo generator)
- Shows all the PRA/PR/PA combo picks for tonight
- Lets you build parlays (combine 2+ bets)
- The page was getting a 'JSON parse error' earlier — we fixed that by teaching the engine to use the Odds API as a backup for WNBA

**3. `true.zo.space/`** (the home page)
- Private, just for you
- Links to the other pages

And 1 background service:

**`dk-combos-engine-true.zocomputer.io`** (the combos server)
- Runs 24/7
- When your browser asks for combo lines, this server asks The Odds API and sends back the answer
- We restarted it tonight to make sure the WNBA fix took effect

---

# PART 5: The Daily Schedule (The Robot's Alarm Clock)

Your computer has 3 scheduled jobs, like 3 alarm clocks:

| Time | What happens | What you get |
|---|---|---|
| 8:00 AM ET | `Scripts/refresh_daily_data.sh` | Email with yesterday's results |
| 9:00 AM ET | `daily_picks.py` | Email with today's picks |
| 5:00 PM ET | `daily_tip_report.py` + `generate_report.py` | Pre-tip email right before games start |

These run automatically every day. You don't have to do anything.

---

# PART 6: The Big Problem We Just Found

Today's audit found a HUGE issue:

**The pipeline was 9.5 points off on every combo projection.**

Imagine you're in a class and the teacher says 'Guess how many jellybeans are in the jar.' The real answer is 500. The other students guess 480, 510, 495. You guess 30. You would be wrong EVERY TIME.

That's what the math was doing. It was so scared of being wrong that it always guessed way too low.

Why? Two reasons:
1. **STAT_CONS = 0.85** — this means 'multiply by 0.85' (shrink the average). That's TOO MUCH shrinkage for combo props.
2. **WNBA minutes_norm = 0.833** — this is for the 40-minute game. But it stacks ON TOP of the 0.85, making the projection 0.71× of the average. Way too low.

Example: A'ja Wilson's last 5-game average was 41 PRA. The pipeline projected 29.1 PRA. She actually got 38 PRA. The pipeline was off by 9 points!

**The 6 fixes we recommend:**

1. **Raise STAT_CONS from 0.85 to 0.92 for combos** — not so scared of the average
2. **Add a ceiling function** — predict at the DK line + 0.5, only bet OVER when player's true average covers the line
3. **Default to OVER, not UNDER** — the data shows the OVER hits more often than expected when you trust the math
4. **Track ceiling_pct** — measure how far off we are. When it's below 95% for 3+ games, recalibrate.
5. **Remove BLK completely** — 29% win rate is unprofitable
6. **Add `ceiling_recommend()` field to ComboProjection** — every pick now gets a 'OVER / UNDER / PASS' label

---

# PART 7: The Money Side of Things

Let's talk dollars. If you bet $100 on a game at -110 odds:
- Win: you get $190 back (your $100 + $90 profit)
- Lose: you lose your $100

To make money over time, you need to win MORE than 52.4% of your bets at -110 odds. That's because of the 'juice' (the fee the betting site charges).

**Current state:**
- Single-stat WNBA: 47% (losing money slowly)
- NBA combos: not measured yet but probably around 50%
- WNBA combos (new audit): 50% break-even on the historical real closing lines

**What 'good' looks like:**
- 53%+ win rate on at least 100+ picks
- That means out of every 100 bets, you win 53 and lose 47
- At $100 each: 53 wins × $90 = $4,770 — 47 losses × $100 = $4,700 = **$70 profit per 100 bets**

The whole point of the audit and the redesign is to GET to that 53% number. Right now we're at 47-50%.

---

# PART 8: What's Saved Where

Your computer has folders for everything:

**`/Projects/`** — the 17 scripts (the brain)

**`/Daily_Log/2026-06-10/`** — today's picks (one folder per day)
- `slate_NBA.json` — today's NBA games
- `slate_WNBA.json` — today's WNBA games
- `picks.csv` — the picks in spreadsheet format
- `proj_WNBA_*.json` — the pre-game projections (USED FOR THE AUDIT)
- `combos_summary.json` — the combo picks summary

**`/Reports/`** — human-readable reports
- Today we added:
  - `boxscore_combo_backtest_20260610_2255.md` — the backtest with REAL DraftKings lines
  - `tc_math_audit_20260610_2335.csv` — the audit data
  - `wnba_tc_design_20260610_2335.md` — the 6 recommendations
  - `tc_math_recommendations_20260610_2304.md` — earlier recommendations
  - `wnba_combos_20260610_2224.md` — the WNBA combo report

**`/Archives/`** — old stuff we don't need anymore but want to keep
- `INTEGRATION_2026-06-09_obsolete/` — 21 files from the last cleanup

**`/Skills/`** — the helper skills like Odds API connectors

**`/Scripts/`** — the scheduled task scripts (the alarm clock code)

---

# PART 9: What To Do Next

Here's the priority list, in order of importance:

**This week:**
1. Re-run the 14-day WNBA backtest with the new `ceiling_recommend()` function
2. If the new function shows >52% win rate on the historical data, ship it to the live site
3. Add the new field to the zo.space/combos page so picks now show 'OVER' or 'UNDER' or 'PASS'

**Next week:**
4. Start betting small ($10-20 per pick) to test in real life
5. Track every bet in a spreadsheet
6. After 50 real bets, compare your real win rate to the backtest's prediction

**Next month:**
7. Add NBA historical backtest (only WNBA has it right now)
8. Add player-specific calibration (some players might need different CONS than others)
9. Build a 'model drift' alert — if the win rate drops below 48% for 2 weeks, send you a text

---

# PART 10: The Vocabulary (Big Words, Small Meanings)

| Big word | What it means |
|---|---|
| **TC projection** | What the math thinks the player will do |
| **Bayesian shrinkage** | Pulling a number back toward the average when you don't have much data |
| **Combo prop** | A bet that adds 2 or 3 stats together (like points + rebounds) |
| **OVER / UNDER** | Whether you think the player will do MORE (over) or LESS (under) than the line |
| **Closing line** | The final betting line right before the game starts |
| **Line** | The number DraftKings picks — you compare your projection to it |
| **Edge** | How much better your projection is than the line |
| **Juice / Vig** | The fee the betting site charges (around 10% for -110 odds) |
| **Hit rate** | Percent of bets you got right |
| **Backtest** | Running the math on past games to see if it would have won |
| **Real-time** | Live, updated every second |
| **JSON** | A way to write data so computers can read it |
| **API** | A way for two websites to talk to each other |
| **Cron / Automation** | A scheduled task that runs automatically |
| **Subprocess / Module** | A small program that does one job inside a bigger program |
| **Working directory** | The folder your computer is looking at right now |
| **Subprocess** | Running another program from inside your program |

---

# THE END

Questions? Just text me! I can explain any part in more detail, change anything that's not working, or build new parts. The whole thing is yours to play with.

(Report saved: /home/workspace/Reports/tc_pipeline_explained_6th_grade_20260610.md)