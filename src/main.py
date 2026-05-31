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

# Trading pairs to monitor
PAIRS = os.environ.get("PAIRS", "BTC_USDT,ETH_USDT,SOL_USDT").split(",")

# Minimum spread to trigger trade (percentage)
MIN_SPREAD = float(os.environ.get("MIN_SPREAD", "0.15"))

# How much to trade per pair in quote currency
TRADE_SIZE_USDT = float(os.environ.get("TRADE_SIZE", "5.0"))

# Max positions open at once
MAX_POSITIONS = int(os.environ.get("MAX_POSITIONS", "3"))

# Dry run mode (no real orders)
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"

# Results tracking
results = []


def sign_request(method, url, query_string="", body=""):
    """Gate.io v4 API signing"""
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
    url = BASE_URL + path
    qs = ""
    if params:
        qs = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        url += "?" + qs
    headers = sign_request("GET", path, qs)
    try:
        r = requests.get(url, headers=headers, timeout=10)
        return r.json()
    except Exception as e:
        print(f"[ERROR] GET {path}: {e}")
        return None


def gate_post(path, data=None):
    url = BASE_URL + path
    body = json.dumps(data) if data else ""
    headers = sign_request("POST", path, "", body)
    try:
        r = requests.post(url, headers=headers, data=body, timeout=10)
        return r.json()
    except Exception as e:
        print(f"[ERROR] POST {path}: {e}")
        return None


def get_spot_price(symbol):
    """Get spot mid-price for a pair"""
    pair = symbol.replace("_", "")
    resp = gate_get(f"/spot/tickers", {"currency_pair": pair})
    if resp and isinstance(resp, list) and len(resp) > 0:
        last = resp[0].get("last")
        if last:
            return float(last)
    return None


def get_futures_price(symbol, settle="usdt"):
    """Get futures last price for a pair"""
    contract = symbol.replace("_", "-") + "_" + settle.upper()
    try:
        resp = gate_get(f"/futures/{settle}/contracts/{contract}")
        if resp and isinstance(resp, dict):
            return float(resp.get("last", 0))
    except:
        pass
    return None


def get_spread(symbol):
    """Calculate spot-futures spread in percentage"""
    spot = get_spot_price(symbol)
    fut = get_futures_price(symbol)
    if spot and fut and spot > 0:
        spread = ((fut - spot) / spot) * 100
        return round(spread, 4), spot, fut
    return None, None, None


def get_balance(currency="USDT"):
    """Get spot balance"""
    resp = gate_get("/spot/accounts")
    if resp and isinstance(resp, list):
        for acc in resp:
            if acc.get("currency") == currency:
                return float(acc.get("available", 0))
    return 0.0


def get_open_positions():
    """Get open futures positions"""
    resp = gate_get("/futures/usdt/positions")
    if resp and isinstance(resp, list):
        positions = []
        for pos in resp:
            if pos.get("size", 0) > 0:
                positions.append({
                    "contract": pos.get("contract"),
                    "size": float(pos.get("size")),
                    "entry": float(pos.get("entry_price")),
                    "unrealized_pnl": float(pos.get("unrealised_pnl")),
                    "leverage": float(pos.get("leverage")),
                })
        return positions
    return []


def create_futures_order(symbol, size, price=None, settle="usdt"):
    """Place a futures order"""
    contract = symbol.replace("_", "-") + "_" + settle.upper()
    data = {
        "contract": contract,
        "size": size,
        "price": price or 0,
        "tif": "gtc",  # good till cancelled
    }
    if not price or price == 0:
        data["tif"] = "ioc"  # immediate-or-cancel for market
        # For market, we set price to 0 and use reduce_only = false
        data["price"] = "0"
    if size > 0:
        data["reduce_only"] = False
    else:
        data["reduce_only"] = True
    print(f"[ORDER] {contract} size={size} price={price or 'MARKET'}")
    if DRY_RUN:
        print(f"[DRY_RUN] Would place order: {json.dumps(data)}")
        return {"id": "dry_run", "status": "dry_run"}
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
        
        print(f"\n[CHECK] {symbol}")
        spread, spot, fut = get_spread(symbol)
        
        if spread is None:
            print(f"  SKIP - could not get prices")
            continue
        
        print(f"  Spot: {spot:.2f} | Futures: {fut:.2f} | Spread: {spread:.4f}%")
        
        # Positive spread = futures premium = short futures + long spot
        # Negative spread = futures discount = long futures + short spot
        if abs(spread) < MIN_SPREAD:
            print(f"  SKIP - spread {spread:.4f}% below threshold {MIN_SPREAD}%")
            continue
        
        if open_position_count >= MAX_POSITIONS:
            print(f"  SKIP - at max positions ({MAX_POSITIONS})")
            continue
        
        # Calculate trade size
        trade_size_contracts = int(TRADE_SIZE_USDT / spot) if spot else 0
        if trade_size_contracts < 1:
            print(f"  SKIP - trade size too small ({trade_size_contracts} contracts)")
            continue
        
        direction = "LONG_FUTURES" if spread < 0 else "SHORT_FUTURES"
        fut_size = trade_size_contracts if spread < 0 else -trade_size_contracts
        
        print(f"[TRADE] {direction} | {symbol} | contracts={fut_size}")
        
        result = create_futures_order(symbol, fut_size)
        print(f"  Order result: {json.dumps(result, default=str)[:200]}")
        
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
        
        print(f"  DONE - {symbol}")
    
    print(f"\n[CYCLE COMPLETE] {datetime.now().isoformat()}")
    print(f"[RESULTS] Trades this cycle: {len(results)}")
    
    # Save results to a file
    with open("arbitrage_results.txt", "w") as f:
        f.write(f"Arbitrage Bot Results\n")
        f.write(f"Time: {datetime.now().isoformat()}\n")
        f.write(f"{'='*60}\n")
        for r in results:
            f.write(f"{json.dumps(r)}\n")
    
    print("[SAVED] Results to arbitrage_results.txt")
    return results


if __name__ == "__main__":
    print("Starting Gate.io Spot-Futures Arbitrage Bot")
    print(f"Pairs: {PAIRS}")
    print(f"Min Spread: {MIN_SPREAD}%")
    print(f"Trade Size: {TRADE_SIZE_USDT} USDT")
    print(f"Max Positions: {MAX_POSITIONS}")
    print(f"Dry Run: {DRY_RUN}")
    print()
    
    run_arbitrage_cycle()
    
    print("\nBot finished.")
