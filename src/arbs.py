# Arithmetic utilities for arbitrage calculations
# Delegates to main.py logic

def calculate_arbitrage_spread(spot_price, futures_price):
    """Calculate spot-futures spread as percentage.
    Positive means futures are trading at premium.
    """
    if not spot_price or spot_price <= 0:
        return None
    spread = ((futures_price - spot_price) / spot_price) * 100
    return round(spread, 4)


def calculate_position_size(usdt_amount, spot_price, min_contract_size=1):
    """Calculate how many contracts to trade given a USDT amount"""
    if not spot_price or spot_price <= 0:
        return 0
    raw = usdt_amount / spot_price
    return max(min_contract_size, int(raw))


def evaluate_trade(spread, min_spread, current_positions, max_positions):
    """Evaluate whether a trade should be executed"""
    if abs(spread) < min_spread:
        return False, "spread_below_threshold"
    if current_positions >= max_positions:
        return False, "max_positions_reached"
    direction = "long_futures" if spread < 0 else "short_futures"
    return True, direction
