"""Edge-condition evaluator.

Evaluates a ``WorkflowEdgeCondition`` (kind = ``always`` | ``equals`` |
``expr``) against the current run state. Returns ``True`` when the edge
should fire. Used by the executor to pick the next node when a source has
``conditional_edges``.

The ``expr`` DSL is a deliberately tiny subset of ``state.path OP literal``
— enough for ``state.requires_human_approval == true`` and similar one-liners.
Anything more is a sign you want a real Condition node, not an edge expr.
"""

from __future__ import annotations

import re
from typing import Any

from app.modules.runtime.state import RunState

_EXPR = re.compile(r"^\s*state\.([\w.]+)\s*(==|!=|>=|<=|>|<)\s*(.+?)\s*$")


def matches(condition: dict[str, Any] | None, state: RunState) -> bool:
    if condition is None:
        return True
    kind = condition.get("kind", "always")

    if kind == "always":
        return True

    if kind == "equals":
        path = condition.get("path")
        if not path:
            return False
        return bool(state.get_path(path) == condition.get("value"))

    if kind == "expr":
        expr = condition.get("expr") or ""
        return _eval_expr(expr, state)

    return False


def _eval_expr(expr: str, state: RunState) -> bool:
    """Tiny ``state.path OP literal`` evaluator.

    Returns ``False`` on parse failure rather than raising — branch
    no-matches are normal control flow, not an executor error.
    """

    match = _EXPR.match(expr)
    if match is None:
        return False
    path, op, raw_value = match.groups()
    actual = state.get_path(path)
    expected = _parse_literal(raw_value)

    try:
        if op == "==":
            return bool(actual == expected)
        if op == "!=":
            return bool(actual != expected)
        if op == ">":
            return bool(actual > expected)
        if op == "<":
            return bool(actual < expected)
        if op == ">=":
            return bool(actual >= expected)
        if op == "<=":
            return bool(actual <= expected)
    except TypeError:
        return False
    return False


def _parse_literal(raw: str) -> Any:
    raw = raw.strip()
    if raw in ("true", "True"):
        return True
    if raw in ("false", "False"):
        return False
    if raw in ("null", "None"):
        return None
    if raw.startswith(("'", '"')) and raw.endswith(raw[0]):
        return raw[1:-1]
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw
