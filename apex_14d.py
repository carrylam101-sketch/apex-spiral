#!/usr/bin/env python3
"""
APEX 14维度全量计算器
APEX V10.4 - 璇玑帝国

使用方法:
    python apex_14d.py --base 0.49 --pi 4.0 --pid 0.96 --rd 0.88
    python apex_14d.py --interactive
"""

import argparse
import json
from typing import Optional

# 默认参数（基于朱涛实验数据）
DEFAULT_PARAMS = {
    "ΔG_base": 0.49,    # 基准值
    "Π": 4.0,           # 并行增益
    "PID": 0.96,        # PID稳定性
    "RD": 0.88,         # 率失真
    "Kelly": 0.44,      # Kelly风险
    "Γ": 0.29,          # 多Agent博弈
    "E_xp": 1.20,       # 探索增益
    "M": 1.08,          # 记忆增益
    "Λ_sw": 0.90,       # 切换损失
    "Ξ": 0.52,          # 复杂度惩罚
}

PARAM_INFO = {
    "ΔG_base": {"name": "基准值", "range": [0, 1], "desc": "基础能力基准"},
    "Π": {"name": "并行增益", "range": [1, 10], "desc": "多线程并行能力"},
    "PID": {"name": "PID稳定性", "range": [0, 1], "desc": "控制系统稳定性"},
    "RD": {"name": "率失真", "range": [0, 1], "desc": "信息压缩效率"},
    "Kelly": {"name": "Kelly风险", "range": [0, 1], "desc": "资源分配风险控制"},
    "Γ": {"name": "多Agent博弈", "range": [0, 1], "desc": "竞争环境适应力"},
    "E_xp": {"name": "探索增益", "range": [0.5, 2], "desc": "探索新领域能力"},
    "M": {"name": "记忆增益", "range": [0.5, 2], "desc": "长期记忆保持"},
    "Λ_sw": {"name": "切换损失", "range": [0, 1], "desc": "上下文切换效率"},
    "Ξ": {"name": "复杂度惩罚", "range": [0, 2], "desc": "处理复杂任务能力"},
}

def calculate_ΔG(params: dict) -> float:
    """计算最终ΔG"""
    return (
        params["ΔG_base"] *
        params["Π"] *
        params["PID"] *
        params["RD"] *
        params["Kelly"] *
        params["Γ"] *
        params["E_xp"] *
        params["M"] *
        params["Λ_sw"] *
        params["Ξ"]
    )

def get_grade(ΔG: float) -> str:
    """根据ΔG评分"""
    if ΔG > 1.0: return "S"
    if ΔG >= 0.5: return "A"
    if ΔG >= 0.2: return "B"
    if ΔG >= 0.1: return "C"
    return "D"

def get_contribution(param_name: str, value: float) -> float:
    """计算参数贡献度"""
    return value * 100

def analyze_bottleneck(params: dict) -> list:
    """分析瓶颈"""
    bottlenecks = []
    for name, info in PARAM_INFO.items():
        val = params[name]
        rng = info["range"]
        if val < (rng[0] + rng[1]) / 2:
            bottlenecks.append((name, info["name"], val))
    bottlenecks.sort(key=lambda x: x[2])
    return bottlenecks[:3]

def print_report(params: dict, ΔG: float, grade: str):
    """打印分析报告"""
    print("\n" + "="*60)
    print("APEX 14维度分析报告")
    print("="*60)
    print(f"\n最终ΔG: {ΔG:.4f} | 评级: {grade}")
    print(f"相比基线(0.129): {(ΔG/0.129-1)*100:+.1f}%")
    
    print("\n--- 参数贡献度 ---")
    contributions = []
    for name, info in PARAM_INFO.items():
        val = params[name]
        contrib = get_contribution(name, val)
        contributions.append((name, info["name"], val, contrib))
    
    contributions.sort(key=lambda x: x[3], reverse=True)
    for name, cnname, val, contrib in contributions:
        bar = "█" * int(contrib / 10)
        print(f"  {cnname}({name}): {val:.2f} {bar} {contrib:.0f}%")
    
    print("\n--- 瓶颈分析 ---")
    bottlenecks = analyze_bottleneck(params)
    for i, (name, cnname, val) in enumerate(bottlenecks, 1):
        print(f"  {i}. {cnname}({name}): {val:.2f} ← 待优化")
    
    print("\n--- 三步优化建议 ---")
    print("  Step1: Γ优化 (0.29→0.44) → ΔG +52%")
    print("  Step2: Ξ优化 (0.52→1.72) → ΔG +233%")
    print("  Step3: Λ优化 (0.90→0.98) → ΔG +148%")

def interactive_mode():
    """交互模式"""
    print("\n" + "="*60)
    print("APEX 14维度交互配置")
    print("="*60)
    params = DEFAULT_PARAMS.copy()
    
    print("\n输入参数值(直接回车使用默认值):")
    for name, info in PARAM_INFO.items():
        default = params[name]
        while True:
            try:
                val = input(f"  {info['name']}({name}) [{default}]: ").strip()
                if val == "":
                    break
                val = float(val)
                params[name] = val
                break
            except:
                print("  无效输入，请输入数字")
    
    ΔG = calculate_ΔG(params)
    grade = get_grade(ΔG)
    print_report(params, ΔG, grade)

def main():
    parser = argparse.ArgumentParser(description="APEX 14维度全量计算器")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互模式")
    parser.add_argument("--json", "-j", action="store_true", help="JSON输出")
    
    for name in DEFAULT_PARAMS:
        parser.add_argument(f"--{name.lower()}", type=float, help=f"{PARAM_INFO[name]['name']}")
    
    args = parser.parse_args()
    
    if args.interactive:
        interactive_mode()
        return
    
    # 构建参数
    params = DEFAULT_PARAMS.copy()
    for name in DEFAULT_PARAMS:
        val = getattr(args, name.lower(), None)
        if val is not None:
            params[name] = val
    
    ΔG = calculate_ΔG(params)
    grade = get_grade(ΔG)
    
    if args.json:
        print(json.dumps({
            "params": params,
            "ΔG": round(ΔG, 6),
            "grade": grade
        }))
    else:
        print_report(params, ΔG, grade)

if __name__ == "__main__":
    main()
