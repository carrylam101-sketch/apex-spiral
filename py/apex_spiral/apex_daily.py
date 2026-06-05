"""
APEX 日常应用脚本 - 将 APEX V10.2 V2 公式代入日常工作流

功能：
1. 训练监控 - 自适应学习率 + 梯度健康
2. 模型评估 - 置信度校准 + 不确定性量化
3. 超参调优 - Λ/Θ/K 参数空间搜索
4. 多任务训练 - Σ_unified 动态权重平衡
5. 资源调度 - Ψ_host GPU 内存自适应

用法:
    python apex_daily.py --mode train
    python apex_daily.py --mode eval
    python apex_daily.py --mode hp_search
    python apex_daily.py --mode multitask
"""

import sys
import math
import argparse
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import deque
import time

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset

# APEX 模块
from apex_spiral import (
    ApexTrainer, ApexLoss, ApexOptimizer,
    AdaptiveEntropyParams, ConfidenceCalibration, GPUMemoryHealth,
    GradientPenalty, UncertaintyQuantification, compute_apex_delta_g
)

logging.basicConfig(
    level=logging.INFO,
    format='[APEX-DAILY] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


# ==================== 演示模型 ====================

class SimpleNet(nn.Module):
    """演示用简单网络"""
    def __init__(self, input_dim=10, hidden_dim=32, num_classes=3):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.fc3 = nn.Linear(hidden_dim, num_classes)
        self.dropout = nn.Dropout(0.2)
    
    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = self.dropout(x)
        x = F.relu(self.fc2(x))
        x = self.dropout(x)
        return self.fc3(x)


# ==================== APEX 训练循环 ====================

def apex_train_loop(
    model: nn.Module,
    train_loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    apex_optimizer: Optional[ApexOptimizer],
    apex_loss_fn: ApexLoss,
    device: str = 'cpu',
    log_interval: int = 50
) -> Dict[str, Any]:
    """
    APEX 增强的训练循环
    
    集成:
    - ApexOptimizer: 自适应 LR (Φ_cycle 驱动)
    - ApexLoss: 置信度校准 (ξ 驱动)
    - 梯度健康监控 (ε_closed 驱动)
    """
    model.train()
    
    total_loss = 0.0
    total_raw_loss = 0.0
    correct = 0
    total = 0
    
    entropy_monitor = AdaptiveEntropyParams()
    grad_penalty = GradientPenalty()
    uncertainty = UncertaintyQuantification()
    
    steps = 0
    
    for batch_idx, (data, target) in enumerate(train_loader):
        data, target = data.to(device), target.to(device)
        
        optimizer.zero_grad()
        
        # 前向传播
        output = model(data)
        
        # APEX Loss (含置信度校准 ξ)
        loss = apex_loss_fn(output, target)
        raw_loss = F.cross_entropy(output, target).item()
        
        # 反向传播
        loss.backward()
        
        # 计算梯度范数
        grad_norm = 0.0
        for p in model.parameters():
            if p.grad is not None:
                grad_norm += p.grad.data.norm(2).item() ** 2
        grad_norm = grad_norm ** 0.5
        
        # APEX 梯度健康 (ε_closed)
        clip_factor = grad_penalty.gradient_clipping_factor(grad_norm)
        if clip_factor < 0.9:
            for p in model.parameters():
                if p.grad is not None:
                    p.grad.data.mul_(clip_factor)
        
        # APEX Optimizer step (自适应 LR)
        if apex_optimizer:
            apex_optimizer.track_loss(raw_loss)
            apex_optimizer.step()
        else:
            optimizer.step()
        
        # 预测 & 统计
        pred = output.argmax(dim=1)
        correct += pred.eq(target).sum().item()
        total += target.size(0)
        
        total_loss += loss.item()
        total_raw_loss += raw_loss
        steps += 1
        
        # 熵监控
        logits_list = output.detach().cpu().numpy().tolist()
        for logit in logits_list:
            entropy_monitor.update(logit)
        
        # 不确定性记录
        delta_g = max(0, 1.0 - raw_loss) / (entropy_monitor.history[-1] + 0.1) if entropy_monitor.history else 0
        uncertainty.add_observation(delta_g, raw_loss)
        
        if (batch_idx + 1) % log_interval == 0:
            acc = 100. * correct / total
            avg_loss = total_loss / steps
            avg_raw = total_raw_loss / steps
            H = entropy_monitor.history[-1] if entropy_monitor.history else 0
            rho = uncertainty.uncertainty_factor()
            
            lr = optimizer.param_groups[0]['lr']
            
            logger.info(
                f"Step {batch_idx+1}/{len(train_loader)} | "
                f"Loss: {avg_raw:.4f} (APEX: {avg_loss:.4f}) | "
                f"Acc: {acc:.1f}% | "
                f"H: {H:.3f} | "
                f"‖g‖: {grad_norm:.3f} | "
                f"ρ: {rho:.3f} | "
                f"LR: {lr:.2e}"
            )
    
    return {
        'avg_loss': total_raw_loss / steps,
        'avg_apex_loss': total_loss / steps,
        'accuracy': 100. * correct / total,
        'final_grad_norm': grad_norm,
        'final_entropy': entropy_monitor.history[-1] if entropy_monitor.history else 0,
        'uncertainty_factor': uncertainty.uncertainty_factor(),
        'delta_g': delta_g,
    }


def apex_eval_loop(
    model: nn.Module,
    eval_loader: DataLoader,
    apex_loss_fn: ApexLoss,
    device: str = 'cpu'
) -> Dict[str, Any]:
    """
    APEX 增强的评估循环
    
    输出:
    - 置信度校准指标
    - 预测不确定性 (MC Dropout)
    - 各 class 的 APEX ΔG
    """
    model.eval()
    
    total_loss = 0.0
    correct = 0
    total = 0
    
    confidence_cal = ConfidenceCalibration()
    entropy_monitor = AdaptiveEntropyParams()
    uncertainty = UncertaintyQuantification()
    
    all_probs = []
    all_targets = []
    
    with torch.no_grad():
        for data, target in eval_loader:
            data, target = data.to(device), target.to(device)
            
            output = model(data)
            
            loss = F.cross_entropy(output, target)
            total_loss += loss.item()
            
            pred = output.argmax(dim=1)
            correct += pred.eq(target).sum().item()
            total += target.size(0)
            
            # 置信度
            probs = F.softmax(output, dim=1)
            all_probs.append(probs.cpu())
            all_targets.append(target.cpu())
            
            # APEX ξ
            logits_list = output.cpu().numpy().tolist()
            for logit in logits_list:
                confidence_cal.compute_xi(logit)
                entropy_monitor.update(logit)
    
    all_probs = torch.cat(all_probs)
    all_targets = torch.cat(all_targets)
    
    # 置信度指标
    pred_conf = all_probs.max(dim=1)[0].mean().item()
    entropy = sum(list(entropy_monitor.history)) / len(entropy_monitor.history) if entropy_monitor.history else 0
    
    # 校准误差
    calib_error = abs(pred_conf - correct/total)
    
    # APEX ΔG per class
    delta_g_per_class = []
    for c in range(all_probs.size(1)):
        mask = all_targets == c
        if mask.sum() > 0:
            class_conf = all_probs[mask, c].mean().item()
            class_entropy = entropy  # simplified
            delta_g = (class_conf + 1e-10) / (class_entropy + 0.1)
            delta_g_per_class.append(delta_g)
        else:
            delta_g_per_class.append(0.0)
    
    return {
        'avg_loss': total_loss / len(eval_loader),
        'accuracy': 100. * correct / total,
        'pred_confidence': pred_conf,
        'calibration_error': calib_error,
        'entropy': entropy,
        'uncertainty_factor': uncertainty.uncertainty_factor(),
        'delta_g_per_class': delta_g_per_class,
    }


# ==================== 超参搜索 ====================

def apex_hp_search(
    base_params: Dict[str, Any],
    search_space: Dict[str, List[Any]],
    train_loader: DataLoader,
    eval_loader: DataLoader,
    device: str = 'cpu',
    max_trials: int = 10
) -> Dict[str, Any]:
    """
    APEX 增强的超参数搜索
    
    APEX 公式可指导搜索方向：
    - Λ (lambda): Learning rate - 核心参数
    - Θ (theta): Batch size × Model capacity
    - K_master: 知识迁移系数
    
    搜索策略: 
    1. 先粗搜索 Λ
    2. 再细搜索 Θ
    3. 最后验证 K
    """
    logger.info(f"开始 APEX 超参搜索 | {max_trials} 轮 | 搜索空间: {list(search_space.keys())}")
    
    results = []
    best_score = -float('inf')
    best_params = None
    
    for trial in range(max_trials):
        # 随机采样
        params = {}
        for k, v_list in search_space.items():
            idx = (trial + hash(str(k)) + trial * 17) % len(v_list)
            params[k] = v_list[idx]
        
        # 创建模型
        model = SimpleNet(
            input_dim=base_params.get('input_dim', 10),
            hidden_dim=params.get('hidden_dim', 32),
            num_classes=base_params.get('num_classes', 3)
        ).to(device)
        
        # 创建优化器
        optimizer = torch.optim.Adam(
            model.parameters(),
            lr=params.get('lr', 1e-3),
            weight_decay=params.get('weight_decay', 0)
        )
        
        # APEX Loss
        apex_loss = ApexLoss(
            label_smoothing=params.get('label_smoothing', 0.1),
            xi_base=1.0
        )
        
        # 快速训练 (3 epochs)
        for epoch in range(3):
            train_result = apex_train_loop(
                model, train_loader, optimizer, None, apex_loss, device, log_interval=100
            )
        
        # 评估
        eval_result = apex_eval_loop(model, eval_loader, apex_loss, device)
        
        # APEX ΔG 评分
        delta_g = compute_apex_delta_g(
            lambda_root=params.get('lr', 0.001) / 0.01,  # 归一化
            theta=params.get('batch_size', 32) / 64,      # 归一化
            k_master=1.0 + params.get('hidden_dim', 32) / 128,
            xi=1.0,
            psi_host=0.98,
            phi_cycle=1.0,
            sigma_unified=1.0,
            omega_multi=1.0,
            h_entropy=eval_result['entropy'] + 0.1,
            t_iteration=1.0,
            epsilon=1.0 + eval_result['calibration_error'],
            rho_uncertainty=eval_result['uncertainty_factor'],
        )
        
        score = eval_result['accuracy'] * delta_g / 100
        
        results.append({
            'trial': trial + 1,
            'params': params,
            'accuracy': eval_result['accuracy'],
            'delta_g': delta_g,
            'score': score,
            'entropy': eval_result['entropy'],
        })
        
        if score > best_score:
            best_score = score
            best_params = params.copy()
            logger.info(f"  Trial {trial+1}: Acc={eval_result['accuracy']:.1f}% ΔG={delta_g:.4f} Score={score:.4f} ⭐ BEST")
        else:
            logger.info(f"  Trial {trial+1}: Acc={eval_result['accuracy']:.1f}% ΔG={delta_g:.4f} Score={score:.4f}")
    
    return {
        'best_params': best_params,
        'best_score': best_score,
        'all_results': sorted(results, key=lambda x: x['score'], reverse=True)
    }


# ==================== 多任务训练 ====================

def apex_multitask_demo():
    """
    多任务训练演示
    
    任务: 3 个分类任务共享 backbone
    Σ_unified 动态平衡各任务权重
    """
    from apex_spiral.deep_learning import MultiTaskUnified
    
    logger.info("=" * 60)
    logger.info("APEX 多任务训练演示")
    logger.info("=" * 60)
    
    # 模拟 4 个任务
    mt = MultiTaskUnified(task_weights=[0.25, 0.25, 0.25, 0.25])
    
    # 模拟训练过程
    logger.info("\n【阶段1】训练初期 (任务 loss 都高)")
    for i in range(4):
        mt.update_task_loss(i, loss=2.5 - i * 0.3)
    
    sigma_safe = mt.compute_sigma_safe()
    sigma_hybrid = mt.compute_hybrid_sigma()
    logger.info(f"  Σ_safe={sigma_safe:.4f} | Σ_hybrid={sigma_hybrid:.4f}")
    
    logger.info("\n【阶段2】训练中期 (任务1,2 收敛快)")
    for i in range(4):
        mt.update_task_loss(i, loss=0.8 - i * 0.15 if i < 2 else 1.5 + i * 0.1)
    
    weights = mt.rebalance_weights()
    sigma_safe = mt.compute_sigma_safe()
    logger.info(f"  新权重: {[f'{w:.3f}' for w in weights]}")
    logger.info(f"  Σ_safe={sigma_safe:.4f}")
    
    logger.info("\n【阶段3】训练后期 (任务3 出现震荡)")
    for i in range(4):
        mt.update_task_loss(i, loss=0.3 + abs(i-1) * 0.1 + 0.1 * (i == 2))
    
    weights = mt.rebalance_weights()
    sigma_safe = mt.compute_sigma_safe()
    logger.info(f"  新权重: {[f'{w:.3f}' for w in weights]}")
    logger.info(f"  Σ_safe={sigma_safe:.4f}")
    
    return mt


# ==================== GPU 资源调度 ====================

def apex_gpu_dashboard():
    """
    APEX GPU 资源调度面板
    
    模拟 GPU 内存监控 + batch size 建议
    """
    from apex_spiral.deep_learning import GPUMemoryHealth
    
    logger.info("=" * 60)
    logger.info("APEX GPU 资源调度面板")
    logger.info("=" * 60)
    
    gpu = GPUMemoryHealth(total_memory_gb=80.0)
    
    # 模拟训练过程中的内存变化
    memory_profile = [25, 35, 45, 60, 68, 72, 70, 65, 72, 76, 74, 72]
    
    logger.info(f"\n{'时刻':<6} {'使用(G)':<10} {'Ψ_健康':<10} {'建议Batch':<12} {'状态'}")
    logger.info("-" * 60)
    
    for t, mem in enumerate(memory_profile):
        psi = gpu.compute_psi(used_gb=mem)
        batch = gpu.suggest_batch_size(64, target_util=0.75)
        
        if psi > 0.8:
            status = "🟢 正常"
        elif psi > 0.5:
            status = "🟡 警告"
        elif psi > 0.2:
            status = "🟠 危险"
        else:
            status = "🔴 OOM"
        
        logger.info(f"t={t:<4} {mem}GB/80GB    {psi:.3f}       {batch:<12} {status}")
    
    return gpu


# ==================== 主函数 ====================

def main():
    parser = argparse.ArgumentParser(description='APEX 日常应用')
    parser.add_argument('--mode', type=str, default='train',
                       choices=['train', 'eval', 'hp_search', 'multitask', 'gpu', 'all'],
                       help='运行模式')
    parser.add_argument('--device', type=str, default='cpu', help='设备')
    parser.add_argument('--epochs', type=int, default=5, help='训练轮数')
    parser.add_argument('--batch_size', type=int, default=32, help='批大小')
    parser.add_argument('--lr', type=float, default=1e-3, help='学习率')
    parser.add_argument('--hidden_dim', type=int, default=32, help='隐藏层维度')
    parser.add_argument('--trials', type=int, default=8, help='超参搜索轮数')
    parser.add_argument('--log_interval', type=int, default=50, help='日志间隔')
    
    args = parser.parse_args()
    
    device = args.device
    
    # 生成演示数据
    logger.info("生成演示数据...")
    torch.manual_seed(42)
    
    n_samples = 1000
    n_features = 10
    n_classes = 3
    
    X = torch.randn(n_samples, n_features)
    y = torch.randint(0, n_classes, (n_samples,))
    
    dataset = TensorDataset(X, y)
    train_size = int(0.8 * n_samples)
    eval_size = n_samples - train_size
    
    train_dataset, eval_dataset = torch.utils.data.random_split(
        dataset, [train_size, eval_size]
    )
    
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True)
    eval_loader = DataLoader(eval_dataset, batch_size=args.batch_size)
    
    logger.info(f"数据: {n_samples} 样本 | {n_features} 特征 | {n_classes} 类别")
    logger.info(f"训练: {train_size} | 评估: {eval_size}")
    
    # === TRAIN MODE ===
    if args.mode in ['train', 'all']:
        logger.info("\n" + "=" * 60)
        logger.info("APEX 训练模式")
        logger.info("=" * 60)
        
        model = SimpleNet(
            input_dim=n_features,
            hidden_dim=args.hidden_dim,
            num_classes=n_classes
        ).to(device)
        
        optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
        
        # APEX Optimizer
        apex_opt = ApexOptimizer(
            optimizer,
            eta_skill_up=0.5,
            rho_feedback=0.5,
            rho_adaptive=True
        )
        
        # APEX Loss
        apex_loss = ApexLoss(
            label_smoothing=0.1,
            xi_base=1.0,
            use_adaptive_xi=True
        )
        
        for epoch in range(args.epochs):
            logger.info(f"\n【Epoch {epoch+1}/{args.epochs}】")
            result = apex_train_loop(
                model, train_loader, optimizer, apex_opt, apex_loss,
                device, log_interval=args.log_interval
            )
            logger.info(f"  总结 → Loss: {result['avg_loss']:.4f} | Acc: {result['accuracy']:.1f}% | ΔG: {result['delta_g']:.4f}")
        
        # 最终评估
        logger.info("\n【最终评估】")
        eval_result = apex_eval_loop(model, eval_loader, apex_loss, device)
        logger.info(f"  准确率: {eval_result['accuracy']:.1f}%")
        logger.info(f"  置信度: {eval_result['pred_confidence']:.4f}")
        logger.info(f"  校准误差: {eval_result['calibration_error']:.4f}")
        logger.info(f"  熵: {eval_result['entropy']:.4f}")
        logger.info(f"  不确定性: {eval_result['uncertainty_factor']:.4f}")
        logger.info(f"  ΔG/class: {[f'{g:.3f}' for g in eval_result['delta_g_per_class']]}")
        
        # 保存模型
        torch.save(model.state_dict(), 'apex_model.pt')
        logger.info("  模型已保存: apex_model.pt")
    
    # === EVAL MODE ===
    if args.mode in ['eval', 'all']:
        logger.info("\n" + "=" * 60)
        logger.info("APEX 评估模式")
        logger.info("=" * 60)
        
        model = SimpleNet(n_features, args.hidden_dim, n_classes).to(device)
        try:
            model.load_state_dict(torch.load('apex_model.pt'))
            logger.info("模型已加载: apex_model.pt")
        except FileNotFoundError:
            logger.warning("未找到模型文件，先训练...")
            return
        
        apex_loss = ApexLoss()
        
        eval_result = apex_eval_loop(model, eval_loader, apex_loss, device)
        
        logger.info(f"\n评估结果:")
        logger.info(f"  准确率: {eval_result['accuracy']:.1f}%")
        logger.info(f"  平均 Loss: {eval_result['avg_loss']:.4f}")
        logger.info(f"  预测置信度: {eval_result['pred_confidence']:.4f}")
        logger.info(f"  校准误差: {eval_result['calibration_error']:.4f}")
        logger.info(f"  预测熵: {eval_result['entropy']:.4f}")
        logger.info(f"  不确定性因子: {eval_result['uncertainty_factor']:.4f}")
        
        # APEX ΔG 评分
        delta_g = compute_apex_delta_g(
            lambda_root=args.lr / 0.01,
            theta=args.batch_size / 64,
            k_master=1.0 + args.hidden_dim / 128,
            h_entropy=eval_result['entropy'] + 0.1,
            epsilon=1.0 + eval_result['calibration_error'],
            rho_uncertainty=eval_result['uncertainty_factor'],
        )
        logger.info(f"  APEX ΔG: {delta_g:.4f}")
        
        # 每类别分析
        logger.info(f"\n各类别 ΔG:")
        for c, dg in enumerate(eval_result['delta_g_per_class']):
            logger.info(f"  Class {c}: ΔG = {dg:.4f}")
    
    # === HP SEARCH MODE ===
    if args.mode in ['hp_search', 'all']:
        logger.info("\n" + "=" * 60)
        logger.info("APEX 超参搜索模式")
        logger.info("=" * 60)
        
        search_space = {
            'lr': [1e-4, 5e-4, 1e-3, 2e-3, 5e-3],
            'batch_size': [16, 32, 64],
            'hidden_dim': [16, 32, 64, 128],
            'weight_decay': [0, 1e-4, 1e-3],
            'label_smoothing': [0.0, 0.05, 0.1, 0.15],
        }
        
        result = apex_hp_search(
            base_params={'input_dim': n_features, 'num_classes': n_classes},
            search_space=search_space,
            train_loader=train_loader,
            eval_loader=eval_loader,
            device=device,
            max_trials=args.trials
        )
        
        logger.info("\n【超参搜索结果】")
        logger.info(f"最佳参数: {result['best_params']}")
        logger.info(f"最佳评分: {result['best_score']:.4f}")
        logger.info("\nTop 3 配置:")
        for r in result['all_results'][:3]:
            logger.info(f"  Acc={r['accuracy']:.1f}% ΔG={r['delta_g']:.4f} Score={r['score']:.4f} | {r['params']}")
    
    # === MULTITASK MODE ===
    if args.mode in ['multitask', 'all']:
        apex_multitask_demo()
    
    # === GPU DASHBOARD MODE ===
    if args.mode in ['gpu', 'all']:
        apex_gpu_dashboard()
    
    logger.info("\n" + "=" * 60)
    logger.info("APEX 日常应用完成")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
