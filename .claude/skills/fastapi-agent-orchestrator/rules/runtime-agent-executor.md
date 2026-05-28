---
title: Agent Executor = LLM Call + Tool Loop + Memory Hooks
impact: CRITICAL
impactDescription: This is the actual agent runtime the spec demands ("real runtime, not UI mockup")
tags: runtime, agent, executor, tools, memory
---

## Agent Executor = LLM Call + Tool Loop + Memory Hooks

The agent executor turns one `Agent` config (system prompt, model, tools, memory) into a node function used by the LangGraph compiler. It has three responsibilities:

1. Build the message list (system prompt + memory + state.messages + tool results)
2. Call the LLM via `LLMProvider` (see [[llm-provider-abstraction]])
3. If the LLM requested tools, execute them via the tool registry, append results, loop

### State

```python
# app/modules/runtime/state.py
from pydantic import BaseModel, Field

from app.modules.messages.schemas import Message


class RuntimeState(BaseModel):
    run_id: str
    messages: list[Message] = Field(default_factory=list)
    scratchpad: dict = Field(default_factory=dict)
```

### Executor

```python
# app/modules/runtime/agent_executor.py
from app.modules.agents.models import Agent
from app.modules.llm.service import LLMService
from app.modules.tools.service import ToolService
from app.modules.messages.schemas import Message
from app.modules.runtime.events import EventEmitter
from app.modules.runtime.schemas import RuntimeEventType


MAX_TOOL_HOPS = 4


async def run_agent_turn(
    agent: Agent,
    state: RuntimeState,
    emit: EventEmitter,
    *,
    llm: LLMService,
    tools: ToolService,
    memory_loader: MemoryLoader,
) -> tuple[Message, TokenUsage]:
    history = await memory_loader.load(agent.id, state)
    messages = (
        [Message(role="system", content=agent.system_prompt)]
        + history
        + state.messages
    )

    total_usage = TokenUsage()

    for hop in range(MAX_TOOL_HOPS):
        await emit.emit(
            RuntimeEventType.LLM_REQUEST,
            agent_id=agent.id,
            payload={"model": agent.model_name, "messages": len(messages)},
        )

        response = await llm.complete(
            provider=agent.model_provider,
            model=agent.model_name,
            messages=messages,
            temperature=agent.temperature,
            tools=tools.descriptors_for(agent.tools_config),
        )
        total_usage += response.usage

        await emit.emit(
            RuntimeEventType.LLM_RESPONSE,
            agent_id=agent.id,
            payload={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        )

        if not response.tool_calls:
            await memory_loader.save(agent.id, state, response.message)
            return response.message, total_usage

        for call in response.tool_calls:
            await emit.emit(
                RuntimeEventType.TOOL_STARTED,
                agent_id=agent.id,
                payload={"tool": call.name, "input": call.arguments},
            )
            result = await tools.execute(call.name, call.arguments)
            await emit.emit(
                RuntimeEventType.TOOL_COMPLETED,
                agent_id=agent.id,
                payload={"tool": call.name, "output": result},
            )
            messages.append(Message(role="tool", content=str(result), tool_call_id=call.id))

    raise RuntimeError(f"agent {agent.id} exceeded MAX_TOOL_HOPS")
```

### Why this shape

- All side effects (LLM call, tool exec, memory write) flow through dedicated services — the executor itself is orchestration, not implementation
- The tool loop is bounded by `MAX_TOOL_HOPS` so a misbehaving agent can't burn budget forever
- Every observable thing emits an event, so the UI sees a faithful timeline

### Agent-to-agent communication

A handoff is just a node transition in the workflow. The "to-agent" gets its turn next; its input is the previous agent's last message (plus any state the workflow keeps). Persist each step into the `agent_messages` table with `from_agent_id` / `to_agent_id` so the UI can render the conversation.

```python
# inside a transition / message node
await messages_repo.create(
    run_id=state.run_id,
    from_agent_id=current_agent_id,
    to_agent_id=next_agent_id,
    role="assistant",
    content=last_message.content,
    metadata={"node_id": node_id},
)
```

### Memory hooks

`MemoryLoader.load` returns prior messages based on `agent.memory_config` (window, summarization, vector recall — keep it simple: a sliding window of last N messages is fine for the assignment). `save` appends the new exchange.

### Guardrails

`agent.guardrails_config` is checked *before* the LLM call (input filters) and *after* the response (output filters). Keep it as a thin layer in the executor; if a guardrail trips, emit `node.failed` and stop.

### Bad — executor imports `httpx` directly

```python
# ❌ Skips the LLM provider abstraction
async def run_agent_turn(...):
    async with httpx.AsyncClient() as client:
        await client.post("https://api.openai.com/...", ...)
```

### Bad — unbounded tool loop

```python
# ❌ Will loop forever on a buggy agent
while response.tool_calls:
    ...
```

### Bad — executor writing directly to Redis / DB

```python
# ❌ Mixes orchestration with persistence; events lose ordering guarantees
await redis.publish(...)
```

Use the `EventEmitter` (see [[runtime-event-emission]]).

### Rules

- One executor function: `run_agent_turn(agent, state, emit, *, llm, tools, memory_loader)`
- All I/O goes through services (`LLMService`, `ToolService`, `MemoryLoader`)
- Tool loop bounded by `MAX_TOOL_HOPS`
- Memory hooks called before LLM (`load`) and after final response (`save`)
- Guardrails run before the LLM call and after the response
- Inter-agent messages persisted into `agent_messages`

See: [[runtime-workflow-compiler]], [[runtime-event-emission]], [[llm-provider-abstraction]], [[tool-registry-interface]]
