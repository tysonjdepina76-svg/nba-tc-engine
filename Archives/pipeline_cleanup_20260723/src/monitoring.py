# src/monitoring.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
from fastapi import Response

REQUESTS = Counter('tc_requests_total', 'Total HTTP requests')
LATENCY = Histogram('tc_request_latency_seconds', 'Request latency')
PICKS_GENERATED = Counter('tc_picks_generated_total', 'Picks generated', ['sport'])
WIN_RATE = Gauge('tc_win_rate', 'Hit rate per sport', ['sport'])
DAILY_PROFIT = Gauge('tc_daily_profit', 'Daily profit')
SHARPE_RATIO = Gauge('tc_sharpe_ratio', 'Sharpe ratio')
MAX_DRAWDOWN = Gauge('tc_max_drawdown', 'Max drawdown')

# This file is already imported by the API and updated by the pipeline.
# To use, add middleware to count requests, etc.
