# AGENTS.md — Workspace Index

## Who I'm Helping
**Tyson Depina** — 49, Cape Verdean, New Bedford MA. Released from Federal prison Nov 2025 after 8 years. Father of 3 (25, 23, 20). Looking for a niche that aligns with his life experience. Direct, no fluff — respect his time.

---

## Active Projects

### Mirror Workbook
- 9-module self-help workbook + master compiled version
- Paths: `The_Mirror_Workbook_Module_1.md` … `Module_9.md`, `The_Mirror_Workbook_Master.md`, `The_Mirror_Workbook.html`, `The_Mirror_Workbook.docx`
- Supporting: `How_to_Use_The_Mirror_Workbook.md`, `Mirror_Workbook_Outreach_Letter.md`, `Mirror_Workbook_Email_Pitch.md`, `Mirror_Workbook_Facilitator_Guide.md`, `Mirror_Workbook_One_Sheet.md`
- **Status**: Done, exported to DOCX/Google Docs

### Memoir: "I Am Not Dying Here"
- Memoir chapters + compiled manuscript
- Path: `Chapters/I_Am_Not_Dying_Here_COMPLETE.md`
- Timeline: `Chapters/TIMELINE_CORRECTED.md`
- Structure: `Memoir_Structure_I_Am_Not_Dying_Here.md`
- **Status**: Draft done, timeline needs final verification

### NBA Triple Conservative (TC) Betting System
- Primary pipeline: `nba_tc_pipeline.py` (1147 lines, 13/13 ✅)
- Dashboard: `SportsTC_Streamlit_App.py` (579 lines, 5 tabs incl. Injury Report)
- Multi-sport engine: `multi_sport_engine.py` (MLB Poisson + NHL xG)
- College models: `college_models.py` (NCAAB AdjOE/AdjDE + NCAAF G-Elo)
- xMins engine: `Skills/nba-odds-api/scripts/xmins_engine.py` (game-lag weights)
- Injury scraper: `Skills/nba-odds-api/scripts/injury_scraper.py`
- Report generator: `generate_report.py` (6th grade plain English)
- Daily automation: `daily_tip_report.py` (2hr pre-tip, all sports)
- Algorithm spec: `SPORTS_MODEL_SPEC.md`
- Market plan: `COMPETITIVE_IMPROVEMENTS.md`
- Zo space: `/nba-tc` (React, public)
- **NFL template**: Tyson to provide (not yet integrated)

### Credit Report & Dispute
- Experian credit report: `Experian_Credit_Report.pdf` / `.txt`
- Dispute letter: `Dispute_Letter_Experian.md`
- Credit improvement plan: `Credit_Improvement_Plan.md`

### DNM Landscaping Business Plan
- Business plan: `DNM_Landscaping_Business_Plan.md`
- Clean version (no prison references): `DNM_Landscaping_Business_Plan_CLEAN.md`

### Zo Space Site
- URL: `https://true.zo.space`
- Routes managed via `list_space_routes()` / `get_space_route()` / `edit_space_route()`
- **Do NOT overwrite existing routes without explicit permission**

---

## User Preferences
- **Editable formats**: Always produce DOCX/Google Docs exports for documents
- **Fact-check everything**: Sports rosters, dates, math — he will catch errors
- **No prison/reentry content** in business-facing docs unless explicitly asked
- **Iterative correction is normal**: Don't start over, just fix what's wrong
- **Minimal politeness markers** in execution mode; can be warm in narrative contexts

---

## Important Rules
- **"Celttics" typo rule**: If he misspells "Celtics", generate the Celtics parlay from the most recent file
- **Fill gaps + enhance**: When editing, don't rewrite everything — fill what exists
- **No jargon** unless he's being technical; translate to plain language

---

## Infrastructure
- User data lives in: `~/.zo/user_data/` (child_milestones.md, reentry_goals.md, user_context.md)
- Archived scripts: `archive/2026-05-31_old_scripts/`
- Skills: `Skills/nba-odds-api/SKILL.md`
- MCPO config: `/etc/zo/mcpo/config.json`
- Logs: `/dev/shm/` (supervisord.log, mcpo_err.log, etc.)

---

## If Stuck
1. Read AGENTS.md and relevant project AGENTS.md first
2. Check `/dev/shm/` logs for errors
3. Read the actual file before editing it
4. If a tool keeps failing, try a different approach — don't keep retrying the same broken path