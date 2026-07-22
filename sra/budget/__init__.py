"""Budget Manager: tracks iterations, tokens, API cost, elapsed time, and
visited sources against hard limits; aborts the run before overspend.
"""

from sra.budget.manager import DefaultBudgetManager

__all__ = ["DefaultBudgetManager"]
