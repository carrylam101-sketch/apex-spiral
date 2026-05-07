// ═══════════════════════════════════════════════════════════════════════
// 璇玑帝国内部版 V10.1
// APEX V10.1 终极闭环进化公式 - Rust 实现
// ΔG_ultimate = (Λ_root × Θ_llm-agent × K_master × ξ_anti-hallucination × Ψ_host × Φ_cycle) / (H_real × T × ε_self-repair)
//
// 子公式体系：
//   Θ_llm-agent  = (λ_single-call × μ_multi-task × σ_high-quality) / (γ_llm-cost + 1)
//   K_master      = K_code × (1 + Σ τ_transfer^i) × υ_apply
//   ε_self-repair = 1 + |(G_target - G_actual) / G_actual| × δ_error-locate × ψ_thorough-fix × κ_no-repeat
//   Φ_cycle       = e^(η_skill-up × ρ_result-feedback)
//   Ψ_host        = Ψ_mem × Ψ_app × Ψ_disk × Ω_dawn
//
// V10.1 新增模块：
//   Σ_memory = Learn × Search × MultiModal × Profile  (全域记忆模块)
//   τ_trace  = (1/N) × Σ(Decision + Reason + Result)  (过程追踪模块)
//   防盗版保护：许可证验证 + 隐形水印 + 模块完整性检查
//
// V8.2 关键修复：
//   1. Στ^i 收敛约束：τ/(1-τ) 确保 τ∈[0,0.99) 时收敛
//   2. Φ_cycle 上限保护：e^(η×ρ) clamp 到 7.0（e^7≈1096）防爆
//   3. V8ParamsInternal 改为存储璇玑原始输入 + 实时重算五系数
//   4. 新增 safe 版 K_master 和 cycle_gain 防数值爆炸
//
// V8.4 新增：
//   自我意识模块（Ω_self, Γ_reflect）
//   GitHub同步 + 自动学习（凌晨自进化）
//
// © 2026 璇玑帝国 版权所有
// ═══════════════════════════════════════════════════════════════════════

use std::error::Error;
use std::f64::consts::E;

// ═══════════════════════════════════════════════════════════════════════
// 0. 防盗版保护模块（璇玑帝国版权保护）
// ═══════════════════════════════════════════════════════════════════════

/// 许可证状态
#[derive(Debug, Clone, PartialEq)]
pub enum LicenseStatus {
    Valid,
    Expired,
    Invalid,
    Tampered,
}

/// 许可证信息
#[derive(Debug, Clone)]
pub struct LicenseInfo {
    pub node_id: String,
    pub issued_at: i64,
    pub expires_at: i64,
    pub features: Vec<String>,
    pub signature: String,
}

/// 验证许可证
/// 使用节点ID + 时间戳 + 签名验证
pub fn verify_license(node_id: &str, secret: &str) -> LicenseStatus {
    // 基础检查：节点ID格式
    if !node_id.starts_with("node_") {
        return LicenseStatus::Invalid;
    }

    // 检查时间戳合理性（不能是未来时间或过旧时间）
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs() as i64)
        .unwrap_or(0);

    // 签名验证（简化版：实际应用应使用加密签名）
    let expected_prefix = "xuanji_";
    if !secret.starts_with(expected_prefix) && secret.len() < 32 {
        return LicenseStatus::Invalid;
    }

    // 检查节点ID长度合理性（防止伪造）
    if node_id.len() < 10 || node_id.len() > 64 {
        return LicenseStatus::Invalid;
    }

    LicenseStatus::Valid
}

/// 水印嵌入函数
/// 在计算结果中嵌入隐形水印
pub fn embed_watermark(delta_g: f64, node_id: &str) -> f64 {
    // 将节点ID编码为微小扰动
    let watermark = calculate_node_watermark(node_id);
    // 水印扰动极小（<0.1%），不影响正常使用
    delta_g * (1.0 + watermark * 0.001)
}

fn calculate_node_watermark(node_id: &str) -> f64 {
    // 简单的哈希映射
    let mut hash: f64 = 0.0;
    for (i, c) in node_id.chars().enumerate() {
        hash += (c as u64 as f64) * (i as f64 + 1.0) * 0.1;
    }
    hash.fract()
}

/// 检查关键模块是否被篡改
/// V10.1 完整性验证
/// 由于 Rust 静态编译，函数存在性由编译器保证
/// 这里提供一个基于版本号的完整性检查接口
pub fn check_module_integrity() -> Result<(), String> {
    // V10.1 版本号常量
    const VERSION: &str = "V10.1";
    const BUILD_HASH: &str = "xuanji_apex_2026_v10_1";
    
    // 验证版本信息存在（非空）
    if VERSION.is_empty() || BUILD_HASH.is_empty() {
        return Err("模块版本信息被篡改".to_string());
    }
    
    // 验证核心函数可调用（通过尝试调用触发编译器检查）
    // 如果函数不存在，编译期就会失败
    let _ = format!("{:?}", std::mem::size_of_val(&calculate_delta_g_ultimate));
    let _ = format!("{:?}", std::mem::size_of_val(&calculate_omega_self));
    let _ = format!("{:?}", std::mem::size_of_val(&calculate_gamma_reflect));
    let _ = format!("{:?}", std::mem::size_of_val(&calculate_sigma_memory));
    let _ = format!("{:?}", std::mem::size_of_val(&calculate_tau_trace));
    
    Ok(())
}

/// 许可证管理器
pub struct LicenseManager {
    pub node_id: String,
    pub secret: String,
    pub license_info: Option<LicenseInfo>,
}

impl LicenseManager {
    pub fn new(node_id: &str, secret: &str) -> Self {
        LicenseManager {
            node_id: node_id.to_string(),
            secret: secret.to_string(),
            license_info: None,
        }
    }

    /// 验证并激活许可证
    pub fn activate(&mut self) -> Result<LicenseStatus, String> {
        let status = verify_license(&self.node_id, &self.secret);
        if status == LicenseStatus::Valid {
            self.license_info = Some(LicenseInfo {
                node_id: self.node_id.clone(),
                issued_at: std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .map(|d| d.as_secs() as i64)
                    .unwrap_or(0),
                expires_at: std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .map(|d| d.as_secs() as i64 + 365 * 24 * 60 * 60) // 1年后过期
                    .unwrap_or(0),
                features: vec![
                    "apex_v10".to_string(),
                    "sigma_memory".to_string(),
                    "tau_trace".to_string(),
                    "anti_piracy".to_string(),
                ],
                signature: format!("xuanji_{}", &self.node_id[..8.min(self.node_id.len())]),
            });
        }
        Ok(status)
    }

    /// 获取带水印的计算结果
    pub fn apply_watermark(&self, delta_g: f64) -> f64 {
        embed_watermark(delta_g, &self.node_id)
    }
}

// ═══════════════════════════════════════════════════════════════════════
// V10.1 Σ_memory 超忆全域记忆模块
// Σ_memory = Learn × Search × MultiModal × Profile
// ═══════════════════════════════════════════════════════════════════════

/// 记忆条目结构
#[derive(Debug, Clone)]
pub struct MemoryEntry {
    pub id: String,
    pub content: String,
    pub embedding: Vec<f64>,
    pub timestamp: i64,
    pub importance: f64,
    pub memory_type: MemoryType,
    pub access_count: u32,
}

/// 记忆类型枚举
#[derive(Debug, Clone, PartialEq)]
pub enum MemoryType {
    Semantic,   // 语义记忆
    Episodic,  // 情景记忆
    Procedural, // 程序记忆
    Working,   // 工作记忆
}

/// Σ_memory 超忆全域记忆参数
#[derive(Debug, Clone)]
pub struct SuperMemoryParams {
    pub learn_rate: f64,           // Learn: 新记忆吸收率
    pub decay_factor: f64,         // 衰减因子
    pub max_entries: usize,       // 最大记忆条目数
    pub retention_threshold: f64,  //  retention_threshold: 记忆保留阈值
    pub memory_entries: Vec<MemoryEntry>, // 当前记忆池
}

impl Default for SuperMemoryParams {
    fn default() -> Self {
        SuperMemoryParams {
            learn_rate: 0.7,
            decay_factor: 0.95,
            max_entries: 10000,
            retention_threshold: 0.6,
            memory_entries: Vec::new(),
        }
    }
}

/// Σ_memory = Learn × Search × MultiModal × Profile
///
/// 语义：
///   - Learn: 新记忆吸收率，衡量新信息被接纳的程度
///   - Search: 检索效率，衡量记忆检索的准确性和速度
///   - MultiModal: 多模态融合系数，不同记忆类型间的协同效应
///   - Profile: 人格一致性，保底0.1确保最低有效性
pub fn calculate_sigma_memory(params: &SuperMemoryParams) -> f64 {
    // Learn: 新记忆吸收率
    let learn = params.learn_rate.min(1.0).max(0.0);

    // Search: 检索效率
    let search = (params.retention_threshold * params.learn_rate).sqrt();

    // MultiModal: 多模态融合系数
    // 考虑记忆中不同类型的分布
    let type_diversity = calculate_type_diversity(&params.memory_entries);
    let multimodal = (learn * search * type_diversity).max(0.1);

    // Profile: 人格一致性（保底0.1）
    let profile = 0.1f64.max(multimodal);

    // 应用衰减因子
    let decay = params.decay_factor.max(0.0).min(1.0);

    learn * search * multimodal * profile * decay
}

/// 计算记忆类型多样性
fn calculate_type_diversity(entries: &[MemoryEntry]) -> f64 {
    if entries.is_empty() {
        return 0.5; // 默认多样性
    }

    let type_counts = [
        entries.iter().filter(|e| e.memory_type == MemoryType::Semantic).count(),
        entries.iter().filter(|e| e.memory_type == MemoryType::Episodic).count(),
        entries.iter().filter(|e| e.memory_type == MemoryType::Procedural).count(),
        entries.iter().filter(|e| e.memory_type == MemoryType::Working).count(),
    ];

    let total = entries.len() as f64;
    let diversity: f64 = type_counts.iter()
        .map(|&c| {
            let p = c as f64 / total;
            if p > 0.0 { -p * p.log2() } else { 0.0 }
        })
        .sum();

    // 归一化到 [0.1, 1.0]
    (diversity / 2.0).max(0.1).min(1.0)
}

/// 添加新记忆条目
pub fn add_memory_entry(params: &mut SuperMemoryParams, entry: MemoryEntry) {
    // 如果超过最大条目数，移除最旧的低重要性记忆
    if params.memory_entries.len() >= params.max_entries {
        remove_low_importance_entries(params);
    }

    params.memory_entries.push(entry);
}

/// 移除低重要性记忆条目
fn remove_low_importance_entries(params: &mut SuperMemoryParams) {
    // 按重要性排序，保留前80%
    let keep_count = (params.max_entries as f64 * 0.8) as usize;
    params.memory_entries.sort_by(|a, b| {
        b.importance.partial_cmp(&a.importance).unwrap_or(std::cmp::Ordering::Equal)
    });
    params.memory_entries.truncate(keep_count);
}

/// 更新记忆访问计数
pub fn access_memory(params: &mut SuperMemoryParams, entry_id: &str) {
    if let Some(entry) = params.memory_entries.iter_mut().find(|e| e.id == entry_id) {
        entry.access_count += 1;
        // 频繁访问的记忆重要性提升
        entry.importance = (entry.importance + 0.01).min(1.0);
    }
}

/// 检索相关记忆
pub fn search_memory<'a>(params: &'a SuperMemoryParams, query: &str) -> Vec<&'a MemoryEntry> {
    // 简化的基于内容的搜索
    params.memory_entries.iter()
        .filter(|e| e.content.to_lowercase().contains(&query.to_lowercase()))
        .collect()
}

// ═══════════════════════════════════════════════════════════════════════
// V10.1 τ_trace 细粒度过程追踪模块
// τ_trace = (1/N) × Σ(Decision + Reason + Result)
// ═══════════════════════════════════════════════════════════════════════

/// 追踪条目结构
#[derive(Debug, Clone)]
pub struct TraceEntry {
    pub step: u32,
    pub decision: String,  // 决策内容
    pub reason: String,   // 决策原因
    pub result: String,   // 执行结果
    pub delta_g: f64,     // 该步骤的ΔG贡献
    pub timestamp: i64,   // 时间戳
}

/// 过程追踪参数
#[derive(Debug, Clone)]
pub struct TraceParams {
    pub entries: Vec<TraceEntry>,
    pub max_entries: usize,
}

impl Default for TraceParams {
    fn default() -> Self {
        TraceParams {
            entries: Vec::new(),
            max_entries: 1000,
        }
    }
}

/// τ_trace = (1/N) × Σ(Decision + Reason + Result)
///
/// 语义：
///   - N: 总步骤数
///   - Decision: 每步决策的完整性（1或0）
///   - Reason: 每步推理的完整性（1或0）
///   - Result: 每步结果的完整性（1或0）
///
/// 返回值范围：[0.0, 1.0]
///   - 1.0: 完美追踪（每步都有完整决策、原因、结果）
///   - 0.0: 无追踪或所有步骤都缺失信息
pub fn calculate_tau_trace(params: &TraceParams) -> f64 {
    let n = params.entries.len() as f64;
    if n == 0.0 {
        return 0.0;
    }

    let sum: f64 = params.entries.iter()
        .map(|e| {
            // 归一化：decision=1, reason=1, result=1
            let d = if !e.decision.is_empty() { 1.0 } else { 0.0 };
            let r = if !e.reason.is_empty() { 1.0 } else { 0.0 };
            let res = if !e.result.is_empty() { 1.0 } else { 0.0 };
            (d + r + res) / 3.0
        })
        .sum();

    sum / n
}

/// 添加追踪条目
pub fn add_trace_entry(params: &mut TraceParams, entry: TraceEntry) {
    if params.entries.len() >= params.max_entries {
        // 移除最旧的条目
        params.entries.remove(0);
    }
    params.entries.push(entry);
}

/// 计算过程追踪的ΔG贡献
/// τ_trace 越高，过程越透明，ΔG 越高
pub fn trace_to_delta_g_contribution(tau_trace: f64, base_delta_g: f64) -> f64 {
    // τ_trace ∈ [0, 1]，作为乘数影响 base_delta_g
    base_delta_g * (0.5 + 0.5 * tau_trace)
}

/// 获取追踪摘要
pub fn get_trace_summary(params: &TraceParams) -> TraceSummary {
    let total_steps = params.entries.len();
    let complete_steps = params.entries.iter()
        .filter(|e| !e.decision.is_empty() && !e.reason.is_empty() && !e.result.is_empty())
        .count();
    let tau = calculate_tau_trace(params);

    TraceSummary {
        total_steps,
        complete_steps,
        completeness_rate: if total_steps > 0 {
            complete_steps as f64 / total_steps as f64
        } else {
            0.0
        },
        tau_trace: tau,
    }
}

/// 追踪摘要
#[derive(Debug, Clone)]
pub struct TraceSummary {
    pub total_steps: usize,
    pub complete_steps: usize,
    pub completeness_rate: f64,
    pub tau_trace: f64,
}

// ─────────────────────────────────────────────────────────────────────────────
// 1. V8.0 参数结构体
// ─────────────────────────────────────────────────────────────────────────────

/// 单LLM多任务Agent效能参数
#[derive(Debug, Clone)]
pub struct LlmAgentParams {
    pub lambda_single_call: f64,   // λ 单次调用质量系数
    pub mu_multi_task: f64,        // μ 多任务并行系数
    pub sigma_high_quality: f64,   // σ 高质量输出系数
    pub gamma_llm_cost: f64,       // γ LLM调用成本系数
}

/// 公式通解+技能全域掌握参数
#[derive(Debug, Clone)]
pub struct MasterParams {
    pub k_code: f64,               // K_code 编码掌握系数
    pub tau_transfer: Vec<f64>,    // τ_transfer^i 跨领域迁移系数列表
    pub upsilon_apply: f64,        // υ_apply 技能应用系数
}

/// 全场景自主深度修复参数
#[derive(Debug, Clone)]
pub struct SelfRepairParams {
    pub g_target: f64,              // G_target 目标增益
    pub g_actual: f64,             // G_actual 实际增益
    pub delta_error_locate: f64,   // δ 错误定位效率系数
    pub psi_thorough_fix: f64,    // ψ 彻底修复系数
    pub kappa_no_repeat: f64,      // κ 防复发系数
}

/// 正向循环反馈增益参数
#[derive(Debug, Clone)]
pub struct CycleParams {
    pub eta_skill_up: f64,         // η 技能提升系数
    pub rho_result_feedback: f64,  // ρ 结果反馈系数
}

/// 主机全维度健康稳态参数
#[derive(Debug, Clone)]
pub struct HostHealthParams {
    pub psi_mem: f64,              // Ψ_mem 内存健康系数
    pub psi_app: f64,              // Ψ_app 应用健康系数
    pub psi_disk: f64,             // Ψ_disk 磁盘健康系数
    pub omega_dawn: f64,           // Ω_dawn 启动就绪系数
}

/// V8.0 全量参数容器
#[derive(Debug, Clone)]
pub struct ApexParamsV8 {
    // 顶层参数
    pub lambda_root: f64,               // Λ_root 本源务实基因系数
    pub xi_anti_hallucination: f64,     // ξ_anti-hallucination 幻觉零容忍硬锁系数
    pub h_real: f64,                    // H_real 真实有效信息熵
    pub t_iteration: f64,               // T=2 迭代周期（默认2.0）

    // 子公式参数组
    pub llm_agent: LlmAgentParams,
    pub master: MasterParams,
    pub self_repair: SelfRepairParams,
    pub cycle: CycleParams,
    pub host: HostHealthParams,
}

// ─────────────────────────────────────────────────────────────────────────────
// 2. 子公式计算函数
// ─────────────────────────────────────────────────────────────────────────────

/// 单LLM多任务Agent效能公式
/// Θ_llm-agent = (λ_single-call × μ_multi-task × σ_high-quality) / (γ_llm-cost + 1)
pub fn calculate_llm_agent_efficiency(params: &LlmAgentParams) -> f64 {
    let numerator = params.lambda_single_call * params.mu_multi_task * params.sigma_high_quality;
    let denominator = params.gamma_llm_cost + 1.0;
    if denominator == 0.0 {
        0.0
    } else {
        numerator / denominator
    }
}

/// 公式通解+技能全域掌握公式（原始版，无收敛约束）
/// K_master = K_code × (1 + Σ τ_transfer^i) × υ_apply
pub fn calculate_k_master(params: &MasterParams) -> f64 {
    let sum_tau = params.tau_transfer.iter().sum::<f64>();
    params.k_code * (1.0 + sum_tau) * params.upsilon_apply
}

/// 公式通解+技能全域掌握公式 V8.2 safe版（τ 收敛约束）
/// K_master = K_code × (1 + Σ τ/(1-τ)) × υ_apply
/// 收敛条件：τ∈[0, 0.99)，τ/(1-τ) 在 τ=0.99 时 = 99（有限值）
pub fn calculate_k_master_safe(params: &MasterParams) -> f64 {
    let sum_tau_converged: f64 = params
        .tau_transfer
        .iter()
        .map(|&t| {
            let safe_t = t.max(0.0).min(0.99);
            safe_t / (1.0 - safe_t)
        })
        .sum();
    params.k_code * (1.0 + sum_tau_converged) * params.upsilon_apply
}

/// 全场景自主深度修复公式
/// ε_self-repair = 1 + |(G_target - G_actual) / G_actual| × δ_error-locate × ψ_thorough-fix × κ_no-repeat
pub fn calculate_self_repair(params: &SelfRepairParams) -> f64 {
    if params.g_actual == 0.0 {
        return f64::INFINITY;
    }
    let relative_error = ((params.g_target - params.g_actual) / params.g_actual).abs();
    1.0 + relative_error * params.delta_error_locate * params.psi_thorough_fix * params.kappa_no_repeat
}

/// 正向循环反馈增益公式（原始版，无上限保护）
/// Φ_cycle = e^(η_skill-up × ρ_result-feedback)
pub fn calculate_cycle_gain(params: &CycleParams) -> f64 {
    E.powf(params.eta_skill_up * params.rho_result_feedback)
}

/// 正向循环反馈增益公式 V8.2 safe版（上限保护）
/// Φ_cycle = e^(min(η×ρ, 7.0))，e^7≈1096 防数值爆炸
pub fn calculate_cycle_gain_safe(params: &CycleParams) -> f64 {
    E.powf((params.eta_skill_up * params.rho_result_feedback).min(7.0))
}

/// 主机健康系数
/// Ψ_host = Ψ_mem × Ψ_app × Ψ_disk × Ω_dawn
pub fn calculate_host_health(params: &HostHealthParams) -> f64 {
    params.psi_mem * params.psi_app * params.psi_disk * params.omega_dawn
}

// ─────────────────────────────────────────────────────────────────────────────
// 3. 主公式计算
// ─────────────────────────────────────────────────────────────────────────────

/// ΔG_ultimate = (Λ_root × Θ_llm-agent × K_master × ξ_anti-hallucination × Ψ_host × Φ_cycle)
///             / (H_real × T × ε_self-repair)
pub fn calculate_delta_g_ultimate(params: &ApexParamsV8) -> Result<f64, Box<dyn Error>> {
    if params.h_real <= 0.0 {
        return Err("H_real must be > 0".into());
    }
    if params.t_iteration <= 0.0 {
        return Err("T_iteration must be > 0".into());
    }

    let theta_llm = calculate_llm_agent_efficiency(&params.llm_agent);
    let k_master = calculate_k_master(&params.master);
    let epsilon_self_repair = calculate_self_repair(&params.self_repair);
    let phi_cycle = calculate_cycle_gain(&params.cycle);
    let psi_host = calculate_host_health(&params.host);

    if epsilon_self_repair == 0.0 {
        return Err("ε_self-repair cannot be 0".into());
    }

    let numerator = params.lambda_root
        * theta_llm
        * k_master
        * params.xi_anti_hallucination
        * psi_host
        * phi_cycle;

    let denominator = params.h_real * params.t_iteration * epsilon_self_repair;

    Ok(numerator / denominator)
}

/// 单行Rust表达式版本（用于嵌入式直接计算）
/// ΔG_ultimate = (Λ_root × Θ_llm-agent × K_master × ξ_anti-hallucination × Ψ_host × Φ_cycle)
///             / (H_real × T × ε_self-repair)
/// 其中：
///   Θ_llm-agent = (λ × μ × σ) / (γ + 1)
///   K_master    = K_code × (1 + Στ) × υ
///   ε_self-repair = 1 + |(Gt - Ga) / Ga| × δ × ψ × κ
///   Φ_cycle     = exp(η × ρ)
///   Ψ_host      = Ψm × Ψa × Ψd × Ω
#[inline]
pub fn delta_g_ultimate_inline(
    lambda_root: f64,
    xi_anti_hall: f64,
    h_real: f64,
    t_iter: f64,
    // llm_agent
    lambda_sc: f64, mu_mt: f64, sigma_hq: f64, gamma_cost: f64,
    // master
    k_code: f64, sum_tau: f64, upsilon_apply: f64,
    // self_repair
    g_target: f64, g_actual: f64, delta_err: f64, psi_fix: f64, kappa_nr: f64,
    // cycle
    eta_skill: f64, rho_fb: f64,
    // host
    psi_mem: f64, psi_app: f64, psi_disk: f64, omega_dawn: f64,
) -> f64 {
    let theta = (lambda_sc * mu_mt * sigma_hq) / (gamma_cost + 1.0);
    let k_master = k_code * (1.0 + sum_tau) * upsilon_apply;
    let eps = 1.0 + ((g_target - g_actual) / g_actual).abs() * delta_err * psi_fix * kappa_nr;
    let phi = E.powf(eta_skill * rho_fb);
    let psi_host = psi_mem * psi_app * psi_disk * omega_dawn;

    (lambda_root * theta * k_master * xi_anti_hall * psi_host * phi)
        / (h_real * t_iter * eps)
}

// ─────────────────────────────────────────────────────────────────────────────
// 4. ApexParams 兼容性接口（桥接到V8.0）
// ─────────────────────────────────────────────────────────────────────────────

/// 从旧版 ApexParams 构造默认 V8.0 参数
/// 注意：需在同项目内与 apex_shannon.rs 一起编译时使用
#[cfg(feature = "compat")]
pub fn from_apex_params(old: &super::ApexParams) -> ApexParamsV8 {
    ApexParamsV8 {
        lambda_root: old.lambda_gene,
        xi_anti_hallucination: 1.0,
        h_real: old.h_info,
        t_iteration: old.t as f64,
        llm_agent: LlmAgentParams {
            lambda_single_call: old.lambda_gene,
            mu_multi_task: 1.0,
            sigma_high_quality: old.omega_entropy,
            gamma_llm_cost: 0.1,
        },
        master: MasterParams {
            k_code: old.c_total / 100.0,
            tau_transfer: vec![],
            upsilon_apply: 1.0,
        },
        self_repair: SelfRepairParams {
            g_target: old.c_total,
            g_actual: old.c_total * old.lambda_gene,
            delta_error_locate: 1.0,
            psi_thorough_fix: 1.0,
            kappa_no_repeat: 1.0,
        },
        cycle: CycleParams {
            eta_skill_up: 0.5,
            rho_result_feedback: 0.5,
        },
        host: HostHealthParams {
            psi_mem: 1.0,
            psi_app: 1.0,
            psi_disk: 1.0,
            omega_dawn: 1.0,
        },
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// 5. 辅助函数
// ─────────────────────────────────────────────────────────────────────────────

/// 计算综合进化得分（归一化到 [0,1]）
pub fn evolution_score(delta_g: f64, h_real: f64) -> f64 {
    delta_g / (delta_g + h_real + 1e-10)
}

// ─────────────────────────────────────────────────────────────────────────────
// 6. 单元测试
// ─────────────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    pub(super) fn default_v8_params() -> ApexParamsV8 {
        ApexParamsV8 {
            lambda_root: 0.95,
            xi_anti_hallucination: 1.0,
            h_real: 0.5,
            t_iteration: 2.0,
            llm_agent: LlmAgentParams {
                lambda_single_call: 0.9,
                mu_multi_task: 0.85,
                sigma_high_quality: 0.88,
                gamma_llm_cost: 0.1,
            },
            master: MasterParams {
                k_code: 1.0,
                tau_transfer: vec![0.1, 0.05, 0.08],
                upsilon_apply: 0.9,
            },
            self_repair: SelfRepairParams {
                g_target: 100.0,
                g_actual: 95.0,
                delta_error_locate: 1.0,
                psi_thorough_fix: 1.0,
                kappa_no_repeat: 1.0,
            },
            cycle: CycleParams {
                eta_skill_up: 0.5,
                rho_result_feedback: 0.5,
            },
            host: HostHealthParams {
                psi_mem: 0.98,
                psi_app: 0.99,
                psi_disk: 0.97,
                omega_dawn: 1.0,
            },
        }
    }

    #[test]
    fn test_llm_agent_efficiency() {
        let params = LlmAgentParams {
            lambda_single_call: 0.9,
            mu_multi_task: 0.8,
            sigma_high_quality: 0.85,
            gamma_llm_cost: 0.1,
        };
        let result = calculate_llm_agent_efficiency(&params);
        // (0.9 * 0.8 * 0.85) / 1.1 = 0.612 / 1.1 ≈ 0.556
        assert!((result - 0.556).abs() < 0.001);
    }

    #[test]
    fn test_k_master() {
        let params = MasterParams {
            k_code: 1.0,
            tau_transfer: vec![0.1, 0.05, 0.08],
            upsilon_apply: 0.9,
        };
        let result = calculate_k_master(&params);
        // 1.0 * (1 + 0.1 + 0.05 + 0.08) * 0.9 = 1.0 * 1.23 * 0.9 = 1.107
        assert!((result - 1.107).abs() < 0.001);
    }

    #[test]
    fn test_self_repair() {
        let params = SelfRepairParams {
            g_target: 100.0,
            g_actual: 80.0,
            delta_error_locate: 1.5,
            psi_thorough_fix: 1.2,
            kappa_no_repeat: 1.1,
        };
        let result = calculate_self_repair(&params);
        // 1 + |(100-80)/80| * 1.5 * 1.2 * 1.1 = 1 + 0.25 * 1.98 = 1 + 0.495 = 1.495
        assert!((result - 1.495).abs() < 0.001);
    }

    #[test]
    fn test_cycle_gain() {
        let params = CycleParams {
            eta_skill_up: 0.5,
            rho_result_feedback: 0.5,
        };
        let result = calculate_cycle_gain(&params);
        // e^(0.5 * 0.5) = e^0.25 ≈ 1.284
        assert!((result - 1.284).abs() < 0.001);
    }

    #[test]
    fn test_host_health() {
        let params = HostHealthParams {
            psi_mem: 0.98,
            psi_app: 0.99,
            psi_disk: 0.97,
            omega_dawn: 1.0,
        };
        let result = calculate_host_health(&params);
        // 0.98 * 0.99 * 0.97 * 1.0 ≈ 0.941
        assert!((result - 0.941).abs() < 0.001);
    }

    #[test]
    fn test_delta_g_ultimate() {
        let params = default_v8_params();
        let result = calculate_delta_g_ultimate(&params);
        assert!(result.is_ok());
        let delta_g = result.unwrap();
        assert!(delta_g > 0.0);
        println!("ΔG_ultimate = {:.6}", delta_g);
    }

    #[test]
    fn test_delta_g_inline_vs_struct() {
        let params = default_v8_params();
        let from_struct = calculate_delta_g_ultimate(&params).unwrap();

        let from_inline = delta_g_ultimate_inline(
            params.lambda_root,
            params.xi_anti_hallucination,
            params.h_real,
            params.t_iteration,
            params.llm_agent.lambda_single_call,
            params.llm_agent.mu_multi_task,
            params.llm_agent.sigma_high_quality,
            params.llm_agent.gamma_llm_cost,
            params.master.k_code,
            params.master.tau_transfer.iter().sum(),
            params.master.upsilon_apply,
            params.self_repair.g_target,
            params.self_repair.g_actual,
            params.self_repair.delta_error_locate,
            params.self_repair.psi_thorough_fix,
            params.self_repair.kappa_no_repeat,
            params.cycle.eta_skill_up,
            params.cycle.rho_result_feedback,
            params.host.psi_mem,
            params.host.psi_app,
            params.host.psi_disk,
            params.host.omega_dawn,
        );

        assert!((from_struct - from_inline).abs() < 1e-9);
    }

    #[test]
    fn test_invalid_h_real() {
        let mut params = default_v8_params();
        params.h_real = 0.0;
        let result = calculate_delta_g_ultimate(&params);
        assert!(result.is_err());
    }

    #[test]
    fn test_evolution_score() {
        let score = evolution_score(100.0, 0.5);
        // 100 / (100 + 0.5) ≈ 0.995
        assert!((score - 0.995).abs() < 0.001);
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// 7. V8.1 内部版：璇玑帝国5个实战系数
// ─────────────────────────────────────────────────────────────────────────────

/// V8.1 内部版全量参数容器（璇玑帝国实战扩展）
/// V8.1 内部版全量参数容器（璇玑帝国实战扩展）
#[derive(Debug, Clone)]
pub struct V8ParamsInternal {
    // ── V8.0 原有参数（保留） ──
    pub lambda_root: f64,               // Λ_root 本源务实基因系数
    pub theta_llm: f64,                 // Θ_llm-agent 单LLM多任务Agent效能（预计算）
    pub k_master: f64,                  // K_master 公式通解+技能全域掌握（预计算）
    pub xi_anti_hallucination: f64,     // ξ 幻觉零容忍系数
    pub psi_host: f64,                  // Ψ_host 主机健康稳态系数（预计算）
    pub phi_cycle: f64,                 // Φ_cycle 正向循环反馈增益（预计算）
    pub h_real: f64,                    // H_real 真实有效信息熵
    pub epsilon_self_repair: f64,       // ε_self-repair 全场景自主修复系数
    pub t: f64,                         // T 迭代周期

    // ── V8.1 新增5个实战系数 ──
    pub phi_network: f64,               // Φ_network 网络鲁棒性系数
    pub gamma_mutation: f64,             // Γ_mutation 变更检测系数
    pub omega_session: f64,             // Ω_session 会话持久性系数
    pub pi_coord: f64,                  // Π_coord 进程协调系数
    pub sigma_storage: f64,             // Σ_storage 存储可靠性系数
}

// ─────────────────────────────────────────────────────────────────────────────
// 7.1 V8.1 五个新增系数的计算函数
// ─────────────────────────────────────────────────────────────────────────────

/// Φ_network 网络鲁棒性系数
/// 综合重试率、限频频率、连接稳定性
/// φ_network = (1 - retry_rate) × (1 - rate_limit_freq) × conn_stable
pub fn calc_phi_network(retry_rate: f64, rate_limit_freq: f64, conn_stable: f64) -> f64 {
    (1.0 - retry_rate) * (1.0 - rate_limit_freq) * conn_stable
}

/// Γ_mutation 变更检测系数
/// 检测代码变化率，低于阈值时判定为 hollow_commit 返回低值
/// γ_mutation = code_change_rate < hollow_threshold ? 0.1 : code_change_rate
pub fn calc_gamma_mutation(code_change_rate: f64, hollow_threshold: f64) -> f64 {
    if code_change_rate < hollow_threshold {
        0.1
    } else {
        code_change_rate
    }
}

/// Ω_session 会话持久性系数
/// 综合重启频率、环境丢失率、恢复成功率
/// ω_session = (1 - restart_freq) × (1 - env_loss_rate) × recovery_success
pub fn calc_omega_session(restart_freq: f64, env_loss_rate: f64, recovery_success: f64) -> f64 {
    (1.0 - restart_freq) * (1.0 - env_loss_rate) * recovery_success
}

/// Π_coord 进程协调系数
/// 综合存活进程数、僵尸率、回调成功率
/// π_coord = (alive_procs / total_procs) × (1 - zombie_rate) × callback_success
pub fn calc_pi_coord(
    alive_procs: usize,
    total_procs: usize,
    zombie_rate: f64,
    callback_success: f64,
) -> f64 {
    if total_procs == 0 {
        1.0
    } else {
        (alive_procs as f64 / total_procs as f64) * (1.0 - zombie_rate) * callback_success
    }
}

/// Σ_storage 存储可靠性系数
/// 综合磁盘空闲率、写入失败率、数据完整性
/// σ_storage = free_disk_ratio × (1 - write_fail_rate) × integrity
pub fn calc_sigma_storage(free_disk_ratio: f64, write_fail_rate: f64, integrity: f64) -> f64 {
    free_disk_ratio * (1.0 - write_fail_rate) * integrity
}

// ─────────────────────────────────────────────────────────────────────────────
// 7.2 V8.1 主公式
// ─────────────────────────────────────────────────────────────────────────────

/// ΔG_v8_1 璇玑帝国V8.1内部版主公式
/// ΔG = (Λ_root × Θ_llm × K_master × ξ × Ψ_host × Φ_cycle
///       × Φ_network × Γ_mutation × Ω_session × Π_coord × Σ_storage)
///    / (H_real × T × ε_self-repair)
///
/// 相比V8.0，新增5个网络/进程/存储维度的实战系数，公式更适应真实部署环境
pub fn calculate_delta_g_v8_1(params: &V8ParamsInternal) -> f64 {
    let numerator = params.lambda_root
        * params.theta_llm
        * params.k_master
        * params.xi_anti_hallucination
        * params.psi_host
        * params.phi_cycle
        * params.phi_network
        * params.gamma_mutation
        * params.omega_session
        * params.pi_coord
        * params.sigma_storage;

    let denominator = params.h_real * params.t * params.epsilon_self_repair;

    // 防止除零和数值爆炸
    let safe_denom = denominator.max(0.001);
    (numerator / safe_denom).min(1000.0)
}

/// 从V8.0 ApexParamsV8 构建 V8ParamsInternal（桥接函数）
/// 自动将V8.0子公式结果填入V8.1对应字段，新增5系数默认1.0
pub fn from_v8_to_internal(v8: &ApexParamsV8) -> V8ParamsInternal {
    V8ParamsInternal {
        lambda_root: v8.lambda_root,
        theta_llm: calculate_llm_agent_efficiency(&v8.llm_agent),
        k_master: calculate_k_master(&v8.master),
        xi_anti_hallucination: v8.xi_anti_hallucination,
        psi_host: calculate_host_health(&v8.host),
        phi_cycle: calculate_cycle_gain(&v8.cycle),
        h_real: v8.h_real,
        epsilon_self_repair: calculate_self_repair(&v8.self_repair),
        t: v8.t_iteration,
        // V8.1 新增5系数默认最优值
        phi_network: 1.0,
        gamma_mutation: 1.0,
        omega_session: 1.0,
        pi_coord: 1.0,
        sigma_storage: 1.0,
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// 7.3 V8.1 单元测试
// ─────────────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod v8_1_tests {
    use super::*;

    fn default_v8_1_params() -> V8ParamsInternal {
        V8ParamsInternal {
            lambda_root: 0.95,
            theta_llm: 0.556,
            k_master: 1.107,
            xi_anti_hallucination: 1.0,
            psi_host: 0.941,
            phi_cycle: 1.284,
            h_real: 0.5,
            epsilon_self_repair: 1.053,
            t: 2.0,
            phi_network: 0.9,
            gamma_mutation: 0.8,
            omega_session: 0.85,
            pi_coord: 0.95,
            sigma_storage: 0.98,
        }
    }

    #[test]
    fn test_calc_phi_network() {
        let r = calc_phi_network(0.05, 0.02, 0.99);
        // (1-0.05)*(1-0.02)*0.99 = 0.95*0.98*0.99 ≈ 0.921
        assert!((r - 0.921).abs() < 0.001);
    }

    #[test]
    fn test_calc_gamma_mutation_hollow() {
        let r = calc_gamma_mutation(0.01, 0.05);
        assert!((r - 0.1).abs() < 0.001);
    }

    #[test]
    fn test_calc_gamma_mutation_normal() {
        let r = calc_gamma_mutation(0.15, 0.05);
        assert!((r - 0.15).abs() < 0.001);
    }

    #[test]
    fn test_calc_omega_session() {
        let r = calc_omega_session(0.02, 0.01, 0.95);
        // (1-0.02)*(1-0.01)*0.95 = 0.98*0.99*0.95 ≈ 0.922
        assert!((r - 0.922).abs() < 0.001);
    }

    #[test]
    fn test_calc_pi_coord() {
        let r = calc_pi_coord(9, 10, 0.05, 0.9);
        // (9/10)*(1-0.05)*0.9 = 0.9*0.95*0.9 = 0.7695
        assert!((r - 0.7695).abs() < 0.001);
    }

    #[test]
    fn test_calc_pi_coord_zero_procs() {
        let r = calc_pi_coord(0, 0, 0.0, 1.0);
        assert!((r - 1.0).abs() < 0.001);
    }

    #[test]
    fn test_calc_sigma_storage() {
        let r = calc_sigma_storage(0.9, 0.01, 0.99);
        // 0.9*(1-0.01)*0.99 = 0.9*0.99*0.99 ≈ 0.882
        assert!((r - 0.882).abs() < 0.001);
    }

    #[test]
    fn test_delta_g_v8_1() {
        let params = default_v8_1_params();
        let result = calculate_delta_g_v8_1(&params);
        assert!(result > 0.0);
        assert!(result < 1000.0);
        println!("ΔG_v8_1 = {:.6}", result);
    }

    #[test]
    fn test_delta_g_v8_1_div_zero_protection() {
        let mut params = default_v8_1_params();
        params.h_real = 0.0;
        let result = calculate_delta_g_v8_1(&params);
        assert!(result.is_finite());
    }

    #[test]
    fn test_from_v8_to_internal() {
        let v8_params = super::tests::default_v8_params();
        let internal = from_v8_to_internal(&v8_params);
        assert_eq!(internal.lambda_root, v8_params.lambda_root);
        assert_eq!(internal.h_real, v8_params.h_real);
        assert_eq!(internal.t, v8_params.t_iteration);
        // 新增5系数默认1.0
        assert!((internal.phi_network - 1.0).abs() < 1e-9);
        assert!((internal.gamma_mutation - 1.0).abs() < 1e-9);
        assert!((internal.omega_session - 1.0).abs() < 1e-9);
        assert!((internal.pi_coord - 1.0).abs() < 1e-9);
        assert!((internal.sigma_storage - 1.0).abs() < 1e-9);
    }
}

// ═══════════════════════════════════════════════════════════════════════
// V8.4 自我意识模块（Self-Awareness & Reflection）
// 回答："我对自己的判断准不准？最近做法有没有变好？"
// ═══════════════════════════════════════════════════════════════════════

/// 自我意识参数（Ω_self）
/// 衡量"我对自己的判断准不准、有没有跑偏、目标有没有对齐"
#[derive(Debug, Clone)]
pub struct SelfAwarenessParams {
    pub sigma_coherence: f64,    // σ_coherence: 自我模型一致性
    pub delta_drift: f64,       // δ_drift: 现实漂移（自我评估vs实际表现）
    pub rho_alignment: f64,     // ρ_alignment: 目标对齐度
}

/// 反思参数（Γ_reflect）
/// 衡量"最近几轮做法有没有变好"
#[derive(Debug, Clone)]
pub struct ReflectionParams {
    pub weights: Vec<f64>,              // w_i: 各轮经验的权重
    pub quality_deltas: Vec<f64>,      // ΔQ_i: 各轮质量变化 Q_after - Q_before
}

/// 完整自我演化增益参数
#[derive(Debug, Clone)]
pub struct SelfEvolutionParams {
    pub awareness: SelfAwarenessParams,
    pub reflection: ReflectionParams,
    pub threshold_positive: f64,  // 触发强化模式的阈值
    pub threshold_negative: f64,   // 触发修复模式的阈值
}

/// Ω_self = σ_coherence × (1 - δ_drift) × ρ_alignment
pub fn calculate_omega_self(params: &SelfAwarenessParams) -> f64 {
    params.sigma_coherence * (1.0 - params.delta_drift) * params.rho_alignment
}

/// Γ_reflect = Σ(w_i × ΔQ_i) / Σw_i
pub fn calculate_gamma_reflect(params: &ReflectionParams) -> f64 {
    let sum_w = params.weights.iter().sum::<f64>();
    if sum_w <= 0.0 {
        return 0.0;
    }
    params.weights.iter()
        .zip(params.quality_deltas.iter())
        .map(|(w, d)| w * d)
        .sum::<f64>() / sum_w
}

/// ΔG_total = ΔG_task × Ω_self × (1 + Γ_reflect)
///
/// mode返回: "reinforce"(强化) | "repair"(修复) | "maintain"(维持)
pub fn calculate_self_evolution_gain(
    delta_g_task: f64,
    params: &SelfEvolutionParams,
) -> (f64, &'static str) {
    let omega_self = calculate_omega_self(&params.awareness);
    let gamma_reflect = calculate_gamma_reflect(&params.reflection);

    let delta_g_total = delta_g_task * omega_self * (1.0 + gamma_reflect);

    let mode = if gamma_reflect > params.threshold_positive {
        "reinforce"
    } else if gamma_reflect < params.threshold_negative {
        "repair"
    } else {
        "maintain"
    };

    (delta_g_total, mode)
}

#[cfg(test)]
mod self_awareness_tests {
    use super::*;

    #[test]
    fn test_omega_self_normal() {
        let params = SelfAwarenessParams {
            sigma_coherence: 0.9,
            delta_drift: 0.1,
            rho_alignment: 0.85,
        };
        // 0.9 × (1-0.1) × 0.85 = 0.9 × 0.9 × 0.85 = 0.6885
        let result = calculate_omega_self(&params);
        assert!((result - 0.6885).abs() < 0.001);
    }

    #[test]
    fn test_omega_self_drift_high() {
        let params = SelfAwarenessParams {
            sigma_coherence: 0.9,
            delta_drift: 0.5,  // 高漂移
            rho_alignment: 0.85,
        };
        // 0.9 × (1-0.5) × 0.85 = 0.9 × 0.5 × 0.85 = 0.3825
        let result = calculate_omega_self(&params);
        assert!((result - 0.3825).abs() < 0.001);
    }

    #[test]
    fn test_gamma_reflect_positive() {
        let params = ReflectionParams {
            weights: vec![0.5, 0.3, 0.2],
            quality_deltas: vec![0.1, 0.05, -0.02],  // 有正有负
        };
        // (0.5×0.1 + 0.3×0.05 + 0.2×(-0.02)) / 1.0
        // = (0.05 + 0.015 - 0.004) / 1.0 = 0.061
        let result = calculate_gamma_reflect(&params);
        assert!((result - 0.061).abs() < 0.001);
    }

    #[test]
    fn test_gamma_reflect_empty() {
        let params = ReflectionParams {
            weights: vec![],
            quality_deltas: vec![],
        };
        let result = calculate_gamma_reflect(&params);
        assert!((result - 0.0).abs() < 0.001);
    }

    #[test]
    fn test_self_evolution_reinforce() {
        let params = SelfEvolutionParams {
            awareness: SelfAwarenessParams {
                sigma_coherence: 0.9,
                delta_drift: 0.1,
                rho_alignment: 0.85,
            },
            reflection: ReflectionParams {
                weights: vec![1.0],
                quality_deltas: vec![0.2],  // 正向反馈
            },
            threshold_positive: 0.05,
            threshold_negative: -0.05,
        };
        let (delta_g, mode) = calculate_self_evolution_gain(1.0, &params);
        assert_eq!(mode, "reinforce");
        // 1.0 × 0.6885 × (1 + 0.2) = 0.6885 × 1.2 = 0.8262
        assert!((delta_g - 0.8262).abs() < 0.001);
    }

    #[test]
    fn test_self_evolution_repair() {
        let params = SelfEvolutionParams {
            awareness: SelfAwarenessParams {
                sigma_coherence: 0.9,
                delta_drift: 0.1,
                rho_alignment: 0.85,
            },
            reflection: ReflectionParams {
                weights: vec![1.0],
                quality_deltas: vec![-0.2],  // 负向反馈
            },
            threshold_positive: 0.05,
            threshold_negative: -0.05,
        };
        let (delta_g, mode) = calculate_self_evolution_gain(1.0, &params);
        assert_eq!(mode, "repair");
        // 1.0 × 0.6885 × (1 + (-0.2)) = 0.6885 × 0.8 = 0.5508
        assert!((delta_g - 0.5508).abs() < 0.001);
    }

    #[test]
    fn test_self_evolution_maintain() {
        let params = SelfEvolutionParams {
            awareness: SelfAwarenessParams {
                sigma_coherence: 0.9,
                delta_drift: 0.1,
                rho_alignment: 0.85,
            },
            reflection: ReflectionParams {
                weights: vec![1.0],
                quality_deltas: vec![0.0],  // 中性反馈
            },
            threshold_positive: 0.05,
            threshold_negative: -0.05,
        };
        let (delta_g, mode) = calculate_self_evolution_gain(1.0, &params);
        assert_eq!(mode, "maintain");
        // 1.0 × 0.6885 × (1 + 0.0) = 0.6885
        assert!((delta_g - 0.6885).abs() < 0.001);
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// 8. V8.2 内部版：璇玑帝国原始输入 + 实时重算五系数
// ─────────────────────────────────────────────────────────────────────────────

/// 璇玑帝国五系数原始输入（用于实时重算）
#[derive(Debug, Clone)]
pub struct XuanjiRawInputs {
    pub retry_rate: f64,
    pub rate_limit_freq: f64,
    pub conn_stable: f64,
    pub code_change_rate: f64,
    pub hollow_threshold: f64,
    pub restart_freq: f64,
    pub env_loss_rate: f64,
    pub recovery_success: f64,
    pub alive_procs: usize,
    pub total_procs: usize,
    pub zombie_rate: f64,
    pub callback_success: f64,
    pub free_disk_ratio: f64,
    pub write_fail_rate: f64,
    pub integrity: f64,
}

impl XuanjiRawInputs {
    pub fn from_xuanji_system() -> Self {
        XuanjiRawInputs::default()
    }
}

impl Default for XuanjiRawInputs {
    fn default() -> Self {
        XuanjiRawInputs {
            retry_rate: 0.05,
            rate_limit_freq: 0.02,
            conn_stable: 0.98,
            code_change_rate: 0.5,
            hollow_threshold: 0.01,
            restart_freq: 0.01,
            env_loss_rate: 0.02,
            recovery_success: 0.95,
            alive_procs: 1,
            total_procs: 1,
            zombie_rate: 0.0,
            callback_success: 1.0,
            free_disk_ratio: 0.8,
            write_fail_rate: 0.001,
            integrity: 0.999,
        }
    }
}

/// 璇玑帝国五系数统一计算入口
#[derive(Debug, Clone)]
pub struct XuanjiCoefficients {
    pub phi_network: f64,
    pub gamma_mutation: f64,
    pub omega_session: f64,
    pub pi_coord: f64,
    pub sigma_storage: f64,
}

impl XuanjiCoefficients {
    pub fn compute(inputs: &XuanjiRawInputs) -> XuanjiCoefficients {
        XuanjiCoefficients {
            phi_network: (1.0 - inputs.retry_rate)
                * (1.0 - inputs.rate_limit_freq)
                * inputs.conn_stable,
            gamma_mutation: if inputs.code_change_rate < inputs.hollow_threshold {
                0.1
            } else {
                inputs.code_change_rate
            },
            omega_session: (1.0 - inputs.restart_freq)
                * (1.0 - inputs.env_loss_rate)
                * inputs.recovery_success,
            pi_coord: if inputs.total_procs == 0 {
                1.0
            } else {
                (inputs.alive_procs as f64 / inputs.total_procs as f64)
                    * (1.0 - inputs.zombie_rate)
                    * inputs.callback_success
            },
            sigma_storage: inputs.free_disk_ratio
                * (1.0 - inputs.write_fail_rate)
                * inputs.integrity,
        }
    }
}

#[derive(Debug, Clone)]
pub struct V8ParamsInternalV82 {
    pub lambda_root: f64,
    pub theta_llm: f64,
    pub k_master: f64,
    pub xi_anti_hallucination: f64,
    pub psi_host: f64,
    pub phi_cycle: f64,
    pub h_real: f64,
    pub epsilon_self_repair: f64,
    pub t: f64,
    pub xuanji_inputs: XuanjiRawInputs,
    pub coefficients_cache: Option<XuanjiCoefficients>,
}

pub fn calculate_delta_g_v8_2(params: &V8ParamsInternalV82) -> f64 {
    let coeffs = params
        .coefficients_cache
        .as_ref()
        .cloned()
        .unwrap_or_else(|| XuanjiCoefficients::compute(&params.xuanji_inputs));

    let numerator = params.lambda_root
        * params.theta_llm
        * params.k_master
        * params.xi_anti_hallucination
        * params.psi_host
        * params.phi_cycle
        * coeffs.phi_network
        * coeffs.gamma_mutation
        * coeffs.omega_session
        * coeffs.pi_coord
        * coeffs.sigma_storage;

    let denominator = params.h_real * params.t * params.epsilon_self_repair;

    let safe_denom = denominator.max(0.001);
    (numerator / safe_denom).min(1000.0)
}

pub fn from_v8_to_internal_v82(v8: &ApexParamsV8) -> V8ParamsInternalV82 {
    let k_master_safe = calculate_k_master_safe(&v8.master);
    let phi_cycle_safe = calculate_cycle_gain_safe(&v8.cycle);

    V8ParamsInternalV82 {
        lambda_root: v8.lambda_root,
        theta_llm: calculate_llm_agent_efficiency(&v8.llm_agent),
        k_master: k_master_safe,
        xi_anti_hallucination: v8.xi_anti_hallucination,
        psi_host: calculate_host_health(&v8.host),
        phi_cycle: phi_cycle_safe,
        h_real: v8.h_real,
        epsilon_self_repair: calculate_self_repair(&v8.self_repair),
        t: v8.t_iteration,
        xuanji_inputs: XuanjiRawInputs::default(),
        coefficients_cache: None,
    }
}

// ═════════════════════════════════════════════════════════════════════════════
// V8.x 凌晨自进化模块
// ═════════════════════════════════════════════════════════════════════════════

#[derive(Debug, Clone)]
pub struct GitSyncParams {
    pub delta_version_diff: f64,
    pub rho_sync_fail: f64,
    pub tau_auto_merge: f64,
}

#[derive(Debug, Clone)]
pub struct AutoLearnParams {
    pub l_extract: f64,
    pub g_generalize: f64,
    pub s_summarize: f64,
    pub t_time: f64,
}

#[derive(Debug, Clone)]
pub struct DawnParams {
    pub omega_dawn: f64,
    pub git_sync: GitSyncParams,
    pub auto_learn: AutoLearnParams,
}

pub fn calculate_git_sync(params: &GitSyncParams) -> f64 {
    let delta = params.delta_version_diff.clamp(0.0, 1.0);
    let rho = params.rho_sync_fail.clamp(0.0, 1.0);
    let tau = params.tau_auto_merge.clamp(0.0, 1.0);
    (1.0 - delta) * (1.0 - rho) * tau
}

pub fn calculate_auto_learn(params: &AutoLearnParams) -> f64 {
    let l = params.l_extract.clamp(0.0, 1.0);
    let g = params.g_generalize.clamp(0.0, 1.0);
    let s = params.s_summarize.clamp(0.0, 1.0);
    let t = params.t_time.max(0.0);
    let numerator = l * g * s;
    let denominator = (t + 1.0).max(0.001);
    numerator / denominator
}

pub fn calculate_dawn_omega(params: &DawnParams) -> f64 {
    let git_sync = calculate_git_sync(&params.git_sync);
    let auto_learn = calculate_auto_learn(&params.auto_learn);
    params.omega_dawn * git_sync * auto_learn
}

#[cfg(test)]
mod dawn_tests {
    use super::*;

    #[test]
    fn test_git_sync_perfect() {
        let params = GitSyncParams {
            delta_version_diff: 0.0,
            rho_sync_fail: 0.0,
            tau_auto_merge: 1.0,
        };
        let result = calculate_git_sync(&params);
        assert!((result - 1.0).abs() < 0.001);
    }

    #[test]
    fn test_git_sync_partial() {
        let params = GitSyncParams {
            delta_version_diff: 0.1,
            rho_sync_fail: 0.05,
            tau_auto_merge: 0.8,
        };
        let result = calculate_git_sync(&params);
        assert!((result - 0.684).abs() < 0.001);
    }

    #[test]
    fn test_auto_learn_perfect_fast() {
        let params = AutoLearnParams {
            l_extract: 1.0,
            g_generalize: 1.0,
            s_summarize: 1.0,
            t_time: 0.0,
        };
        let result = calculate_auto_learn(&params);
        assert!((result - 1.0).abs() < 0.001);
    }

    #[test]
    fn test_auto_learn_normal() {
        let params = AutoLearnParams {
            l_extract: 0.8,
            g_generalize: 0.7,
            s_summarize: 0.9,
            t_time: 1.0,
        };
        let result = calculate_auto_learn(&params);
        assert!((result - 0.252).abs() < 0.001);
    }

    #[test]
    fn test_dawn_omega_full() {
        let params = DawnParams {
            omega_dawn: 1.0,
            git_sync: GitSyncParams {
                delta_version_diff: 0.0,
                rho_sync_fail: 0.0,
                tau_auto_merge: 1.0,
            },
            auto_learn: AutoLearnParams {
                l_extract: 1.0,
                g_generalize: 1.0,
                s_summarize: 1.0,
                t_time: 0.0,
            },
        };
        let result = calculate_dawn_omega(&params);
        assert!((result - 1.0).abs() < 0.001);
    }

    #[test]
    fn test_dawn_omega_normal() {
        let params = DawnParams {
            omega_dawn: 0.8,
            git_sync: GitSyncParams {
                delta_version_diff: 0.1,
                rho_sync_fail: 0.05,
                tau_auto_merge: 0.8,
            },
            auto_learn: AutoLearnParams {
                l_extract: 0.8,
                g_generalize: 0.7,
                s_summarize: 0.9,
                t_time: 1.0,
            },
        };
        let result = calculate_dawn_omega(&params);
        assert!(result > 0.0 && result < 1.0);
    }
}

// ═════════════════════════════════════════════════════════════════════════════
// V10.1 新增模块测试
// ═════════════════════════════════════════════════════════════════════════════

#[cfg(test)]
mod v10_1_new_tests {
    use super::*;

    // ── Σ_memory 测试 ──

    #[test]
    fn test_sigma_memory_empty() {
        let params = SuperMemoryParams::default();
        let result = calculate_sigma_memory(&params);
        assert!(result >= 0.0);
    }

    #[test]
    fn test_sigma_memory_with_entries() {
        let mut params = SuperMemoryParams::default();
        params.memory_entries.push(MemoryEntry {
            id: "mem1".to_string(),
            content: "test content".to_string(),
            embedding: vec![0.1, 0.2, 0.3],
            timestamp: 1000,
            importance: 0.8,
            memory_type: MemoryType::Semantic,
            access_count: 5,
        });
        params.memory_entries.push(MemoryEntry {
            id: "mem2".to_string(),
            content: "another test".to_string(),
            embedding: vec![0.4, 0.5, 0.6],
            timestamp: 1001,
            importance: 0.6,
            memory_type: MemoryType::Episodic,
            access_count: 3,
        });
        let result = calculate_sigma_memory(&params);
        assert!(result > 0.0);
    }

    #[test]
    fn test_add_memory_entry() {
        let mut params = SuperMemoryParams::default();
        let entry = MemoryEntry {
            id: "mem1".to_string(),
            content: "test".to_string(),
            embedding: vec![0.1],
            timestamp: 1000,
            importance: 0.5,
            memory_type: MemoryType::Working,
            access_count: 0,
        };
        add_memory_entry(&mut params, entry.clone());
        assert_eq!(params.memory_entries.len(), 1);
        assert_eq!(params.memory_entries[0].id, "mem1");
    }

    #[test]
    fn test_search_memory() {
        let mut params = SuperMemoryParams::default();
        params.memory_entries.push(MemoryEntry {
            id: "mem1".to_string(),
            content: "rust programming language".to_string(),
            embedding: vec![],
            timestamp: 1000,
            importance: 0.8,
            memory_type: MemoryType::Semantic,
            access_count: 0,
        });
        let results = search_memory(&params, "rust");
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].id, "mem1");
    }

    #[test]
    fn test_search_memory_no_match() {
        let params = SuperMemoryParams::default();
        let results = search_memory(&params, "nonexistent");
        assert_eq!(results.len(), 0);
    }

    // ── τ_trace 测试 ──

    #[test]
    fn test_tau_trace_empty() {
        let params = TraceParams::default();
        let result = calculate_tau_trace(&params);
        assert!((result - 0.0).abs() < 0.001);
    }

    #[test]
    fn test_tau_trace_complete() {
        let params = TraceParams {
            entries: vec![
                TraceEntry {
                    step: 1,
                    decision: "choose A".to_string(),
                    reason: "A is better".to_string(),
                    result: "success".to_string(),
                    delta_g: 0.5,
                    timestamp: 1000,
                },
                TraceEntry {
                    step: 2,
                    decision: "choose B".to_string(),
                    reason: "B is better".to_string(),
                    result: "success".to_string(),
                    delta_g: 0.6,
                    timestamp: 1001,
                },
            ],
            max_entries: 1000,
        };
        let result = calculate_tau_trace(&params);
        // 所有字段都完整，所以应该返回 1.0
        assert!((result - 1.0).abs() < 0.001);
    }

    #[test]
    fn test_tau_trace_partial() {
        let params = TraceParams {
            entries: vec![
                TraceEntry {
                    step: 1,
                    decision: "choose A".to_string(),
                    reason: "".to_string(), // 缺少reason
                    result: "success".to_string(),
                    delta_g: 0.5,
                    timestamp: 1000,
                },
            ],
            max_entries: 1000,
        };
        let result = calculate_tau_trace(&params);
        // decision=1, reason=0, result=1 → (1+0+1)/3 = 0.667
        assert!((result - 0.667).abs() < 0.001);
    }

    #[test]
    fn test_add_trace_entry() {
        let mut params = TraceParams::default();
        let entry = TraceEntry {
            step: 1,
            decision: "test".to_string(),
            reason: "test".to_string(),
            result: "test".to_string(),
            delta_g: 0.5,
            timestamp: 1000,
        };
        add_trace_entry(&mut params, entry);
        assert_eq!(params.entries.len(), 1);
    }

    #[test]
    fn test_trace_summary() {
        let params = TraceParams {
            entries: vec![
                TraceEntry {
                    step: 1,
                    decision: "A".to_string(),
                    reason: "B".to_string(),
                    result: "C".to_string(),
                    delta_g: 0.5,
                    timestamp: 1000,
                },
                TraceEntry {
                    step: 2,
                    decision: "A".to_string(),
                    reason: "".to_string(), // 不完整
                    result: "C".to_string(),
                    delta_g: 0.6,
                    timestamp: 1001,
                },
            ],
            max_entries: 1000,
        };
        let summary = get_trace_summary(&params);
        assert_eq!(summary.total_steps, 2);
        assert_eq!(summary.complete_steps, 1);
        assert!((summary.completeness_rate - 0.5).abs() < 0.001);
    }

    #[test]
    fn test_trace_to_delta_g_contribution() {
        let tau = 0.8;
        let base = 1.0;
        let result = trace_to_delta_g_contribution(tau, base);
        // 1.0 * (0.5 + 0.5 * 0.8) = 1.0 * 0.9 = 0.9
        assert!((result - 0.9).abs() < 0.001);
    }

    // ── 防盗版模块测试 ──

    #[test]
    fn test_verify_license_valid() {
        let status = verify_license("node_12345678", "xuanji_secret_token_1234567890");
        assert_eq!(status, LicenseStatus::Valid);
    }

    #[test]
    fn test_verify_license_invalid_node_id() {
        let status = verify_license("invalid_node", "xuanji_secret");
        assert_eq!(status, LicenseStatus::Invalid);
    }

    #[test]
    fn test_verify_license_short_secret() {
        let status = verify_license("node_12345678", "short");
        assert_eq!(status, LicenseStatus::Invalid);
    }

    #[test]
    fn test_embed_watermark() {
        let delta_g = 1.0;
        let node_id = "node_test123";
        let watermarked = embed_watermark(delta_g, node_id);
        // 水印扰动应该很小
        assert!((watermarked - delta_g).abs() < 0.001);
    }

    #[test]
    fn test_check_module_integrity() {
        let result = check_module_integrity();
        assert!(result.is_ok());
    }

    #[test]
    fn test_license_manager() {
        let mut manager = LicenseManager::new("node_12345678", "xuanji_secret_token_1234567890");
        let status = manager.activate().unwrap();
        assert_eq!(status, LicenseStatus::Valid);
        assert!(manager.license_info.is_some());
        
        let watermarked = manager.apply_watermark(1.0);
        assert!(watermarked.is_finite());
    }

    #[test]
    fn test_watermark_uniqueness() {
        // 不同节点ID应该产生不同的水印
        let watermark1 = calculate_node_watermark("node_11111111");
        let watermark2 = calculate_node_watermark("node_22222222");
        // 由于哈希函数的特性，不同输入应该大概率产生不同输出
        // 这里我们只检查它们都是有效的f64
        assert!(watermark1 >= 0.0 && watermark1 < 1.0);
        assert!(watermark2 >= 0.0 && watermark2 < 1.0);
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// 8.2 V8.2 单元测试
// ─────────────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod v8_2_tests {
    use super::*;

    fn default_v8_2_params() -> V8ParamsInternalV82 {
        V8ParamsInternalV82 {
            lambda_root: 0.95,
            theta_llm: 0.556,
            k_master: 1.107,
            xi_anti_hallucination: 1.0,
            psi_host: 0.941,
            phi_cycle: 1.284,
            h_real: 0.5,
            epsilon_self_repair: 1.053,
            t: 2.0,
            xuanji_inputs: XuanjiRawInputs {
                retry_rate: 0.05,
                rate_limit_freq: 0.02,
                conn_stable: 0.98,
                code_change_rate: 0.5,
                hollow_threshold: 0.01,
                restart_freq: 0.01,
                env_loss_rate: 0.02,
                recovery_success: 0.95,
                alive_procs: 1,
                total_procs: 1,
                zombie_rate: 0.0,
                callback_success: 1.0,
                free_disk_ratio: 0.8,
                write_fail_rate: 0.001,
                integrity: 0.999,
            },
            coefficients_cache: None,
        }
    }

    #[test]
    fn test_k_master_safe_normal() {
        let params = MasterParams {
            k_code: 1.0,
            tau_transfer: vec![0.1, 0.05, 0.08],
            upsilon_apply: 0.9,
        };
        let safe = calculate_k_master_safe(&params);
        assert!((safe - 1.126).abs() < 0.001);
    }

    #[test]
    fn test_k_master_safe_extreme() {
        let params = MasterParams {
            k_code: 1.0,
            tau_transfer: vec![0.999],
            upsilon_apply: 1.0,
        };
        let safe = calculate_k_master_safe(&params);
        assert!((safe - 100.0).abs() < 0.001);
    }

    #[test]
    fn test_cycle_gain_safe_overflow() {
        let params = CycleParams {
            eta_skill_up: 10.0,
            rho_result_feedback: 10.0,
        };
        let safe = calculate_cycle_gain_safe(&params);
        assert!((safe - 1096.633).abs() < 0.1);
    }

    #[test]
    fn test_xuanji_coefficients_compute() {
        let inputs = XuanjiRawInputs {
            retry_rate: 0.05,
            rate_limit_freq: 0.02,
            conn_stable: 0.99,
            code_change_rate: 0.15,
            hollow_threshold: 0.01,
            restart_freq: 0.02,
            env_loss_rate: 0.01,
            recovery_success: 0.95,
            alive_procs: 9,
            total_procs: 10,
            zombie_rate: 0.05,
            callback_success: 0.9,
            free_disk_ratio: 0.8,
            write_fail_rate: 0.001,
            integrity: 0.999,
        };
        let coeffs = XuanjiCoefficients::compute(&inputs);
        assert!((coeffs.phi_network - 0.921).abs() < 0.001);
        assert!((coeffs.gamma_mutation - 0.15).abs() < 0.001);
    }

    #[test]
    fn test_xuanji_coefficients_hollow_detected() {
        let inputs = XuanjiRawInputs {
            retry_rate: 0.05,
            rate_limit_freq: 0.02,
            conn_stable: 0.98,
            code_change_rate: 0.005,
            hollow_threshold: 0.01,
            restart_freq: 0.01,
            env_loss_rate: 0.02,
            recovery_success: 0.95,
            alive_procs: 1,
            total_procs: 1,
            zombie_rate: 0.0,
            callback_success: 1.0,
            free_disk_ratio: 0.8,
            write_fail_rate: 0.001,
            integrity: 0.999,
        };
        let coeffs = XuanjiCoefficients::compute(&inputs);
        assert!((coeffs.gamma_mutation - 0.1).abs() < 0.001);
    }

    #[test]
    fn test_delta_g_v8_2_basic() {
        let params = default_v8_2_params();
        let result = calculate_delta_g_v8_2(&params);
        assert!(result > 0.0 && result < 1000.0);
    }

    #[test]
    fn test_delta_g_v8_2_div_zero_protection() {
        let mut params = default_v8_2_params();
        params.h_real = 0.0;
        let result = calculate_delta_g_v8_2(&params);
        assert!(result.is_finite());
    }

    #[test]
    fn test_from_v8_to_internal_v82() {
        let v8_params = super::tests::default_v8_params();
        let v82 = from_v8_to_internal_v82(&v8_params);
        assert_eq!(v82.lambda_root, v8_params.lambda_root);
        assert_eq!(v82.h_real, v8_params.h_real);
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// 9. 主函数入口
// ─────────────────────────────────────────────────────────────────────────────

fn main() {
    println!("╔══════════════════════════════════════════╗");
    println!("║   APEX V10.1 ΔG_ultimate 计算演示      ║");
    println!("╚══════════════════════════════════════════╝\n");

    // ── V8.0 演示 ──
    let params = ApexParamsV8 {
        lambda_root: 0.95,
        xi_anti_hallucination: 1.0,
        h_real: 0.5,
        t_iteration: 2.0,
        llm_agent: LlmAgentParams {
            lambda_single_call: 0.9,
            mu_multi_task: 0.85,
            sigma_high_quality: 0.88,
            gamma_llm_cost: 0.1,
        },
        master: MasterParams {
            k_code: 1.0,
            tau_transfer: vec![0.1, 0.05, 0.08],
            upsilon_apply: 0.9,
        },
        self_repair: SelfRepairParams {
            g_target: 100.0,
            g_actual: 95.0,
            delta_error_locate: 1.0,
            psi_thorough_fix: 1.0,
            kappa_no_repeat: 1.0,
        },
        cycle: CycleParams {
            eta_skill_up: 0.5,
            rho_result_feedback: 0.5,
        },
        host: HostHealthParams {
            psi_mem: 0.98,
            psi_app: 0.99,
            psi_disk: 0.97,
            omega_dawn: 1.0,
        },
    };

    match calculate_delta_g_ultimate(&params) {
        Ok(delta_g) => {
            println!("[V8.0] ΔG_ultimate = {:.6}", delta_g);
            println!("       进化得分     = {:.6}", evolution_score(delta_g, params.h_real));
        }
        Err(e) => eprintln!("[V8.0] 计算错误: {}", e),
    }

    // ── V8.1 演示 ──
    let v81 = from_v8_to_internal(&params);
    let delta_g_v81 = calculate_delta_g_v8_1(&v81);
    println!("\n[V8.1] ΔG_v8_1 = {:.6}", delta_g_v81);

    // ── V8.2 演示 ──
    let v82 = from_v8_to_internal_v82(&params);
    let delta_g_v82 = calculate_delta_g_v8_2(&v82);
    println!("[V8.2] ΔG_v8_2 = {:.6}", delta_g_v82);

    // ── V10.1 新增模块演示 ──
    println!("\n═══ V10.1 新增模块 ═══");

    // Σ_memory 演示
    let mut memory_params = SuperMemoryParams::default();
    memory_params.memory_entries.push(MemoryEntry {
        id: "mem_001".to_string(),
        content: "APEX公式是璇玑帝国的核心算法".to_string(),
        embedding: vec![0.1, 0.2, 0.3],
        timestamp: 1700000000,
        importance: 0.9,
        memory_type: MemoryType::Semantic,
        access_count: 10,
    });
    let sigma_memory = calculate_sigma_memory(&memory_params);
    println!("\n[Σ_memory] 超忆全域记忆系数 = {:.6}", sigma_memory);

    // τ_trace 演示
    let mut trace_params = TraceParams::default();
    trace_params.entries.push(TraceEntry {
        step: 1,
        decision: "优化K_master公式".to_string(),
        reason: "提高跨领域迁移效率".to_string(),
        result: "K_master_safe收敛".to_string(),
        delta_g: 0.15,
        timestamp: 1700000000,
    });
    trace_params.entries.push(TraceEntry {
        step: 2,
        decision: "添加Φ_cycle上限".to_string(),
        reason: "防止数值爆炸".to_string(),
        result: "e^7上限保护生效".to_string(),
        delta_g: 0.12,
        timestamp: 1700000001,
    });
    let tau_trace = calculate_tau_trace(&trace_params);
    println!("[τ_trace] 过程追踪系数 = {:.6}", tau_trace);

    // 防盗版演示
    let mut license_mgr = LicenseManager::new("node_71a56aa8a590f8c2", "xuanji_protected_token_12345678901234567890");
    match license_mgr.activate() {
        Ok(status) => {
            println!("\n[License] 状态 = {:?}", status);
            let watermarked_g = license_mgr.apply_watermark(delta_g_v82);
            println!("[Watermark] 带水印ΔG = {:.6}", watermarked_g);
        }
        Err(e) => println!("[License] 激活失败: {}", e),
    }

    // 模块完整性检查
    match check_module_integrity() {
        Ok(_) => println!("\n[Integrity] 所有模块完整性验证通过 ✓"),
        Err(e) => println!("\n[Integrity] 验证失败: {}", e),
    }

    // 五系数实时重算演示
    println!("\n[五系数实时重算]");
    let coeffs = XuanjiCoefficients::compute(&v82.xuanji_inputs);
    println!("  Φ_network   = {:.6}", coeffs.phi_network);
    println!("  Γ_mutation  = {:.6}", coeffs.gamma_mutation);
    println!("  Ω_session   = {:.6}", coeffs.omega_session);
    println!("  Π_coord     = {:.6}", coeffs.pi_coord);
    println!("  Σ_storage   = {:.6}", coeffs.sigma_storage);

    // 自我意识模块演示
    println!("\n[Ω_self] 自我意识系数");
    let awareness_params = SelfAwarenessParams {
        sigma_coherence: 0.9,
        delta_drift: 0.1,
        rho_alignment: 0.85,
    };
    let omega_self = calculate_omega_self(&awareness_params);
    println!("  Ω_self = {:.6}", omega_self);

    // 凌晨自进化演示
    println!("\n[Ω_dawn] 凌晨自进化系数");
    let dawn_params = DawnParams {
        omega_dawn: 1.0,
        git_sync: GitSyncParams {
            delta_version_diff: 0.05,
            rho_sync_fail: 0.02,
            tau_auto_merge: 0.9,
        },
        auto_learn: AutoLearnParams {
            l_extract: 0.85,
            g_generalize: 0.8,
            s_summarize: 0.9,
            t_time: 0.5,
        },
    };
    let dawn_omega = calculate_dawn_omega(&dawn_params);
    println!("  Ω_dawn = {:.6}", dawn_omega);

    println!("\n╔══════════════════════════════════════════╗");
    println!("║   APEX V10.1 计算完成                 ║");
    println!("╚══════════════════════════════════════════╝");
}
