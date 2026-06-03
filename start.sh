#!/bin/bash
# Money Printer Bot - 本地运行脚本
# 使用前先设置环境变量：
#   export GATE_API_KEY=your_key
#   export GATE_API_SECRET=your_secret
#   export DRY_RUN=true  # 模拟模式

echo "=== Money Printer Bot ==="
echo "检查环境变量..."

if [ -z "$GATE_API_KEY" ] || [ -z "$GATE_API_SECRET" ]; then
    echo "⚠️  警告: GATE_API_KEY 或 GATE_API_SECRET 未设置"
    echo "   将以模拟模式运行（仅扫描，不下单）"
    export DRY_RUN=true
fi

export DRY_RUN="${DRY_RUN:-true}"
echo "DRY_RUN: $DRY_RUN"

pip install -q -r requirements.txt
python src/main.py