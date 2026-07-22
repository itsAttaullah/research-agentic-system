"""Confidence Estimator: per-topic confidence scores with rationale and
evidence references. Low-confidence topics automatically enqueue more research.
"""

from sra.confidence.estimator import EvidenceConfidenceEstimator

__all__ = ["EvidenceConfidenceEstimator"]
