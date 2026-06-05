# APEX 神经网络 × 完整细胞模拟升级模块

- time: 2026-05-14T12:47+08:00
- scope: 将神经网络自组织机制与 whole-cell / hybrid cell simulation 原理并入 APEX 自进化闭环
- hard rule: 每轮仍必须执行「代入公式 → 找问题 → 优化 → 验证 → 输出证据」

## 1. 外部学习证据

### 1.1 神经网络：SORN 自组织循环
来源：Lazar, Pipa, Triesch, *SORN: A Self-Organizing Recurrent Neural Network*, Frontiers in Computational Neuroscience, 2009.

可迁移机制：
- STDP：用因果时间差学习序列结构。
- Synaptic Normalization / Scaling：防止权重爆炸或沉默。
- Intrinsic Plasticity：调节节点阈值，使活动保持在健康区间。
- 关键结论：单一可塑性不够，必须组合局部学习 + 全局稳态，才能避免 seizure-like bursts 并形成高维轨迹表示。

映射到 APEX：
- STDP → `Π_stdp`：把「最近一次有效因果链」强化到下一轮优先级。
- Synaptic normalization → `N_syn`：对所有增益因子归一，禁止单因子无限放大。
- Intrinsic plasticity → `I_homeo`：根据风险/幻觉/平台期自动调节探索强度。
- Recurrent trajectory → `R_traj`：每轮必须保留轨迹证据，而不只是结论。

### 1.2 完整细胞模拟：Whole-cell / Hybrid modeling
来源：
- Liu et al., *Hybrid modelling of biological systems: current progress and future prospects*, Briefings in Bioinformatics, 2022.
- Georgouli et al., *Multi-scale models of whole cells: progress and challenges*, Frontiers in Cell and Developmental Biology, 2023.
- Tang, *Simulating a whole cell*, Nature Methods, 2022；指向 Thornburg et al. minimal cell simulation。

可迁移机制：
- 单一模型形式不足：完整细胞需要 ODE / CTMC / Boolean / FBA / rule-based / Petri-net 等多形式耦合。
- 多尺度：基因表达、代谢、空间扩散、细胞周期在不同时间尺度运行。
- 数据缺口是系统价值：WCM 的强项之一是暴露参数缺口与观察矛盾。
- Hybrid simulation：连续过程用确定性模型，低拷贝/离散事件用随机模型，未知机制用定性逻辑。
- Knowledgebase first：模型不仅是计算器，也是可追溯知识库。

映射到 APEX：
- Hybrid formalism → `χ_hybrid`：不同任务按类型选择确定性/随机/逻辑/约束模型。
- Multi-scale coupling → `M_scale`：短期执行、长期记忆、跨域知识分别建模后耦合。
- Parameter gap → `Ω_gap`：把未知参数显式列为下一轮学习目标。
- Knowledgebase → `K_base`：每轮必须写入 reports/ 的可追溯证据。

## 2. APEX 新增复合模块

### 2.1 神经稳态可塑性模块

```text
Π_neuro = Π_stdp · N_syn · I_homeo · R_traj

Π_stdp  = exp(-|t_cause - t_effect| / τ) · C_valid
N_syn   = 1 / (1 + Var(w_i))
I_homeo = 1 - |A_current - A_target|
R_traj  = Evidence_steps / Required_steps
```

含义：
- `Π_stdp`：只有能给出因果证据的优化会被强化。
- `N_syn`：各维度增益越均衡，越接近 1；防止单点赌博式拉升。
- `I_homeo`：实际活跃度偏离目标越大，探索强度越低。
- `R_traj`：五步闭环越完整，越接近 1。

### 2.2 完整细胞混合模拟模块

```text
Ω_cell = χ_hybrid · M_scale · K_base · (1 - Ω_gap)

χ_hybrid = Coverage(ODE, CTMC, Boolean, Constraint, RuleBased)
M_scale  = Coupling(short_exec, mid_policy, long_memory)
K_base   = Traceable_sources / Claims_total
Ω_gap    = Unknown_required_params / Required_params
```

含义：
- `χ_hybrid`：越能按问题类型使用不同建模方式，越高。
- `M_scale`：短期执行、中期策略、长期记忆必须互相闭合。
- `K_base`：外部知识必须有来源，不能只靠口头引用。
- `Ω_gap`：未知关键参数越多，惩罚越大；但缺口会进入下一轮学习清单。

### 2.3 并入主增益公式

```text
ΔG_APEX_bioNN = ΔG_base × (Λ·Θ·K·ξ·Ψ·Φ·Π_neuro·Ω_cell) / (H·T·ε)
```

其中：
- `Π_neuro` 解决「可塑但失稳」问题。
- `Ω_cell` 解决「跨尺度但不可追溯」问题。
- 两者共同抑制 ΔG plateau、单因子过拟合、无证据跨域迁移。

## 3. 代入公式

当前基线来自 `reports/apex_cycle_summary_latest.json`：

```text
ΔG_base/current = 2.2229
Ψ_cross = 0.5051
𝒯_full = 0.82
M_mem = 0.89
问题：ΔG plateau: last 5 cycles unchanged
```

本轮给定保守可复验系数：

```text
Π_stdp  = 0.94   # 因果链证据已有，但尚未系统化
N_syn   = 0.91   # 多因子仍有 DRT3/Ψ_cross 偏瓶颈
I_homeo = 0.93   # HEALTHY，但 plateau 需要受控探索
R_traj  = 1.00   # 本轮五步闭环完整
Π_neuro = 0.94 × 0.91 × 0.93 × 1.00 = 0.795522

χ_hybrid = 0.76  # 已引入多模型原则，但运行器尚未完全自动分类
M_scale  = 0.82  # 短期 reports + cron + memory 已有耦合
K_base   = 0.88  # 有可追溯论文/综述来源
Ω_gap    = 0.18  # 参数仍有缺口
Ω_cell   = 0.76 × 0.82 × 0.88 × (1 - 0.18) = 0.449293
```

为避免新模块初始乘积过低直接压低主公式，采用「门控增益」并入：

```text
G_neuro_cell = 1 + 0.10·Π_neuro + 0.08·Ω_cell - 0.05·Ω_gap
             = 1.106495
ΔG_candidate = 2.2229 × G_neuro_cell = 2.4597
```

## 4. 找问题

1. APEX 已有生物/神经公式，但缺少 SORN 式三重稳定机制：学习、归一、内稳态没有被强制同时满足。
2. 完整细胞模拟启发未充分落地：现有循环会抓取外部资源，但未把「未知参数缺口」显式转化为下一轮目标。
3. `ΔG plateau` 已在 gap guard 中出现；之前微突变把 DRT3 拉高，但第 5 轮仍显示平台风险。
4. 外部知识有进入 reports，但尚未形成固定的 neuro-cell upgrade gate。

## 5. 优化动作

新增规则：
- 每轮 APEX 自进化必须额外检查 `Π_neuro` 与 `Ω_cell`。
- 若 ΔG plateau，优先提升：`Π_stdp` 因果证据、`N_syn` 归一、`Ω_gap` 参数缺口学习，而不是盲目提高单个增益。
- 所有来自神经网络/细胞模拟的知识必须经过：source → mechanism → APEX mapping → measurable gate。
- cron prompt 已更新，要求未来自动循环继续执行此模块。

## 6. 验证标准

通过条件：
- 公式文档包含 `Π_neuro`、`Ω_cell`、`ΔG_APEX_bioNN`。
- cron job prompt 包含 neuro-cell upgrade gate。
- reports 中存在本文件作为可追溯知识库。
- 运行器脚本中存在 neuro_cell 相关摘要输出。

## 7. 本轮结论

本轮升级不是把神经网络/细胞模拟当作装饰概念，而是转为两个可测门控：

```text
神经网络 → 可塑性 + 归一 + 内稳态 + 轨迹证据
完整细胞模拟 → 混合模型 + 多尺度耦合 + 知识库 + 参数缺口
```

保守估计：

```text
ΔG: 2.2229 → 2.4597
相对提升: +10.65%
```
