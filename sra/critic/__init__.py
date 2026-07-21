"""Critic: hard quality gate before report generation. Flags missing evidence,
weak assumptions, unsupported claims, and bias; can force a return to planning.
"""

from sra.critic.llm_critic import LLMCritic
from sra.critic.schemas import DraftCritique, DraftFinding

__all__ = [
    "DraftCritique",
    "DraftFinding",
    "LLMCritic",
]
