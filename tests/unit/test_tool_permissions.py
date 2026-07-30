"""Unit tests for tool autonomy gating."""

from __future__ import annotations

import pytest
from sra.core.context import RunContext
from sra.core.errors import InvalidActionError
from sra.models.actions import InvokeToolAction
from sra.models.goal import ResearchGoal
from sra.runtime.validation import ActionValidator
from sra.tools.permissions import required_autonomy_for_tags, tool_allowed

from tests.unit.runtime_fakes import FakeTool, FakeToolRegistry


def test_permission_matrix() -> None:
    assert required_autonomy_for_tags(["compute"]) == "safe"
    assert required_autonomy_for_tags(["search", "web"]) == "standard"
    assert required_autonomy_for_tags(["side_effect"]) == "unrestricted"
    assert tool_allowed(tags=["search"], autonomy="safe") is False
    assert tool_allowed(tags=["search"], autonomy="standard") is True


def test_action_validator_blocks_network_tools_under_safe_autonomy() -> None:
    registry = FakeToolRegistry(FakeTool("google_search", tags=["search", "web"]))
    validator = ActionValidator(registry, autonomy="safe")
    ctx = RunContext.create(ResearchGoal(question="Test"))
    with pytest.raises(InvalidActionError, match="autonomy"):
        validator.validate(
            InvokeToolAction(tool_name="google_search", arguments={"query": "x"}),
            ctx,
        )
