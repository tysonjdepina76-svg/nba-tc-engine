# Crypto Leverage Sentinel

Real-time risk daemon for high-leverage BTC positions. Runs in `/home/workspace/crypto_sentinel/`.

## What it does

1. Reads your watched position from `position_state.json` (entry, leverage, side)
2. Fetches live BTC spot (Coinbase → CoinGecko → Binance fallback chain)
3. Fetches live BTC implied volatility (Deribit DVOL → CME BVI → baseline fallback)
4. Computes liquidation price, distance to liquidation, unrealized P&L, a volatility-aware recommended stop
5. Classifies the regime as `STABLE` / `ELEVATED` / `CRITICAL`
6. Decides alert routing: emergency SMS if `distance ≤ 1.5%`, email if CRITICAL/ELEVATED, log-only if STABLE
7. Persists `last_metrics.json` (latest) and `run_history.jsonl` (time series)
8. Auto-refreshes every 5 minutes via [Automations](/?t=automations); escalates to 60-second loop on CRITICAL

## Live surfaces

| URL | Purpose | Access |
|---|---|---|
| `https://true.zo.space/sentinel` | Real-time dashboard with sparkline + emergency banner | Public |
| `https://true.zo.space/api/sentinel` | JSON snapshot + last 288 runs (24h) | Public |
| `https://true.zo.space/api/sentinel-email-alert` | Trigger email alert (only fires when distance ≤ 1.5%) | Public |

## Files

| File | Role |
|---|---|
| `leverage_check.py` | Risk daemon — pure functions + live IO. ~370 lines. |
| `controller.sh` | Cadence decision — emits `{"cadence": "5m"\|"60s", ...}` for the automation runner. |
| `position_state.json` | Your active position. Edit this to change the watched trade. |
| `last_metrics.json` | Latest run (written by daemon, read by dashboard). |
| `run_history.jsonl` | Append-only history (one JSON line per run). |
| `sentinel.log` | Local append-only log. |
| `AGENTS.md` | Agent rules: schedule, throttling, emergency broadcast. |
| `test_sentinel.py` | Unit tests. **18 tests, all passing.** |
| `Makefile` | Convenience: `make run`, `make test`, `make watch`, `make clean`. |
| `archive/2026-06-02-baseline/` | Pre-cleanup snapshots of all original files. |

## Run it

```bash
cd /home/workspace/crypto_sentinel
make test      # unit tests
make run       # one risk check
make watch     # loop every 60s, prints cadence each tick
make controller  # one controller tick
```

## Change your watched position

Edit `position_state.json`:

```json
{
  "entry_price": 70250.00,
  "leverage": 20,
  "position_type": "short"
}
```

Valid `position_type`: `short` or `long`. The daemon will pick up the change on the next 5-minute tick.

## Alert thresholds

| Status | Trigger | Channel |
|---|---|---|
| `MARGIN_HAZARD` | `distance_to_liq_percent ≤ 1.5` | SMS (email in sandbox) |
| `CRITICAL` | DVOL > 80 | Email |
| `ELEVATED` | DVOL 60–80 | Email |
| `STABLE` | DVOL < 60 | Log only |

The automation rule fires every 5 minutes; on `CRITICAL` the controller switches to 60s until `STABLE` returns.

## Data sources

- **Spot:** Coinbase (primary) → CoinGecko (fallback) → Binance (final fallback)
- **Volatility:** Deribit DVOL (primary, live 30-day implied vol) → CME CF BVI (fallback) → 45.0 baseline (last resort)

## Privacy

`position_state.json` and `run_history.jsonl` are in your workspace (not on zo.space). The dashboard API exposes position data publicly because the route is public — lock it down to owner-only in [Space settings](/?t=space) if you want to keep your position private.
