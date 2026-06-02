import urllib.request
import json
import sys
import os
from datetime import datetime, timezone
import time as _time

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, "position_state.json")
LOG_FILE = os.path.join(BASE_DIR, "sentinel.log")
LAST_METRICS_FILE = os.path.join(BASE_DIR, "last_metrics.json")
RUN_HISTORY_FILE = os.path.join(BASE_DIR, "run_history.jsonl")

# --- Thresholds (must match AGENTS.md) ---
EMERGENCY_LIQ_DISTANCE_PCT = 1.5
THROTTLE_STATUS = "CRITICAL"
THROTTLE_RESET_STATUS = "STABLE"

# --- Alert routing ---
ALERT_CHANNEL_MAP = {
    "MARGIN_HAZARD": "sms",   # distance_to_liq_percent <= 1.5
    "CRITICAL": "email",
    "ELEVATED": "email",
    "STABLE": "log",
}


def log_event(message, level="INFO"):
    """Append a timestamped line to the local sentinel log."""
    try:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] [{level}] {message}\n")
    except Exception:
        pass


def load_position_state():
    """Load active position from position_state.json. Fails loud if file is missing."""
    if not os.path.exists(STATE_FILE):
        log_event("position_state.json not found", level="ERROR")
        print(json.dumps({"error": "position_state.json missing. Create it before running."}))
        sys.exit(1)

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)

    required = ["entry_price", "leverage", "position_type"]
    for key in required:
        if key not in state:
            log_event(f"Missing required key '{key}' in position_state.json", level="ERROR")
            print(json.dumps({"error": f"position_state.json missing key: {key}"}))
            sys.exit(1)

    return state


def http_get_json(url, timeout=5):
    """GET a URL and return parsed JSON. Raises on failure."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode())


def get_market_data():
    """
    Fetches real-time BTC spot price and the CME CF Bitcoin Volatility Index (BVI).
    Falls back gracefully so the daemon never crashes.
    """
    spot_url = "https://api.coinbase.com/v2/prices/BTC-USD/spot"
    fallback_url_1 = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    fallback_url_2 = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"

    # Deribit DVOL — build a 24h window at 1h resolution (most reliable)
    _now_ms = int(_time.time() * 1000)
    _start_ms = _now_ms - (24 * 60 * 60 * 1000)
    dvol_url = (
        f"https://www.deribit.com/api/v2/public/get_volatility_index_data"
        f"?currency=BTC&start_timestamp={_start_ms}"
        f"&end_timestamp={_now_ms}&resolution=3600"
    )
    bvi_index_url = "https://api.cfbenchmarks.com/v1/indices/BVI"

    spot_price = None
    bvi_vol = 45.0  # Baseline fallback for the volatility index

    # 1. Spot price with 3-source fallback chain
    for source_url, parser in (
        (spot_url, lambda d: float(d["data"]["amount"])),
        (fallback_url_1, lambda d: float(d["bitcoin"]["usd"])),
        (fallback_url_2, lambda d: float(d["price"])),
    ):
        try:
            data = http_get_json(source_url)
            spot_price = parser(data)
            log_event(f"Spot price fetched from {source_url}")
            break
        except Exception as e:
            log_event(f"Spot source failed ({source_url}): {e}", level="WARN")
            continue

    if spot_price is None:
        log_event("All spot price sources failed", level="ERROR")
        print(json.dumps({"error": "Failed to acquire spot data streams."}))
        sys.exit(1)

    # 2. Volatility index — Deribit DVOL first, then CME BVI, then baseline
    try:
        dvol_data = http_get_json(dvol_url)
        # Deribit returns: {"result": {"data": [[ts, open, high, low, close], ...]}}
        # Use the most recent close.
        series = dvol_data.get("result", {}).get("data", [])
        if series:
            latest_close = float(series[-1][4])
            bvi_vol = latest_close
            log_event(f"Deribit DVOL fetched: {bvi_vol}")
        else:
            raise ValueError("Deribit DVOL series empty")
    except Exception as e:
        log_event(f"Deribit DVOL failed ({e}), trying CME BVI", level="WARN")
        try:
            data = http_get_json(bvi_index_url)
            bvi_vol = float(data["index_value"])
            log_event(f"CME BVI fetched: {bvi_vol}")
        except Exception as e2:
            log_event(f"CME BVI also failed, using baseline {bvi_vol}: {e2}", level="WARN")

    return spot_price, bvi_vol


def calculate_dynamic_risk(entry_price, leverage, position_type="short"):
    current_price, bvi_vol = get_market_data()

    # Mathematical calculation of liquidation bounds
    if position_type.lower() == "short":
        price_change = (current_price - entry_price) / entry_price
        liquidation_price = entry_price * (1 + (1 / leverage))
        distance_to_liq = ((liquidation_price - current_price) / current_price) * 100
    else:  # Long
        price_change = (entry_price - current_price) / entry_price
        liquidation_price = entry_price * (1 - (1 / leverage))
        distance_to_liq = ((current_price - liquidation_price) / current_price) * 100

    # Dynamic risk band driven by the CME BVI
    if bvi_vol > 80:
        risk_coefficient = 0.15
        risk_status = "CRITICAL"
    elif bvi_vol > 60:
        risk_coefficient = 0.25
        risk_status = "ELEVATED"
    else:
        risk_coefficient = 0.40
        risk_status = "STABLE"

    recommended_stop_distance = distance_to_liq * risk_coefficient
    unrealized_pnl = price_change * leverage * 100

    return {
        "status": risk_status,
        "current_btc_price": round(current_price, 2),
        "volatility_index": round(bvi_vol, 2),
        "liquidation_price": round(liquidation_price, 2),
        "distance_to_liq_percent": round(distance_to_liq, 2),
        "unrealized_pnl_percent": round(unrealized_pnl, 2),
        "recommended_stop_percent": round(recommended_stop_distance, 2),
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def classify_alert(metrics):
    """
    Decide which alert (if any) this run triggers.
    Returns: (alert_key, channel, message)
    """
    distance = metrics["distance_to_liq_percent"]
    status = metrics["status"]

    # Emergency broadcast — highest priority
    if distance <= EMERGENCY_LIQ_DISTANCE_PCT:
        message = (
            f"⚠️ MARGIN HAZARD: BTC is currently at ${metrics['current_btc_price']}. "
            f"Your liquidation barrier is ${metrics['liquidation_price']} "
            f"({distance}% away). Current Implied Volatility is high: "
            f"{metrics['volatility_index']}%."
        )
        return ("MARGIN_HAZARD", "sms", message)

    # Status-tiered alerts
    if status == "CRITICAL":
        return (
            "CRITICAL",
            "email",
            f"CRITICAL vol regime. BTC ${metrics['current_btc_price']} | "
            f"liq ${metrics['liquidation_price']} | "
            f"distance {distance}% | BVI {metrics['volatility_index']}",
        )
    if status == "ELEVATED":
        return (
            "ELEVATED",
            "email",
            f"Elevated vol. BTC ${metrics['current_btc_price']} | "
            f"liq distance {distance}% | BVI {metrics['volatility_index']}",
        )
    return ("STABLE", "log", "stable")


def persist_run(metrics, alert_key, channel, message):
    """Write last_metrics.json + append to run_history.jsonl so the scheduler can read state."""
    try:
        with open(LAST_METRICS_FILE, "w", encoding="utf-8") as f:
            json.dump({**metrics, "alert": alert_key, "channel": channel, "message": message}, f, indent=2)
        with open(RUN_HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps({**metrics, "alert": alert_key, "channel": channel}) + "\n")
    except Exception as e:
        log_event(f"Failed to persist run state: {e}", level="WARN")


def main():
    state = load_position_state()
    metrics = calculate_dynamic_risk(
        entry_price=float(state["entry_price"]),
        leverage=float(state["leverage"]),
        position_type=state["position_type"],
    )
    alert_key, channel, message = classify_alert(metrics)
    metrics["alert"] = alert_key
    metrics["channel"] = channel

    persist_run(metrics, alert_key, channel, message)
    log_event(f"Run complete: status={metrics['status']}, dist={metrics['distance_to_liq_percent']}%, alert={alert_key}")

    # Always print JSON for the agent parser. The alert message is also included
    # so a downstream cron/automation can deliver it without re-deriving text.
    print(json.dumps({**metrics, "alert_message": message}, indent=2))


if __name__ == "__main__":
    main()
