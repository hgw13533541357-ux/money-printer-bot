# Risk management utilities
import os

MAX_DRAWDOWN_PERCENT = float(os.environ.get("MAX_DRAWDOWN", "10.0"))
MAX_DAILY_TRADES = int(os.environ.get("MAX_DAILY_TRADES", "20"))
CONSECUTIVE_LOSS_LIMIT = int(os.environ.get("CONSECUTIVE_LOSS_LIMIT", "3"))

daily_trade_count = 0
consecutive_losses = 0
peak_balance = 0.0


def check_risk_limits(current_balance, trade_result=None):
    """Check if risk limits are breached"""
    global daily_trade_count, consecutive_losses, peak_balance
    
    peak_balance = max(peak_balance, current_balance)
    
    # Check drawdown
    if peak_balance > 0:
        drawdown = ((peak_balance - current_balance) / peak_balance) * 100
        if drawdown > MAX_DRAWDOWN_PERCENT:
            return False, f"drawdown_exceeded: {drawdown:.2f}% > {MAX_DRAWDOWN_PERCENT}%"
    
    # Check daily trade count
    if daily_trade_count >= MAX_DAILY_TRADES:
        return False, f"max_daily_trades: {daily_trade_count}"
    
    # Check consecutive losses
    if trade_result:
        if trade_result.get("pnl", 0) < 0:
            consecutive_losses += 1
        else:
            consecutive_losses = 0
    
    if consecutive_losses >= CONSECUTIVE_LOSS_LIMIT:
        return False, f"consecutive_losses: {consecutive_losses}"
    
    return True, "ok"


def reset_daily_counters():
    """Reset daily counters (call at start of each day)"""
    global daily_trade_count, consecutive_losses
    daily_trade_count = 0
    consecutive_losses = 0