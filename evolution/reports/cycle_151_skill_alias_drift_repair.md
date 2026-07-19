# Cycle 151 Skill Alias Drift Repair (2026-07-17)

## 结论
- 状态：已达成
- 一句话结论：cron 9 步验证 step 2（alias drift auto-detect）命中 drift=1，drift 源为 `references/cron-verification-tool-invocation-pitfalls.md`（root 在 2026-07-16 扩展过但 mlops 未同步）+ `SKILL.md` 同步段单 bullet 差异。已同步 SKILL.md + references + scripts 到 mlops alias，最终 `alias_drift=0`。

## 任务前真实性声明
- 可真实执行：cp/sha256sum/diff/registry parse/EVM/Rust gate
- 需要工具/资源：filesystem + Python + Rust apex_devour binary
- 当前限制：无
- 幻觉风险：低，所有步骤均有落盘 verify

## 代入公式

本轮无新可测增量，沿用 APEX 基础公式：

```
Delta_G = G_base * (Lambda * Theta * K * xi * Psi * Phi) / (H * T * epsilon)
G_base = 0.50, Delta_G_current = 1.0581, Delta_G_candidate = 1.404
```

代入 drift repair 上下文：

- 增益因子：本轮无新增（status=completed_cron_alias_drift_repair，gain_ratio=1.0）
- drift 触发面：root ↔ mlops SKILL.md + references/cron-verification-tool-invocation-pitfalls.md
- ΔG_candidate 不变（沿用 cycle_150 = 1.404）

## 找问题

cron 9 步验证 step 2（alias drift auto-detect）输出：

```
sha256(root SKILL.md) = 961041c4cd662bbff663b1c9c5154e5d4c37ff8491c2e3ac9fb5aebeb80c0b98
sha256(mlops SKILL.md) = be3789957a9d83cc173f47779ee8c5249492149d0e14dcf8e58ff96935eec5b2
diff references/ 输出 1 行:
  Files ...cron-verification-tool-invocation-pitfalls.md differ
```

drift 文件根因（追溯）：
1. `references/cron-verification-tool-invocation-pitfalls.md` 在 2026-07-16 由 root alias 扩展（增加「Dashboard script: CLI invocation only」与「Recovery-first principle」两段，size 1430→3331 字节），mlops 仍为 2026-07-01 的 1430 字节版本。
2. `SKILL.md` 的 `cron-verification-tool-invocation-pitfalls.md` 引用 bullet 在 2026-07-16 同步添加「2026-07-16 extension: dashboard script CLI-only」说明，mlops bullet 缺失该说明。

判定：drift=1 → 必走 `completed_cron_alias_drift_repair` 模式（cycle_138 cycle_137 强化规则），禁止 verification/watch 吞掉。

## 优化

执行 5 步修复 SOP（按 SKILL.md §cycle_137 + cycle_138）：

1. **备份**：无需新备份（修复目标为 skills alias，不是 jobs.json / SOUL.md）
2. **同步 SKILL.md**：`cp ~/.hermes/skills/apex-spiral-v10/SKILL.md ~/.hermes/skills/mlops/apex-spiral-v10/SKILL.md` + `chmod 600`
3. **同步 references/**：`cp ~/.hermes/skills/apex-spiral-v10/references/cron-verification-tool-invocation-pitfalls.md ~/.hermes/skills/mlops/apex-spiral-v10/references/cron-verification-tool-invocation-pitfalls.md` + `chmod 600`
4. **同步 scripts/**：无需同步（diff -q scripts/ 干净）
5. **验证**：sha256sum 双侧一致 + diff -q references/ + scripts/ 无输出 + 79/79 references 计数一致

## 验证与证据

```text
sha256sum 双侧一致:
  root   = 961041c4cd662bbff663b1c9c5154e5d4c37ff8491c2e3ac9fb5aebeb80c0b98
  mlops  = 961041c4cd662bbff663b1c9c5154e5d4c37ff8491c2e3ac9fb5aebeb80c0b98  ✓

cron-verification-tool-invocation-pitfalls.md:
  root   = 7e81f729afb63a31892046a4fcd21c7063a4d5fa296f6650e31c61cc39124eff
  mlops  = 7e81f729afb63a31892046a4fcd21c7063a4d5fa296f6650e31c61cc39124eff  ✓

最终 alias gate:
  diff -q references/  → 0 输出
  diff -q scripts/    → 0 输出
  alias_drift = 0
  references_count = 79/79

apex_devour gate:
  Delta_G_current=1.0581  G_neuro=1.1142  G_self=1.0908  G_evm=1.0600  G_devour=1.0000
  Delta_G_candidate=1.4040  gate_open=true  5/5 gates pass

EVM:
  EVM=0.7691 defect_rate=0.0000 G_evm=1.0600

Orphan scan:
  file_count=21 registered_count=21 orphaned=[]

Apex version: 0.3.0  ✓
```

## 未完成 / 未验证 / 风险

- 无（所有步骤已落盘 verify）
- 复发风险：medium。cycle_150/151 连续两次漂移都源自 root 单独扩展 references/*.md 后 mlops 未同步。下次任何 write_file / patch 改 references/ 必须在同 turn 完成 cp + sha256sum。

## 真实性门控结论

- 是否存在幻觉：否
- 说明：所有 sha256 / diff / gate 输出均为实际命令运行结果；cp + chmod + sha256sum 全部 verify pass；registry cycle_151 字段已写入。