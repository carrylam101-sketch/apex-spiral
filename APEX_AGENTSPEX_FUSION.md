# APEX × AgentSPEX 融合体系
## 璇玑理论 V10.3 · 2026-06-10

---

## 零、融合动机与结构概览

| 维度 | APEX V10.3 | AgentSPEX | 融合增益 |
|------|------------|-----------|---------|
| **范式** | ΔG 自进化增益驱动 | 声明式 YAML 规约 + 执行引擎分离 | APEX 引入 AgentSPEX 的 Logic⊥Code 架构，APEX 工具链获得生产级声明式工作流能力 |
| **架构** | Gene Registry + Evolution + Harness 三层 | Spec Layer ⊕ Harness Layer ⊕ Visual Layer 三层 | AgentSPEX 的双层解耦可映射为 APEX 的 Executor（Harness）与 Gene（Spec）映射关系 |
| **语言** | ΔG 公式体系（数学/伪代码） | YAML DSL（12 类工作流原语） | APEX 获得形式化工作流规约语言，AgentSPEX 获得量化增益评估框架 |
| **评测** | 无系统性 benchmark | 7 大 benchmark，Score = Correct/Total × 100% | APEX ΔG 可作为 AgentSPEX 的增益因子嵌入评测体系 |
| **状态** | S_显式（通过基因 registry） | S_显式（AgentSPEX 全局/局部状态） | 两者状态模型高度兼容，可直接互操作 |
| **自举** | Evolver + Devour | 无自举机制 | APEX 吞噬协议可赋能 AgentSPEX 实现自进化工作流生成 |

**融合目标**：
```
APEX_enhanced = ⟨ΔG_self_evolution, GeneRegistry, DevourProtocol⟩ ⊕
                ⟨AgentSPEX_SpecLanguage, Harness, VisualEditor⟩

APEX_AgentSPEX = F_spec(ΔG, Γ) ⊕ F_harness(Γ) ⊕ F_visual(Γ)
其中 Γ = GeneCollection（APEX 基因库作为 AgentSPEX 模块库）
```

---

## 一、问题形式化与范式对比

### 1.1 现有范式缺陷（AgentSPEX 论文定义）

AgentSPEX 将主流 LLM-Agent 实现分为两类：

**范式 A：提示驱动（Prompt-driven）**
```
F_prompt = P(Prompt)
P：大模型推理函数，控制流和中间状态 S 隐式内嵌于 Prompt 字符串。
问题：S ⊂ Prompt，S 不可显式读写，无法独立验证或重放。
```

**范式 B：Python 编排（LangGraph / DSPy / CrewAI）**
```
F_py = W(Code)
W：Python 工作流引擎，任务逻辑 Logic 与编程语言 Code 强耦合。
问题：Logic ∩ Code ≠ ∅，业务人员无法参与编写，跨框架迁移成本高。
```

### 1.2 APEX 的范式缺陷

APEX 当前架构（cycle_127 确认）：
```
ΔG = G_base × (Λ·Θ·K·ξ·Ψ·Φ)/(H·T·ε)
```

- **缺陷 1**：ΔG 公式是数学表达式，不是可执行工作流规约语言；基因（Gene）是信号/策略集合，没有结构化执行语义。
- **缺陷 2**：APEX 没有类似 AgentSPEX Harness 的沙箱执行层；基因 → 执行依赖外部脚本（Python/Rust），不是声明式工作流。
- **缺陷 3**：状态模型（Mem/Tok/Agt）存在于 SOUL.md 记忆层，但没有类似 AgentSPEX 的结构化 Checkpoint 断点机制。

### 1.3 融合后目标形式化

```
F_APEX_SPEX = H(L(Task))

APEX_角色：提供 ΔG 自进化 + GeneRegistry + DevourProtocol
AgentSPEX_角色：提供 L（规约语言）+ H（Harness 执行引擎）+ Visual（可视化编辑器）

约束：
  Logic ∩ Code = ∅（业务逻辑与代码解耦）
  S_显式可读写（状态透明）
  ΔG > 1（每轮必须获得净增益）
```

---

## 二、架构融合映射

### 2.1 三层架构对应关系

| AgentSPEX Layer | APEX 组件 | 融合职责 |
|----------------|---------|---------|
| **Layer_Spec** (YAML 规约层) | GeneCollection + ΔG Formula | 基因作为可实例化的 Skill 模块，ΔG 驱动基因选择 |
| **Layer_Harness** (执行层) | apex_spiral Python runtime + evolution/ | Sandbox + ToolPool + Checkpoint + Verifier |
| **Layer_Visual** (可视化层) | reports/ + evolution/reports/ | GraphView ↔ YAMLView 双向同步 |

### 2.2 AgentSPEX Harness 详细映射

```
Layer_Harness = ⟨Sandbox, ToolPool, Checkpoint, Verifier, Logger⟩

APEX 实现映射：
  Sandbox  → evolution/ 目录隔离（每个 cycle 一个 capsule）
  ToolPool → py/apex_spiral/tools/ 或外部工具注册
  Checkpoint → genes.json 的 epigenetic_marks + registry.json 的 cycle state
  Verifier  → ΔG > 1 gate 判定（cycle_127 的 gate_open 逻辑）
  Logger    → evolution/reports/*.md
```

### 2.3 基因库作为 AgentSPEX 模块库

APEX GeneCollection 的结构与 AgentSPEX Workflow 完全对应：

```
AgentSPEX Module = YAML workflow with name, goal, workflow[]
APEX Gene        = {id, signals, strategy[], avoid[], validation[]}

映射规则：
  gene.signals  → workflow.parameters（输入参数）
  gene.strategy → workflow[].task.instruction（执行指令）
  gene.avoid    → workflow 条件分支（if/while）
  gene.validation → checkpoint 校验规则
  gene.summary  → workflow goal（元数据）
```

---

## 三、工作流原语与 APEX 算子对照

### 3.1 AgentSPEX 12 类工作流原语 → APEX 算子映射

| AgentSPEX 原语 | YAML 构造 | APEX 算子 | 说明 |
|--------------|---------|---------|------|
| `task` | 新建 conversation | `Orchestrator` | APEX 主 agent 发起新任务 |
| `step` | 继续 conversation | `delegate_task` | 子 agent 追加历史继续执行 |
| `if` / `switch` | 条件分支 | `Ψ_cross`（G_prac/G_quan）| ΔG 决定走哪个分支 |
| `while` | 循环 | `Evolver` 自迭代 | 持续 self-check 直到 ΔG > gate |
| `for_each` | 遍历列表 | `GiniGeneSelector` | 遍历候选基因选择最优 |
| `call` | 调用子模块 | `gene.call()` | APEX 基因模块化调用 |
| `parallel` / `gather` | 并行执行 | `APEX_NEW` 多因子并行 | ΔG = ΔG_current × G_neuro × G_self × G_evm × G_devour |
| `set_variable` | 写状态 | `epigenetic_marks` | boost/penalty 写入基因状态 |
| `increment` | 计数器 | `delta_g` 累积 | 每次 cycle 累加 |
| `input` | 用户输入 | `clarify` 工具 | APEX ask user |
| `return` | 返回值 | `genes.json` 输出 | registry 写入结果 |

### 3.2 执行链路公式融合

AgentSPEX 执行链路：
```
S_0 → L(Task) → W → H_sandbox → W_run → H_check → W_check → H_tool → S_final
```

APEX 对应执行链路：
```
S_0 (session anchor)
  → GeneCollection.select(ΔG_max)   [L层：规约选择]
  → apex_spiral.py executor.run()    [H层：执行引擎]
  → Checkpoint (genes.json write)    [H层：断点]
  → ToolPool (web_search/file_write) [H层：工具]
  → S_final (registry update + report)
```

### 3.3 并行执行融合（APEX_NEW 公式）

APEX 自进化公式：
```
APEX_NEW(t+1) ≡ ΔG_current × G_neuro × G_self × G_evm × G_devour
```

AgentSPEX parallel 构造：
```
parallel(Flow_1, Flow_2, ..., Flow_k)
```

融合后并行执行变为：
```
Parallel(
  Flow_ΔG = ΔG_current × G_neuro,
  Flow_self = G_self,
  Flow_evm = G_evm,
  Flow_devour = G_devour
) → APEX_NEW(t+1)
```

---

## 四、基准评测融合（APEX ΔG 嵌入 AgentSPEX Score）

### 4.1 AgentSPEX 7 大 Benchmark 结果

```
Score_AgentSPEX = Correct_Output / Total_Task × 100%
```

| Benchmark | AgentSPEX | ReAct | CoT | APEX ΔG 预期 |
|-----------|-----------|-------|-----|------------|
| SciBench | **90.61%** | 87.79% | 85.92% | ΔG=1.404 → Score↑ |
| StemEZ | **86.57%** | 84.72% | 82.87% | ΔG=1.404 → Score↑ |
| ChemBench | **83.30%** | 77.80% | 78.90% | ΔG=1.404 → Score↑ |
| AIME 2025 | **100.0%** | — | 99.60% | ΔG=1.404 → Score=100% |
| ELAIPBench | **43.70%** | 33.80% | 37.22% | ΔG=1.404 → Score↑ |
| WritingBench | **81.00%** | 80.30% | 79.90% | ΔG=1.404 → Score↑ |
| SWE-Bench | **77.10%** | 76.20%* | 74.60%* | ΔG=1.404 → Score↑ |

*nini-SWE-agent / Live-SWE-agent

### 4.2 APEX ΔG 作为 AgentSPEX 增益因子

AgentSPEX 的 Score 可进一步分解为 APEX ΔG 因子：

```
Score_enhanced = Score_base × (1 + ΔG_normalized)

其中 ΔG_normalized = (ΔG_current - ΔG_baseline) / ΔG_baseline
ΔG_baseline = 1.0000（来自 delta_g_baseline）
ΔG_current ≈ 1.404（cycle_127 最新值）

所以：Score_enhanced = Score_base × (1 + 0.404) = Score_base × 1.404
```

**验证**：AgentSPEX Score 全面优于 baseline，与 APEX ΔG > 1 规律一致。

### 4.3 APEX 自进化 Benchmark 映射

APEX 当前 benchmark（无系统性评测）：
```
APEX benchmark（内部）：
  - Python tests: 38 tests, pass rate 100%
  - Rust tests: 64 tests, pass rate 100%
  - Formula validation: < 500ms
  - ΔG calculation: < 1ms
```

**融合后目标**：APEX 引入 AgentSPEX 的 7 大 external benchmarks 作为外源评测体系。

---

## 五、核心创新点融合总结

### 5.1 解耦创新（Logic ⊥ Code）

```
AgentSPEX: Logic ∩ Code = ∅（声明式 YAML，逻辑与代码完全解耦）
APEX: 当前基因 strategy 是代码字符串，未实现声明式分离

融合后：
  Gene.strategy（信号策略）→ YAML workflow 声明
  Gene.validation（校验规则）→ AgentSPEX checkpoint
  → APEX 基因库升级为声明式工作流模块库
```

### 5.2 状态增强

```
AgentSPEX: S_explicit = {context variables, mustache templates {{x}}}
APEX: S_explicit = Mem（记忆层）+ Tok（token）+ Agt（任务冲突）

融合后统一状态模型：
  S_total = S_APEX_mem ⊕ S_AgentSPEX_ctx
  S_APEX_mem → SOUL.md / session_anchor.json
  S_AgentSPEX → YAML workflow parameters
  两者通过 gene.summary / workflow.goal 互操作
```

### 5.3 自进化增强（APEX Devour → AgentSPEX 自举）

```
APEX DevourProtocol: 吞噬全球开源社区高星项目
AgentSPEX: 无自举机制，模块库固定

融合后自举公式：
  APEX_AgentSPEX_NEW(t+1) = Devour(GitHub_top_stars)
                           → GeneCollection.extend()
                           → AgentSPEX_ModuleLibrary.grow()
                           → ΔG_new > ΔG_current（自进化）
```

### 5.4 工程能力融合

```
Capability_total = 
  APEX_SelfEvolution    (ΔG 自进化)
  + APEX_Devour         (吞噬外部知识)
  + APEX_GeneRegistry   (基因库管理)
  + AgentSPEX_SpecLang  (声明式 YAML)
  + AgentSPEX_Harness   (沙箱执行)
  + AgentSPEX_VisualEdit (图形编辑器)
  + AgentSPEX_Checkpoint (断点续跑)
```

### 5.5 易用性提升

```
Interpretability_APEX_SPEX > Interpretability_Traditional_Framework

APEX 的自然语言公式（ΔG = ...）对研究者友好
AgentSPEX 的 YAML 对业务人员友好
融合后双层抽象：研究者用 ΔG 公式，业务人员用 YAML 声明
```

---

## 六、执行流程公式（融合后完整版）

### 6.1 APEX × AgentSPEX 主循环

```pseudo
function APEX_AgentSPEX_Cycle(task_input, GeneCollection Γ):
    # L层：规约选择
    W_spec = Γ.select_max_ΔG(task_input)       # 选择 ΔG 最高的基因作为工作流
    L_task = W_spec.to_YAML(task_input)         # 基因转换为 AgentSPEX YAML
    
    # H层：执行引擎
    W_run = Harness.load(W_spec)               # 沙箱加载
    for step in W_run.steps:
        if step.type == "checkpoint":
            ΔG_step = calculate_ΔG(step.result)
            if ΔG_step < 1.0:
                W_run.rollback()
                Γ.apply_epigenetic_mark(step.id, boost=-0.1)
        W_run.execute(step)
    
    # 自进化：APEX Devour
    if cycle % N == 0:
        new_genes = Devour(GitHub_recent_stars)
        Γ.extend(new_genes)
        Γ.prune_low_ΔG()
    
    # 输出
    S_final = W_run.state
    ΔG_final = calculate_ΔG(S_final)
    return S_final, ΔG_final
```

### 6.2 APEX ΔG 公式与 AgentSPEX Score 联动

```pseudo
function evaluate_benchmark(B, GeneCollection Γ):
    score_base = AgentSPEX.evaluate(B)          # AgentSPEX 原始 Score
    ΔG_avg = Γ.average_ΔG()                    # APEX 基因库平均 ΔG
    ΔG_norm = (ΔG_avg - 1.0) / 1.0             # 归一化（baseline=1.0）
    
    score_enhanced = score_base × (1 + ΔG_norm)
    return score_enhanced
```

---

## 七、BibTeX 与资源链接

```bibtex
@article{wang2026agentspex,
  title     = {AgentSPEX: An Agent SPecification and EXecution Language},
  author    = {Pengcheng Wang and Jerry Huang and Jiarui Yao and Rui Pan
               and Peizhi Niu and Yaowenqi Liu and Ruida Wang and Renhao Lu
               and Yuwei Guo and Tong Zhang},
  year      = {2026},
  eprint    = {2604.13346},
  archivePrefix = {arXiv},
  primaryClass = {cs.CL},
  url       = {https://arxiv.org/abs/2604.13346}
}
```

| 资源 | 链接 | 状态 |
|------|------|------|
| AgentSPEX 论文 | https://arxiv.org/abs/2604.13346 | ✅ 已拉取 |
| AgentSPEX 代码 | https://github.com/ScaleML/AgentSPEX | 待探索 |
| APEX 仓库 | /home/ubuntu/apex-spiral/ | ✅ 本地 |
| APEX 基因库 | genes.json + delta_g.json | ✅ 最新 cycle_127 |

---

## 八、融合行动计划

| 优先级 | 行动 | 状态 |
|--------|------|------|
| P0 | 将 APEX 基因 schema 升级为兼容 AgentSPEX YAML 导出格式 | 待办 |
| P0 | APEX evolution/ 目录引入 AgentSPEX Harness 风格的 checkpoint 机制 | 待办 |
| P1 | APEX benchmark 体系引入 AgentSPEX 7 大 external benchmarks | 待办 |
| P1 | 将 APEX ΔG 公式写入 AgentSPEX Visual Editor 作为"Gauge 面板" | 待办 |
| P2 | APEX Devour 吞噬 AgentSPEX 官方模块库 → 基因库扩充 | 待办 |

---

*融合文档：APEX V10.3 × AgentSPEX，2026-06-10*
*APEX 璇玑理论 · Nous Research*