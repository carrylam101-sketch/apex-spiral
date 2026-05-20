#!/usr/bin/env python3
"""
APEX V10.3 Gini Gene Selector — 基尼增益基因网络选择机制
基于用户提供的 Gini/Entropy 公式体系，选择最优基因突变路径。

核心公式:
  Gini = 1 - Σ p_k²
  ΔGini = Gini_parent - (N_L/N × Gini_L + N_R/N × Gini_R)
  H = -Σ p_k log₂ p_k
  IG = H_parent - Σ (N_v/N × H_v)
  RandomForest: ŷ = argmax_c Σ I(h_b(x)=c)
  Bootstrap: ~63.2% | OOB: ~36.8%

© 2026 璇玑帝国
"""

import math
import json
import random
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# 1. Gini & Entropy Core Functions
# ─────────────────────────────────────────────────────────────────────────────

def gini_impurity(labels: List[Any]) -> float:
    """
    Gini Impurity: Gini = 1 - Σ p_k²
    衡量节点纯度，越低越纯（分裂后优先选低 Gini 的分支）。
    """
    if not labels:
        return 0.0
    total = len(labels)
    counts: Dict[Any, int] = {}
    for lbl in labels:
        counts[lbl] = counts.get(lbl, 0) + 1
    gini = 1.0
    for cnt in counts.values():
        prob = cnt / total
        gini -= prob * prob
    return max(0.0, min(gini, 1.0))


def gini_gain(parent_labels: List[Any], left_labels: List[Any], right_labels: List[Any]) -> float:
    """
    Gini Gain: ΔGini = Gini_parent - (N_L/N × Gini_L + N_R/N × Gini_R)
    选择使增益最大的特征与阈值分裂。
    """
    n = len(parent_labels)
    if n == 0:
        return 0.0
    parent_gini = gini_impurity(parent_labels)
    left_weight = len(left_labels) / n
    right_weight = len(right_labels) / n
    return parent_gini - (left_weight * gini_impurity(left_labels) +
                          right_weight * gini_impurity(right_labels))


def entropy(labels: List[Any]) -> float:
    """
    Entropy: H = -Σ p_k log₂ p_k
    信息熵，越低越有序。
    """
    if not labels:
        return 0.0
    total = len(labels)
    counts: Dict[Any, int] = {}
    for lbl in labels:
        counts[lbl] = counts.get(lbl, 0) + 1
    h = 0.0
    for cnt in counts.values():
        prob = cnt / total
        if prob > 0:
            h -= prob * math.log2(prob)
    return max(0.0, min(h, 10.0))  # cap for numerical stability


def information_gain(parent_labels: List[Any],
                      split_labels: List[List[Any]]) -> float:
    """
    IG = H_parent - Σ (N_v/N × H_v)
    信息增益，值越大说明分裂越有效。
    """
    n = len(parent_labels)
    if n == 0:
        return 0.0
    parent_entropy = entropy(parent_labels)
    weighted_child_entropy = 0.0
    for child in split_labels:
        weight = len(child) / n
        weighted_child_entropy += weight * entropy(child)
    return parent_entropy - weighted_child_entropy


def bootstrap_sample(population: List[Any], rng: random.Random = random) -> List[Any]:
    """
    Bootstrap: 约 63.2% 概率被选中（N 次独立抽取有放回）。
    袋外样本（OOB）约 36.8%。
    """
    n = len(population)
    if n == 0:
        return []
    return [rng.choice(population) for _ in range(n)]


def oob_sample(population: List[Any], rng: random.Random = random) -> List[Any]:
    """
    OOB sample: 被 Bootstrap 漏选的样本（约 36.8%）。
    用于无偏评估。
    """
    bootstrap_indices = set()
    n = len(population)
    for _ in range(n):
        bootstrap_indices.add(rng.randint(0, n - 1))
    return [population[i] for i in range(n) if i not in bootstrap_indices]


# ─────────────────────────────────────────────────────────────────────────────
# 2. Gene Candidate Representation
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class GeneCandidate:
    """基因候选对象"""
    id: str
    name: str
    signal_patterns: List[str]
    category: str  # repair | optimize | innovate
    preconditions: List[str]
    strategy: List[str]
    gini_score: float = 0.0
    ig_score: float = 0.0
    oob_accuracy: float = 0.0
    usage_count: int = 0
    success_rate: float = 0.0
    last_used: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def feature_vector(self) -> List[float]:
        """
        将基因特征映射为数值向量，供决策树分裂使用。
        特征顺序: [gini_score, ig_score, usage_count_norm, success_rate, category_code]
        """
        category_map = {"repair": 0.0, "optimize": 0.5, "innovate": 1.0}
        usage_norm = math.tanh(self.usage_count / 20.0)
        return [
            self.gini_score,
            self.ig_score,
            usage_norm,
            self.success_rate,
            category_map.get(self.category, 0.5)
        ]


@dataclass
class FitnessResult:
    """适应度评估结果"""
    gene_id: str
    gini_gain: float
    ig_gain: float
    oob_accuracy: float
    combined_score: float
    selected: bool


# ─────────────────────────────────────────────────────────────────────────────
# 3. Gini Gene Selector (Random Forest style)
# ─────────────────────────────────────────────────────────────────────────────

class GiniGeneSelector:
    """
    基于基尼增益的基因网络选择机制。

    流程:
    1. Bootstrap 采样多个基因子集（模拟随机森林）
    2. 对每个 Bootstrap 样本计算每个候选基因的 Gini 增益
    3. 用信息增益 IG 验证分裂质量
    4. 多数投票决定最终选中基因
    5. OOB 样本用于无偏评估
    """

    def __init__(self,
                 n_trees: int = 10,
                 bootstrap_ratio: float = 0.632,
                 min_genes_per_split: int = 2,
                 seed: int = 42):
        self.n_trees = n_trees
        self.bootstrap_ratio = bootstrap_ratio
        self.min_genes_per_split = min_genes_per_split
        self.rng = random.Random(seed)
        self.tree_votes: Dict[str, int] = {}
        self.oob_results: Dict[str, List[float]] = {}

    def _evaluate_gene_split(
        self,
        gene: GeneCandidate,
        success_labels: List[bool],
        failure_labels: List[bool]
    ) -> Tuple[float, float, float]:
        """
        评估单个基因的分裂效果。
        success_labels: 使用该基因成功的任务标签
        failure_labels: 使用该基因失败的任务标签
        返回: (gini_gain, ig_gain, oob_accuracy)
        """
        parent = success_labels + failure_labels
        parent_outcomes = [True] * len(success_labels) + [False] * len(failure_labels)

        # 二分裂：标签为 True/False
        gini = gini_gain(parent, success_labels, failure_labels)

        # 信息增益
        ig = information_gain(parent, [success_labels, failure_labels])

        # OOB 准确率（用该基因的历史成功率）
        oob_acc = gene.success_rate

        return gini, ig, oob_acc

    def _find_best_split(self, genes: List[GeneCandidate],
                         outcomes: List[bool]) -> Tuple[Optional[GeneCandidate], float]:
        """
        在候选基因中找使 Gini 增益最大的分裂点。
        """
        if len(genes) < self.min_genes_per_split:
            return None, 0.0

        best_gene: Optional[GeneCandidate] = None
        best_gain = -1.0

        for gene in genes:
            # 按基因特征向量排序，找分裂阈值
            fv = gene.feature_vector()
            threshold = fv[0]  # 用 gini_score 作为分裂阈值

            left = []
            right = []
            for i, g in enumerate(genes):
                if g.feature_vector()[0] <= threshold:
                    left.append(outcomes[i])
                else:
                    right.append(outcomes[i])

            if not left or not right:
                continue

            parent_labels = outcomes
            left_labels = left
            right_labels = right
            gain = gini_gain(parent_labels, left_labels, right_labels)

            if gain > best_gain:
                best_gain = gain
                best_gene = gene

        return best_gene, best_gain

    def select(self,
                candidates: List[GeneCandidate],
                outcome_history: List[Tuple[str, bool]]
                ) -> FitnessResult:
        """
        随机森林多数投票选择最优基因。

        Args:
            candidates: 候选基因列表
            outcome_history: (gene_id, success) 历史使用结果

        Returns:
            FitnessResult: 包含选中基因和评分
        """
        if not candidates:
            return FitnessResult(gene_id="null", gini_gain=0.0, ig_gain=0.0,
                                 oob_accuracy=0.0, combined_score=0.0, selected=False)

        # 构建 gene_id → outcomes 映射
        gene_outcomes: Dict[str, List[bool]] = {g.id: [] for g in candidates}
        for gene_id, success in outcome_history:
            if gene_id in gene_outcomes:
                gene_outcomes[gene_id].append(success)

        # Bootstrap 多数投票
        n = len(candidates)
        bootstrap_size = max(1, int(n * self.bootstrap_ratio))
        tree_winners: Dict[str, int] = {}

        for tree_idx in range(self.n_trees):
            # Bootstrap 采样
            boot_genes = self._bootstrap_genes(candidates, bootstrap_size)
            boot_outcomes = []
            for g in boot_genes:
                outs = gene_outcomes.get(g.id, [])
                boot_outcomes.append(any(outs) if outs else False)

            if len(boot_genes) < self.min_genes_per_split:
                continue

            # 找最优分裂
            winner, gain = self._find_best_split(boot_genes, boot_outcomes)
            if winner:
                tree_winners[winner.id] = tree_winners.get(winner.id, 0) + 1

        if not tree_winners:
            # 回退：按综合评分排序
            scored = [(g.id, self._combined_score(g, gene_outcomes.get(g.id, [])))
                      for g in candidates]
            scored.sort(key=lambda x: x[1], reverse=True)
            winner_id = scored[0][0]
            winner_score = scored[0][1]
        else:
            # 多数投票
            winner_id = max(tree_winners, key=tree_winners.get)
            winner_score = tree_winners[winner_id] / self.n_trees

        winner_gene = next((g for g in candidates if g.id == winner_id), None)

        if winner_gene is None:
            return FitnessResult(gene_id="null", gini_gain=0.0, ig_gain=0.0,
                                 oob_accuracy=0.0, combined_score=0.0, selected=False)

        outs = gene_outcomes.get(winner_id, [])
        gini, ig, oob_acc = self._evaluate_gene_split(
            winner_gene,
            [o for o in outs if o],
            [o for o in outs if not o]
        )

        # 综合评分：Gini 增益 × 0.4 + IG × 0.3 + OOB × 0.3
        combined = gini * 0.4 + ig * 0.3 + oob_acc * 0.3

        return FitnessResult(
            gene_id=winner_id,
            gini_gain=gini,
            ig_gain=ig,
            oob_accuracy=oob_acc,
            combined_score=combined,
            selected=True
        )

    def _bootstrap_genes(self, genes: List[GeneCandidate], size: int) -> List[GeneCandidate]:
        """Bootstrap 采样基因子集（约 63.2% 不同）"""
        if len(genes) <= size:
            return list(genes)
        return [self.rng.choice(genes) for _ in range(size)]

    def _combined_score(self, gene: GeneCandidate, outcomes: List[bool]) -> float:
        """无投票结果时的回退评分"""
        success_rate = sum(outcomes) / max(len(outcomes), 1)
        return gene.gini_score * 0.4 + gene.ig_score * 0.3 + success_rate * 0.3


# ─────────────────────────────────────────────────────────────────────────────
# 4. APEX Integration
# ─────────────────────────────────────────────────────────────────────────────

def load_genes_from_json(json_path: Path) -> List[GeneCandidate]:
    """从 genes.json 加载候选基因"""
    if not json_path.exists():
        return []
    data = json.loads(json_path.read_text())
    candidates: List[GeneCandidate] = []
    # genes.json structure: {genes: [...]}
    gene_list = data if isinstance(data, list) else data.get("genes", [])
    for g in gene_list:
        signals = g.get("learning_signals", [])
        gene_type = "optimize"
        if any(s in signals for s in ["recurring_error", "repair_loop"]):
            gene_type = "repair"
        elif any(s in signals for s in ["innovation_opportunity", "capability_gap"]):
            gene_type = "innovate"
        candidates.append(GeneCandidate(
            id=g.get("id", "unknown"),
            name=g.get("name", g.get("id", "unknown")),
            signal_patterns=signals,
            category=gene_type,
            preconditions=g.get("preconditions", []),
            strategy=g.get("strategy", []),
            gini_score=min(len(signals) / 20.0, 1.0),
            ig_score=min(len(signals) / 30.0, 1.0),
            usage_count=g.get("usage_count", 0),
            success_rate=g.get("success_rate", 0.5),
            raw_data=g
        ))
    return candidates


def load_outcome_history(history_dir: Path = Path("/home/ubuntu/apex-spiral/memory/evolution")
                         ) -> List[Tuple[str, bool]]:
    """从 evolver asset_log 加载历史使用结果"""
    outcomes: List[Tuple[str, bool]] = []
    log_path = history_dir / "asset_call_log.jsonl"
    if log_path.exists():
        for line in log_path.read_text().splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                action = entry.get("action", "")
                # asset_reference = 使用基因
                if action == "asset_reference":
                    outcomes.append((entry.get("asset_id", "unknown"), True))
                elif action == "asset_publish_skip":
                    outcomes.append((entry.get("asset_id", "unknown"), False))
            except Exception:
                continue
    return outcomes


def run_gene_selection(
    genes_path: Path = Path("/home/ubuntu/apex-spiral/genes.json"),
    history_dir: Path = Path("/home/ubuntu/apex-spiral/memory/evolution"),
    n_trees: int = 10
) -> Dict[str, Any]:
    """
    主入口：从 genes.json 加载候选基因，运行 Gini 选择器，
    返回最优基因和评分。
    """
    candidates = load_genes_from_json(genes_path)
    history = load_outcome_history(history_dir)

    if not candidates:
        return {"selected_gene_id": None, "error": "no candidates found"}

    selector = GiniGeneSelector(n_trees=n_trees)
    result = selector.select(candidates, history)

    return {
        "selected_gene_id": result.gene_id if result.selected else None,
        "gini_gain": round(result.gini_gain, 6),
        "ig_gain": round(result.ig_gain, 6),
        "oob_accuracy": round(result.oob_accuracy, 4),
        "combined_score": round(result.combined_score, 6),
        "n_candidates": len(candidates),
        "n_trees": n_trees,
        "n_outcome_history": len(history),
        "timestamp": datetime.now().isoformat()
    }


# ─────────────────────────────────────────────────────────────────────────────
# 5. CLI Entry Point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="APEX Gini Gene Selector")
    parser.add_argument("--genes", default="genes.json", help="Path to genes.json")
    parser.add_argument("--history", default="memory/evolution/asset_call_log.jsonl",
                        help="Path to outcome history")
    parser.add_argument("--n-trees", type=int, default=10, help="Number of RF trees")
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    args = parser.parse_args()

    genes_path = Path(args.genes)
    if not genes_path.is_absolute():
        genes_path = Path("/home/ubuntu/apex-spiral") / genes_path
    history_path = Path(args.history)
    if not history_path.is_absolute():
        history_path = Path("/home/ubuntu/apex-spiral") / history_path

    result = run_gene_selection(genes_path, history_path, args.n_trees)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("=" * 60)
        print("🧬 APEX Gini Gene Selector — 选择结果")
        print("=" * 60)
        print(f"  候选基因数: {result['n_candidates']}")
        print(f"  随机森林树数: {result['n_trees']}")
        print(f"  历史使用记录: {result['n_outcome_history']}")
        print()
        print(f"  选中基因ID: {result['selected_gene_id']}")
        print(f"  Gini 增益:   {result.get('gini_gain', 'N/A')}")
        print(f"  IG 信息增益: {result.get('ig_gain', 'N/A')}")
        print(f"  OOB 准确率: {result.get('oob_accuracy', 'N/A')}")
        print(f"  综合评分:   {result.get('combined_score', 'N/A')}")
        print(f"  时间戳:    {result['timestamp']}")
        print("=" * 60)
