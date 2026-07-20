"""Safe calculator tool — expression evaluation without unrestricted exec."""

from __future__ import annotations

import ast
import math
import operator
from typing import Any

from pydantic import BaseModel, Field

from sra.core.errors import ToolExecutionError
from sra.core.ports.tools import ToolContext
from sra.tools.base import BaseTool

_BINARY_OPS: dict[type[ast.operator], Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS: dict[type[ast.unaryop], Any] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}
_FUNCTIONS: dict[str, Any] = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "ceil": math.ceil,
    "floor": math.floor,
}
_CONSTANTS: dict[str, float] = {
    "pi": math.pi,
    "e": math.e,
}


class CalculatorInput(BaseModel):
    expression: str = Field(min_length=1, max_length=500)


class CalculatorOutput(BaseModel):
    expression: str
    result: float | int


class CalculatorTool(BaseTool):
    name = "calculator"
    description = (
        "Evaluate a safe arithmetic expression (supports +, -, *, /, **, sqrt, log, etc.)."
    )
    input_schema = CalculatorInput
    output_schema = CalculatorOutput
    tags = ["compute", "math"]

    async def execute(self, payload: BaseModel, ctx: ToolContext) -> BaseModel:
        assert isinstance(payload, CalculatorInput)
        try:
            result = _safe_eval(payload.expression)
        except ToolExecutionError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ToolExecutionError(
                f"Could not evaluate expression: {exc}",
                details={"expression": payload.expression},
            ) from exc
        if isinstance(result, float) and (math.isnan(result) or math.isinf(result)):
            raise ToolExecutionError("Expression produced a non-finite result")
        if isinstance(result, (int, float)):
            return CalculatorOutput(expression=payload.expression, result=result)
        raise ToolExecutionError(
            "Expression did not evaluate to a number",
            details={"type": type(result).__name__},
        )


def _safe_eval(expression: str) -> float | int:
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ToolExecutionError("Invalid calculator expression syntax") from exc
    return _eval_node(tree.body)


def _eval_node(node: ast.AST) -> float | int:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp):
        op = _BINARY_OPS.get(type(node.op))
        if op is None:
            raise ToolExecutionError(f"Operator not allowed: {type(node.op).__name__}")
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        result = op(left, right)
        if not isinstance(result, (int, float)):
            raise ToolExecutionError("Binary operation did not return a number")
        return result
    if isinstance(node, ast.UnaryOp):
        op = _UNARY_OPS.get(type(node.op))
        if op is None:
            raise ToolExecutionError(f"Unary operator not allowed: {type(node.op).__name__}")
        value = _eval_node(node.operand)
        result = op(value)
        if not isinstance(result, (int, float)):
            raise ToolExecutionError("Unary operation did not return a number")
        return result
    if isinstance(node, ast.Name) and node.id in _CONSTANTS:
        return _CONSTANTS[node.id]
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCTIONS:
            raise ToolExecutionError("Function call not allowed")
        args = [_eval_node(arg) for arg in node.args]
        if node.keywords:
            raise ToolExecutionError("Keyword arguments are not allowed")
        result = _FUNCTIONS[node.func.id](*args)
        if not isinstance(result, (int, float)):
            raise ToolExecutionError("Function call did not return a number")
        return result
    raise ToolExecutionError(f"Unsupported expression node: {type(node).__name__}")
