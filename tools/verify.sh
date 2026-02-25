#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[STEP] 运行基础质量审计"
python3 tools/quality_audit.py

echo "[STEP] 运行一致性质检（语音/角色/场景/物品）"
python3 tools/consistency_audit.py \
  --profile tools/consistency_profile.example.json \
  --input tools/sample_timeline.consistent.json

echo "[DONE] 全部检查已执行完成。"
