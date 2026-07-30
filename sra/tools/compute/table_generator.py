"""Table generator — normalize rows into markdown/CSV/JSON tables."""

from __future__ import annotations

import csv
import io
import json
from typing import Any, Literal

from pydantic import BaseModel, Field

from sra.core.errors import ToolExecutionError
from sra.core.ports.tools import ToolContext
from sra.tools.base import BaseTool


class TableGeneratorInput(BaseModel):
    columns: list[str] = Field(min_length=1)
    rows: list[list[Any]] = Field(default_factory=list)
    format: Literal["markdown", "csv", "json"] = "markdown"
    title: str = ""


class TableGeneratorOutput(BaseModel):
    format: str
    content: str
    row_count: int
    column_count: int


class TableGeneratorTool(BaseTool):
    name = "table_generator"
    description = (
        "Build a markdown, CSV, or JSON table from columns and rows. "
        "Use to structure comparisons (competitors, pricing, features)."
    )
    input_schema = TableGeneratorInput
    output_schema = TableGeneratorOutput
    tags = ["compute", "format"]

    async def execute(self, payload: BaseModel, ctx: ToolContext) -> BaseModel:
        assert isinstance(payload, TableGeneratorInput)
        width = len(payload.columns)
        for index, row in enumerate(payload.rows):
            if len(row) != width:
                raise ToolExecutionError(
                    f"Row {index} has {len(row)} values; expected {width}",
                )

        if payload.format == "markdown":
            content = _to_markdown(payload.columns, payload.rows, title=payload.title)
        elif payload.format == "csv":
            content = _to_csv(payload.columns, payload.rows)
        else:
            content = json.dumps(
                {"title": payload.title, "columns": payload.columns, "rows": payload.rows},
                indent=2,
                default=str,
            )

        return TableGeneratorOutput(
            format=payload.format,
            content=content,
            row_count=len(payload.rows),
            column_count=width,
        )


def _to_markdown(columns: list[str], rows: list[list[Any]], *, title: str) -> str:
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    body = ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    parts = [header, separator, *body]
    if title:
        return f"### {title}\n\n" + "\n".join(parts)
    return "\n".join(parts)


def _to_csv(columns: list[str], rows: list[list[Any]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(columns)
    writer.writerows(rows)
    return buffer.getvalue()
