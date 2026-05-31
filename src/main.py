# -*- coding: utf-8 -*-
"""
Money Printer Bot - Main Entry (Gate.io)
"""

import os
import time
import yaml
import sys
sys.path.insert(0, os.path.dirname(__file__))

from arbs import GateArb
from risk import RiskManager
from notifier import Notifier


def load_config():
    path = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
    with open(path) as f:
        return yaml.safe_load(f)


def main():
    cfg = load_config()

    api_key = os.getenv("GATE_API_KEY") or cfg.get("gateio", {}).get("api_key", "")
    secret = os.getenv("GATE_API_SECRET") or cfg.get("gateio", {}).get("secret_key", "")
    tg_token = os.getenv("TELEGRAM_BOT_TOKEN") or cfg.get("telegram", {}).get("bot_token", "")
    tg_chat = os.getenv("TELEGRAM_CHAT_ID") or cfg.get("telegram", {}).get("chat_id", "")
    symbols = cfg.get("symbols", ["BTC/USDT", "ETH/USDT", "SOL/USDT"])

    if not api_key or not secret:
        print("[ERROR] GATE_API_KEY or GATE_API_SECRET not set!")
        return

    arb = GateArb(api_key, secret)
    risk = RiskManager(balance_usdt=100.0)
    notify = Notifier(tg_token, tg_chat)

    print("[BOT] Money Printer Bot (Gate.io) started")
    notify.send("[BOT] Bot started (Gate.io)")

    rounds = 0
    while rounds < 60:
        try:
            opps = arb.top_opportunities(base_symbols=symbols, min_spread_pct=0.1)
            if opps:
                msg_lines = ["[OPP] Arbitrage opportunities found!\n"]
                for o in opps[:3]:
                    msg_lines.append(
                        f"  {o['symbol']} | "
                        f"spread: {o['spread_pct']:+.3f}% | "
                        f"{o['signal']}"
                    )
                    print(f"[OPP] {o['symbol']} spread={o['spread_pct']:+.3f}% signal={o['signal']}")
                notify.send("\n".join(msg_lines))
            else:
                print(f"[{time.strftime('%H:%M:%S')}] No arbitrage opportunities found")

            rounds += 1
            time.sleep(60)

        except KeyboardInterrupt:
            print("[BOT] Manual stop")
            notify.send("[BOT] Bot stopped")
            break
        except Exception as e:
            print(f"[ERROR] {e}")
            notify.send(f"[ERROR] Bot exception: {e}")
            time.sleep(30)

    print(f"[BOT] Run complete. Scanned {rounds} rounds")
    notify.send(f"[BOT] Run complete. Scanned {rounds} rounds")


if __name__ == "__main__":
    main()
