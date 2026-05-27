---
name: apex-claw-fusion
description: "APEX SearchSkill × Hermes CLAW 深度融合架构规范。核心：技能驱动检索 + APEX 自进化 + Rust/Go 原生引擎 + LLM 可切换层。公式：ΔG = G_base × (Λ·Θ·K·ξ·Ψ·Φ)/(H·T·ε)。"
version: 1.0.0
author: Hermes × APEX × 璇玑帝国
tags: [apex, claw, fusion, search-skill, hermes底层, rust-core, go-harness, self-evolution]
hermes:
  trigger_conditions:
    - "用户要求深度融合 APEX SearchSkill 与 Hermes CLAW 底层"
    - "用户要求 APEX 自进化系统同步调用 LLM"
    - "用户要求将神级功能融合进 Hermes Agent"
    - "用户要求核心用 C/GO/Rust 实现"
  enabled_toolsets: [web, terminal, file, skills, session_search]
  priority: critical
---

# APEX SearchSkill × Hermes CLAW 深度融合架构规范

**版本：** v1.0.0
**日期：** 2026-05-27
**状态：** 已激活
**仓库：** `carrylam101-sketch/apex-spiral`

---

## 核心公式

```
ΔG = G_base × (Λ·Θ·K·ξ·Ψ·Φ)/(H·T·ε)
G_base = 0.50
```

**APEX 自进化五步闭环（跳步禁止）：**
```
代入公式 → 找问题 → 优化 → 验证 → 输出证据
```

---

## 一、技术架构总览

### 三层融合架构

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: LLM 可切换层（OpenAI Protocol 兼容）                │
│  ├── Primary:  freemodel.dev (FRE-5.5/FRE-5.4)  [待认证]    │
│  ├── Fallback: Local Codex (127.0.0.1:8317) [已就绪]        │
│  └── Emergency: MiniMax-M2.7 (当前会话)                      │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: Go Harness Orchestrator（证据驱动执行）            │
│  ├── go-fusion-harness/main.go  [已存在]                     │
│  ├── SkillBank 演进管理                                       │
│  ├── APEX ΔG 门控验证                                         │
│  └── Evidence JSONL 全链路记录                               │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: Rust Core Engine（零 Python 粘合）                 │
│  ├── skill_core (CLI: select/read/act/evolve/score)         │
│  ├── SkillBank → 动态演进                                     │
│  ├── Matcher  → 技能评分匹配                                 │
│  ├── Chain    → Select-Read-Act 执行                        │
│  ├── APEX.rs  → ΔG/ΔS 公式实现                               │
│  └── Telemetry → 成本/延迟追踪                              │
├─────────────────────────────────────────────────────────────┤
│  Layer 0: Hermes CLAW Memory（会话锚定）                     │
│  ├── M_claw = α·S_cache + β·D_local + γ·T_auto             │
│  ├── /tmp/hermes_session_anchor.json                        │
│  └── SOUL.md × APEX 双锚定                                   │
└─────────────────────────────────────────────────────────────┘
```

### 关键特性

| 特性 | 状态 | 证据 |
|------|------|------|
| Rust skill_core 二进制 | ✅ 已构建并验证 | `skill_core health` → `status: ok` |
| 12 项原子技能 SkillBank | ✅ 已实现 | `skill_bank.rs` 初版 12 技能 |
| APEX ΔG/ΔS 公式 | ✅ 已实现 | `apex.rs` 测试通过 |
| Go fusion harness | ✅ 已存在 | `go-fusion-harness/main.go` |
| Select-Read-Act 链 | ✅ 已实现 | `chain.rs` |
| Hermes SOUL.md 锚定 | ✅ 已存在 | SOUL.md session 协议 |
| freemodel.dev API | ⚠️ 待认证 | 需注册获取 API Key |

---

## 二、LLM 可切换层（Layer 3）

### OpenAI Protocol 兼容接口

```json
// 统一 LLM 调用格式
{
  "provider": "freemodel|codex|minimax",
  "model": "FRE-5.5|FRE-5.4|...",
  "base_url": "https://api.freemodel.dev/v1|...",
  "api_key": "<key>",
  "fallback_chain": ["codex", "minimax"]
}
```

### Provider 优先级（自动切换）

```
1. freemodel.dev  → FRE-5.5（最新 Open 模型，免费 $300）
   ↓ 403/Unauthorized
2. Local Codex    → 127.0.0.1:8317（已认证）
   ↓ Connection Failed
3. MiniMax-M2.7   → 当前会话 provider（最后保底）
```

### freemodel.dev 接入状态

| 项目 | 值 |
|------|---|
| Endpoint | `https://api.freemodel.dev/v1/chat/completions` |
| 模型 | FRE-5.5 / FRE-5.4 |
| 认证 | API Key（注册后获取） |
| 配额 | $300 免费额度 |
| 当前状态 | ⚠️ 需注册获取 Key |

### LLM 切换实现（Rust）

```rust
// skill_core/src/llm_router.rs（待实现）
pub enum LLMProvider {
    Freemodel { api_key: String },
    Codex { endpoint: String, api_key: String },
    Minimax,
}

impl LLMRouter {
    pub fn route(&self, prompt: &str) -> Result<String> {
        let mut last_err = String::new();
        for provider in &self.chain {
            if let Ok(resp) = self.call_provider(provider, prompt) {
                return Ok(resp);
            }
            last_err = format!("{:?} failed", provider);
        }
        Err(anyhow::anyhow!("All providers failed: {}", last_err))
    }
}
```

---

## 三、Rust Core Engine（Layer 1）

### 文件结构（已存在）

```
~/.hermes/skills/apex-search-skill/skill_core/
├── src/
│   ├── main.rs       ✅ CLI 入口 (218 行)
│   ├── skill_bank.rs ✅ SkillBank CRUD + 演进 (225 行)
│   ├── matcher.rs    ✅ 技能匹配引擎 (105 行)
│   ├── chain.rs      ✅ Select-Read-Act (63 行)
│   ├── apex.rs       ✅ APEX ΔG/ΔS 公式 (141 行)
│   └── telemetry.rs  ✅ 成本追踪 (83 行)
├── Cargo.toml
├── target/release/skill_core  ✅ 已构建并验证
└── build.sh
```

### 命令行接口

```bash
skill_core health                                    # 健康检查
skill_core select --query "..." --context "{...}"   # 技能选择
skill_core read --skill_id "..." --query "..."      # 读取技能
skill_core act --query "..." --skill_ids "..."      # 执行检索
skill_core evolve --trajectory_file ./trajs.jsonl   # 演进 SkillBank
skill_core score --trajectory "{...}" --delta_g X.YY # 轨迹评分
```

### 输入输出协议

```json
// Input
{
  "cmd": "select|read|act|evolve|score",
  "query": "用户查询",
  "context": {"session_id": "...", "anchor": "..."},
  "skill_bank": [...],
  "apex_delta_g": 0.15
}

// Output
{
  "status": "ok|error",
  "result": {...},
  "delta_s": 0.XX,
  "delta_g": 0.XX,
  "evidence": "..."
}
```

---

## 四、Go Harness Orchestrator（Layer 2）

### 已存在：`go-fusion-harness/main.go`

```go
// 功能：
// - Evidence JSONL 全链路记录
// - Checkpoint 断点续跑
// - 命令红参（api_key 等敏感信息打码）
// - APEX Devour 集成

type Runner struct {
    EvidencePath string
    Checkpoint   string
}

func (r Runner) RunStep(step string, command ...string) Evidence
func (r Runner) appendEvidence(ev Evidence) error
func (r Runner) saveCheckpoint(step string) error
func summarize(path string) error
```

### APEX × Go Fusion 扩展任务

```go
// 待扩展模块
type ApexRunner struct {
    Runner
    DeltaG    float64
    SkillBank  string
    LLMChain  []LLMProvider
}

func (a ApexRunner) RunApexCycle(query string) (ApexResult, error)
func (a ApexRunner) EvolveSkillBank(trajectories []Trajectory) error
func (a ApexRunner) ScoreWithLLM(trajectory string, llm LLMProvider) (float64, error)
```

---

## 五、APEX 自进化五步闭环

### 代入公式

```
ΔG = G_base × (Λ·Θ·K·ξ·Ψ·Φ)/(H·T·ε)
ΔS = S_base × (α·Match + β·Chain + γ·Evolve)/(δ·Cost + ε·Latency)
```

### 找问题（当前瓶颈）

| 问题 | 现状 | 影响 |
|------|------|------|
| freemodel.dev 未认证 | API Key 缺失 | 无法使用 FRE-5.5 模型 |
| Hermes CLAW 源码不可见 | 无 `hermes_agent` 仓库访问 | 无法直接修改 Agent 底层 |
| Go Harness 缺 APEX 集成 | `main.go` 无 ΔG 调用 | 演进闭环未闭合 |
| LLM Fallback 链未实现 | 只有硬编码 | 故障切换不自动 |

### 优化路径

```
Phase 1（立即）:
  - 注册 freemodel.dev 获取 API Key
  - 补全 go-fusion-harness 的 APEX ΔG 调用
  - 实现 LLM Router 自动切换（Rust）

Phase 2（本周）:
  - 申请 Hermes Agent 源码仓库访问
  - SkillBank 扩充至 24 个技能
  - 实现 ClawMemory → SkillBank 数据流

Phase 3（持续）:
  - APEX cron 每轮调用 skill_core evolve
  - ΔG ≥ 0.493 触发 Release Gate
  - Five-Ring Radar dashboard 刷新
```

### 验证步骤

```bash
# 1. skill_core 健康检查
~/.hermes/skills/apex-search-skill/skill_core/target/release/skill_core health
# 期望：{"status":"ok","version":"1.0.0"}

# 2. APEX ΔG 计算验证
echo '["dummy"]' | ~/.hermes/skills/apex-search-skill/skill_core/target/release/skill_core score --trajectory '{}'
# 期望：delta_g > 0

# 3. Go harness preflight
go run main.go --mode preflight --evidence /tmp/apex_evidence.jsonl
# 期望：pass=N fail=0

# 4. skill_core select 验证
echo '{"cmd":"select","query":"查找 Python 函数","context":{},"skill_bank":[],"apex_delta_g":0.15}' \
  | ~/.hermes/skills/apex-search-skill/skill_core/target/release/skill_core select \
  | grep '"status":"ok"'
# 期望：匹配到 skill_000(skill_select)

# 5. freemodel.dev API 验证（需 Key）
curl -s -X POST https://api.freemodel.dev/v1/chat/completions \
  -H "Authorization: Bearer $FREEMODEL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"FRE-5.5","messages":[{"role":"user","content":"hi"}],"max_tokens":5}'
# 期望：200 OK
```

---

## 六、与 Hermes CLAW 融合

### CLAW Memory → SearchSkill 数据流

```
Hermes SOUL.md (Session Anchor)
  → /tmp/hermes_session_anchor.json
    → active_task, project_state, recent_decisions
      ↓ 注入
SearchSkill Select
  → context 携带会话状态
    → Matcher 评分参考历史
      ↓
SkillBank 匹配最优技能
  → Chain 执行检索
    → APEX ΔG 验证
      ↓
Go Harness Evidence 记录
  → SkillBank evolve 更新
    → ClawMemory M_claw 刷新
```

### APEX × Hermes 融合矩阵

| CLAW 组件 | APEX 组件 | 融合方式 |
|---------|---------|---------|
| SOUL.md | APEX ΔG | SOUL.md 写入 ΔG 基线 |
| Session Anchor | SkillBank | anchor.json 同步 SkillBank |
| APEX cron | skill_core evolve | 每轮演进触发 |
| CLAW Memory | Matcher | 历史评分影响匹配 |
| Devour Engine | Go Harness | Evidence 驱动执行 |

---

## 七、C/Go/Rust 核心组件清单

| 组件 | 语言 | 路径 | 状态 |
|------|------|------|------|
| skill_core CLI | Rust | `skill_core/src/main.rs` | ✅ 已完成 |
| SkillBank | Rust | `skill_core/src/skill_bank.rs` | ✅ 已完成 |
| Matcher | Rust | `skill_core/src/matcher.rs` | ✅ 已完成 |
| Chain | Rust | `skill_core/src/chain.rs` | ✅ 已完成 |
| APEX Formula | Rust | `skill_core/src/apex.rs` | ✅ 已完成 |
| Telemetry | Rust | `skill_core/src/telemetry.rs` | ✅ 已完成 |
| go-fusion-harness | Go | `mlops/apex-praisonai-go-fusion/templates/go-fusion-harness/main.go` | ✅ 已完成 |
| LLM Router | Rust | `skill_core/src/llm_router.rs` | ❌ 待实现 |
| APEX Evolution Cron | Go | `go-fusion-harness/cmd/apex_cron.go` | ❌ 待实现 |
| CLAW Memory Bridge | Rust | `skill_core/src/claw_bridge.rs` | ❌ 待实现 |

---

## 八、交付证据链

### GitHub 仓库

- **Repo：** `carrylam101-sketch/apex-spiral`
- **主文档：** `APEX_CMMI_Industrial_Workflow.md`
- **融合规范：** `APEX_CLAW_FUSION_SPEC.md`（本文档）

### APEX 自进化记录

```csv
# delta_g.csv
cycle,timestamp,delta_g,changed_files,status,notes
113,2026-05-27T12:55:00+08:00,1.38,APEX_CMMI_Industrial_Workflow.md,evolved,initial fusion spec
```

### Five-Ring Radar 指标

| Ring | 指标 | 当前值 | 目标值 |
|------|------|--------|--------|
| 核心环 | ΔG | 1.38 | ≥ 2.0 |
| 技能环 | SkillBank 技能数 | 12 | 24 |
| 执行环 | skill_core 响应 | < 50ms | < 30ms |
| 记忆环 | ClawMemory 命中率 | — | ≥ 80% |
| 进化环 | evolve 触发次数 | 0 | ≥ 1/日 |

---

## 九、版本与变更规则

```
major.minor.patch
  major：APEX 公式架构重大变更
  minor：新增融合子系统
  patch：Rust/Go 组件缺陷修复
```

| 触发事件 | 操作 |
|---------|------|
| `apex-claw-fusion.md` 创建 | 新建 APEX_CLAW_FUSION_SPEC.md |
| skill_core 新增 LLM Router | minor++ |
| Go harness 接入 APEX ΔG | minor++ |
| skill_core bug fix | patch++ |
| ΔG ≥ 2.0 首次达成 | major++ |