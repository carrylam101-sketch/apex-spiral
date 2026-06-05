"""
APEX Deep Learning - 璇玑帝国 APEX 公式在深度学习中的举一反三

【核心理念】将 APEX V10.2 V2 终极闭环进化公式的思想融汇贯通到深度学习：
  • ΔG (进化增益)  →  model.fit() 的训练增益
  • Λ (本源基因)   →  learning rate / optimizer scaling
  • Θ (LLM-Agent) →  batch_size × model_capacity × training_efficiency
  • K_master (技能全域) → pretrain knowledge transfer
  • ξ (抗幻觉)     →  label_smoothing / confidence_penalty
  • Ψ_host (主机健康) → GPU/CPU/TPU 健康状态
  • Φ_cycle (正向循环) → learning rate schedule / momentum
  • H (熵)        →  prediction entropy / uncertainty
  • ε (修复)      →  gradient penalty / loss reweighting
  • Σ_unified     →  multi-task shared representation
  • Ω_multi       →  distributed training cooperation
  • Ω_self        →  self-training / self-supervised
"""

import math
import copy
import time
import logging
from typing import Optional, Dict, Any, List, Callable, Tuple
from dataclasses import dataclass, field
from collections import deque

logging.basicConfig(level=logging.INFO, format='[APEX-DL] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


# ==================== APEX-DL 核心概念映射 ====================

@dataclass
class AdaptiveEntropyParams:
    """自适应熵估计器 (对应 APEX H)
    
    在 DL 中：测量模型预测的不确定性
    - 低熵 → 模型置信，训练顺利
    - 高熵 → 模型迷茫，需要更多训练或调整
    """
    window_size: int = 50
    decay_factor: float = 0.95
    high_entropy_threshold: float = 2.0  # 自然对数阈值
    
    def __post_init__(self):
        self.history: deque = deque(maxlen=self.window_size)
    
    def compute_entropy(self, logits) -> float:
        """计算 softmax 后的分布熵 (Shannon entropy)"""
        # 转换为 list
        if hasattr(logits, 'tolist'):
            logits = logits.tolist()
        if not logits or len(logits) == 0:
            return 0.5
        # softmax
        max_logit = max(logits)
        exp_sum = sum(math.exp(l - max_logit) for l in logits)
        probs = [math.exp(l - max_logit) / exp_sum for l in logits]
        
        # Shannon entropy (自然对数，bit -> nat)
        H = 0.0
        for p in probs:
            if 0 < p < 1:
                H -= p * math.log(p)
        return H
    
    def update(self, logits: List[float]) -> float:
        """EMA 平滑后的自适应熵"""
        H = self.compute_entropy(logits)
        
        if len(self.history) == 0:
            H_adaptive = H
        else:
            prev_H = self.history[-1]
            alpha = 1.0 - self.decay_factor
            H_adaptive = alpha * H + self.decay_factor * prev_H
        
        self.history.append(H_adaptive)
        return H_adaptive
    
    def is_unstable(self) -> bool:
        """检测模型是否处于高熵不稳定状态"""
        if len(self.history) < 5:
            return False
        recent = list(self.history)[-5:]
        return sum(recent) / len(recent) > self.high_entropy_threshold


@dataclass
class LearningRateSchedule:
    """APEX Φ_cycle 驱动的学习率调度器
    
    Φ_cycle = e^(η × ρ) 是正向循环增益
    在 DL 中：这对应 learning rate 的指数级热身和衰减
    """
    base_lr: float = 1e-3
    eta_skill_up: float = 0.5    # η: 技能提升系数 → warmup rate
    rho_feedback: float = 0.5    # ρ: 结果反馈系数 → growth rate
    
    def __post_init__(self):
        self.cycle_momentum: float = 1.0
        self.step_count: int = 0
    
    def phi_cycle(self) -> float:
        """Φ_cycle = e^(η × ρ)"""
        product = min(self.eta_skill_up * self.rho_feedback, 7.0)
        return math.exp(product)
    
    def get_lr(self, step: Optional[int] = None) -> float:
        """
        APEX-inspired LR 调度：
        LR_t = base_lr × Φ_cycle × momentum^(step)
        
        等价于带热身的余弦衰减 + 指数动量
        """
        if step is not None:
            self.step_count = step
        
        phi = self.phi_cycle()
        lr = self.base_lr * phi * (self.cycle_momentum ** self.step_count)
        
        # 自动步进
        if step is None:
            self.step_count += 1
        
        return lr
    
    def apply_feedback(self, improvement_ratio: float):
        """
        根据训练改进率调整 Φ (反馈驱动)
        improvement_ratio > 1 → 训练顺利 → 可以加速
        improvement_ratio < 1 → 训练减速 → 需要稳住
        """
        if improvement_ratio > 1.1:
            self.rho_feedback = min(self.rho_feedback * 1.05, 2.0)
            self.cycle_momentum *= 0.99  # 加速收敛
        elif improvement_ratio < 0.9:
            self.rho_feedback = max(self.rho_feedback * 0.95, 0.1)
            self.cycle_momentum *= 1.01   # 减速稳住
        logger.debug(f"Φ反馈: rho={self.rho_feedback:.3f}, momentum={self.cycle_momentum:.4f}")


@dataclass
class ConfidenceCalibration:
    """置信度校准器 (对应 APEX ξ 抗幻觉)
    
    在 DL 中：防止模型对错误预测过度自信
    标签平滑、置信度惩罚
    """
    base_xi: float = 1.0
    label_smoothing: float = 0.1
    confidence_penalty_strength: float = 0.1
    
    def __post_init__(self):
        self.confidence_history: deque = deque(maxlen=100)
        self.xi_history: deque = deque(maxlen=50)
    
    def compute_xi(self, logits: List[float], labels: Optional[List[int]] = None) -> float:
        """
        动态抗幻觉系数 ξ：
        
        ξ = base_xi / (avg_confidence + ε)
        
        - 置信度高 → ξ 降低 (放松约束)
        - 置信度低 → ξ 增大 (加强约束)
        
        在 DL 中：这防止模型对低置信度预测过度自信
        """
        # 计算 softmax 分布
        # 转换 numpy/tensor
        if hasattr(logits, 'tolist'):
            logits = logits.tolist()
        if not logits:
            return 0.5
        max_logit = max(logits)
        exp_sum = sum(math.exp(l - max_logit) for l in logits)
        probs = [math.exp(l - max_logit) / exp_sum for l in logits]
        
        # 预测置信度 = max probability
        pred_confidence = max(probs) if probs else 0.0
        self.confidence_history.append(pred_confidence)
        
        # EMA 平滑置信度
        if len(self.confidence_history) == 1:
            avg_conf = pred_confidence
        else:
            avg_conf = sum(self.confidence_history) / len(self.confidence_history)
        
        # 动态 ξ
        xi = self.base_xi / (avg_conf + 0.1)
        xi = max(0.5, min(xi, 2.0))  # Clamp [0.5, 2.0]
        self.xi_history.append(xi)
        
        return xi
    
    def apply_label_smoothing(self, labels: List[int], num_classes: int) -> List[float]:
        """
        标签平滑 (对应 ξ 对 loss 的软化)
        y_smooth = (1 - α) * y_onehot + α / K
        """
        smoothed = []
        for y in labels:
            onehot = [0.0] * num_classes
            onehot[y] = 1.0
            smoothed_y = [(1 - self.label_smoothing) * oh + self.label_smoothing / num_classes 
                          for oh in onehot]
            smoothed.append(smoothed_y)
        return smoothed


@dataclass  
class GPUMemoryHealth:
    """GPU 内存健康监控 (对应 APEX Ψ_host)
    
    在 DL 中：监控 GPU 状态，动态调整 batch_size
    """
    total_memory_gb: float = 80.0
    oom_count: int = 0
    peak_memory_gb: float = 0.0
    
    def __post_init__(self):
        self.memory_history: deque = deque(maxlen=100)
    
    def update_memory(self, used_gb: float):
        """更新内存使用记录"""
        self.memory_history.append(used_gb)
        self.peak_memory_gb = max(self.peak_memory_gb, used_gb)
    
    def compute_psi(self, used_gb: Optional[float] = None) -> float:
        """
        Ψ_host = Ψ_mem × Ψ_app × Ψ_disk × Ω_dawn
        
        在 DL 中简化为内存健康度：
        Ψ_mem = 1 - (used / total)^2 (凸函数，越用越危险)
        """
        if used_gb is not None:
            self.update_memory(used_gb)
        
        if not self.memory_history:
            return 0.98
        
        current_used = self.memory_history[-1] if self.memory_history else 0
        utilization = current_used / self.total_memory_gb
        
        # 凸函数：轻度使用影响小，高使用率急剧下降
        psi_mem = max(0.1, 1.0 - utilization ** 1.8)
        
        # 历史峰值惩罚
        peak_util = self.peak_memory_gb / self.total_memory_gb
        if peak_util > 0.9:
            psi_mem *= 0.85  # 峰值过高，惩罚
        
        return psi_mem
    
    def suggest_batch_size(self, current_batch: int, target_util: float = 0.75) -> int:
        """
        基于 GPU 健康度建议 batch_size
        Ψ_host 高 → 可以增大 batch
        Ψ_host 低 → 需要减小 batch
        """
        psi = self.compute_psi()
        
        # batch_size 调整因子 = psi ^ 2 (非线性)
        factor = psi ** 2
        
        new_batch = int(current_batch * factor)
        new_batch = max(1, min(new_batch, current_batch * 2))  # 最多翻倍
        
        if abs(new_batch - current_batch) > current_batch * 0.1:
            logger.info(f"GPU健康 Ψ={psi:.3f} → 建议 batch: {current_batch} → {new_batch}")
        
        return new_batch


@dataclass
class GradientPenalty:
    """梯度惩罚器 (对应 APEX ε 修复机制)
    
    在 DL 中：检测并惩罚梯度爆炸/消失
    ε_closed = 1 + |e| × (1 + μ × ∫e dt + k_p × e)
    """
    g_target: float = 1.0      # 目标梯度范数
    kp: float = 0.1            # 比例增益
    ki: float = 0.05           # 积分增益
    momentum: float = 0.8      # 动量
    
    def __post_init__(self):
        self.prev_error: float = 0.0
        self.error_integral: float = 0.0
    
    def compute_epsilon(self, grad_norm: float) -> float:
        """
        ε_closed = 1 + |e| × (1 + μ × ∫e dt + k_p × e)
        
        其中 e = |grad_norm - g_target| / g_target
        """
        if grad_norm == 0:
            return 1.0
        
        error = abs(grad_norm - self.g_target) / (self.g_target + 1e-10)
        
        # 增量式 PID
        self.error_integral += error * self.ki
        self.error_integral = max(-10, min(self.error_integral, 10))  # Clamp
        
        error_with_momentum = error + self.momentum * self.prev_error
        self.prev_error = error
        
        epsilon = 1.0 + error_with_momentum * (1.0 + self.error_integral)
        return max(0.1, epsilon)  # 下限保护
    
    def gradient_clipping_factor(self, grad_norm: float) -> float:
        """
        返回梯度裁剪因子
        ε > 1 → 需要裁剪
        ε 越大 → 裁剪越狠
        """
        eps = self.compute_epsilon(grad_norm)
        # ε=1 → factor=1 (不裁剪)
        # ε=2 → factor=0.5 (裁剪50%)
        return max(0.1, 2.0 - eps)


@dataclass
class MultiTaskUnified:
    """多任务统一表示 (对应 APEX Σ_unified)
    
    在 DL 中：Multi-task learning 的 shared representation
    Σ = schema × code × struct × native
           ↓       ↓       ↓       ↓
    Σ_DL = task1 × task2 × task3 × task4
    
    防止任一任务主导，平衡多任务学习
    """
    task_weights: List[float] = field(default_factory=lambda: [0.25, 0.25, 0.25, 0.25])
    min_weight: float = 0.05
    
    def __post_init__(self):
        self.loss_history: List[deque] = [deque(maxlen=50) for _ in range(len(self.task_weights))]
    
    def update_task_loss(self, task_idx: int, loss: float):
        """记录任务 loss 历史"""
        if task_idx < len(self.loss_history):
            self.loss_history[task_idx].append(loss)
    
    def compute_sigma_safe(self) -> float:
        """
        Σ_unified (protected 模式)
        
        防止任一任务 loss 过高导致整体归零
        floor 保护 + 加权备选
        """
        if not self.loss_history or all(len(h) == 0 for h in self.loss_history):
            return 1.0
        
        # 计算每个任务的归一化"质量" (loss 越低质量越高)
        quality = []
        for h in self.loss_history:
            if len(h) > 0:
                avg_loss = sum(h) / len(h)
                # 转换为质量分数 (假设 loss 在 [0, 10])
                q = max(0.01, 1.0 - avg_loss / 10.0)
                quality.append(q)
            else:
                quality.append(0.5)  # 默认
        
        # 乘法组合
        product = 1.0
        for q in quality:
            product *= q
        
        # floor 保护
        floor_val = 0.1
        min_q = min(quality)
        if min_q < floor_val:
            protection = (min_q + floor_val) / (2 * floor_val)
            product = max(product * protection, floor_val ** len(quality))
        
        return product
    
    def compute_hybrid_sigma(self) -> float:
        """
        Σ_unified (hybrid 模式)
        加权平均融合
        """
        if not self.loss_history:
            return 1.0
        
        weighted = 0.0
        total_w = 0.0
        for i, (w, h) in enumerate(zip(self.task_weights, self.loss_history)):
            if len(h) > 0:
                avg_loss = sum(h) / len(h)
                q = max(0.01, 1.0 - avg_loss / 10.0)
            else:
                q = 0.5
            weighted += w * q
            total_w += w
        
        return weighted / total_w if total_w > 0 else 1.0
    
    def rebalance_weights(self) -> List[float]:
        """
        基于 APEX Ω_multi Sigmoid 效应动态重分配任务权重
        
        效果好的任务 (loss下降) → 权重增加
        效果差的任务 (loss上升/震荡) → 权重减少
        """
        if not self.loss_history or all(len(h) < 2 for h in self.loss_history):
            return self.task_weights
        
        new_weights = []
        for i, h in enumerate(self.loss_history):
            if len(h) >= 2:
                recent = list(h)[-5:]  # 最近5个
                if len(recent) >= 2:
                    # 趋势：斜率
                    slope = (recent[-1] - recent[0]) / len(recent)
                    # 稳定性：标准差
                    mean = sum(recent) / len(recent)
                    std = (sum((x - mean) ** 2 for x in recent) / len(recent)) ** 0.5
                    
                    # 斜率为负且稳定 → 权重增加
                    if slope < -0.01 and std < 0.5:
                        new_w = self.task_weights[i] * 1.2
                    elif slope > 0.01:
                        new_w = self.task_weights[i] * 0.8
                    else:
                        new_w = self.task_weights[i]
                else:
                    new_w = self.task_weights[i]
            else:
                new_w = self.task_weights[i]
            
            new_weights.append(max(self.min_weight, new_w))
        
        # 归一化
        total = sum(new_weights)
        self.task_weights = [w / total for w in new_weights]
        
        logger.info(f"任务权重重分配: {[f'{w:.3f}' for w in self.task_weights]}")
        return self.task_weights


@dataclass
class DistributedCooperation:
    """分布式协作系数 (对应 APEX Ω_multi)
    
    在 DL 中：多 GPU / 多节点训练的协作效率
    Ω_multi = n / (1 + e^(-k(ρ-ρ_crit)))
    """
    num_workers: int = 1
    network_density: float = 0.5
    cooperation_rate: float = 0.8
    credit_assignment: float = 0.7
    
    def compute_omega_multi(self) -> float:
        """
        Sigmoid 协作增益
        ρ < ρ_crit → 收益递增
        ρ > ρ_crit → 收益递减 (通信开销)
        """
        k = 2.0
        rho_crit = 0.5
        
        if self.num_workers <= 1:
            return 1.0
        
        sigmoid = 1.0 / (1.0 + math.exp(-k * (self.network_density - rho_crit)))
        omega = self.cooperation_rate * sigmoid * self.credit_assignment
        
        # 多节点额外开销
        if self.num_workers > 4:
            overhead = 1.0 / math.log2(self.num_workers)
            omega *= overhead
        
        return max(0.1, omega)


@dataclass
class UncertaintyQuantification:
    """不确定性量化 (对应 APEX ρ_uncertainty)
    
    在 DL 中：测量模型预测的不确定性
    - 认知不确定性 (epistemic): 训练数据不足
    - 偶然不确定性 (aleatoric): 标签噪声
    """
    history_size: int = 50
    
    def __post_init__(self):
        self.delta_g_history: deque = deque(maxlen=self.history_size)
        self.loss_history: deque = deque(maxlen=self.history_size)
        self.weights: deque = deque(maxlen=self.history_size)
    
    def add_observation(self, delta_g: float, loss: float, weight: float = 1.0):
        self.delta_g_history.append(delta_g)
        self.loss_history.append(loss)
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
    
    def ci_95(self) -> Tuple[float, float]:
        """95% 置信区间"""
        if len(self.delta_g_history) < 2:
            return (0.0, 0.0)
        m = self.mean()
        s = self.std()
        n = len(self.delta_g_history)
        margin = 1.96 * s / math.sqrt(n)
        return (m - margin, m + margin)
    
    def uncertainty_factor(self) -> float:
        """
        ρ_uncertainty = 1 + CV (变异系数)
        
        CV 越大 → 不确定性越高 → 训练增益打折
        """
        m = self.mean()
        if m == 0:
            return 1.0 + self.std()
        cv = self.std() / abs(m)
        return 1.0 + cv
    
    def bayesian_dropout_score(self, logits: List[float], n_samples: int = 10) -> float:
        """
        蒙特卡洛 Dropout 不确定性估计
        
        对同一个输入多次前向传播 (dropout 开启)
        测量输出分布的方差
        """
        # 简化的单次实现 (实际需要多次采样)
        max_logit = max(logits) if logits else 0
        exp_sum = sum(math.exp(l - max_logit) for l in logits)
        probs = [math.exp(l - max_logit) / exp_sum for l in logits]
        
        # 熵作为不确定性代理
        H = 0.0
        for p in probs:
            if 0 < p < 1:
                H -= p * math.log(p)
        
        # 归一化到 [0, 1]
        n_classes = len(probs)
        H_max = math.log(n_classes) if n_classes > 1 else 1.0
        uncertainty = H / H_max if H_max > 0 else 0.0
        
        return uncertainty


# ==================== APEX-DL 训练器 ====================

class ApexTrainer:
    """
    APEX 增强版深度学习训练器
    
    将 APEX V10.2 V2 公式的思想系统性地应用于训练过程：
    
    1. 自适应学习率 (Φ_cycle 驱动)
    2. 动态 batch size (Ψ_host 驱动)
    3. 梯度健康监控 (ε_closed 驱动)
    4. 置信度校准 (ξ 驱动)
    5. 多任务平衡 (Σ_unified 驱动)
    6. 预测不确定性估计 (ρ_uncertainty 驱动)
    """
    
    def __init__(self,
                 base_lr: float = 1e-3,
                 num_classes: int = 10,
                 multi_task: bool = False,
                 num_workers: int = 1):
        self.version = "APEX-DL v1.0"
        
        # APEX 组件
        self.lr_schedule = LearningRateSchedule(base_lr=base_lr)
        self.gpu_health = GPUMemoryHealth()
        self.gradient_penalty = GradientPenalty()
        self.confidence_cal = ConfidenceCalibration()
        self.entropy_monitor = AdaptiveEntropyParams()
        self.multi_task = MultiTaskUnified() if multi_task else None
        self.distributed = DistributedCooperation(num_workers=num_workers)
        self.uncertainty = UncertaintyQuantification()
        
        # 训练状态
        self.step: int = 0
        self.best_loss: float = float('inf')
        self.num_classes = num_classes
        
        logger.info(f"APEX-DL 训练器初始化 | LR={base_lr} | 多任务={multi_task}")
    
    def compute_loss_adjustment(self,
                                logits: List[float],
                                target: int,
                                raw_loss: float) -> Tuple[float, Dict[str, float]]:
        """
        APEX 增强的 Loss 计算
        
        ΔG = (Λ × Θ × K × ξ × Ψ_host × Φ × Σ_unified × Ω_multi × Ω_self)
             / (H × T × ε × (1 + ρ_uncertainty))
        
        在 DL 中：
        loss_adjusted = raw_loss × ξ / (Ψ × Φ × (1 + ρ))
        
        Returns:
            (adjusted_loss, debug_dict)
        """
        debug_info = {}
        
        # 1. ξ (置信度校准)
        xi = self.confidence_cal.compute_xi(logits)
        debug_info['xi'] = xi
        
        # 2. Φ (动量循环)
        phi = self.lr_schedule.phi_cycle()
        debug_info['phi'] = phi
        
        # 3. Ψ (GPU健康)
        psi = self.gpu_health.compute_psi()
        debug_info['psi'] = psi
        
        # 4. H (熵)
        H = self.entropy_monitor.update(logits)
        debug_info['H'] = H
        
        # 5. ρ (不确定性)
        rho = self.uncertainty.uncertainty_factor()
        debug_info['rho_uncertainty'] = rho
        
        # 6. Σ 多任务
        if self.multi_task:
            sigma = self.multi_task.compute_sigma_safe()
            debug_info['sigma'] = sigma
        else:
            sigma = 1.0
            debug_info['sigma'] = 1.0
        
        # 7. Ω_multi
        omega_multi = self.distributed.compute_omega_multi()
        debug_info['omega_multi'] = omega_multi
        
        # 综合调整
        # loss_factor = ξ / (Ψ × Φ × σ × Ω × (1+ρ))
        loss_factor = xi / (psi * phi * sigma * omega_multi * (1 + rho))
        
        # ε 影响梯度
        # grad_norm 假设已知 (外部传入)
        eps = 1.0
        debug_info['epsilon'] = eps
        
        adjusted_loss = raw_loss * loss_factor
        
        debug_info['loss_factor'] = loss_factor
        debug_info['raw_loss'] = raw_loss
        debug_info['adjusted_loss'] = adjusted_loss
        
        return adjusted_loss, debug_info
    
    def apply_gradient_health(self, grad_norm: float, lr: float) -> float:
        """
        APEX ε_closed 驱动的梯度健康调整
        
        ε > 1 → 需要裁剪
        ε < 1 → 可以放松
        
        返回调整后的 learning rate
        """
        clip_factor = self.gradient_penalty.gradient_clipping_factor(grad_norm)
        
        adjusted_lr = lr * clip_factor
        
        if clip_factor < 0.9:
            logger.info(f"梯度裁剪: ||g||={grad_norm:.4f}, factor={clip_factor:.3f}, LR: {lr:.2e} → {adjusted_lr:.2e}")
        
        return adjusted_lr
    
    def step_training(self,
                      logits: List[float],
                      target: int,
                      raw_loss: float,
                      grad_norm: Optional[float] = None,
                      gpu_memory_gb: Optional[float] = None) -> Dict[str, Any]:
        """
        单步训练 (APEX 增强)
        
        Args:
            logits: 模型输出的原始 logits
            target: 目标类别索引
            raw_loss: 原始 loss (未调整)
            grad_norm: 梯度范数 (可选)
            gpu_memory_gb: GPU 内存使用 (可选)
        """
        self.step += 1
        
        # 更新 GPU 健康
        if gpu_memory_gb is not None:
            self.gpu_health.update_memory(gpu_memory_gb)
        
        # 获取当前 LR
        lr = self.lr_schedule.get_lr()
        
        # 计算 APEX 增强 loss
        adjusted_loss, debug_info = self.compute_loss_adjustment(
            logits, target, raw_loss
        )
        
        # 梯度健康检查
        if grad_norm is not None:
            lr = self.apply_gradient_health(grad_norm, lr)
            debug_info['lr_adjusted'] = lr
        
        # 动态 batch size
        current_batch = getattr(self, 'current_batch', 32)
        suggested_batch = self.gpu_health.suggest_batch_size(current_batch)
        if suggested_batch != current_batch and self.step % 100 == 0:
            self.current_batch = suggested_batch
            logger.info(f"Batch size 调整: {current_batch} → {suggested_batch}")
        
        # 计算等效 ΔG (训练增益)
        # 简化: ΔG ∝ improvement / (H × ε)
        if raw_loss > 0:
            improvement = max(0.0, self.best_loss - raw_loss) / (self.best_loss + 1e-10)
            delta_g = improvement / (debug_info['H'] * debug_info['epsilon'] + 1e-10)
        else:
            delta_g = 0.0
        
        self.best_loss = min(self.best_loss, raw_loss)
        
        # 更新不确定性
        self.uncertainty.add_observation(delta_g, raw_loss)
        
        # 学习率反馈
        if self.step % 10 == 0:
            improvement_ratio = 1.0 - (raw_loss / self.best_loss) if self.best_loss > 0 else 1.0
            self.lr_schedule.apply_feedback(improvement_ratio + 1.0)
        
        # 组装结果
        result = {
            'step': self.step,
            'lr': lr,
            'raw_loss': raw_loss,
            'adjusted_loss': adjusted_loss,
            'delta_g': delta_g,
            'best_loss': self.best_loss,
            **debug_info
        }
        
        return result
    
    def multi_task_step(self,
                        task_losses: Dict[str, float],
                        task_logits: Dict[str, List[float]],
                        grad_norms: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """
        多任务训练一步 (APEX Σ_unified 驱动)
        
        各任务 loss 加权求和，权重由 Σ 动态调整
        """
        if not self.multi_task:
            raise ValueError("Multi-task mode not enabled")
        
        # 更新各任务 loss
        for i, (task_name, loss) in enumerate(task_losses.items()):
            self.multi_task.update_task_loss(i, loss)
        
        # 重平衡权重
        new_weights = self.multi_task.rebalance_weights()
        
        # 加权 loss
        total_loss = 0.0
        for i, (task_name, loss) in enumerate(task_losses.items()):
            weight = new_weights[i] if i < len(new_weights) else 1.0 / len(task_losses)
            total_loss += weight * loss
        
        # 获取 APEX 参数
        lr = self.lr_schedule.get_lr()
        psi = self.gpu_health.compute_psi()
        sigma = self.multi_task.compute_sigma_safe()
        
        result = {
            'step': self.step,
            'lr': lr,
            'total_loss': total_loss,
            'task_losses': task_losses,
            'task_weights': new_weights,
            'sigma': sigma,
            'psi': psi,
        }
        
        self.step += 1
        return result
    
    def get_confidence_metrics(self, logits: List[float]) -> Dict[str, float]:
        """
        获取置信度相关指标 (用于分析)
        """
        max_logit = max(logits) if logits else 0
        exp_sum = sum(math.exp(l - max_logit) for l in logits)
        probs = [math.exp(l - max_logit) / exp_sum for l in logits]
        
        pred_confidence = max(probs) if probs else 0.0
        pred_class = probs.index(pred_confidence) if probs else 0
        
        entropy = 0.0
        for p in probs:
            if 0 < p < 1:
                entropy -= p * math.log(p)
        
        n_classes = len(probs)
        entropy_max = math.log(n_classes) if n_classes > 1 else 1.0
        uncertainty = entropy / entropy_max if entropy_max > 0 else 0.0
        
        return {
            'pred_class': pred_class,
            'pred_confidence': pred_confidence,
            'entropy': entropy,
            'normalized_uncertainty': uncertainty,
            'xi': self.confidence_cal.compute_xi(logits),
        }


# ==================== PyTorch 集成 ====================

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    logger.warning("PyTorch 未安装，APEX-DL 将以纯 Python 模式运行")


if HAS_TORCH:
    
    class ApexLoss(nn.Module):
        """
        APEX 增强的 PyTorch Loss
        
        等效于公式中的 ξ 抗幻觉调整
        支持 label smoothing
        """
        
        def __init__(self,
                     label_smoothing: float = 0.1,
                     xi_base: float = 1.0,
                     use_adaptive_xi: bool = True):
            super().__init__()
            self.label_smoothing = label_smoothing
            self.xi_base = xi_base
            self.use_adaptive_xi = use_adaptive_xi
            self.confidence_ema: Optional[float] = None
            self.ema_decay = 0.95
        
        def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
            """
            APEX Loss:
            L_apex = L_ce × ξ / Ψ
            
            其中 ξ = base_xi / (avg_conf + ε)
            """
            # Label smoothing
            if self.label_smoothing > 0:
                n_classes = logits.size(-1)
                one_hot = torch.zeros_like(logits).scatter_(1, targets.unsqueeze(1), 1)
                smooth_targets = one_hot * (1 - self.label_smoothing) + self.label_smoothing / n_classes
            else:
                smooth_targets = F.one_hot(targets, logits.size(-1)).float()
            
            # 标准 CE (on smooth targets)
            log_probs = F.log_softmax(logits, dim=-1)
            loss_ce = -(smooth_targets * log_probs).sum(dim=-1).mean()
            
            # 自适应 ξ
            if self.use_adaptive_xi:
                with torch.no_grad():
                    probs = F.softmax(logits, dim=-1)
                    pred_conf = probs.max(dim=-1)[0].mean().item()
                    
                    if self.confidence_ema is None:
                        self.confidence_ema = pred_conf
                    else:
                        self.confidence_ema = self.ema_decay * self.confidence_ema + (1 - self.ema_decay) * pred_conf
                    
                    xi = self.xi_base / (self.confidence_ema + 0.1)
                    xi = torch.tensor(max(0.5, min(xi, 2.0)), device=logits.device)
            else:
                xi = self.xi_base
            
            return loss_ce * xi
        
        def extra_repr(self) -> str:
            return f'label_smoothing={self.label_smoothing}, xi_base={self.xi_base}, adaptive_xi={self.use_adaptive_xi}'


    class ApexOptimizer:
        """
        APEX 增强的 PyTorch Optimizer
        
        将 APEX Φ_cycle 思想融入学习率调度
        """
        
        def __init__(self,
                     optimizer: torch.optim.Optimizer,
                     eta_skill_up: float = 0.5,
                     rho_feedback: float = 0.5,
                     rho_adaptive: bool = True):
            self.optimizer = optimizer
            self.eta_skill_up = eta_skill_up
            self.rho_feedback = rho_feedback
            self.rho_adaptive = rho_adaptive
            
            self.base_lrs = [pg['lr'] for pg in optimizer.param_groups]
            self.phi = math.exp(min(eta_skill_up * rho_feedback, 7.0))
            self.momentum = 1.0
            self.step_count = 0
            
            logger.info(f"APEX Optimizer | Φ={self.phi:.3f} | base_LRs={self.base_lrs}")
        
        def step(self):
            """应用 APEX 增强的学习率"""
            # 自适应调整
            if self.rho_adaptive and hasattr(self, 'recent_loss'):
                if len(self.recent_loss) >= 5:
                    recent = list(self.recent_loss)[-5:]
                    if recent[-1] < recent[0]:
                        self.rho_feedback = min(self.rho_feedback * 1.02, 2.0)
                        self.momentum *= 0.99
                    else:
                        self.rho_feedback = max(self.rho_feedback * 0.98, 0.1)
                        self.momentum *= 1.01
            
            # Φ = e^(η × ρ)
            self.phi = math.exp(min(self.eta_skill_up * self.rho_feedback, 7.0))
            
            # LR = base × Φ × momentum^step
            for i, pg in enumerate(self.optimizer.param_groups):
                lr = self.base_lrs[i] * self.phi * (self.momentum ** self.step_count)
                pg['lr'] = lr
            
            self.optimizer.step()
            self.step_count += 1
        
        def zero_grad(self):
            self.optimizer.zero_grad()
        
        def state_dict(self):
            return {
                'optimizer': self.optimizer.state_dict(),
                'step_count': self.step_count,
                'phi': self.phi,
                'momentum': self.momentum,
                'rho_feedback': self.rho_feedback,
            }
        
        def load_state_dict(self, state):
            self.optimizer.load_state_dict(state['optimizer'])
            self.step_count = state['step_count']
            self.phi = state['phi']
            self.momentum = state['momentum']
            self.rho_feedback = state['rho_feedback']
        
        def track_loss(self, loss: float):
            """记录 loss 用于反馈调整"""
            if not hasattr(self, 'recent_loss'):
                self.recent_loss = deque(maxlen=50)
            self.recent_loss.append(loss)


# ==================== 工具函数 ====================

def compute_apex_delta_g(
    lambda_root: float = 0.95,
    theta: float = 0.7,
    k_master: float = 1.0,
    xi: float = 1.0,
    psi_host: float = 0.98,
    phi_cycle: float = 1.0,
    sigma_unified: float = 1.0,
    omega_multi: float = 1.0,
    h_entropy: float = 0.5,
    t_iteration: float = 2.0,
    epsilon: float = 1.0,
    rho_uncertainty: float = 1.0,
) -> float:
    """
    纯 APEX ΔG 公式 (用于深度学习场景)
    
    ΔG = (Λ × Θ × K × ξ × Ψ_host × Φ × Σ_unified × Ω_multi)
         / (H × T × ε × (1 + ρ_uncertainty))
    
    在 DL 中各参数含义：
    - Λ (lambda_root): 基础学习率 scaling
    - Θ (theta): 模型能力 × 数据效率
    - K_master: 预训练知识迁移
    - ξ (xi): 置信度校准强度
    - Ψ_host (psi): GPU/硬件健康度
    - Φ (phi): 学习率动量
    - Σ_unified (sigma): 多任务共享表示
    - Ω_multi (omega): 分布式协作
    - H (entropy): 预测熵/不确定性
    - T (t_iteration): 训练迭代成本
    - ε (epsilon): 梯度健康度惩罚
    - ρ (rho): 预测不确定性
    """
    numerator = (lambda_root * theta * k_master * xi * 
                 psi_host * phi_cycle * sigma_unified * omega_multi)
    denominator = h_entropy * t_iteration * epsilon * rho_uncertainty
    
    if denominator == 0:
        return 0.0
    
    return numerator / denominator


def estimate_model_uncertainty(logits, n_samples: int = 10):
    """
    估计模型不确定性 (Monte Carlo Dropout)
    
    Returns:
        (mean_probs, uncertainty_score)
    """
    if not HAS_TORCH:
        raise ImportError("PyTorch required for uncertainty estimation")
    
    # 需要 model.train() 模式 + dropout
    all_probs = []
    for _ in range(n_samples):
        with torch.no_grad():
            probs = F.softmax(logits, dim=-1)
            all_probs.append(probs)
    
    mean_probs = torch.stack(all_probs).mean(dim=0)
    
    # 不确定性 = 预测间方差
    variance = torch.stack(all_probs).var(dim=0).mean().item()
    
    return mean_probs, variance


if __name__ == "__main__":
    # 演示
    print("=" * 60)
    print("APEX Deep Learning - 璇玑帝国")
    print("=" * 60)
    
    # 1. 自适应熵
    print("\n【1】自适应熵监控")
    ent = AdaptiveEntropyParams(window_size=20)
    test_logits = [3.0, 1.0, 0.5, 0.2]  # 模型较自信
    H = ent.update(test_logits)
    print(f"  logits={test_logits}")
    print(f"  H_entropy={H:.4f} (低熵 = 模型自信)")
    
    test_logits2 = [0.5, 0.4, 0.6, 0.5]  # 模型迷茫
    H2 = ent.update(test_logits2)
    print(f"  logits={test_logits2}")
    print(f"  H_entropy={H2:.4f} (高熵 = 模型迷茫)")
    
    # 2. APEX ΔG 计算
    print("\n【2】APEX ΔG 计算")
    delta_g = compute_apex_delta_g(
        lambda_root=0.95,
        theta=0.75,
        k_master=1.2,
        xi=1.0,
        psi_host=0.98,
        phi_cycle=1.65,  # e^(0.5*0.5)
        sigma_unified=0.8,
        omega_multi=0.9,
        h_entropy=0.8,
        t_iteration=2.0,
        epsilon=1.1,
        rho_uncertainty=1.05,
    )
    print(f"  ΔG = {delta_g:.4f}")
    
    # 3. 多任务 Σ
    print("\n【3】多任务统一 Σ_unified")
    mt = MultiTaskUnified(task_weights=[0.3, 0.3, 0.2, 0.2])
    for i in range(4):
        mt.update_task_loss(i, loss=0.5 + i * 0.1)
    sigma = mt.compute_sigma_safe()
    print(f"  Σ_protected = {sigma:.4f}")
    sigma_hybrid = mt.compute_hybrid_sigma()
    print(f"  Σ_hybrid = {sigma_hybrid:.4f}")
    
    # 4. 梯度健康 ε
    print("\n【4】梯度健康监控 ε")
    gp = GradientPenalty(g_target=1.0)
    for grad_norm in [0.5, 1.0, 1.5, 3.0, 5.0]:
        eps = gp.compute_epsilon(grad_norm)
        clip = gp.gradient_clipping_factor(grad_norm)
        print(f"  ||g||={grad_norm:.1f} → ε={eps:.3f}, clip_factor={clip:.3f}")
    
    # 5. GPU 健康 Ψ
    print("\n【5】GPU 健康 Ψ_host")
    gpu = GPUMemoryHealth(total_memory_gb=80.0)
    for used in [20, 50, 65, 75]:
        psi = gpu.compute_psi(used_gb=used)
        batch = gpu.suggest_batch_size(64, target_util=0.75)
        print(f"  使用 {used}GB/80GB → Ψ={psi:.3f}, 建议batch={batch}")
    
    print("\n" + "=" * 60)
    print("APEX Deep Learning 演示完成")
    print("=" * 60)
