"""Reflection Engine: after each research step, evaluates progress, source
trust, and whether the strategy should change. Its output feeds the planner
and task manager — it is not just logging.
"""

from sra.reflection.llm_engine import LLMReflectionEngine
from sra.reflection.schemas import DraftReflection

__all__ = [
    "DraftReflection",
    "LLMReflectionEngine",
]
