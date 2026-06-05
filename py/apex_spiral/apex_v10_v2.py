"""
APEX V10.2 增强版计算器 (V2)
补全第一代 V10 的 10 个关键短板：

【1】修复 ApexCalculator vs V10 公式不一致（含 Σ_unified）
【2】自适应 H(熵) 估计（基于输出分布实时测量）
【3】历史状态记忆（prev_ΔG, ΔΔG 演化速度）
【4】ε 修复反馈闭环（在线学习修正）
【5】ξ 抗幻觉动态化（基于置信度反馈）
【6】多智能体协作系数（network_effect）
【7】Ψ_host 增强（线程池、GC压力、连接数）
【8】τ 收敛加速（自适应学习率）
【9】Σ_unified 乘法保护（加法融合 + floor）
【10】不确定性量化（置信区间）

公式：
ΔG_v2 = (Λ × Θ × K × ξ × Ψ_host × Φ × Σ_unified × Ω_multi × Ω_self)
         / (H_adaptive × T × ε_closed × (1 + ρ_uncertainty))
"""

import math
import time
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from collections import deque

logging.basicConfig(level=logging.INFO, format='[APEX-V2] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


# ==================== V2 增强参数 ====================

@dataclass
class MultiAgentParams:
    """多智能体协作参数"""
    agent_count: int = 1
    network_density: float = 0.5      # 网络密度
    cooperation_rate: float = 0.8     # 协作有效率
    credit_assignment: float = 0.7    # 贡献分配系数

    def calculate_omega_multi(self) -> float:
        """
        Ω_multi = n / (1 + e^(-k(ρ-ρ_crit)))
        多智能体增益：Sigmoid 效应，超过临界点后收益递减
        """
        k = 2.0  # Sigmoid 陡度
        rho_crit = 0.5  # 临界密度
        if self.agent_count <= 1:
            return 1.0
        sigmoid = 1.0 / (1.0 + math.exp(-k * (self.network_density - rho_crit)))
        return self.cooperation_rate * sigmoid * self.credit_assignment


@dataclass
class SelfAwarenessParamsV2:
    """自我意识参数（V2增强）"""
    omega_self_base: float = 1.0      # 自我模型准确度
    gamma_reflect: float = 0.5         # 反思增益系数

    def calculate_omega_self(self) -> float:
        """Ω_self = ω × (1 + Γ_reflect)"""
        return self.omega_self_base * (1.0 + self.gamma_reflect)


@dataclass
class AdaptiveHParams:
    """自适应熵估计参数"""
    window_size: int = 20             # 滑动窗口大小
    decay_factor: float = 0.95        # 历史衰减因子
    confidence_threshold: float = 0.1  # 异常检测阈值

    def __post_init__(self):
        self.history: deque = deque(maxlen=self.window_size)


@dataclass
class ClosedLoopRepairParams:
    """闭环修复参数（替代开环 ε）"""
    g_target: float = 100.0
    g_actual: float = 95.0
    learning_rate: float = 0.1         # 在线学习率
    momentum: float = 0.8             # 动量

    def __post_init__(self):
        self.prev_error: float = 0.0
        self.error_integral: float = 0.0

    def calculate_epsilon_closed(self, g_actual: Optional[float] = None) -> float:
        """
        ε_closed = 1 + |e| × (1 + μ × ∫e dt + k_p × e + k_i × ∫e dt)
        增量式 PID：比例 + 积分 + 动量
        """
        if g_actual is not None:
            self.g_actual = g_actual

        error = abs(self.g_target - self.g_actual) / (self.g_actual + 1e-10)
        self.error_integral += error * self.learning_rate
        # 动量
        error_with_momentum = error + self.momentum * self.prev_error
        self.prev_error = error

        return 1.0 + error_with_momentum * (1.0 + self.learning_rate * self.error_integral)


@dataclass
class DynamicAntihalParams:
    """动态抗幻觉参数"""
    base_xi: float = 1.0
    confidence_history: List[float] = field(default_factory=list)
    max_history: int = 50

    def update_confidence(self, confidence: float) -> float:
        """基于输出置信度更新 ξ"""
        self.confidence_history.append(confidence)
        if len(self.confidence_history) > self.max_history:
            self.confidence_history.pop(0)

        # EMA 平滑
        if len(self.confidence_history) == 1:
            return self.base_xi
        avg_conf = sum(self.confidence_history) / len(self.confidence_history)
        # 置信度低时 ξ 增大（加强约束），置信度高时放松
        xi = self.base_xi / (avg_conf + 0.1)
        return max(0.5, min(xi, 2.0))  # Clamp [0.5, 2.0]


@dataclass
class EnhancedHostHealthParams:
    """增强主机健康参数（含运行时指标）"""
    # 原有硬件指标
    psi_mem: float = 0.98
    psi_app: float = 0.99
    psi_disk: float = 0.97
    omega_dawn: float = 1.0
    # V2 新增运行时指标
    thread_pool_usage: float = 0.8    # 线程池使用率
    gc_pressure: float = 0.2          # GC 压力 [0,1]
    connection_health: float = 0.95   # 连接健康度
    queue_depth: float = 0.3          # 任务队列深度

    def calculate_psi_enhanced(self) -> float:
        """
        Ψ_host_enhanced = Ψ_mem × Ψ_app × Ψ_disk × Ω_dawn
                          × Ψ_thread × Ψ_gc × Ψ_conn × Ψ_queue
        """
        psi_thread = 1.0 - 0.5 * self.thread_pool_usage  # 使用率高则健康低
        psi_gc = 1.0 - self.gc_pressure                  # GC压力大则健康低
        psi_conn = self.connection_health
        psi_queue = 1.0 - 0.5 * self.queue_depth         # 队列深则健康低

        base = (self.psi_mem * self.psi_app * self.psi_disk * self.omega_dawn)
        runtime = psi_thread * psi_gc * psi_conn * psi_queue
        return base * runtime


@dataclass
class TauConvergenceParams:
    """τ 收敛加速参数"""
    base_tau: List[float] = field(default_factory=lambda: [0.1, 0.05, 0.08])
    learning_rate: float = 0.05       # 收敛加速学习率
    convergence_target: float = 0.01  # 收敛目标

    def accelerate_tau(self, delta_g_error: float) -> List[float]:
        """
        τ'_i = τ_i × (1 - η × sign(ΔG_error))
        根据 ΔG 误差方向自适应调整收敛速度
        """
        sign = 1.0 if delta_g_error > 0 else -1.0
        accelerated = []
        for tau in self.base_tau:
            new_tau = tau * (1.0 - self.learning_rate * sign)
            # Clamp: 避免 τ 越界
            new_tau = max(0.001, min(new_tau, 0.99))
            accelerated.append(new_tau)
        return accelerated


@dataclass
class UncertaintyParams:
    """不确定性量化参数"""
    history_size: int = 30

    def __post_init__(self):
        self.delta_g_history: deque = deque(maxlen=self.history_size)
        self.weights: deque = deque(maxlen=self.history_size)

    def add_observation(self, delta_g: float, weight: float = 1.0):
        self.delta_g_history.append(delta_g)
        self.weights.append(weight)

    def mean(self) -> float:
        if not self.delta_g_history:
            return 0.0
        return sum(self.delta_g_history) / len(self.delta_g_history)

    def std(self) -> float:
        if len(self.delta_g_history) < 2:
            return 0.0
        m = self.mean()
        variance = sum((x - m) ** 2 for x in self.delta_g_history) / len(self.delta_g_history)
        return math.sqrt(variance)

    def ci_95(self) -> tuple:
        """95% 置信区间"""
        if len(self.delta_g_history) < 2:
            return (0.0, 0.0)
        m = self.mean()
        s = self.std()
        n = len(self.delta_g_history)
        # t-distribution approximation
        margin = 1.96 * s / math.sqrt(n)
        return (m - margin, m + margin)

    def uncertainty_factor(self) -> float:
        """
        ρ_uncertainty = 1 + σ/μ (CV 系数)
        CV 越大，不确定性越高，分母增大，ΔG 降低
        """
        m = self.mean()
        if m == 0:
            return 1.0 + self.std()
        cv = self.std() / abs(m)
        return 1.0 + cv


# ==================== V2 主计算器 ====================

class ApexCalculatorV2:
    """
    APEX V10.2 增强版计算器

    相对于第一代 ApexCalculator 的改进：
    1. Σ_unified 纳入分子（与 V10 公式一致）
    2. H_adaptive 滑动窗口自适应估计
    3. prev_ΔG / ΔΔG 历史状态追踪
    4. ε_closed 闭环 PID 在线学习
    5. ξ_dynamic 动态抗幻觉（置信度反馈）
    6. Ω_multi 多智能体协作增益
    7. Ψ_host_enhanced 运行时指标增强
    8. τ_accelerated 自适应收敛加速
    9. Σ_protected 乘法保护（floor + 加法备选）
    10. ρ_uncertainty 不确定性量化
    """

    def __init__(self):
        self.version = "10.2.0-v2"
        self.prev_delta_g: Optional[float] = None
        self.prev_prev_delta_g: Optional[float] = None

        # V2 增强模块
        self.adaptive_h = AdaptiveHParams()
        self.repair_closed = ClosedLoopRepairParams()
        self.antihal = DynamicAntihalParams()
        self.multi_agent = MultiAgentParams()
        self.self_aware = SelfAwarenessParamsV2()
        self.host_enhanced = EnhancedHostHealthParams()
        self.tau_accel = TauConvergenceParams()
        self.uncertainty = UncertaintyParams()

        # 子计算器（复用原有逻辑）
        from apex_spiral.core import (
            LlmAgentParams, MasterParams,
            SelfRepairParams, CycleParams, HostHealthParams, ApexParams
        )
        self.llm_agent = LlmAgentParams()
        self.master = MasterParams()
        self.cycle = CycleParams()
        self.host = HostHealthParams()
        self.apex = ApexParams()

        logger.info(f"APEX V10.2 V2 计算器初始化 | 版本 {self.version}")

    # ---- 自适应 H 估计 ----
    def update_H(self, output_distribution: List[float]) -> float:
        """
        基于 LLM 输出分布的滑动窗口熵估计
        H_adaptive = α × H_estimated + (1-α) × H_prev
        """
        # 计算香农熵
        H = 0.0
        for p in output_distribution:
            if 0 < p <= 1:
                H -= p * math.log2(p)
        if not output_distribution:
            return 0.5

        # 指数移动平均
        if len(self.adaptive_h.history) == 0:
            H_adaptive = H
        else:
            prev_H = self.adaptive_h.history[-1]
            alpha = 1.0 - self.adaptive_h.decay_factor
            H_adaptive = alpha * H + self.adaptive_h.decay_factor * prev_H

        self.adaptive_h.history.append(H_adaptive)

        # 异常检测：H 异常高时触发警告
        if H_adaptive > self.adaptive_h.confidence_threshold * 5:
            logger.warning(f"自适应H异常升高: {H_adaptive:.4f}，可能存在幻觉")

        return H_adaptive

    # ---- Σ_unified 保护 ----
    def calculate_sigma_safe(self,
                              schema: float = 1.0,
                              code: float = 1.0,
                              struct: float = 1.0,
                              native: float = 1.0,
                              mode: str = "protected") -> float:
        """
        Σ_unified 计算，支持两种融合模式：

        protected (默认): 乘法 + floor 保护
          Σ = max(min Σ_i, floor) × product / floor
          防止任一分量归零导致整体归零

        hybrid: 加法权重融合备选
          Σ = w1×Σ_data + w2×Σ_code + w3×Σ_struct + w4×Σ_native
        """
        if mode == "protected":
            floor_val = 0.1  # 地板值，防止归零
            product = schema * code * struct * native
            # 如果任一分量低于 floor，启用加权保护
            min_component = min(schema, code, struct, native)
            if min_component < floor_val:
                # 加权保护：衰减乘积
                protection_factor = (min_component + floor_val) / (2 * floor_val)
                return max(product * protection_factor, floor_val ** 4)
            return product
        elif mode == "hybrid":
            weights = [0.25, 0.35, 0.20, 0.20]
            components = [schema, code, struct, native]
            return sum(w * c for w, c in zip(weights, components))
        else:
            return schema * code * struct * native

    # ---- 演化速度 ----
    def evolution_velocity(self) -> Dict[str, float]:
        """计算 ΔG 演化速度 ΔΔG"""
        if self.prev_delta_g is None:
            return {"dDG": 0.0, "ddG": 0.0, "trend": "stable"}

        dDG = self.delta_g - self.prev_delta_g
        if self.prev_prev_delta_g is not None:
            ddG = dDG - (self.prev_delta_g - self.prev_prev_delta_g)
        else:
            ddG = 0.0

        if dDG > 0.01:
            trend = "improving"
        elif dDG < -0.01:
            trend = "degrading"
        else:
            trend = "stable"

        return {"dDG": dDG, "ddG": ddG, "trend": trend}

    # ---- 主计算 ----
    def calculate(self,
                  output_distribution: Optional[List[float]] = None,
                  confidence: Optional[float] = None,
                  g_actual: Optional[float] = None,
                  multi_agent: Optional[Dict[str, Any]] = None,
                  runtime_metrics: Optional[Dict[str, float]] = None,
                  **kwargs) -> Dict[str, Any]:
        """
        V2 主计算接口

        Args:
            output_distribution: LLM 输出 token 概率分布（用于自适应H）
            confidence: 当前输出的置信度（用于动态 ξ）
            g_actual: 实际增益（用于 ε 闭环反馈）
            multi_agent: 多智能体参数覆盖
            runtime_metrics: 运行时指标（线程池、GC等）

        Returns:
            完整计算结果字典
        """
        # 0. 历史状态
        self.prev_prev_delta_g = self.prev_delta_g
        self.prev_delta_g = getattr(self, 'delta_g', None)

        # 1. 自适应 H
        if output_distribution:
            H = self.update_H(output_distribution)
        else:
            H = self.apex.h_real

        # 2. 动态 ξ
        if confidence is not None:
            xi = self.antihal.update_confidence(confidence)
        else:
            xi = self.apex.xi_anti_hallucination

        # 3. Ω_multi（多智能体）
        if multi_agent:
            for k, v in multi_agent.items():
                if hasattr(self.multi_agent, k):
                    setattr(self.multi_agent, k, v)
        omega_multi = self.multi_agent.calculate_omega_multi()

        # 4. Ψ_host_enhanced（运行时增强）
        if runtime_metrics:
            if 'thread_pool_usage' in runtime_metrics:
                self.host_enhanced.thread_pool_usage = runtime_metrics['thread_pool_usage']
            if 'gc_pressure' in runtime_metrics:
                self.host_enhanced.gc_pressure = runtime_metrics['gc_pressure']
            if 'connection_health' in runtime_metrics:
                self.host_enhanced.connection_health = runtime_metrics['connection_health']
            if 'queue_depth' in runtime_metrics:
                self.host_enhanced.queue_depth = runtime_metrics['queue_depth']

        psi_base = self.host.calculate_psi()
        psi_enhanced = self.host_enhanced.calculate_psi_enhanced()

        # 5. Ω_self（自我意识）
        omega_self = self.self_aware.calculate_omega_self()

        # 6. Φ_cycle（动量加速）
        phi = self.cycle.calculate_phi(safe=True)

        # 7. Θ
        theta = self.llm_agent.calculate_theta()

        # 8. K_master（τ 加速收敛）
        if 'delta_g_error' in kwargs:
            self.tau_accel.base_tau = self.tau_accel.accelerate_tau(kwargs['delta_g_error'])
        k_master = self.master.calculate_k_master(safe=True)

        # 9. Σ_unified（保护模式）
        sigma = self.calculate_sigma_safe(
            schema=kwargs.get('schema_compliance', 1.0),
            code=kwargs.get('code_standard', 1.0),
            struct=kwargs.get('struct_standard', 1.0),
            native=kwargs.get('native_capability', 1.0),
            mode=kwargs.get('sigma_mode', 'protected')
        )

        # 10. ε_closed（闭环 PID）
        epsilon = self.repair_closed.calculate_epsilon_closed(g_actual)

        # 11. 不确定性
        T = kwargs.get('t_iteration', self.apex.t_iteration)
        Λ = kwargs.get('lambda_root', self.apex.lambda_root)

        numerator = (Λ * theta * k_master * xi *
                     psi_enhanced * phi * sigma * omega_multi * omega_self)
        denominator = H * T * epsilon

        if denominator == 0:
            delta_g = 0.0
        else:
            delta_g = numerator / denominator

        # 加入不确定性因子
        rho_uncertainty = self.uncertainty.uncertainty_factor()
        delta_g_adjusted = delta_g / rho_uncertainty

        # 更新不确定性历史
        self.uncertainty.add_observation(delta_g)

        # τ 收敛加速后的 K
        k_master_new = self.master.calculate_k_master(safe=True)

        # 存储当前值
        self.delta_g = delta_g_adjusted

        # 演化速度
        velocity = self.evolution_velocity()

        # 置信区间
        ci = self.uncertainty.ci_95()

        return {
            "version": self.version,
            "delta_g": delta_g,
            "delta_g_adjusted": delta_g_adjusted,
            "rho_uncertainty": rho_uncertainty,
            "ci_95_lower": ci[0],
            "ci_95_upper": ci[1],
            "H_adaptive": H,
            "xi_dynamic": xi,
            "theta": theta,
            "k_master": k_master,
            "k_master_new": k_master_new,
            "epsilon_closed": epsilon,
            "phi_cycle": phi,
            "psi_host_base": psi_base,
            "psi_host_enhanced": psi_enhanced,
            "sigma_unified": sigma,
            "omega_multi": omega_multi,
            "omega_self": omega_self,
            "evolution_velocity": velocity,
            "H_history_size": len(self.adaptive_h.history),
            "uncertainty_samples": len(self.uncertainty.delta_g_history),
        }

    def summary(self) -> Dict[str, Any]:
        """返回当前状态摘要"""
        result = self.calculate()
        return {k: v for k, v in result.items() if k != "evolution_velocity"}


def calculate_delta_g_v2(**kwargs) -> Dict[str, Any]:
    """便捷函数"""
    calc = ApexCalculatorV2()
    return calc.calculate(**kwargs)
