"""Unit tests for the runtime — state/template/conditions/branch routing.

The full Executor exercise (with a DB) lives in the integration suite.
Here we cover the pure-Python pieces so a regression in the DSL or the
state walker doesn't slip through."""

from __future__ import annotations

from app.modules.runtime.conditions import matches
from app.modules.runtime.state import RunState, render_template

# ──────────────────────────────────────────────────────────────────────
# RunState
# ──────────────────────────────────────────────────────────────────────


def test_runstate_get_path_walks_nested_dicts() -> None:
    state = RunState({"intake": {"intent": "billing", "score": 0.92}})
    assert state.get_path("intake.intent") == "billing"
    assert state.get_path("intake.score") == 0.92
    assert state.get_path("intake.missing") is None
    assert state.get_path("missing.path") is None


def test_runstate_set_then_get() -> None:
    state = RunState({"a": 1})
    state.set("b", {"c": "hello"})
    assert state.get_path("b.c") == "hello"
    assert state.as_dict() == {"a": 1, "b": {"c": "hello"}}


def test_runstate_initial_is_shallow_copied() -> None:
    src = {"x": 1}
    state = RunState(src)
    state.set("y", 2)
    assert "y" not in src  # source not mutated


# ──────────────────────────────────────────────────────────────────────
# render_template
# ──────────────────────────────────────────────────────────────────────


def test_render_template_substitutes_dotted_paths() -> None:
    state = RunState({"user": {"name": "Aman"}, "message": "hi"})
    assert render_template("Hello {{user.name}}!", state) == "Hello Aman!"
    assert render_template("{{message}}", state) == "hi"


def test_render_template_missing_keys_become_empty_string() -> None:
    state = RunState({"a": 1})
    assert render_template("[{{missing.thing}}]", state) == "[]"


# ──────────────────────────────────────────────────────────────────────
# matches — edge condition evaluation
# ──────────────────────────────────────────────────────────────────────


def test_matches_always_true_when_no_condition() -> None:
    assert matches(None, RunState({})) is True
    assert matches({"kind": "always"}, RunState({})) is True


def test_matches_equals_kind() -> None:
    state = RunState({"requires_human_approval": True})
    yes = {"kind": "equals", "path": "requires_human_approval", "value": True}
    no = {"kind": "equals", "path": "requires_human_approval", "value": False}
    assert matches(yes, state) is True
    assert matches(no, state) is False


def test_matches_expr_kind_supports_state_dot_path() -> None:
    state = RunState({"intake": {"intent": "billing"}, "score": 7})
    assert matches({"kind": "expr", "expr": "state.intake.intent == 'billing'"}, state)
    assert matches({"kind": "expr", "expr": "state.score > 5"}, state)
    assert matches({"kind": "expr", "expr": "state.score < 5"}, state) is False
    assert matches({"kind": "expr", "expr": "state.intake.intent != 'tech'"}, state)


def test_matches_expr_falsey_on_garbage() -> None:
    # Parse failure must not raise — branching no-match is normal control flow.
    assert matches({"kind": "expr", "expr": "garbage in == garbage out"}, RunState({})) is False
    assert matches({"kind": "expr", "expr": ""}, RunState({})) is False


def test_matches_expr_handles_type_coercion_safely() -> None:
    state = RunState({"v": "not a number"})
    # `>` against a string vs int raises TypeError under the hood;
    # the matcher swallows it and returns False so the run can move on.
    assert matches({"kind": "expr", "expr": "state.v > 5"}, state) is False
