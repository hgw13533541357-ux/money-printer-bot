import os
import sys
import time
import json
import hmac
import hashlib
import requests
from datetime import datetime

# ------------------------- ARBITRAGE BOT (GATE.IO) -------------------------
# Spot-Futures spread arbing
# --------------------------------------------------------------------------

GATE_API_KEY = os.environ.get("GATE_API_KEY", "")
GATE_API_SECRET = os.environ.get("GATE_API_SECRET", "")
BASE_URL = "https://api.gateio.ws/api/v4"

# Trading pairs to monitor (Gate.io format: BTC_USDT)
PAIRS = os.environ.get("PAIRS", "BTC_USDT,ETH_USDT,SOL_USDT").split(",")

# Minimum spread to trigger trade (percentage)
MIN_SPREAD = float(os.environ.get("MIN_SPREAD", "0.15"))

# Trade size
TRADE_SIZE = float(os.environ.get("TRADE_SIZE", "5.0"))

# Max positions
MAX_POSITIONS = int(os.environ.get("MAX_POSITIONS", "3"))

# Dry run
DRY_RUN = os.environ.get("DRY_RUN", "true").lower() == "true"

results = []


def sign_request(method, url, query_string="", body=""):
    t = str(int(time.time()))
    m = method.upper()
    hashed_payload = hashlib.sha512(body.encode()).hexdigest()
    sig_str = f"{m}\n{url}\n{query_string}\n{hashed_payload}\n{t}"
    sig = hmac.new(GATE_API_SECRET.encode(), sig_str.encode(), hashlib.sha512).hexdigest()
    headers = {
        "KEY": GATE_API_KEY,
        "SIGN": sig,
        "TIMESTAMP": t,
        "Content-Type": "application/json",
    }
    return headers


def gate_get(path, params=None):
    """Gate.io v4 GET request"""
    qs = ""
    if params:
        qs = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    full_path = path + ("?" + qs if qs else "")
    headers = sign_request("GET", path, qs)
    try:
        r = requests.get(BASE_URL + full_path, headers=headers, timeout=15)
        return r.json()
    except Exception as e:
        print(f"[ERROR] GET {path}: {e}")
        return None


def gate_post(path, data=None):
    """Gate.io v4 POST request"""
    body = json.dumps(data) if data else ""
    headers = sign_request("POST", path, "", body)
    try:
        r = requests.post(BASE_URL + path, headers=headers, data=body, timeout=15)
        return r.json()
    except Exception as e:
        print(f"[ERROR] POST {path}: {e}")
        return None


def get_spot_price(symbol):
    """
    Get spot last price.
    symbol format: BTC_USDT (Gate.io format, keep underscore)
    """
    resp = gate_get("/spot/tickers", {"currency_pair": symbol})
    if resp and isinstance(resp, list) and len(resp) > 0:
        last = resp[0].get("last")
        if last:
            return float(last)
    return None


def get_futures_price(symbol, settle="usdt"):
    """
    Get futures last price.
    For Gate.io USDT perpetual: contract name = BTC_USDT (same as spot pair)
    """
    resp = gate_get(f"/futures/{settle}/tickers", {"contract": symbol})
    if resp and isinstance(resp, list) and len(resp) > 0:
        last = resp[0].get("last")
        if last:
            return float(last)
    return None


def get_spread(symbol):
    """Calculate spot-futures spread percentage"""
    spot = get_spot_price(symbol)
    fut = get_futures_price(symbol)
    if spot and fut and spot > 0:
        spread = ((fut - spot) / spot) * 100
        return round(spread, 4), spot, fut
    return None, None, None


def get_balance(currency="USDT"):
    """Get spot account balance"""
    resp = gate_get("/spot/accounts")
    if resp and isinstance(resp, list):
        for acc in resp:
            if acc.get("currency") == currency:
                return float(acc.get("available", 0))
    return 0.0


def get_open_positions(settle="usdt"):
    """Get open futures positions"""
    resp = gate_get(f"/futures/{settle}/positions")
    if resp and isinstance(resp, list):
        positions = []
        for pos in resp:
            size = float(pos.get("size", 0))
            if size != 0:
                positions.append({
                    "contract": pos.get("contract"),
                    "size": size,
                    "entry": float(pos.get("entry_price", 0)),
                    "unrealized_pnl": float(pos.get("unrealised_pnl", 0)),
                    "leverage": float(pos.get("leverage", 1)),
                })
        return positions
    return []


def create_futures_order(symbol, size, price=None, settle="usdt"):
    """Place a futures order on Gate.io"""
    data = {
        "contract": symbol,
        "size": str(int(size)),
        "price": str(price) if price else "0",
        "tif": "ioc" if not price else "gtc",
    }
    if size > 0:
        data["reduce_only"] = False
    else:
        data["reduce_only"] = True
    print(f"[ORDER] {symbol} size={size} price={price or 'MARKET'}")
    if DRY_RUN:
        print(f"[DRY_RUN] Would place order: {json.dumps(data)}")
        return {"id": "dry_run", "status": "accepted"}
    resp = gate_post(f"/futures/{settle}/orders", data)
    return resp


def run_arbitrage_cycle():
    """Main arbitrage logic"""
    print("=" * 60)
    print(f"[CYCLE] {datetime.now().isoformat()}")

    balance = get_balance("USDT")
    print(f"[BALANCE] USDT available: {balance:.2f}")

    positions = get_open_positions()
    print(f"[POSITIONS] Open: {len(positions)}")
    for p in positions:
        print(f"  {p['contract']} | size={p['size']:.4f} | entry={p['entry']:.2f} | PnL={p['unrealized_pnl']:.2f}")

    open_position_count = len(positions)

    for symbol in PAIRS:
        symbol = symbol.strip()
        if not symbol:
            continue

        print(f"")
        print(f"[CHECK] {symbol}")
        spread, spot, fut = get_spread(symbol)

        if spread is None:
            print(f"  SKIP - could not get prices")
            continue

        print(f"  Spot: {spot:.2f} | Futures: {fut:.2f} | Spread: {spread:.4f}%")

        if abs(spread) < MIN_SPREAD:
            print(f"  SKIP - spread {spread:.4f}% below threshold {MIN_SPREAD}%")
            continue

        if open_position_count >= MAX_POSITIONS:
            print(f"  SKIP - at max positions ({MAX_POSITIONS})")
            continue

        # Calculate position size
        size = int(TRADE_SIZE / spot) if spot > 0 else 1
        if size < 1:
            size = 1

        direction = "LONG" if spread < 0 else "SHORT"
        fut_size = size if spread < 0 else -size

        print(f"[TRADE] {direction} FUTURES | {symbol} | contracts={fut_size}")

        result = create_futures_order(symbol, fut_size)
        result_str = json.dumps(result, default=str)[:300]
        print(f"  Order result: {result_str}")

        open_position_count += 1

        results.append({
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "spread": spread,
            "spot": spot,
            "futures": fut,
            "direction": direction,
            "size": fut_size,
            "balance": balance,
        })

    print(f"")
    print(f"[CYCLE COMPLETE] {datetime.now().isoformat()}")
    print(f"[RESULTS] Trades this cycle: {len(results)}")

    with open("arbitrage_results.txt", "w") as f:
        f.write("Arbitrage Bot Results
")
        f.write(f"Time: {datetime.now().isoformat()}
")
        f.write("=" * 60 + "
")
        for r in results:
            f.write(f"{json.dumps(r)}
")

    print(f"[SAVED] Results to arbitrage_results.txt")
    return results


if __name__ == "__main__":
    print("Starting Gate.io Spot-Futures Arbitrage Bot")
    print(f"Pairs: {PAIRS}")
    print(f"Min Spread: {MIN_SPREAD}%")
    print(f"Trade Size: {TRADE_SIZE} USDT")
    print(f"Max Positions: {MAX_POSITIONS}")
    print(f"Dry Run: {DRY_RUN}")
    print()

    run_arbitrage_cycle()

    print()
    print("Bot finished.")
