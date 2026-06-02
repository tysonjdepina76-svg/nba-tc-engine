"""
Crypto Leverage Sentinel — risk daemon.

Reads a watched position from position_state.json, fetches live BTC spot and
Deribit DVOL volatility, computes liquidation distance and a volatility-aware
stop recommendation, classifies status, persists results for the dashboard,
and prints machine-readable JSON to stdout.

Modules:
    config        — paths, thresholds, alert routing
    feeds         — network IO with fallback chains
    math          — position, liquidation, P&L, status classification
    persistence   — last_metrics + run_history writers
    io_log        — timestamped local log
    classify      — alert decision (emergency / status-tiered)
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Optional, Tuple


# =====================================================================
# config
# =====================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, "position_state.json")
LOG_FILE = os.path.join(BASE_DIR, "sentinel.log")
LAST_METRICS_FILE = os.path.join(BASE_DIR, "last_metrics.json")
RUN_HISTORY_FILE = os.path.join(BASE_DIR, "run_history.jsonl")

# Volatility regime bands (DVOL percentage)
DVOL_STABLE_MAX = 60.0
DVOL_ELEVATED_MAX = 80.0

# Fraction of distance-to-liq to use as a recommended stop
STOP_COEFF_STABLE = 0.40
STOP_COEFF_ELEVATED = 0.25
STOP_COEFF_CRITICAL = 0.15

# Emergency broadcast threshold
EMERGENCY_LIQ_DISTANCE_PCT = 1.5

# Throttle state names (must match AGENTS.md)
THROTTLE_CRITICAL = "CRITICAL"
THROTTLE_STANDARD = "STABLE"

# Baseline fallback for volatility
DVOL_BASELINE_FALLBACK = 45.0

# HTTP timeout
HTTP_TIMEOUT_SEC = 5


# =====================================================================
# io_log
# =====================================================================

def log_event(message: str, level: str = "INFO") -> None:
    """Append a timestamped line to the local sentinel log. Never raises."""
    try:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] [{level}] {message}\n")
    except Exception:
        pass


# =====================================================================
# feeds
# =====================================================================

def http_get_json(url: str, timeout: int = HTTP_TIMEOUT_SEC) -> dict:
    """GET a URL and return parsed JSON. Raises on failure."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode())


# --- spot price (3-source fallback chain) ---

_SPOT_SOURCES: Tuple[Tuple[str, Callable[[dict], float]], ...] = (
    ("https://api.coinbase.com/v2/prices/BTC-USD/spot",
        lambda d: float(d["data"]["amount"])),
    ("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
        lambda d: float(d["bitcoin"]["usd"])),
    ("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
        lambda d: float(d["price"])),
)


def fetch_btc_spot() -> float:
    """Fetch BTC/USD spot from a 3-source fallback chain. Raises on total failure."""
    last_err: Optional[Exception] = None
    for url, parser in _SPOT_SOURCES:
        try:
            data = http_get_json(url)
            price = parser(data)
            log_event(f"Spot price fetched from {url}: {price}")
            return price
        except Exception as e:  # noqa: BLE001
            last_err = e
            log_event(f"Spot source failed ({url}): {e}", level="WARN")
    raise RuntimeError(f"All spot price sources failed: {last_err}")


def fetch_dvol() -> float:
    """
    Fetch Deribit DVOL (30-day implied volatility) using a 24h hourly window.
    Falls back to CME CF BVI, then a hardcoded baseline.
    """
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - (24 * 60 * 60 * 1000)
    dvol_url = (
        f"https://www.deribit.com/api/v2/public/get_volatility_index_data"
        f"?currency=BTC&start_timestamp={start_ms}"
        f"&end_timestamp={now_ms}&resolution=3600"
    )
    bvi_index_url = "https://api.cfbenchmarks.com/v1/indices/BVI"

    try:
        dvol_data = http_get_json(dvol_url)
        # Deribit: {"result": {"data": [[ts, open, high, low, close], ...]}}
        series = dvol_data.get("result", {}).get("data", [])
        if not series:
            raise ValueError("Deribit DVOL series empty")
        latest_close = float(series[-1][4])
        log_event(f"Deribit DVOL fetched: {latest_close}")
        return latest_close
    except Exception as e:  # noqa: BLE001
        log_event(f"Deribit DVOL failed ({e}), trying CME BVI", level="WARN")

    try:
        data = http_get_json(bvi_index_url)
        value = float(data["index_value"])
        log_event(f"CME BVI fetched: {value}")
        return value
    except Exception as e:  # noqa: BLE001
        log_event(f"CME BVI also failed, using baseline {DVOL_BASELINE_FALLBACK}: {e}",
                  level="WARN")
        return DVOL_BASELINE_FALLBACK


# =====================================================================
# math
# =====================================================================

@dataclass(frozen=True)
class Position:
    entry_price: float
    leverage: float
    position_type: str  # "short" | "long"

    def liquidation_price(self) -> float:
        """Liq price for isolated margin (ignores fees and maintenance margin)."""
        if self.position_type.lower() == "short":
            return self.entry_price * (1.0 + (1.0 / self.leverage))
        return self.entry_price * (1.0 - (1.0 / self.leverage))


@dataclass(frozen=True)
class RiskMetrics:
    status: str
    current_btc_price: float
    volatility_index: float
    liquidation_price: float
    distance_to_liq_percent: float
    unrealized_pnl_percent: float
    recommended_stop_percent: float
    timestamp: str


def classify_status(dvol: float) -> Tuple[str, float]:
    """
    Map DVOL to (status, stop_coefficient).
    STABLE:  dvol <= 60,  coeff 0.40
    ELEVATED: 60 < dvol <= 80,  coeff 0.25
    CRITICAL: dvol > 80,  coeff 0.15
    """
    if dvol > DVOL_ELEVATED_MAX:
        return THROTTLE_CRITICAL, STOP_COEFF_CRITICAL
    if dvol > DVOL_STABLE_MAX:
        return "ELEVATED", STOP_COEFF_ELEVATED
    return THROTTLE_STANDARD, STOP_COEFF_STABLE


def compute_metrics(
    position: Position,
    *,
    spot: Optional[float] = None,
    dvol: Optional[float] = None,
) -> RiskMetrics:
    """
    Compute risk metrics for a position.

    When `spot` and `dvol` are provided (e.g. by tests), the function is pure
    and side-effect-free. When omitted, the function performs live network
    fetches via the feeds module.
    """
    if spot is None:
        spot = fetch_btc_spot()
    if dvol is None:
        dvol = fetch_dvol()
    spot_price = spot
    dvol_value = dvol
    liq_price = position.liquidation_price()

    if position.position_type.lower() == "short":
        pnl = ((position.entry_price - spot_price) / position.entry_price) * position.leverage * 100
        distance_pct = ((liq_price - spot_price) / spot_price) * 100
    else:
        pnl = ((spot_price - position.entry_price) / position.entry_price) * position.leverage * 100
        distance_pct = ((spot_price - liq_price) / spot_price) * 100

    status, stop_coeff = classify_status(dvol_value)
    recommended_stop = max(0.0, distance_pct) * stop_coeff

    return RiskMetrics(
        status=status,
        current_btc_price=round(spot_price, 2),
        volatility_index=round(dvol_value, 2),
        liquidation_price=round(liq_price, 2),
        distance_to_liq_percent=round(distance_pct, 2),
        unrealized_pnl_percent=round(pnl, 2),
        recommended_stop_percent=round(recommended_stop, 2),
        timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


# =====================================================================
# classify
# =====================================================================

@dataclass(frozen=True)
class Alert:
    key: str
    channel: str
    message: str

    @property
    def is_emergency(self) -> bool:
        return self.key == "MARGIN_HAZARD"


def classify_alert(m: RiskMetrics) -> Alert:
    """Decide which alert (if any) this run triggers."""
    distance = m.distance_to_liq_percent

    if distance <= EMERGENCY_LIQ_DISTANCE_PCT:
        message = (
            f"\u26a0\ufe0f MARGIN HAZARD: BTC is currently at ${m.current_btc_price}. "
            f"Your liquidation barrier is ${m.liquidation_price} "
            f"({distance}% away). Current Implied Volatility is high: "
            f"{m.volatility_index}%."
        )
        return Alert("MARGIN_HAZARD", "sms", message)

    if m.status == THROTTLE_CRITICAL:
        return Alert(
            THROTTLE_CRITICAL,
            "email",
            f"CRITICAL vol regime. BTC ${m.current_btc_price} | "
            f"liq ${m.liquidation_price} | "
            f"distance {distance}% | DVOL {m.volatility_index}",
        )
    if m.status == "ELEVATED":
        return Alert(
            "ELEVATED",
            "email",
            f"Elevated vol. BTC ${m.current_btc_price} | "
            f"liq distance {distance}% | DVOL {m.volatility_index}",
        )
    return Alert("STABLE", "log", "stable")


# =====================================================================
# persistence
# =====================================================================

def _to_dict(m: RiskMetrics, a: Alert) -> dict:
    return {
        **m.__dict__,
        "alert": a.key,
        "channel": a.channel,
        "message": a.message,
    }


def write_last_metrics(m: RiskMetrics, a: Alert) -> None:
    """Write the canonical last_metrics.json used by the dashboard / API."""
    payload = _to_dict(m, a)
    payload["alert_message"] = a.message
    with open(LAST_METRICS_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def append_run_history(m: RiskMetrics, a: Alert) -> None:
    """Append a compact record to run_history.jsonl."""
    with open(RUN_HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(_to_dict(m, a)) + "\n")


# =====================================================================
# state (position_state.json)
# =====================================================================

REQUIRED_STATE_KEYS = ("entry_price", "leverage", "position_type")


def load_position() -> Position:
    """Load the watched position. Fails loud if the file is missing or malformed."""
    if not os.path.exists(STATE_FILE):
        log_event("position_state.json not found", level="ERROR")
        print(json.dumps({"error": "position_state.json missing. Create it before running."}))
        sys.exit(1)

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)

    for key in REQUIRED_STATE_KEYS:
        if key not in state:
            log_event(f"Missing required key '{key}' in position_state.json", level="ERROR")
            print(json.dumps({"error": f"position_state.json missing key: {key}"}))
            sys.exit(1)

    pos = Position(
        entry_price=float(state["entry_price"]),
        leverage=float(state["leverage"]),
        position_type=str(state["position_type"]).lower(),
    )
    if pos.leverage <= 0:
        log_event("leverage must be > 0", level="ERROR")
        sys.exit(1)
    if pos.position_type not in ("short", "long"):
        log_event(f"position_type must be 'short' or 'long', got {pos.position_type}",
                  level="ERROR")
        sys.exit(1)
    return pos


# =====================================================================
# entry point
# =====================================================================

def main() -> int:
    try:
        position = load_position()
        metrics = compute_metrics(position)
        alert = classify_alert(metrics)
        write_last_metrics(metrics, alert)
        append_run_history(metrics, alert)
    except Exception as e:  # noqa: BLE001
        log_event(f"Run failed: {e}", level="ERROR")
        print(json.dumps({"error": str(e)}))
        return 1

    log_event(
        f"Run complete: status={metrics.status}, "
        f"dist={metrics.distance_to_liq_percent}%, alert={alert.key}"
    )
    print(json.dumps({**metrics.__dict__, "alert_message": alert.message}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
