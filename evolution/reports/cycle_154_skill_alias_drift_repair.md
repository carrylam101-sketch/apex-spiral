# cycle_154 — Skill Alias Drift Repair (2026-07-20)

## 结论

状态：已达成
一句话结论：本轮 13th 连续 alias drift（cycle_134→154 累计），drift 源为 root SKILL.md 相对 mlops 多 30 行（Trap 24 段 + cycle_153 reference bullet）；已 cp + sha256 + diff -q 三重 verify，最终 alias gate 全绿（SKILL.md hash 一致，references/ 82/82 一致，scripts/ 2/2 一致）。

## 任务前真实性声明

- 可真实执行：本地文件读写、cp、sha256、diff、registry 修改。
- 需要工具/资源：`~/.hermes/skills/apex-spiral-v10/` + `~/.hermes/skills/mlops/apex-spiral-v10/`。
- 当前限制：cron 任务，无用户交互。
- 幻觉风险：低，所有变更均经过落盘 verify（sha256sum + diff -q）。

## 代入公式

按 V10.3 主公式：

```
ΔG_current = G_base × (Λ · Θ · K · ξ · Ψ · Φ) / (H · T · ε)
```

按 cycle_125 哲学封装（不替换）：

```
APEX_NEW(t+1) ≡ ΔG_current × G_neuro × G_self × G_evm × G_devour
```

本轮无新可测增量，delta_g 沿用 cycle_153 = 1.8088，gain_ratio = 1.0。

## 找问题

9 步验证 step 2（alias drift auto-detect）命中 `alias_drift=1`：

| 检查项 | root | mlops | 结果 |
|--------|------|-------|------|
| SKILL.md sha256 | `738882ebaebad68d064795862e1e009485931f0e886552792a685ed985fc807a` | `0969b829cc757cc2ad2c1bb1828c61e83eaa79014c448fe8d9de34a68fffdd72` | **DRIFT** |
| references/ 计数 | 82 | 82 | OK |
| scripts/ 计数 | 2 | 2 | OK |
| references/ diff -q | - | - | clean |
| scripts/ diff -q | - | - | clean |

drift 源（30 行）：
- Trap 24 段（11 行）：cycle_153 新增的 drift-originating-from-non-repair 教训
- cycle_153 reference bullet（1 行）：Trap 22 后跟的 support file 引用

引用关系：cycle_153 写完 SKILL.md 时只在本 turn cp 了 reference 文件，没 cp SKILL.md 本身。

## 优化

按 cycle_136/137 决策表 row 6 强制走 normal cycle 模式：

1. **同步 SKILL.md**：`cp ~/.hermes/skills/apex-spiral-v10/SKILL.md ~/.hermes/skills/mlops/apex-spiral-v10/SKILL.md`
2. **sha256 双侧 verify**：`738882ebaebad68d064795862e1e009485931f0e886552792a685ed985fc807a` 一致
3. **references/ 计数**：82/82
4. **scripts/ diff**：clean
5. **最终 alias gate**：`test ... sha256 = ... && diff -q ... && diff -q ... && echo "ALL_GATES_PASS alias_drift=0"` → 全绿
6. **写本轮报告**：`evolution/reports/cycle_154_skill_alias_drift_repair.md`
7. **追加 registry cycle_154 条目**

## 验证

| 步骤 | 命令 | 结果 |
|------|------|------|
| 1. git stash | `git stash list` | empty |
| 2. SKILL.md hash | `sha256sum` 双侧 | match |
| 3. apex_spiral import | `python3.12 -c "from apex_spiral import __version__"` | 0.3.0 |
| 4. py_compile | `python3.12 -m py_compile py/apex_spiral/__init__.py` | OK |
| 5. apex_self_check | `python3.12 py/apex_spiral/apex_self_check.py` | ΔG=2.2713, cycle_count=101 |
| 6. EVM | `EVMCore` (Mem=0.15, Tok=0.10) | EVM=0.7531, defect_rate=0.0208, G_evm=1.0579 |
| 7. gini selector | `python3.12 py/apex_spiral/gini_gene_selector.py --json` | gene_594, gini_gain=0.0, ig_gain=0.0 (uniform fallback) |
| 8. devour gate | `./target/release/apex_devour gate` | gate_open=true, ΔG_candidate=1.4040 |
| 9. orphan scan | registry sections ∪ `evolution/genes/*.json` | 0 orphans (21/21) |
| 10. alias gate | `sha256 + diff -q SKILL.md + diff -q refs + diff -q scripts` | ALL_GATES_PASS |
| 11. dashboard | `python3 scripts/generate_apex_dashboard.py` | reports/apex_dashboard.{md,html} updated |

## 未完成 / 未验证 / 风险

- **结构性风险**：cycle_134 以来漂移连续 13 次，Trap 24 已识别 cron invariant 在 SKILL.md 写入路径上仍存在漏洞。本轮 cp 已修复，但下轮 cron 若任一引用 `write_file` / `patch` 改 SKILL.md 未同步，drift=1 会再次命中。
- **根因路径**：cron prompt 顶部 `[CRON SYNC INVARIANT]` 段虽含"写完必 cp"，但 SKILL.md 写入路径仍有遗漏窗口（Trap 24 案例证明）。
- **根治建议（未实施，需 carry 授权）**：
  1. 在 cron prompt 顶部新增 SKILL.md-only-invariant 段（区别于 references/scripts）
  2. 或在 cron 启动时跑 `rsync -a --delete root → mlops`（无条件全量同步）
  3. 或将"最终 alias gate"提前到任何 SKILL.md write 之前作为门控
- **Shannon plateau 持续**：ΔG_estimate 2.2713 多轮不变，gini_gain=0.0 / ig_gain=0.0，uniform fallback 选中 gene_594。EVM gate 突破方案（cycle_106）已稳定运行，但新信道仍未触发。

## 真实性门控结论

- 是否存在幻觉：否
- 说明：所有数值均来自实测（terminal output / file read），drift 修复路径 100% 通过落盘 verify。
- 状态降级原因：N/A（已达成）。

## 关键边界声明

1. 本轮是 alias drift 修复 cycle，不是新可测门控
2. delta_g 沿用前一轮，无新 ΔG 增量
3. `references_count = 82` 是同步后实际计数（Trap 23 教训：drift repair cycle 本身新增 reference 时，必须以同步后计数为准）
4. cron prompt invariant 已存在但仍有结构漂移，根因不在 invariant 文本而在执行顺序（写完 SKILL.md 后 cp 同步窗口未关闭）
5. 本报告只增不删