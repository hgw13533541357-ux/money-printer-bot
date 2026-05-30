# Money Printer Bot

加密货币现货-合约价差套利机器人

## 快速开始

1. 在仓库 Settings → Secrets 添加：
   - BINANCE_API_KEY
   - BINANCE_SECRET_KEY
   - TELEGRAM_BOT_TOKEN（可选）
   - TELEGRAM_CHAT_ID（可选）

2. 推送代码后，Workflow 每30分钟自动扫描

3. 手动触发：Actions → Money Printer Bot → Run workflow

## 策略

- 现货-合约价差套利（资金费率套利）
- 风控：止损2%、止盈4%、日亏损上限5%
- 通知：Telegeam 推送套利机会
