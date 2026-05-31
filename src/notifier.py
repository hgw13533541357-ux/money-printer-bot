# Telegram notifier (placeholder)
# Configure TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID env vars to enable

import os
import requests

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")


def send_notification(message):
    """Send a Telegram message"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[NOTIFIER] (disabled) Would send: {message[:100]}...")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message[:4000],
        "parse_mode": "HTML",
    }
    try:
        r = requests.post(url, data=data, timeout=10)
        if r.status_code == 200:
            print("[NOTIFIER] Sent successfully")
        else:
            print(f"[NOTIFIER] Failed: {r.status_code}")
    except Exception as e:
        print(f"[NOTIFIER] Error: {e}")


def notify_trade(trade_info):
    """Format and send a trade notification"""
    msg = f"Trade executed: {trade_info.get('symbol')}\n"
    msg += f"Direction: {trade_info.get('direction')}\n"
    msg += f"Size: {trade_info.get('size')}\n"
    msg += f"Spread: {trade_info.get('spread')}%\n"
    msg += f"Timestamp: {trade_info.get('timestamp')}"
    send_notification(msg)
