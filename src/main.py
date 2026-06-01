import os, sys, time, json, hmac, hashlib, requests
from datetime import datetime

GATE_API_KEY = os.environ.get("GATE_API_KEY", "")
GATE_API_SECRET = os.environ.get("GATE_API_SECRET", "")
BASE_URL = "https://api.gateio.ws/api/v4"
PAIRS = os.environ.get("PAIRS", "BTC_USDT,ETH_USDT,SOL_USDT").split(",")
MIN_SPREAD = float(os.environ.get("MIN_SPREAD", "0.15"))
TRADE_SIZE = float(os.environ.get("TRADE_SIZE", "5.0"))
MAX_POSITIONS = int(os.environ.get("MAX_POSITIONS", "3"))
DRY_RUN = os.environ.get("DRY_RUN", "true").lower() == "true"
results = []

def sign_request(method, url, qs="", body=""):
    t = str(int(time.time()))
    hp = hashlib.sha512(body.encode()).hexdigest()
    sig = hmac.new(GATE_API_SECRET.encode(), f"{method}\n{url}\n{qs}\n{hp}\n{t}".encode(), hashlib.sha512).hexdigest()
    return {"KEY": GATE_API_KEY, "SIGN": sig, "TIMESTAMP": t, "Content-Type": "application/json"}

def gate_get(path, params=None):
    qs = "&".join(f"{k}={v}" for k,v in sorted(params.items())) if params else ""
    try:
        r = requests.get(BASE_URL + path + ("?" + qs if qs else ""), headers=sign_request("GET", path, qs), timeout=15)
        return r.json()
    except Exception as e:
        print(f"[ERROR] GET {path}: {e}")
        return None

def gate_post(path, data=None):
    body = json.dumps(data) if data else ""
    try:
        r = requests.post(BASE_URL + path, headers=sign_request("POST", path, "", body), data=body, timeout=15)
        return r.json()
    except Exception as e:
        print(f"[ERROR] POST {path}: {e}")
        return None

def get_spot_price(sym):
    resp = gate_get("/spot/tickers", {"currency_pair": sym})
    if resp and isinstance(resp, list) and len(resp) > 0:
        last = resp[0].get("last")
        if last: return float(last)
    return None

def get_futures_price(sym, settle="usdt"):
    resp = gate_get(f"/futures/{settle}/tickers", {"contract": sym})
    if resp and isinstance(resp, list) and len(resp) > 0:
        last = resp[0].get("last")
        if last: return float(last)
    return None

def get_spread(sym):
    spot = get_spot_price(sym)
    fut = get_futures_price(sym)
    if spot and fut and spot > 0:
        sp = ((fut - spot) / spot) * 100
        return round(sp, 4), spot, fut
    return None, None, None

def get_balance(cur="USDT"):
    resp = gate_get("/spot/accounts")
    if resp and isinstance(resp, list):
        for a in resp:
            if a.get("currency") == cur: return float(a.get("available", 0))
    return 0.0

def get_open_positions(settle="usdt"):
    resp = gate_get(f"/futures/{settle}/positions")
    out = []
    if resp and isinstance(resp, list):
        for p in resp:
            if float(p.get("size", 0)) != 0:
                out.append({"contract": p.get("contract"), "size": float(p.get("size")), "entry": float(p.get("entry_price", 0)), "pnl": float(p.get("unrealised_pnl", 0)), "lev": float(p.get("leverage", 1))})
    return out

def create_order(sym, size, price=None, settle="usdt"):
    data = {"contract": sym, "size": str(int(size)), "price": str(price) if price else "0", "tif": "ioc" if not price else "gtc"}
    data["reduce_only"] = False if size > 0 else True
    print(f"[ORDER] {sym} size={size}")
    if DRY_RUN:
        print(f"[DRY_RUN] Would place: {json.dumps(data)}")
        return {"id": "dry_run", "status": "accepted"}
    return gate_post(f"/futures/{settle}/orders", data)

def run():
    print("=" * 60)
    print(f"[CYCLE] {datetime.now().isoformat()}")
    bal = get_balance("USDT")
    print(f"[BALANCE] USDT: {bal:.2f}")
    pos = get_open_positions()
    print(f"[POSITIONS] Open: {len(pos)}")
    for p in pos:
        print(f"  {p['contract']} | size={p['size']:.4f} | entry={p['entry']:.2f} | PnL={p['pnl']:.2f}")
    cnt = len(pos)
    for sym in PAIRS:
        sym = sym.strip()
        if not sym: continue
        print()
        print(f"[CHECK] {sym}")
        spread, spot, fut = get_spread(sym)
        if spread is None:
            print("  SKIP - no prices")
            continue
        print(f"  Spot: {spot:.2f} | Futures: {fut:.2f} | Spread: {spread:.4f}%")
        if abs(spread) < MIN_SPREAD:
            print(f"  SKIP - spread {spread:.4f}% < {MIN_SPREAD}%")
            continue
        if cnt >= MAX_POSITIONS:
            print(f"  SKIP - max pos ({MAX_POSITIONS})")
            continue
        sz = max(1, int(TRADE_SIZE / spot)) if spot > 0 else 1
        direction = "LONG" if spread < 0 else "SHORT"
        fut_sz = sz if spread < 0 else -sz
        print(f"[TRADE] {direction} {sym} contracts={fut_sz}")
        res = create_order(sym, fut_sz)
        print(f"  Result: {json.dumps(res, default=str)[:300]}")
        cnt += 1
        results.append({"ts": datetime.now().isoformat(), "sym": sym, "spread": spread, "spot": spot, "futures": fut, "dir": direction, "size": fut_sz, "bal": bal})
    print()
    print(f"[CYCLE DONE] {datetime.now().isoformat()}")
    print(f"[TRADES] {len(results)}")
    for r in results:
        print(json.dumps(r))

if __name__ == "__main__":
    print("=== GATE.IO SPOT-FUTURES ARB BOT ===")
    print(f"Pairs: {PAIRS}")
    print(f"Min Spread: {MIN_SPREAD}%")
    print(f"Trade Size: {TRADE_SIZE} USDT")
    print(f"Max Positions: {MAX_POSITIONS}")
    print(f"Dry Run: {DRY_RUN}")
    print()
    run()
    print()
    print("Done.")