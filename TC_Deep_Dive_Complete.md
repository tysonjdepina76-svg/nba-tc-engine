# TC Full Deep-Dive — Local + Drive + Gmail
Generated: 2026-07-12 14:55 ET (UTC 18:55)
User: tysonjdepina76@gmail.com / tysondepina99@gmail.com

## 1. LOCAL TEMPLATE & ORIGINAL FILES

### /home/workspace/tc-sports-app/ (CLEAN TEMPLATE — original)
Built Jul 8-9 2026. This is the production template structure.

  • .github/workflows/ci.yml (719 bytes)
  • Dockerfile (177 bytes)
  • render.yaml (202 bytes)
  • src/__init__.py (0 bytes)
  • src/adapters/__init__.py (0 bytes)
  • src/adapters/oddsapi/__init__.py (400 bytes)
  • src/adapters/oddsapi/base.py (10,215 bytes)
  • src/adapters/oddsapi/mlb.py (747 bytes)
  • src/adapters/oddsapi/nba.py (723 bytes)
  • src/adapters/oddsapi/nfl.py (741 bytes)
  • src/adapters/oddsapi/nhl.py (758 bytes)
  • src/adapters/oddsapi/wnba.py (743 bytes)
  • src/adapters/sportsdataio/__init__.py (297 bytes)
  • src/adapters/sportsdataio/base.py (6,829 bytes)
  • src/adapters/sportsdataio/mlb.py (3,153 bytes)
  • src/adapters/sportsdataio/nfl.py (3,038 bytes)
  • src/adapters/sportsdataio/wnba.py (2,279 bytes)
  • src/adapters/sportsgameodds/__init__.py (322 bytes)
  • src/adapters/sportsgameodds/base.py (5,870 bytes)
  • src/adapters/sportsgameodds/mlb.py (435 bytes)
  • src/adapters/sportsgameodds/nba.py (325 bytes)
  • src/adapters/sportsgameodds/nfl.py (570 bytes)
  • src/adapters/sportsgameodds/nhl.py (338 bytes)
  • src/adapters/sportsgameodds/wnba.py (435 bytes)
  • src/api/__init__.py (0 bytes)
  • src/api/app.py (3,130 bytes)
  • src/cache/optimized_cache.py (4,134 bytes)
  • src/dashboard/__init__.py (0 bytes)
  • src/dashboard/tc_dashboard.py (10,481 bytes)
  • src/domain/__init__.py (0 bytes)
  • src/domain/combo_optimizer.py (4,872 bytes)
  • src/domain/combo_qualifier.py (2,281 bytes)
  • src/domain/entities.py (5,385 bytes)
  • src/domain/fantasy_images.py (12,790 bytes)
  • src/domain/market_line_provider.py (5,958 bytes)
  • src/domain/projection_service.py (8,505 bytes)
  • src/domain/roster_manager.py (2,647 bytes)
  • src/domain/services/__init__.py (0 bytes)
  • src/domain/services/backup_service.py (1,568 bytes)
  • src/domain/services/ownership_estimator.py (2,233 bytes)
  • src/domain/sport_config.py (7,878 bytes)
  • src/gates/live_poller.py (3,843 bytes)
  • src/monitoring/api_call_budget.py (6,325 bytes)
  • src/monitoring/odds_monitor.py (5,851 bytes)
  • src/services/event_trigger.py (3,634 bytes)
  • src/services/parlay_builder.py (8,705 bytes)
  • test_sdio_news.py (3,447 bytes)
  • tests/test_projection_service.py (2,397 bytes)

### /home/workspace/Projects-backup-20260708/ (FULL TC PIPELINE — Jul 8 backup)
This is the most complete snapshot of all original TC scripts.

  • api_cache.py (3,894 bytes)
  • api_fallback.py (10,323 bytes)
  • api_scan.py (4,789 bytes)
  • api_tc_unified.py (56,644 bytes)
  • backtest_30day.py (7,427 bytes)
  • backtest_pipeline.py (44,286 bytes)
  • boxscore_backfill.py (12,854 bytes)
  • boxscore_saver.py (20,480 bytes)
  • build_pregame_combos.py (26,154 bytes)
  • config/columns.py (3,421 bytes)
  • consensus_engine.py (32,532 bytes)
  • daily_picks.py (42,460 bytes)
  • dk_combos_engine.py (13,132 bytes)
  • fantasy_images.py (10,684 bytes)
  • inbox_forward_2026-06-17_1303.md (382 bytes)
  • mlb_sdio_props.py (5,735 bytes)
  • mlb_tc_engine.py (38,790 bytes)
  • multi_sport_backtest.py (6,125 bytes)
  • nfl_preseason_scheduler.py (1,134 bytes)
  • oddsapi_live_enabler.py (2,222 bytes)
  • pipeline_master.py (24,838 bytes)
  • render_backtest_report.py (2,625 bytes)
  • reports/images/WNBA_roundup_20260702_221449.png (47,819 bytes)
  • reports/images/WNBA_roundup_20260702_225449.png (47,819 bytes)
  • reports/images/WNBA_roundup_20260702_231137.png (47,819 bytes)
  • reports/images/WNBA_roundup_20260703_200738.png (26,292 bytes)
  • reports/images/WNBA_roundup_20260703_203546.png (26,292 bytes)
  • reports/images/WNBA_roundup_20260703_204302.png (26,292 bytes)
  • reports/images/WNBA_roundup_20260703_204515.png (26,292 bytes)
  • reports/images/WNBA_roundup_20260704_011510.png (26,173 bytes)
  • reports/images/WNBA_roundup_20260704_011936.png (26,173 bytes)
  • reports/images/WNBA_roundup_20260705_173818.png (27,905 bytes)
  • requirements.txt (381 bytes)
  • runtime_health_check.py (2,441 bytes)
  • soccer_boxscore_capture.py (12,626 bytes)
  • soccer_combo_engine.py (12,259 bytes)
  • soccer_tc_engine.py (44,560 bytes)
  • sources/__init__.py (883 bytes)
  • sources/line_fetcher.py (3,518 bytes)
  • sources/mlb_book_fetcher.py (12,787 bytes)
  • sources/mlb_fetcher.py (1,753 bytes)
  • sources/mlb_live_summary.py (53 bytes)
  • sources/odds_api_client.py (7,645 bytes)
  • sources/scrape (81 bytes)
  • sources/scrapers/__init__.py (877 bytes)
  • sources/scrapers/baseball_reference.py (7,001 bytes)
  • sources/scrapers/basketball_reference.py (3,237 bytes)
  • sources/scrapers/draftkings_web.py (5,747 bytes)
  • sources/scrapers/fangraphs.py (5,015 bytes)
  • sources/scrapers/soccer_projections.py (803 bytes)
  • sources/scrapers/soccer_roster_wiki.py (3,458 bytes)
  • sources/scrapers/team_ids.py (807 bytes)
  • sources/soccer_lines_fetcher.py (3,261 bytes)
  • sources/sports_registry.py (6,370 bytes)
  • sources/utils/cache.py (1,992 bytes)
  • sources/wnba_data_fetcher.py (5,672 bytes)
  • sources/wnba_lines_fetcher.py (2,267 bytes)
  • sports_registry.py (8,973 bytes)
  • src/adapters/__init__.py (639 bytes)
  • src/adapters/cache.py (2,797 bytes)
  • src/adapters/espn.py (2,165 bytes)
  • src/adapters/odds_api.py (2,157 bytes)
  • src/adapters/sgo.py (1,422 bytes)
  • src/domain/daily_picks.py (3,735 bytes)
  • src/domain/run_measured.py (2,151 bytes)
  • src/measure.py (4,744 bytes)
  • starter_detector.py (4,973 bytes)
  • tc_dashboard.py (60,140 bytes)
  • tc_unified.py (31,214 bytes)
  • team_game_mapper.py (9,780 bytes)
  • wc_backtest_recent.py (9,254 bytes)
  • wc_boxscore_backtest.py (8,804 bytes)
  • wc_filter_demo.py (2,309 bytes)
  • wc_projections.py (4,236 bytes)
  • wc_self_edge.py (10,121 bytes)
  • wc_tc_calibrate.py (3,059 bytes)
  • wc_tc_math.py (3,534 bytes)
  • wnba_backte (6,205 bytes)
  • wnba_backtest_full.py (6,205 bytes)
  • wnba_tc_engine.py (26,313 bytes)
  • worldcup_picks.py (27,562 bytes)

## 2. CURRENT /home/workspace/Projects/ (LIVE, modified through 7/12)

  • _add_helper.py                                907 bytes  07-11 19:10 UTC
  • _add_shrink.py                              1,185 bytes  07-11 19:26 UTC
  • alert_system.py                             3,417 bytes  07-10 18:14 UTC
  • api_cache.py                                3,894 bytes  06-29 23:27 UTC
  • api_fallback.py                            10,323 bytes  06-22 20:10 UTC
  • api_scan.py                                 4,789 bytes  06-27 16:16 UTC
  • api_tc_unified.py                          60,031 bytes  07-08 01:32 UTC
  • backtest_30day.py                           7,427 bytes  06-29 12:10 UTC
  • backtest_all_sports.py                      8,147 bytes  07-12 04:42 UTC
  • backtest_pipeline.py                       44,286 bytes  06-20 22:42 UTC
  • backtest_report.py                          1,178 bytes  07-11 22:31 UTC
  • boxscore_backfill.py                       12,854 bytes  06-18 04:36 UTC
  • boxscore_saver.py                          20,480 bytes  06-23 00:12 UTC
  • build_backtest_db.py                        4,713 bytes  07-11 22:32 UTC
  • build_pregame_combos.py                    26,154 bytes  06-30 04:13 UTC
  • cleanup.py                                  1,066 bytes  07-10 22:58 UTC
  • combo_builder.py                            5,398 bytes  07-12 00:40 UTC
  • consensus_engine.py                        33,913 bytes  07-12 00:41 UTC
  • daily_picks.py                             52,410 bytes  07-11 20:48 UTC
  • dk_combos_engine.py                        13,132 bytes  06-29 23:28 UTC
  • espn_odds_fallback.py                       5,488 bytes  07-12 02:13 UTC
  • fantasy_images.py                          11,101 bytes  07-09 21:35 UTC
  • grade_daily_picks.py                       11,485 bytes  07-11 22:44 UTC
  • health_check.py                             1,228 bytes  07-11 22:45 UTC
  • hit_rate_report.py                          2,433 bytes  07-12 02:44 UTC
  • manual_grade.py                             3,853 bytes  07-12 02:13 UTC
  • measure_daily_picks.py                      1,605 bytes  07-10 18:12 UTC
  • mlb_dashboard.py                            5,003 bytes  07-10 22:36 UTC
  • mlb_integration.py                          8,422 bytes  07-10 22:32 UTC
  • mlb_sdio_props.py                           5,735 bytes  06-27 16:40 UTC
  • mlb_tc_engine.py                           46,002 bytes  07-11 20:32 UTC
  • mock_lines.py                               4,436 bytes  07-11 17:16 UTC
  • multi_sport_backtest.py                     6,125 bytes  06-30 03:07 UTC
  • nfl_preseason_scheduler.py                  1,134 bytes  06-29 21:43 UTC
  • nfl_tc_engine.py                            3,618 bytes  07-12 03:48 UTC
  • oddsapi_live_enabler.py                     2,222 bytes  06-29 21:43 UTC
  • pipeline_master.py                         24,919 bytes  07-08 08:07 UTC
  • player_stats_scraper.py                     5,037 bytes  07-12 02:13 UTC
  • render_backtest_report.py                   2,625 bytes  06-30 03:07 UTC
  • report.py                                   2,165 bytes  07-10 23:25 UTC
  • run.py                                      1,982 bytes  07-12 03:27 UTC
  • run_mlb_pipeline.py                         1,148 bytes  07-10 18:14 UTC
  • runtime_health_check.py                     2,494 bytes  07-10 23:01 UTC
  • seed_test_bets.py                           1,559 bytes  07-10 23:36 UTC
  • settle_positions.py                         4,622 bytes  07-10 23:51 UTC
  • soccer_boxscore_capture.py                 12,626 bytes  07-07 23:58 UTC
  • soccer_combo_engine.py                     12,727 bytes  07-11 18:34 UTC
  • soccer_tc_engine.py                        44,901 bytes  07-11 17:39 UTC
  • sports_registry.py                          9,221 bytes  07-12 03:48 UTC
  • starter_detector.py                         4,973 bytes  06-29 22:24 UTC
  • tc_dashboard.py                            10,481 bytes  07-12 01:40 UTC
  • tc_dashboard_backup.py                      5,584 bytes  07-11 23:16 UTC
  • tc_dashboard_backup_20260712_011836.py     65,860 bytes  07-12 01:18 UTC
  • tc_dashboard_backup_20260712_012046.py     65,860 bytes  07-12 01:20 UTC
  • tc_math.py                                 10,280 bytes  07-12 02:11 UTC
  • tc_math_hybrid.py                          12,071 bytes  07-12 04:37 UTC
  • team_game_mapper.py                         9,780 bytes  06-19 03:13 UTC
  • wc_backtest_recent.py                       9,254 bytes  06-30 03:38 UTC
  • wc_boxscore_backtest.py                     8,804 bytes  06-16 22:01 UTC
  • wc_filter_demo.py                           2,309 bytes  06-30 04:11 UTC
  • wc_projections.py                           4,236 bytes  06-27 16:40 UTC
  • wc_self_edge.py                            10,121 bytes  06-19 19:39 UTC
  • wc_tc_calibrate.py                          3,059 bytes  06-27 16:40 UTC
  • wc_tc_math.py                               3,534 bytes  06-27 16:41 UTC
  • wnba_backtest_full.py                       6,205 bytes  06-30 04:24 UTC
  • wnba_tc_engine.py                          26,430 bytes  07-11 19:35 UTC
  • worldcup_picks.py                          27,562 bytes  06-24 02:01 UTC

## 3. ARCHIVES & DAILY LOG

Archives TC files: 1
  • archives/projects/tc_math.py

Daily_Log dates: ['halftime', 'live_props', 'mlb_boxscores', 'soccer', 'wc_boxscores', 'wc_historical', 'worldcup']

2026-07-12 contents:
  • combos_jpn_bra.json (125 bytes)
  • combos_jpn_bra.md (411 bytes)
  • combos_lv_ny.json (118 bytes)
  • combos_lv_ny.md (404 bytes)
  • combos_mar_ned.json (125 bytes)
  • combos_mar_ned.md (411 bytes)
  • combos_par_ger.json (125 bytes)
  • combos_par_ger.md (411 bytes)
  • combos_summary.json (646 bytes)
  • picks.json (81,306 bytes)
  • soccer_game_picks.csv (385 bytes)
  • soccer_game_picks.json (670 bytes)
  • soccer_player_picks.csv (36,822 bytes)
  • soccer_player_projs.json (210,522 bytes)
  • wnba_injuries.json (2 bytes)

## 4. GOOGLE DRIVE (tysondepina99@gmail.com)

Total files: 450 | Folders: 14 | TC-tagged: 84 | Sports-tagged: 35
Full inventory: see TC_Deep_Dive_Drive_Inventory.md

Key Drive folders & files:
  📁 voicemail-backup
  📁 (root TC docs, briefs, projections, backtest zips)

## 5. /home/workspace/Drive_Sync/ (TC deliverables to Drive)

  📁 TC_Desktop_Installer/
    • TC_Desktop_Installer/.local/share/applications/tc-app.desktop (237 bytes)
    • TC_Desktop_Installer/README.txt (1,829 bytes)
    • TC_Desktop_Installer/requirements.txt (35 bytes)
    • TC_Desktop_Installer/run_tc_app.sh (1,772 bytes)
  • TC_Desktop_Installer.zip (9,668 bytes)
  • TC_Integration_Report_20260601.md (5,209 bytes)
  • TC_Workspace_Full.zip (1,880,351 bytes)
  📁 Workbook/
    • Workbook/How_to_Use_The_Mirror_Workbook.md (938,798 bytes)
    • Workbook/How_to_Use_The_Mirror_Workbook_EDITABLE.docx (938,762 bytes)
    • Workbook/The_Mirror_Workbook.docx (938,753 bytes)
    • Workbook/The_Mirror_Workbook.gdoc (938,476 bytes)
    • Workbook/The_Mirror_Workbook.pdf (939,054 bytes)
    • Workbook/The_Mirror_Workbook_Edit_Log.md (938,523 bytes)
    • Workbook/The_Mirror_Workbook_Final.docx (939,904 bytes)
    • Workbook/The_Mirror_Workbook_Master.md (938,968 bytes)
    • Workbook/The_Mirror_Workbook_Master_v2.md (938,981 bytes)
    • Workbook/The_Mirror_Workbook_Updated_April_2026.docx (938,325 bytes)

## 6. GMAIL (tysondepina99@gmail.com)

40 TC-related messages found (search: TC/projections/picks/parlay × NBA/NFL/WNBA/sports)
Spans: 2026-06-30 → 2026-07-09
Gmail 76 (tysonjdepina76): NOT CONNECTED — needs inline widget authorization