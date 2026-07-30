"""CLI smoke tests (no live LLM calls)."""

from __future__ import annotations

import pytest
from sra.cli.main import main


def test_cli_requires_subcommand() -> None:
    with pytest.raises(SystemExit) as excinfo:
        main([])
    assert excinfo.value.code == 2


def test_cli_run_help_exits_zero_via_argparse_systemexit() -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["run", "--help"])
    assert excinfo.value.code == 0
