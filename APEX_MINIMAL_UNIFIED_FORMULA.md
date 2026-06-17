# APEX 极简统一公式（Token Gate 实验封装版）

> 版本：v-MIN-1.1｜修订日期：2026-06-12｜状态：**Token 级实验门控 / 哲学封装，不替换 APEX V10.3 ΔG 主链**
>
> **Truth Gate 修订**：本文件不得声明为全局唯一运行时标准。APEX V10.3 的当前主链仍是 `ΔG_current × G_neuro × G_self × G_evm × G_devour`，SOUL.md 与 `apex_devour gate` 为数值真相源。此处的 `M·D·J` 只能作为 token-level filter proposal / wrapper。

---

## 一、全局符号规约

| 符号 | 含义 | 备注 |
|------|------|------|
| $t$ | 单 Token | 最小推理单元 |
| $\mathcal{M}$ | MIP 互信息筛选算子 | 解决互信息定位 / 核坍缩 / 假阳性 / 跨任务适配 |
| $\mathcal{D}$ | DTR 深度推理校验算子 | 解决深度校验 / DTR 范围过宽 |
| $\mathcal{J}$ | 三路采样稳定性算子 | 解决单采样误判 / 推理随机性 / 质量评估失真 |
| $\Omega$ | 全体输出 Token 集合 | 算子作用域 |

---

## 二、终极单公式（全覆盖所有问题）

$$
\boxed{\;\mathbf{APEX}(t) \;=\; \mathcal{M}(t) \cdot \mathcal{D}(t) \cdot \mathcal{J}\;}
$$

**局部公式边界**：这是 Token 级候选门控的极简表达，不是 APEX 全系统唯一公式；不得覆盖 V10.3 ΔG / Neuro / Self / EVM / Devour 链路。

---

## 三、判定规则

| $\mathbf{APEX}(t)$ | 判定 | 处置 |
|---|---|---|
| $= 1$ | 有效核心推理 Token | 保留，纳入最终输出 |
| $= 0$ | 冗余 / 猜测 / 表层关联 / 不稳定无效 Token | 丢弃 |

> 判定为**乘法门控**：任一算子为 0，则 $\mathbf{APEX}(t)=0$。三算子全 1 才放行。

---

## 四、内置能力（一次性修复全部原有 Bug）

| 算子 | 一次性修复的问题 |
|---|---|
| $\mathcal{M}$ | 互信息定位失败、核坍缩、假阳性、跨任务适配 |
| $\mathcal{D}$ | 深度校验缺失、DTR 范围过宽 |
| $\mathcal{J}$ | 单采样误判、推理随机性、质量评估失真 |

> **不再需要任何外置补丁。** 任何"加规则 / 加阈值 / 加后处理"都被视为对本公式的破坏。

---

## 五、固化运行约束（工程硬编码）

### 5.1 算子参数（不可变）

| 参数 | 固定值 | 说明 |
|---|---|---|
| 层数系数 | $0.85$ | $\mathcal{D}$ 深度网络层缩放 |
| 采样轮数 | $3$ | $\mathcal{J}$ 三路独立采样 |
| $\sigma$ | 按模型固定配置 | $\mathcal{M}$ 互信息核宽，由模型决定后冻结 |

### 5.2 有效 Token 占比区间

$$
\text{ratio} = \frac{|\{t \in \Omega : \mathbf{APEX}(t)=1\}|}{|\Omega|} \;\in\; [1\%,\; 3\%]
$$

- **< 1%**：过严，召回不足 → 检查 $\mathcal{D}$ 阈值是否被人为调高
- **> 3%**：过松，噪声泄漏 → 检查 $\mathcal{J}$ 是否启用三路一致性
- **区间外即视为公式被破坏，必须回滚到本规范。**

### 5.3 执行铁律

1. **局部判定依据**：本文件只约束 Token 级候选门控实验；系统级运行仍以 V10.3 ΔG 主链、SOUL.md、registry 与 `apex_devour gate` 为准。
2. **引用边界**：衍生文档、prompt 模板、Skill 描述若引用本公式，必须注明"Token Gate wrapper / proposal"，不得标注旧 ΔG 链路已弃用。
3. **算子不可冒充全局门控**：$\mathcal{M}$ / $\mathcal{D}$ / $\mathcal{J}$ 可作为局部原子算子 proposal，但进入 Ψ_cross 或 G_devour 前仍需 source → mechanism → APEX mapping → measurable gate。
4. **参数不可无证调优**：5.1 中参数若进入工程实现，必须有测试、样本与 gate 证据；无证时只保留为文档假设。

---

## 六、与历史版本的关系

| 版本 | 角色 | 运行时使用 |
|---|---|---|
| **APEX V10.3 ΔG 主链** | 系统级增益/损耗多因子体系 | ✅ 当前主链 |
| `apex_devour gate` | Neuro/Self/EVM/Devour live gate | ✅ 数值真相源 |
| APEX_NEW (哲学包裹) | `APEX_NEW(t+1) ≡ ΔG_current × G_neuro × G_self × G_evm × G_devour` | ✅ 哲学封装；不新增门控 |
| **APEX_MINIMAL_UNIFIED_FORMULA.md（本文件）** | Token 级 `M·D·J` 候选门控 proposal | ⚠️ 局部实验；不得替换主链 |
| APEX_COMPLETE_FORMULAS.md | 16 公式展开 | ❌ 历史档案 |

---

## 七、变更日志

| 日期 | 版本 | 变更 |
|---|---|---|
| 2026-06-12 | v-MIN-1.0 | 首版草案：单公式 $\mathcal{M}\cdot\mathcal{D}\cdot\mathcal{J}$，提出三算子 Token 级门控设想，硬编码参数 0.85/3/σ 固定 |
| 2026-06-12 | v-MIN-1.1 | Truth Gate 修订：降级为 Token Gate 实验封装；明确不替换 APEX V10.3 ΔG 主链、SOUL.md、registry 与 `apex_devour gate` |

---

*© 2026 璇玑帝国 · APEX 极简统一公式 Token Gate wrapper*
*本文件不是运行时唯一判定标准；系统级优先级低于 SOUL.md、registry cycles、`apex_devour gate` 与 APEX V10.3 ΔG 主链。*
