"""
现货-合约价差套利 + 三角套利检测
"""

import hmac
import hashlib
import time
import requests

BASE_URL = "https://api.binance.com"
FUTURES_URL = "https://fapi.binance.com"


class BinanceArb:
    def __init__(self, api_key, secret_key):
        self.api_key = api_key
        self.secret_key = secret_key

    def _sign(self, params):
        query = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
        return hmac.new(
            self.secret_key.encode(),
            query.encode(),
            hashlib.sha256,
        ).hexdigest()

    def _request(self, endpoint, params=None, signed=False, futures=False):
        base = FUTURES_URL if futures else BASE_URL
        url = f"{base}{endpoint}"
        headers = {"X-MBX-APIKEY": self.api_key} if self.api_key else {}
        if signed:
            params = params or {}
            params["timestamp"] = int(time.time() * 1000)
            params["signature"] = self._sign(params)
        resp = requests.get(url, params=params, headers=headers)
        return resp.json()

    def get_spot_price(self, symbol):
        data = self._request("/api/v3/ticker/price", {"symbol": symbol})
        return float(data.get("price", 0))

    def get_futures_price(self, symbol):
        data = self._request("/fapi/v1/ticker/price", {"symbol": symbol}, futures=True)
        return float(data.get("price", 0))

    def spot_futures_spread(self, symbol):
        spot = self.get_spot_price(symbol)
        fut = self.get_futures_price(symbol)
        spread = fut - spot
        spread_pct = (spread / spot) * 100 if spot else 0
        return {
            "symbol": symbol,
            "spot": spot,
            "futures": fut,
            "spread": round(spread, 4),
            "spread_pct": round(spread_pct, 4),
            "signal": "LONG_SPOT_SHORT_FUT" if spread_pct > 0.1 else (
                "SHORT_SPOT_LONG_FUT" if spread_pct < -0.1 else "NEUTRAL"
            ),
        }

    def top_opportunities(self, base_symbols=None, min_spread_pct=0.1):
        if base_symbols is None:
            base_symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "DOGEUSDT"]
        results = []
        for sym in base_symbols:
            try:
                data = self.spot_futures_spread(sym)
                if abs(data["spread_pct"]) >= min_spread_pct:
                    results.append(data)
            except Exception:
                continue
        return sorted(results, key=lambda x: abs(x["spread_pct"]), reverse=True)