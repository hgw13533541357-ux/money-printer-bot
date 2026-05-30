"""
风险管理：仓位控制、止损、最大回撤检测
"""

MAX_POSITION_SIZE = 0.1
MAX_DAILY_LOSS = 0.05
STOP_LOSS_PCT = 0.02
TAKE_PROFIT_PCT = 0.04


class RiskManager:
    def __init__(self, balance_usdt):
        self.balance = balance_usdt
        self.daily_pnl = 0.0
        self.trades_today = 0
        self.max_drawdown = 0.0
        self.peak_balance = balance_usdt

    def can_trade(self, trade_value_usdt):
        if self.daily_pnl / self.balance <= -MAX_DAILY_LOSS:
            return (False, f"日亏损达到上限 ({self.daily_pnl:.2f} USDT)")
        if trade_value_usdt > self.balance * MAX_POSITION_SIZE:
            return (False, f"单笔仓位超过限制 ({MAX_POSITION_SIZE*100}%)")
        return (True, "OK")

    def update_pnl(self, pnl):
        self.daily_pnl += pnl
        self.balance += pnl
        if self.balance > self.peak_balance:
            self.peak_balance = self.balance
        drawdown = (self.peak_balance - self.balance) / self.peak_balance
        self.max_drawdown = max(self.max_drawdown, drawdown)

    def should_stop(self, entry_price, current_price, side):
        if side == "LONG":
            ret = (current_price - entry_price) / entry_price
        else:
            ret = (entry_price - current_price) / entry_price
        if ret <= -STOP_LOSS_PCT:
            return True
        if ret >= TAKE_PROFIT_PCT:
            return True
        return False

    def summary(self):
        return (
            f"余额: {self.balance:.2f} USDT\n"
            f"今日交易: {self.trades_today} 笔 | PnL: {self.daily_pnl:+.2f}\n"
            f"最大回撤: {self.max_drawdown*100:.2f}%"
        )