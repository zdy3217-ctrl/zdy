# NarratorAI Omega（稳定优化 + 一致性优化版）

本仓库以 `cmd.exe` 为核心交付物。你要求“**不新增业务功能，只在原有功能上持续优化**”，所以本轮继续采用**非侵入式优化**：

- 不修改 `cmd.exe`
- 增强检查、约束、质检与可追踪性
- 重点强化：**语音一致性、动漫角色一致性、场景一致性、物品一致性**

---

## 本轮优化重点（10项）

1. 语音一致性规则（speaker 固定）
2. 语音参数范围约束（pitch/speed 区间）
3. 角色 ID 一致性检查
4. 角色核心特征稳定性检查
5. 角色漂移特征拦截（forbidden drift）
6. 场景锚点一致性检查（style anchor）
7. 场景光照一致性检查
8. 场景色板一致性检查
9. 物品身份标签一致性检查
10. 物品材质/尺寸带宽一致性检查

---

## 目录结构

- `cmd.exe`：NarratorAI Omega 主程序（未改动）
- `tools/quality_audit.py`：基础质量审计（完整性/环境）
- `tools/consistency_audit.py`：一致性质检（语音/角色/场景/物品）
- `tools/consistency_profile.example.json`：一致性配置模板
- `tools/sample_timeline.consistent.json`：一致性样例输入
- `tools/verify.sh`：一键执行全部检查
- `tools/launch.sh`：安全启动脚本

---

## 一键检查

```bash
bash tools/verify.sh
```

会生成：

- `reports/quality_audit.json`
- `reports/consistency_audit.json`

---

## 启动应用

```bash
bash tools/launch.sh
```

> 若未安装 Wine，脚本会提示并退出。

---

## 如何接入你的真实数据

你可以把生成结果导出成如下结构的 JSON（时间线/分镜均可）：

```json
{
  "frames": [
    {
      "voice": {"speaker_id": "...", "pitch": 0.0, "speed": 1.0},
      "character": {"id": "...", "traits": ["..."]},
      "scene": {"style_anchor": "...", "lighting": "...", "palette": "..."},
      "object": [{"identity_tags": ["..."], "material": "...", "size": "..."}]
    }
  ]
}
```

并执行：

```bash
python3 tools/consistency_audit.py --profile tools/consistency_profile.example.json --input your_timeline.json
```

这样就能在不改核心程序的情况下，持续迭代一致性优化。
