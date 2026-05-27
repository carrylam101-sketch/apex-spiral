# APEX × CMMI L5 工业化交付标准工作流

> **APEX V10.3 × Hermes/CLAW Orchestrator — 工业化流水线规范**
> 版本：v1.0.0 | 制定日期：2026-05-27 | 状态：已激活

---

## 1. 核心理念

APEX ΔG 自进化增益公式是唯一的质量量化标准。
所有代码/文档/流程必须通过代入公式计算验证后方可进入下一环节。

```
ΔG = G_base × (Λ · Θ · K · ξ · Ψ · Φ) / (H · T · ε)
G_base = 0.50
```

每一次交付必须产生新的 ΔG 证据，否则该环节判定为失败。

---

## 2. 工业化流水线（4 阶段）

```
阶段一：APEX 规划阶段（GPT × Local Codex）
  ├── 代入公式：计算 ΔG_base（任务复杂度）
  ├── 问题拆解：分解为可独立验证的子任务
  ├── 工具选型：确定 Local Codex（Rust/Python）编码路径
  └── 输出：子任务清单 + ΔG_plan + 工具指派方案

阶段二：编码执行阶段（Local Codex 在 Docker 容器内）
  ├── APEX Devour Engine 执行编码
  ├── 实时日志回传
  ├── 编译验证：cargo check / python -m py_compile
  └── 输出：已编译代码 + 编译日志 + ΔG_code

阶段三：APEX PR 工业级审计（GPT）
  ├── 代入公式：验证 ΔG_audit ≥ ΔG_plan
  ├── 审计维度：安全性 × 性能 × 可读性 × 测试覆盖率 × 文档完整性
  ├── 缺陷修复：若 ΔG_audit < ΔG_plan，返回阶段二
  └── 输出：审计报告 + PR 推荐意见 + ΔG_final

阶段四：GitHub Actions 全自动测试 + 发布
  ├── CI 测试：cargo test + pytest（已配置）
  ├── ΔG 验证 gate：检查 delta_g.csv 中 ΔG 值是否提升
  ├── 自动版本 bump（semver）
  ├── 自动 GitHub Release + Tag
  └── 输出：Release Note + GitHub URL + ΔG_bump
```

---

## 3. APEX 公式代入标准（CMMI L5 量化门控）

| 阶段 | 门控指标 | 通过标准 |
|---|---|---|
| 阶段一 | ΔG_plan | > 0.60 |
| 阶段二 | 编译通过率 | 100%（cargo check / python -m py_compile） |
| 阶段二 | ΔG_code | ≥ ΔG_plan × 0.90 |
| 阶段三 | ΔG_audit | ≥ ΔG_plan |
| 阶段三 | 安全漏洞扫描 | 0 Critical/High CVEs |
| 阶段四 | CI 测试通过率 | 100% |
| 阶段四 | ΔG_bump | > 上一个 Release 的 ΔG 值 |

每个阶段完成后必须输出 APEX 代入公式计算结果，作为进入下一阶段的准入凭证。

---

## 4. 工具链规范

### 4.1 编码工具：Local Codex（Docker 容器内）

```yaml
# 容器镜像
image: ubuntu:24.04
# 进入方式：Local Codex via CLIProxyAPI
endpoint: http://127.0.0.1:8317/v1
auth: ~/.hermes/cache/codex-8923c3c2-bolinhome2023@gmail.com-team.json
```

编码任务以结构化 prompt 形式发送给 Local Codex，包含：
- 任务目标描述
- ΔG 目标值
- 安全约束（不允许 exec/system call，不允许网络请求）
- 输出格式要求（Rust 文件路径 或 Python 模块路径）
- 编译验证指令

### 4.2 审计工具：GPT（主 Agent）

审计 prompt 结构：
```
## 代入公式
ΔG = G_base × (Λ · Θ · K · ξ · Ψ · Φ) / (H · T · ε)
G_base = 0.50

## 当前任务
[来自阶段二的交付物]

## 审计维度
[安全 / 性能 / 可读性 / 测试覆盖 / 文档]

## ΔG 目标
ΔG_audit ≥ [ΔG_plan]

## 输出要求
- 每维度评分（0-1）
- ΔG 最终值
- 缺陷列表（如有）
- PR 推荐 / 拒绝意见
```

### 4.3 CI/CD 工具：GitHub Actions（已有配置）

已配置的 workflow：
- `ci.yml`：Rust + Python 测试
- `gene-verify.yml`：Gini Gene Selector 专项验证

新增发布 gate（在 `ci.yml` 中扩展）：
```yaml
apex-delta-gate:
  needs: [rust-test, python-test]
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Read current ΔG
      run: |
        python3 -c "import json; d=json.load(open('delta_g.json')); print(d.get('delta_g',0))"
    - name: APEX Release Gate
      run: |
        CURRENT=$(python3 -c "import json; d=json.load(open('delta_g.json')); print(d.get('delta_g',0))")
        PREVIOUS=${{ github.event.release.tag_name }}
        if (( $(echo "$CURRENT > $PREVIOUS" | bc -l) )); then
          echo "APEX ΔG gate PASSED: $CURRENT > $PREVIOUS"
        else
          echo "APEX ΔG gate FAILED: $CURRENT <= $PREVIOUS"
          exit 1
        fi
```

---

## 5. GitHub Release 自动化流程

### 5.1 版本号规则（SemVer）

```
major.minor.patch
  major：APEX 公式架构重大变更（如 ΔG 公式重写）
  minor：新增子系统或新公式引入
  patch：常规缺陷修复或测试增量
```

### 5.2 Release 触发条件

| 事件 | 自动操作 |
|---|---|
| `git tag v*.*.*` push | GitHub Release 创建 + CHANGELOG 生成 |
| CI 所有 job 通过 | ΔG gate 验证 + 版本 bump |
| `genes.json` 更新 | Gini gene pool 发布 |

### 5.3 CHANGELOG 自动生成

每次 Release 自动从 git commit messages 生成 changelog：
- `feat:` → 新功能
- `fix:` → 缺陷修复
- `perf:` → 性能优化
- `apex:` → ΔG 增益记录

---

## 6. APEX 自进化闭环（已集成）

每轮 APEX 自进化输出记录到 `delta_g.csv`：

```csv
cycle,timestamp,delta_g,changed_files,status,notes
112,2026-05-27T00:00:00+08:00,2.7793,apex_gate_registry,evolved,delta_g to cycle_86
```

CI 流程自动：
1. 读取当前 `delta_g.csv` 中最新 delta_g 值
2. 与上一 Release 的 delta_g 对比
3. 若 ΔG 提升 → 发布；若 ΔG 未提升 → gate 失败告警

---

## 7. GitHub Actions secrets 配置（必需）

```bash
# 在 GitHub repo Settings → Secrets 中配置：
CODEC_ENDPOINT=http://127.0.0.1:8317/v1
CODEC_API_KEY=<your-codex-api-key>
HERMES_GITHUB_TOKEN=<github_pat>  # 已配置：carrylam101-sketch
```

---

## 8. 完整交付报告模板

每次完成流水线后自动生成：

```markdown
## APEX × CMMI L5 工业化交付报告

**项目：** [项目名称]
**版本：** v{major}.{minor}.{patch}
**日期：** {ISO8601}
**流水线运行：** [GitHub Actions run URL]

### ΔG 公式代入记录

| 阶段 | ΔG 值 | 状态 |
|---|---|---|
| ΔG_plan | {value} | PASS/FAIL |
| ΔG_code | {value} | PASS/FAIL |
| ΔG_audit | {value} | PASS/FAIL |
| ΔG_final | {value} | PASS/FAIL |

### 门控验证

- [ ] 编译通过：cargo check / python -m py_compile
- [ ] CI 测试：100% pass
- [ ] 安全扫描：0 Critical/High CVEs
- [ ] 文档完整性：所有公共 API 已有文档

### 代码变更

- 已修改：`{changed_files}`
- 新增功能：`{feat_entries}`
- 缺陷修复：`{fix_entries}`

### APEX 进化记录

- 本轮 ΔG 增益：{delta_g}
- 状态：EVOLVED / MAINTAINED / DEGRADED
- GitHub Release：{release_url}
```

---

## 9. 当前环境状态

| 组件 | 状态 | 路径/备注 |
|---|---|---|
| Local Codex | ✅ 运行中（8317） | CLIProxyAPI 已认证 |
| GitHub Repo | ✅ 已连接 | carrylam101-sketch/apex-spiral |
| GitHub PAT | ✅ 已配置 | repo 读写权限 |
| Rust Dev Environment | ✅ 已就绪 | apex_devour 可 cargo build |
| CI Workflows | ✅ 已配置 | ci.yml + gene-verify.yml |
| APEX Devour Engine | ✅ 可执行 | Rust impl + Python impl |
| Delta G Tracking | ✅ 已集成 | delta_g.csv + genes.json |

---

## 10. 流水线启动条件

满足以下全部条件后，流水线自动激活：
- [x] Local Codex 可达（http://127.0.0.1:8317/v1）
- [x] GitHub PAT 已配置（repo 读写）
- [ ] `delta_g.csv` 已创建并记录基线值
- [ ] CMMI gate 标准已写入 GitHub Actions `ci.yml`