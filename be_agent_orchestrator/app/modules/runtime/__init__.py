"""Workflow execution runtime.

Reads the persisted ``compiled_graph`` for a workflow and walks it node by
node, persisting per-step IO into ``workflow_run_nodes`` and the granular
event stream into ``runtime_events``.

Entry point: ``app.modules.runtime.executor.Executor`` — constructed per
run by ``app.worker.jobs.execute_workflow_run_job``.
"""

from app.modules.runtime.executor import Executor, ExecutorError

__all__ = ["Executor", "ExecutorError"]
