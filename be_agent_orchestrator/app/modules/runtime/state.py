"""Mutable execution state threaded through every node.

Starts as the run's ``input`` (the webhook body) and grows as nodes write
their outputs back. Each node's output lands at ``state[node_id]`` so
downstream nodes can reference it via dotted paths in edge conditions
(``state.intake.intent``) and via ``{{intake.content}}`` templates.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

_PLACEHOLDER = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z0-9_]+)*)\s*\}\}")


class RunState:
    def __init__(self, initial: dict[str, Any]) -> None:
        # Shallow-copy so the caller's input dict isn't mutated by node writes.
        self._data: dict[str, Any] = dict(initial)

    def as_dict(self) -> dict[str, Any]:
        return dict(self._data)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def get_path(self, path: str) -> Any:
        """Resolve a dotted path against state. Missing → ``None``.

        ``"intake.intent"`` walks ``state["intake"]["intent"]``. Used by
        edge conditions and by ``render_template``.
        """

        node: Any = self._data
        for part in path.split("."):
            if isinstance(node, Mapping):
                node = node.get(part)
            else:
                return None
            if node is None:
                return None
        return node


def render_template(template: str, state: RunState) -> str:
    """Replace ``{{a.b.c}}`` placeholders with values from state.

    Missing paths → empty string (same convention as the tool executor's
    placeholder resolver, kept consistent so a template that works in a
    tool config also works as an agent input template).
    """

    def _replace(match: re.Match[str]) -> str:
        value = state.get_path(match.group(1))
        return "" if value is None else str(value)

    return _PLACEHOLDER.sub(_replace, template)
