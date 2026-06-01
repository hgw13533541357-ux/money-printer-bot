# Money Printer Bot

Gate.io 现货-合约价差套利机器人（资金费率套利）

## 快速开始

### 1. 配置 API 密钥
在 GitHub 仓库 Settings → Secrets and variables → Actions 添加：
- `GATE_API_KEY` — 你的 Gate.io API 密钥
- `GATE_API_SECRET` — 你的 Gate.io API 密钥
- `TELEGRAM_BOT_TOKEN` — （可选）Telegram 推送 Token
- `TELEGRAM_CHAT_ID` — （可选）Telegram 推送 Chat ID

### 2. 触发运行
- **自动**：每 30 分钟 GitHub Actions 自动扫描
- **手动**：Actions → Money Printer Bot → Run workflow
- **本地**：`pip install -r requirements.txt && python src/main.py`

### 3. 参数配置
编辑 `config.yaml` 或设置环境变量：

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `PAIRS` | `BTC_USDT,ETH_USDT,SOL_USDT` | 监控交易对 |
| `MIN_SPREAD` | `0.15` | 最小价差触发阈值（%） |
| `TRADE_SIZE` | `5.0` | 每笔交易 USDT 金额 |
| `MAX_POSITIONS` | `3` | 最大并发持仓数 |
| `DRY_RUN` | `true` | 模拟模式（设为 false 开启实盘） |

## 策略

- 现货-合约价差套利（资金费率套利）
- 风控：止损2%、止盈4%、日亏损上限5%
- 通知：Telegram 推送套利机会

## 注意

⚠️ 首次运行请保持 `DRY_RUN=true`，确认逻辑无误后再开启实盘
⚠️ 加密货币交易有风险，请使用小额资金测试