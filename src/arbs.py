# -*- coding: utf-8 -*-
"""
Gate.io spot-futures spread arbitrage engine
"""

import ccxt
import time


class GateArb:
    def __init__(self, api_key, secret_key):
        self.exchange = ccxt.gate({
            'apiKey': api_key,
            'secret': secret_key,
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'},
        })
        self.futures = ccxt.gate({
            'apiKey': api_key,
            'secret': secret_key,
            'enableRateLimit': True,
            'options': {'defaultType': 'swap'},
        })
        self._spot_cache = {}
        self._futures_cache = {}
        self._cache_ts = 0

    def _refresh_cache(self):
        now = time.time()
        if now - self._cache_ts < 2:
            return
        try:
            tickers = self.exchange.fetch_tickers()
            for sym, t in tickers.items():
                if t.get('last'):
                    self._spot_cache[sym] = t['last']
        except:
            pass
        try:
            ftickers = self.futures.fetch_tickers()
            for sym, t in ftickers.items():
                if t.get('last'):
                    self._futures_cache[sym] = t['last']
        except:
            pass
        self._cache_ts = now

    def _to_futures_symbol(self, spot_sym):
        base = spot_sym.split('/')[0]
        return f"{base}/USDT:USDT"

    def spot_futures_spread(self, spot_symbol):
        self._refresh_cache()
        fut_symbol = self._to_futures_symbol(spot_symbol)
        spot_price = self._spot_cache.get(spot_symbol, 0)
        fut_price = self._futures_cache.get(fut_symbol, 0)
        if not spot_price or not fut_price:
            return None
        spread = fut_price - spot_price
        spread_pct = (spread / spot_price) * 100
        return {
            'symbol': spot_symbol,
            'spot': round(spot_price, 2),
            'futures': round(fut_price, 2),
            'spread': round(spread, 2),
            'spread_pct': round(spread_pct, 4),
            'signal': (
                'LONG_SPOT_SHORT_FUT' if spread_pct > 0.15 else
                'SHORT_SPOT_LONG_FUT' if spread_pct < -0.15 else
                'NEUTRAL'
            ),
        }

    def top_opportunities(self, base_symbols=None, min_spread_pct=0.1):
        if base_symbols is None:
            base_symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'DOGE/USDT']
        self._refresh_cache()
        results = []
        for sym in base_symbols:
            try:
                data = self.spot_futures_spread(sym)
                if data and abs(data['spread_pct']) >= min_spread_pct:
                    results.append(data)
            except Exception:
                continue
        return sorted(results, key=lambda x: abs(x['spread_pct']), reverse=True)
