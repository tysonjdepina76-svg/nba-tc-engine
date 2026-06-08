# WNBA Backtest Archive

This archive holds WNBA TC backtest reports and CSV data. Each run
corresponds to a single day's full pipeline output.

## Files

- `wnba_backtest_report_v3_tpm_20260607.md` — initial 4-day backtest (06-04 to 06-07) with per-stat CONS tuning and TPM/3PM fix
- `wnba_backtest_report_v3_tpm_20260607.docx` — same, DOCX
- `wnba_pipeline_v2_14day_20260608.md` — 14-day backtest (05-25 to 06-08) with starter gate, pace, B2B adjustments. **2882 picks, 47.0% hit rate.**
- `wnba_pipeline_v2_14day_20260608.docx` — same, DOCX

## How to regenerate

```bash
# 4-day quick backtest
cd /home/workspace
python3 /home/.z/workspaces/con_OB12KUuZU4i7gF7u/pull_recent_boxscores.py
python3 /home/.z/workspaces/con_OB12KUuZU4i7gF7u/append_suggestions.py

# 14-day full backtest
python3 /home/workspace/Projects/wnba_pipeline_v2.py --days 14
```

## Key results

- REB is the strongest stat (54.7% hit rate)
- PTS and AST also above 50%
- BLK is unreliable (29%) — skip in WNBA
- 47.0% overall is the baseline; production model has additional filters (injuries, market line, prop lines)
