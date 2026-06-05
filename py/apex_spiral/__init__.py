"""
ApexSpiral - 璇玑帝国 APEX 终极闭环进化公式 Python 实现
"""

__version__ = "0.3.0"
__author__ = "璇玑帝国"

from apex_spiral.core import ApexCalculator, ApexParams

__all__ = [
    "ApexCalculator", "ApexParams", "__version__",
]

try:
    from apex_spiral.deep_learning import (
        ApexTrainer, ApexLoss, ApexOptimizer,
        AdaptiveEntropyParams, ConfidenceCalibration, GPUMemoryHealth,
        GradientPenalty, MultiTaskUnified, DistributedCooperation,
        UncertaintyQuantification, compute_apex_delta_g
    )
    __all__.extend([
        "ApexTrainer", "ApexLoss", "ApexOptimizer",
        "AdaptiveEntropyParams", "ConfidenceCalibration", "GPUMemoryHealth",
        "GradientPenalty", "MultiTaskUnified", "DistributedCooperation",
        "UncertaintyQuantification", "compute_apex_delta_g",
    ])
except ImportError:
    pass  # PyTorch not available
