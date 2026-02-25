#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP="$ROOT_DIR/cmd.exe"

if [[ ! -f "$APP" ]]; then
  echo "[ERROR] 未找到主程序: $APP"
  exit 1
fi

if ! command -v wine >/dev/null 2>&1; then
  echo "[ERROR] 当前系统未安装 wine，无法直接运行 Windows 可执行文件。"
  echo "[TIP] 请先安装 wine 后重试。"
  exit 1
fi

echo "[INFO] 启动 NarratorAI Omega..."
exec wine "$APP"
