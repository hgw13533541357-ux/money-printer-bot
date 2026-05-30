"""
Money Printer Bot - 主入口
"""

import os
import time
import yaml
from arbs import BinanceArb
from risk import RiskManager
from notifier import Notifier


def load_config():
    path = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
    with open(path) as f:
        return yaml.safe_load(f)


def main():
    cfg = load_config()

    api_key = os.getenv("BINANCE_API_KEY") or cfg.get("binance", {}).get("api_key", "")
    secret = os.getenv("BINANCE_SECRET_KEY") or cfg.get("binance", {}).get("secret_key", "")
    tg_token = os.getenv("TELEGRAM_BOT_TOKEN") or cfg.get("telegram", {}).get("bot_token", "")
    tg_chat = os.getenv("TELEGRAM_CHAT_ID") or cfg.get("telegram", {}).get("chat_id", "")
    symbols = cfg.get("symbols", ["BTCUSDT", "ETHUSDT", "SOLUSDT"])

    arb = BinanceArb(api_key, secret)
    risk = RiskManager(balance_usdt=1000.0)
    notify = Notifier(tg_token, tg_chat)

    print("Money Printer Bot 启动")
    notify.send("印钞机已启动")

    while True:
        try:
            opps = arb.top_opportunities(base_symbols=symbols, min_spread_pct=0.1)
            if opps:
                msg_lines = ["套利机会发现！\n"]
                for o in opps[:3]:
                    msg_lines.append(
                        f"{o['symbol']} | "
                        f"价差: {o['spread_pct']:+.3f}% | "
                        f"建议: {o['signal']}"
                    )
                notify.send("\n".join(msg_lines))

            print(f"[{time.strftime('%H:%M:%S')}] 扫描完成 | {len(opps)} 个机会")
            time.sleep(1800)

        except KeyboardInterrupt:
            print("手动停止")
            notify.send("印钞机停止")
            break
        except Exception as e:
            print(f"错误: {e}")
            notify.send(f"印钞机异常: {e}")
            time.sleep(60)


if __name__ == "__main__":
    main()