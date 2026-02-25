#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[STEP] 运行基础质量审计"
python3 tools/quality_audit.py

echo "[STEP] 运行一致性质检（正样本：应通过）"
python3 tools/consistency_audit.py \
  --profile tools/consistency_profile.example.json \
  --input tools/sample_timeline.consistent.json

echo "[STEP] 运行一致性质检（反样本：应失败，用于验证规则有效）"
if python3 tools/consistency_audit.py \
  --profile tools/consistency_profile.example.json \
  --input tools/sample_timeline.inconsistent.json; then
  echo "[ERROR] 反样本未触发失败，规则可能失效。"
  exit 1
else
  echo "[PASS] 反样本正确触发失败，规则有效。"
fi

echo "[DONE] 全部检查已执行完成。"
