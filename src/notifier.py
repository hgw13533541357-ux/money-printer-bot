"""
Telegram通知
"""

import requests


class Notifier:
    def __init__(self, bot_token=None, chat_id=None):
        self.bot_token = bot_token
        self.chat_id = chat_id

    def send(self, message):
        if not self.bot_token or not self.chat_id:
            print(f"[NOTIFIER] {message}")
            return
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": message, "parse_mode": "Markdown"}
        try:
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            print(f"[NOTIFIER] 发送失败: {e}")
