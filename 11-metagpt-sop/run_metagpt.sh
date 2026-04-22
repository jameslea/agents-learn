#!/bin/bash
# MetaGPT SOP 演示启动脚本
# 通过预导出环境变量解决 MetaGPT 在 import 阶段就读取配置的问题

# 读取项目根目录的 .env 文件
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"

if [ ! -f "$ENV_FILE" ]; then
    echo "❌ 找不到 .env 文件: $ENV_FILE"
    exit 1
fi

# 将 .env 中的变量导出到当前 shell 环境（MetaGPT import 时能读到）
set -a
source "$ENV_FILE"
set +a

echo "✅ 已从 .env 加载环境变量："
echo "   OPENAI_API_KEY = ${OPENAI_API_KEY:0:10}..."
echo "   OPENAI_BASE_URL = $OPENAI_BASE_URL"
echo "   MODEL_NAME = $MODEL_NAME"
echo ""

# 使用独立的 MetaGPT venv 运行脚本
"$SCRIPT_DIR/venv_metagpt/bin/python" "$SCRIPT_DIR/metagpt_sop_demo.py"
