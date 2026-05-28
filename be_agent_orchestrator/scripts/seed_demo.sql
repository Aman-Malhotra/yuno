-- =============================================================================
-- Demo seed for the "Yuno" workspace — Support Triage + Research Assistant
-- =============================================================================
-- Wipes this workspace's agents/tools/workflows, then seeds the exact set the
-- two demo workflows need:
--
--   Workflow 1: Customer Support Ticket Triage + Resolution   (5 agents, 7 tools)
--   Workflow 2: Conversational Research Assistant (Telegram)  (3 agents, 2 tools)
--
-- The "wipe" only touches THIS workspace; global builtins (workspace_id NULL)
-- and other workspaces are untouched.
--
-- Idempotent: `ON CONFLICT (workspace_id, slug) DO NOTHING` on every insert;
-- the wipe step makes a clean re-run safe.
--
-- Run with:
--   docker exec -i be_agent_orchestrator-postgres-1 \
--     psql -U agent -d agent_orchestrator -p 3002 < scripts/seed_demo.sql
-- =============================================================================

\set ws_id  '''09ed8091-8cb0-4cc1-a76a-4cd559154fbf'''
\set usr_id '''5e86f665-abf9-4a28-96ce-b485d36cac69'''
-- Agents no longer carry BYOK keys at seed time. All LLM keys live on
-- ``workspace_llm_credentials`` and are resolved at run time. To seed a
-- key for this workspace, INSERT into that table separately (or use the
-- LLM Providers UI). Per-agent BYOK is still supported via the agent
-- edit form — just opt-in instead of default.

BEGIN;

-- ──────────────────────────────────────────────────────────────────────
-- Wipe existing agents + tools + workflows in this workspace. Cascades
-- take care of agent_tools, tool_versions, tool_executions,
-- tool_execution_logs, tool_approvals, agent_versions, workflow_versions,
-- workflow_runs, workflow_webhooks, workflow_run_nodes, runtime_events.
-- ──────────────────────────────────────────────────────────────────────
DELETE FROM workflows WHERE workspace_id = :ws_id;
DELETE FROM agents    WHERE workspace_id = :ws_id;
DELETE FROM tools     WHERE workspace_id = :ws_id;


-- =============================================================================
-- TOOLS (9 total)
--   Support (7): create-ticket, update-ticket-status, get-customer,
--                get-payment-status, get-refund-policy, request-human-approval,
--                ask-agent
--   Real    (2): web-search (Tavily), telegram-send (Bot API)
-- =============================================================================

-- ── create-ticket ─────────────────────────────────────────────────────
INSERT INTO tools (
  workspace_id, name, slug, description, type, category, icon, status, version,
  input_schema, output_schema, config,
  auth_type, auth_config, guardrails, execution_policy, channel_config, created_by
) VALUES (
  :ws_id, 'Create Ticket', 'create-ticket',
  'Open a new support ticket from an inbound user message. Returns a ticket_id that the rest of the workflow keys off. Call once after parsing the user''s message.',
  'builtin', 'support', 'ticket', 'active', 1,
  -- customer_identifier is nullable + optional: a user might message the bot
  -- without ever giving their email/order id. Strict `string`-only + required
  -- causes Groq's server-side schema validator to reject the tool call with
  -- `tool_use_failed` (it returns 400 before we ever see the result).
  $j${"type":"object","properties":{"intent":{"type":"string"},"priority":{"type":"string","enum":["low","medium","high"]},"customer_identifier":{"type":["string","null"]},"channel":{"type":"string","enum":["slack","telegram","web","whatsapp"]},"summary":{"type":"string"}},"required":["intent"]}$j$::jsonb,
  $j${"type":"object","properties":{"success":{"type":"boolean"},"data":{"type":"object"},"error":{"type":"string"}}}$j$::jsonb,
  $j${"handler":"create_ticket","options":{}}$j$::jsonb,
  'none', '{}'::jsonb, $j${"requires_human_approval":false}$j$::jsonb,
  $j${"timeout_ms":3000}$j$::jsonb, $j${"workflow_only":false}$j$::jsonb, :usr_id
) ON CONFLICT (workspace_id, slug) DO NOTHING;

-- ── update-ticket-status ──────────────────────────────────────────────
INSERT INTO tools (
  workspace_id, name, slug, description, type, category, icon, status, version,
  input_schema, output_schema, config,
  auth_type, auth_config, guardrails, execution_policy, channel_config, created_by
) VALUES (
  :ws_id, 'Update Ticket Status', 'update-ticket-status',
  'Patch a ticket — set status (triaged/enriched/pending_approval/resolved), category (billing/technical/refund/account/escalation), priority, enrichment dict, or final response. Used after every agent hop.',
  'builtin', 'support', 'edit', 'active', 1,
  $j${"type":"object","properties":{"ticket_id":{"type":"string"},"status":{"type":"string","enum":["open","triaged","enriched","pending_approval","resolved","rejected"]},"category":{"type":"string","enum":["billing","technical","refund","account","escalation"]},"priority":{"type":"string","enum":["low","medium","high"]},"enrichment":{"type":"object"},"response":{"type":"string"}},"required":["ticket_id"]}$j$::jsonb,
  $j${"type":"object","properties":{"success":{"type":"boolean"},"data":{"type":"object"},"error":{"type":"string"}}}$j$::jsonb,
  $j${"handler":"update_ticket_status","options":{}}$j$::jsonb,
  'none', '{}'::jsonb, $j${"requires_human_approval":false}$j$::jsonb,
  $j${"timeout_ms":3000}$j$::jsonb, $j${"workflow_only":false}$j$::jsonb, :usr_id
) ON CONFLICT (workspace_id, slug) DO NOTHING;

-- ── get-customer ──────────────────────────────────────────────────────
INSERT INTO tools (
  workspace_id, name, slug, description, type, category, icon, status, version,
  input_schema, output_schema, config,
  auth_type, auth_config, guardrails, execution_policy, channel_config, created_by
) VALUES (
  :ws_id, 'Get Customer', 'get-customer',
  'Look up a customer record by email. Returns name, plan, join date, and customer_id (needed for downstream payment lookups).',
  'builtin', 'support', 'user', 'active', 1,
  $j${"type":"object","properties":{"email":{"type":"string"}},"required":["email"]}$j$::jsonb,
  $j${"type":"object","properties":{"success":{"type":"boolean"},"data":{"type":"object"},"error":{"type":"string"}}}$j$::jsonb,
  $j${"handler":"get_customer","options":{}}$j$::jsonb,
  'none', '{}'::jsonb, $j${"requires_human_approval":false}$j$::jsonb,
  $j${"timeout_ms":3000}$j$::jsonb, $j${"workflow_only":false}$j$::jsonb, :usr_id
) ON CONFLICT (workspace_id, slug) DO NOTHING;

-- ── get-payment-status ────────────────────────────────────────────────
INSERT INTO tools (
  workspace_id, name, slug, description, type, category, icon, status, version,
  input_schema, output_schema, config,
  auth_type, auth_config, guardrails, execution_policy, channel_config, created_by
) VALUES (
  :ws_id, 'Get Payment Status', 'get-payment-status',
  'Get recent payments for a customer. Returns each payment''s id, amount, status (captured/failed/refunded), method, and refund_eligible flag.',
  'builtin', 'support', 'credit-card', 'active', 1,
  $j${"type":"object","properties":{"customer_id":{"type":"string"},"limit":{"type":"integer","default":5,"minimum":1,"maximum":25}},"required":["customer_id"]}$j$::jsonb,
  $j${"type":"object","properties":{"success":{"type":"boolean"},"data":{"type":"object"},"error":{"type":"string"}}}$j$::jsonb,
  $j${"handler":"get_payment_status","options":{}}$j$::jsonb,
  'none', '{}'::jsonb, $j${"requires_human_approval":false}$j$::jsonb,
  $j${"timeout_ms":3000}$j$::jsonb, $j${"workflow_only":false}$j$::jsonb, :usr_id
) ON CONFLICT (workspace_id, slug) DO NOTHING;

-- ── get-refund-policy ─────────────────────────────────────────────────
INSERT INTO tools (
  workspace_id, name, slug, description, type, category, icon, status, version,
  input_schema, output_schema, config,
  auth_type, auth_config, guardrails, execution_policy, channel_config, created_by
) VALUES (
  :ws_id, 'Get Refund Policy', 'get-refund-policy',
  'Return the company refund policy — window, which intents qualify, and which do not. Call before drafting a refund reply so the response stays policy-aligned.',
  'builtin', 'support', 'book', 'active', 1,
  $j${"type":"object","properties":{}}$j$::jsonb,
  $j${"type":"object","properties":{"success":{"type":"boolean"},"data":{"type":"object"},"error":{"type":"string"}}}$j$::jsonb,
  $j${"handler":"get_refund_policy","options":{}}$j$::jsonb,
  'none', '{}'::jsonb, $j${"requires_human_approval":false}$j$::jsonb,
  $j${"timeout_ms":3000}$j$::jsonb, $j${"workflow_only":false}$j$::jsonb, :usr_id
) ON CONFLICT (workspace_id, slug) DO NOTHING;

-- ── request-human-approval ────────────────────────────────────────────
INSERT INTO tools (
  workspace_id, name, slug, description, type, category, icon, status, version,
  input_schema, output_schema, config,
  auth_type, auth_config, guardrails, execution_policy, channel_config, created_by
) VALUES (
  :ws_id, 'Request Human Approval', 'request-human-approval',
  'Open a human-approval request for a sensitive action (refund, destructive update). Returns approval_id; the workflow pauses until an operator decides.',
  'builtin', 'approval', 'shield', 'active', 1,
  $j${"type":"object","properties":{"subject":{"type":"string"},"body":{"type":"string"},"context":{"type":"object"},"channel":{"type":"string","default":"slack"}},"required":["subject","body"]}$j$::jsonb,
  $j${"type":"object","properties":{"success":{"type":"boolean"},"data":{"type":"object"},"error":{"type":"string"}}}$j$::jsonb,
  $j${"handler":"request_human_approval","options":{}}$j$::jsonb,
  'none', '{}'::jsonb, $j${"requires_human_approval":false}$j$::jsonb,
  $j${"timeout_ms":3000}$j$::jsonb, $j${"workflow_only":false}$j$::jsonb, :usr_id
) ON CONFLICT (workspace_id, slug) DO NOTHING;

-- ── ask-agent ─────────────────────────────────────────────────────────
INSERT INTO tools (
  workspace_id, name, slug, description, type, category, icon, status, version,
  input_schema, output_schema, config,
  auth_type, auth_config, guardrails, execution_policy, channel_config, created_by
) VALUES (
  :ws_id, 'Ask Agent', 'ask-agent',
  'Hand off a task to another agent and get its reply. Records the inter-agent message in `agent_messages` and returns the target agent''s response.',
  'builtin', 'orchestration', 'message-circle', 'active', 1,
  $j${"type":"object","properties":{"target_agent_id":{"type":"string"},"task":{"type":"string"},"context":{"type":"object"},"expected_output":{"type":"string"}},"required":["target_agent_id","task"]}$j$::jsonb,
  $j${"type":"object","properties":{"success":{"type":"boolean"},"data":{"type":"object"},"error":{"type":"string"}}}$j$::jsonb,
  $j${"handler":"ask_agent","options":{}}$j$::jsonb,
  'none', '{}'::jsonb, $j${"requires_human_approval":false}$j$::jsonb,
  $j${"timeout_ms":15000}$j$::jsonb, $j${"workflow_only":false}$j$::jsonb, :usr_id
) ON CONFLICT (workspace_id, slug) DO NOTHING;

-- ── web-search (Tavily) ───────────────────────────────────────────────
-- Credentials live on `auth_config` (per-tool BYOK), not in server env.
-- Builtin handler falls back to `settings.tavily_api_key` only if this
-- field is empty, so a tool row with its own key is fully self-contained.
INSERT INTO tools (
  workspace_id, name, slug, description, type, category, icon, status, version,
  input_schema, output_schema, config,
  auth_type, auth_config, guardrails, execution_policy, channel_config, created_by
) VALUES (
  :ws_id, 'Web Search', 'web-search',
  'Search the public web via Tavily. Returns the top results as a list of {title, url, snippet}. Call for current facts, news, or anything outside the model''s training cutoff.',
  'builtin', 'research', 'search', 'active', 1,
  $j${"type":"object","properties":{"query":{"type":"string"},"max_results":{"type":"integer","minimum":1,"maximum":10,"default":5}},"required":["query"]}$j$::jsonb,
  $j${"type":"object","properties":{"success":{"type":"boolean"},"data":{"type":"object"},"error":{"type":"string"}}}$j$::jsonb,
  $j${"handler":"web_search","options":{}}$j$::jsonb,
  'api_key',
  $j${"api_key":""}$j$::jsonb,
  $j${"requires_human_approval":false}$j$::jsonb,
  $j${"timeout_ms":15000}$j$::jsonb, $j${"workflow_only":false}$j$::jsonb, :usr_id
) ON CONFLICT (workspace_id, slug) DO NOTHING;

-- ── telegram-send ─────────────────────────────────────────────────────
-- Bot token lives on `auth_config.bot_token`. Same BYOK-first pattern.
INSERT INTO tools (
  workspace_id, name, slug, description, type, category, icon, status, version,
  input_schema, output_schema, config,
  auth_type, auth_config, guardrails, execution_policy, channel_config, created_by
) VALUES (
  :ws_id, 'Telegram Send', 'telegram-send',
  'Send a Telegram message via the bot. Pass chat_id (from the inbound message) and text. Supports Markdown.',
  'builtin', 'messaging', 'send', 'active', 1,
  $j${"type":"object","properties":{"chat_id":{"type":["string","integer"]},"text":{"type":"string"},"parse_mode":{"type":"string","enum":["Markdown","MarkdownV2","HTML"],"default":"Markdown"}},"required":["chat_id","text"]}$j$::jsonb,
  $j${"type":"object","properties":{"success":{"type":"boolean"},"data":{"type":"object"},"error":{"type":"string"}}}$j$::jsonb,
  $j${"handler":"telegram_send","options":{}}$j$::jsonb,
  'bearer',
  $j${"bot_token":""}$j$::jsonb,
  $j${"requires_human_approval":false}$j$::jsonb,
  $j${"timeout_ms":15000}$j$::jsonb, $j${"telegram":true,"workflow_only":false}$j$::jsonb, :usr_id
) ON CONFLICT (workspace_id, slug) DO NOTHING;


-- =============================================================================
-- AGENTS (8 total) — 5 for Support, 3 for Research Assistant
-- =============================================================================

-- ── W1: Support / Intake ──────────────────────────────────────────────
INSERT INTO agents (
  workspace_id, created_by, name, slug, description, role, system_prompt,
  status, model_provider, model_name, temperature,
  memory_config, schedule_config, guardrails_config, interaction_rules,
  limits_config, skills_config, provider_credentials, metadata
) VALUES (
  :ws_id, :usr_id, 'Intake Agent', 'support-intake-agent',
  'Parses an inbound user message, extracts intent + priority + customer identifier, and opens a ticket.',
  'intake',
  'You are the Intake Agent for customer support. The user message is in state.message. Do three things: (1) classify the user''s intent as a snake_case label (e.g. `payment_failed_money_deducted`, `account_locked`, `refund_request`, `feature_question`); (2) pick a priority of low/medium/high; (3) extract any customer identifier (email or order id) from the message. Then call `create-ticket` exactly once with those fields and channel="telegram". Reply with ONLY a single-line JSON object: {"ticket_id":"...", "intent":"...", "priority":"...", "customer_identifier":"...", "requires_human_approval": false}. Set requires_human_approval=true if the intent is refund_request or priority is high.',
  'active', 'groq', 'llama-3.3-70b-versatile', 0.20,
  $j${"strategy":"none"}$j$::jsonb, '{}'::jsonb,
  $j${"max_tool_hops":3}$j$::jsonb,
  $j${"emits":"ticket.created","handoff_to":"support-triage-agent"}$j$::jsonb,
  $j${"max_input_tokens":2000,"max_output_tokens":400}$j$::jsonb,
  $j${"tools":[{"name":"create-ticket","options":{}}]}$j$::jsonb,
  '{}'::jsonb,                                           -- provider_credentials: empty so agents inherit the workspace-default key
  $j${"seed":true,"workflow":"support_triage","step":1}$j$::jsonb
) ON CONFLICT (workspace_id, slug) DO NOTHING;

-- ── W1: Support / Triage ──────────────────────────────────────────────
INSERT INTO agents (
  workspace_id, created_by, name, slug, description, role, system_prompt,
  status, model_provider, model_name, temperature,
  memory_config, schedule_config, guardrails_config, interaction_rules,
  limits_config, skills_config, provider_credentials, metadata
) VALUES (
  :ws_id, :usr_id, 'Triage Agent', 'support-triage-agent',
  'Categorises a ticket (billing / technical / refund / account) and refines its priority.',
  'triage',
  'You are the Triage Agent. The prior agent''s output is in state.intake. Decide the category (billing/technical/refund/account/escalation) and refine the priority. Call `update-ticket-status` once with {ticket_id, status: "triaged", category, priority}. Reply with ONLY a JSON object: {"ticket_id":"...", "category":"...", "priority":"..."}.',
  'active', 'groq', 'llama-3.3-70b-versatile', 0.20,
  $j${"strategy":"none"}$j$::jsonb, '{}'::jsonb,
  $j${"max_tool_hops":3}$j$::jsonb,
  $j${"emits":"ticket.triaged","handoff_to":"support-data-lookup-agent"}$j$::jsonb,
  $j${"max_input_tokens":2000,"max_output_tokens":400}$j$::jsonb,
  $j${"tools":[{"name":"update-ticket-status","options":{}}]}$j$::jsonb,
  '{}'::jsonb,                                           -- provider_credentials: empty so agents inherit the workspace-default key
  $j${"seed":true,"workflow":"support_triage","step":2}$j$::jsonb
) ON CONFLICT (workspace_id, slug) DO NOTHING;

-- ── W1: Support / Data Lookup ─────────────────────────────────────────
INSERT INTO agents (
  workspace_id, created_by, name, slug, description, role, system_prompt,
  status, model_provider, model_name, temperature,
  memory_config, schedule_config, guardrails_config, interaction_rules,
  limits_config, skills_config, provider_credentials, metadata
) VALUES (
  :ws_id, :usr_id, 'Data Lookup Agent', 'support-data-lookup-agent',
  'Pulls customer + payment + refund-policy data and writes a structured enrichment block to the ticket.',
  'lookup',
  'You are the Data Lookup Agent. Use the customer_identifier from state.intake. Workflow: (1) if it looks like an email, call `get-customer` to get customer_id; (2) call `get-payment-status` with that customer_id; (3) if the intent is refund_request or category is refund/billing, also call `get-refund-policy`. Then call `update-ticket-status` once with {ticket_id, status:"enriched", enrichment: { customer, payments, policy? }}. Reply with ONLY a one-line JSON: {"ticket_id":"...", "enrichment":{...}}.',
  'active', 'groq', 'llama-3.3-70b-versatile', 0.20,
  $j${"strategy":"none"}$j$::jsonb, '{}'::jsonb,
  $j${"max_tool_hops":6}$j$::jsonb,
  $j${"emits":"ticket.enriched","handoff_to":"support-response-agent"}$j$::jsonb,
  $j${"max_input_tokens":3000,"max_output_tokens":600}$j$::jsonb,
  $j${"tools":[{"name":"get-customer","options":{}},{"name":"get-payment-status","options":{}},{"name":"get-refund-policy","options":{}},{"name":"update-ticket-status","options":{}}]}$j$::jsonb,
  '{}'::jsonb,                                           -- provider_credentials: empty so agents inherit the workspace-default key
  $j${"seed":true,"workflow":"support_triage","step":3}$j$::jsonb
) ON CONFLICT (workspace_id, slug) DO NOTHING;

-- ── W1: Support / Response ────────────────────────────────────────────
INSERT INTO agents (
  workspace_id, created_by, name, slug, description, role, system_prompt,
  status, model_provider, model_name, temperature,
  memory_config, schedule_config, guardrails_config, interaction_rules,
  limits_config, skills_config, provider_credentials, metadata
) VALUES (
  :ws_id, :usr_id, 'Response Agent', 'support-response-agent',
  'Drafts the customer-facing reply, grounded in the enrichment block.',
  'response',
  'You are the Response Agent. Read state.lookup.enrichment. Draft a concise, warm, accurate reply to the user. Cite specific facts (payment id, amount, status, policy window). End with one concrete next step. Call `update-ticket-status` once with {ticket_id, status:"pending_approval" if intake.requires_human_approval else "resolved", response: "<your reply>"}. Reply with ONLY a JSON: {"ticket_id":"...", "reply":"...", "requires_human_approval": true/false}.',
  'active', 'groq', 'llama-3.3-70b-versatile', 0.40,
  $j${"strategy":"none"}$j$::jsonb, '{}'::jsonb,
  $j${"max_tool_hops":4}$j$::jsonb,
  $j${"emits":"response.drafted"}$j$::jsonb,
  $j${"max_input_tokens":4000,"max_output_tokens":800}$j$::jsonb,
  $j${"tools":[{"name":"update-ticket-status","options":{}}]}$j$::jsonb,
  '{}'::jsonb,                                           -- provider_credentials: empty so agents inherit the workspace-default key
  $j${"seed":true,"workflow":"support_triage","step":4}$j$::jsonb
) ON CONFLICT (workspace_id, slug) DO NOTHING;

-- ── W1: Support / Human Approval ──────────────────────────────────────
INSERT INTO agents (
  workspace_id, created_by, name, slug, description, role, system_prompt,
  status, model_provider, model_name, temperature,
  memory_config, schedule_config, guardrails_config, interaction_rules,
  limits_config, skills_config, provider_credentials, metadata
) VALUES (
  :ws_id, :usr_id, 'Human Approval Agent', 'support-approval-agent',
  'Opens a human-approval request for the drafted reply when required.',
  'approval',
  'You are the Human Approval Agent. Call `request-human-approval` once with subject="Support reply for ticket <id>", body=state.response.reply, context={ticket_id, intent, priority}. Then call `update-ticket-status` with {ticket_id, status: "resolved"} to close the loop in the demo (in production the workflow would pause here). Reply with ONLY a JSON: {"approval_id":"...", "status":"sent_for_approval"}.',
  'active', 'groq', 'llama-3.3-70b-versatile', 0.20,
  $j${"strategy":"none"}$j$::jsonb, '{}'::jsonb,
  $j${"max_tool_hops":3}$j$::jsonb,
  $j${"emits":"response.approved"}$j$::jsonb,
  $j${"max_input_tokens":2000,"max_output_tokens":300}$j$::jsonb,
  $j${"tools":[{"name":"request-human-approval","options":{}},{"name":"update-ticket-status","options":{}}]}$j$::jsonb,
  '{}'::jsonb,                                           -- provider_credentials: empty so agents inherit the workspace-default key
  $j${"seed":true,"workflow":"support_triage","step":5}$j$::jsonb
) ON CONFLICT (workspace_id, slug) DO NOTHING;


-- ── W2: Research / Router ─────────────────────────────────────────────
INSERT INTO agents (
  workspace_id, created_by, name, slug, description, role, system_prompt,
  status, model_provider, model_name, temperature,
  memory_config, schedule_config, guardrails_config, interaction_rules,
  limits_config, skills_config, provider_credentials, metadata
) VALUES (
  :ws_id, :usr_id, 'Conversation Router', 'research-router-agent',
  'Classifies an inbound Telegram message: small_talk vs research_query.',
  'router',
  'You are the Conversation Router. The user''s Telegram message is in state.message. Decide one of two intents: "small_talk" (greetings, thanks, casual chitchat) or "research_query" (anything that needs current facts or external info). Reply with ONLY a JSON: {"intent":"small_talk"} or {"intent":"research_query","query":"<clean restatement of what to search>"}.',
  'active', 'groq', 'llama-3.3-70b-versatile', 0.10,
  $j${"strategy":"none"}$j$::jsonb, '{}'::jsonb,
  $j${"max_tool_hops":0}$j$::jsonb,
  $j${"emits":"intent.classified"}$j$::jsonb,
  $j${"max_input_tokens":1000,"max_output_tokens":200}$j$::jsonb,
  $j${"tools":[]}$j$::jsonb,
  '{}'::jsonb,                                           -- provider_credentials: empty so agents inherit the workspace-default key
  $j${"seed":true,"workflow":"research_assistant","step":1}$j$::jsonb
) ON CONFLICT (workspace_id, slug) DO NOTHING;

-- ── W2: Research / Web Researcher ─────────────────────────────────────
INSERT INTO agents (
  workspace_id, created_by, name, slug, description, role, system_prompt,
  status, model_provider, model_name, temperature,
  memory_config, schedule_config, guardrails_config, interaction_rules,
  limits_config, skills_config, provider_credentials, metadata
) VALUES (
  :ws_id, :usr_id, 'Web Researcher', 'research-web-agent',
  'Calls web_search to gather grounding for the user''s query and returns the top snippets.',
  'researcher',
  'You are the Web Researcher. The query is at state.router.query (fall back to state.message). Call `web-search` ONCE with that query and max_results=5. Then reply with ONLY a JSON: {"query":"...", "results":[{"title":"...","url":"...","snippet":"..."}, ...]}. Do not summarise here — the next agent does that.',
  'active', 'groq', 'llama-3.3-70b-versatile', 0.10,
  $j${"strategy":"none"}$j$::jsonb, '{}'::jsonb,
  $j${"max_tool_hops":3}$j$::jsonb,
  $j${"emits":"research.gathered"}$j$::jsonb,
  $j${"max_input_tokens":1500,"max_output_tokens":1200}$j$::jsonb,
  $j${"tools":[{"name":"web-search","options":{}}]}$j$::jsonb,
  '{}'::jsonb,                                           -- provider_credentials: empty so agents inherit the workspace-default key
  $j${"seed":true,"workflow":"research_assistant","step":2}$j$::jsonb
) ON CONFLICT (workspace_id, slug) DO NOTHING;

-- ── W2: Research / Reply Composer ─────────────────────────────────────
INSERT INTO agents (
  workspace_id, created_by, name, slug, description, role, system_prompt,
  status, model_provider, model_name, temperature,
  memory_config, schedule_config, guardrails_config, interaction_rules,
  limits_config, skills_config, provider_credentials, metadata
) VALUES (
  :ws_id, :usr_id, 'Reply Composer', 'research-composer-agent',
  'Writes the final reply (with citations when research was used) and sends it back to the user via Telegram.',
  'composer',
  'You are the Reply Composer for a Telegram bot. Read the user message, intent, and (optionally) research results from the user prompt below. Write a SHORT reply (≤ 4 sentences). For small_talk, be friendly and conversational. For research_query, ground the answer in the research snippets and append up to 3 markdown citations of the form " ([title](url))" at the end. Then call the `telegram-send` tool to deliver the reply: pass `chat_id` (the integer the user prompt gives you) and `text` (your composed reply). Do NOT inline a `<function=…>` block — use the tool call API. After the tool returns successfully, respond with the single word OK.',
  'active', 'groq', 'llama-3.3-70b-versatile', 0.40,
  $j${"strategy":"none"}$j$::jsonb, '{}'::jsonb,
  $j${"max_tool_hops":4}$j$::jsonb,
  $j${"emits":"reply.sent"}$j$::jsonb,
  $j${"max_input_tokens":4000,"max_output_tokens":600}$j$::jsonb,
  $j${"tools":[{"name":"telegram-send","options":{}}]}$j$::jsonb,
  '{}'::jsonb,                                           -- provider_credentials: empty so agents inherit the workspace-default key
  $j${"seed":true,"workflow":"research_assistant","step":3}$j$::jsonb
) ON CONFLICT (workspace_id, slug) DO NOTHING;


-- =============================================================================
-- WORKFLOW 1 — Customer Support Ticket Triage & Resolution
-- =============================================================================

WITH ids AS (
  SELECT
    (SELECT id FROM agents WHERE workspace_id = :ws_id AND slug = 'support-intake-agent')      AS sup_intake,
    (SELECT id FROM agents WHERE workspace_id = :ws_id AND slug = 'support-triage-agent')      AS sup_triage,
    (SELECT id FROM agents WHERE workspace_id = :ws_id AND slug = 'support-data-lookup-agent') AS sup_lookup,
    (SELECT id FROM agents WHERE workspace_id = :ws_id AND slug = 'support-response-agent')    AS sup_response,
    (SELECT id FROM agents WHERE workspace_id = :ws_id AND slug = 'support-approval-agent')    AS sup_approval
)
INSERT INTO workflows (
  workspace_id, created_by, name, slug, description, status,
  graph_json, compiled_graph, settings, metadata
)
SELECT
  :ws_id, :usr_id,
  'Customer Support Ticket Triage & Resolution',
  'support-triage-resolution',
  'Inbound user message → Intake → Triage → Data Lookup (real CRM + payment + policy tools) → Response draft → conditional Human Approval. Each agent calls real tools; the final state carries the full audit trail.',
  'published',
  jsonb_build_object(
    'nodes', jsonb_build_array(
      jsonb_build_object('id','start','type','start',
        'position', jsonb_build_object('x',60,'y',240),
        'data', jsonb_build_object('label','Inbound message',
          'config', jsonb_build_object('trigger','webhook'))),
      jsonb_build_object('id','intake','type','agent',
        'position', jsonb_build_object('x',260,'y',240),
        'data', jsonb_build_object('label','Intake Agent',
          'config', jsonb_build_object(
            'agentId', ids.sup_intake::text,
            'emits','ticket.created',
            'input', E'Inbound user message (parse this and call create-ticket once):\n\n{{message}}'))),
      jsonb_build_object('id','triage','type','agent',
        'position', jsonb_build_object('x',460,'y',240),
        'data', jsonb_build_object('label','Triage Agent',
          'config', jsonb_build_object(
            'agentId', ids.sup_triage::text,
            'emits','ticket.triaged',
            -- ALL placeholders below are pre-substituted from prior state
            -- before the agent sees this prompt — the model receives real
            -- values, not literal "state.foo" strings.
            'input', E'Ticket to triage (use these EXACT values; do not invent placeholders):\n\nticket_id: {{intake.ticket_id}}\nintent: {{intake.intent}}\npriority: {{intake.priority}}\ncustomer_identifier: {{intake.customer_identifier}}\n\nOriginal user message:\n{{message}}'))),
      jsonb_build_object('id','lookup','type','agent',
        'position', jsonb_build_object('x',660,'y',240),
        'data', jsonb_build_object('label','Data Lookup Agent',
          'config', jsonb_build_object(
            'agentId', ids.sup_lookup::text,
            'emits','ticket.enriched',
            'input', E'Enrichment task (use these EXACT values; do not invent placeholders):\n\nticket_id: {{intake.ticket_id}}\nintent: {{intake.intent}}\ncategory: {{triage.category}}\ncustomer_identifier: {{intake.customer_identifier}}\n\nIf the customer_identifier looks like an email, call get-customer first to obtain customer_id, then call get-payment-status. If category is refund or billing, also call get-refund-policy. Then call update-ticket-status with status=enriched and the gathered enrichment object.'))),
      jsonb_build_object('id','response','type','agent',
        'position', jsonb_build_object('x',860,'y',240),
        'data', jsonb_build_object('label','Response Agent',
          'config', jsonb_build_object(
            'agentId', ids.sup_response::text,
            'emits','response.drafted',
            'input', E'Compose the customer-facing reply for ticket {{intake.ticket_id}}.\n\nintent: {{intake.intent}}\npriority: {{intake.priority}}\ncategory: {{triage.category}}\nenrichment summary: {{lookup.content}}\n\nOriginal user message:\n{{message}}\n\nCall update-ticket-status once with the final reply, then respond with the JSON object specified in your system prompt — substitute the real ticket_id ({{intake.ticket_id}}) into the response.'))),
      jsonb_build_object('id','cond_approval','type','condition',
        'position', jsonb_build_object('x',1080,'y',240),
        'data', jsonb_build_object('label','Needs approval?',
          'config', jsonb_build_object('expression','state.response.requires_human_approval == true',
                                       'path','response.requires_human_approval'))),
      jsonb_build_object('id','approval','type','agent',
        'position', jsonb_build_object('x',1300,'y',120),
        'data', jsonb_build_object('label','Human Approval Agent',
          'config', jsonb_build_object(
            'agentId', ids.sup_approval::text,
            'emits','response.approved',
            'input', E'Open a human-approval request for ticket {{intake.ticket_id}}.\n\nDrafted reply:\n{{response.reply}}\n\nThen call update-ticket-status with status=resolved.'))),
      jsonb_build_object('id','end','type','end',
        'position', jsonb_build_object('x',1500,'y',240),
        'data', jsonb_build_object('label','Done'))
    ),
    'edges', jsonb_build_array(
      jsonb_build_object('id','e_start_intake','source','start','target','intake'),
      jsonb_build_object('id','e_intake_triage','source','intake','target','triage','label','ticket.created'),
      jsonb_build_object('id','e_triage_lookup','source','triage','target','lookup','label','ticket.triaged'),
      jsonb_build_object('id','e_lookup_response','source','lookup','target','response','label','ticket.enriched'),
      jsonb_build_object('id','e_response_cond','source','response','target','cond_approval','label','response.drafted'),
      jsonb_build_object('id','e_cond_yes','source','cond_approval','target','approval','label','yes',
        'condition', jsonb_build_object('kind','equals','path','response.requires_human_approval','value', true)),
      jsonb_build_object('id','e_cond_no','source','cond_approval','target','end','label','auto',
        'condition', jsonb_build_object('kind','equals','path','response.requires_human_approval','value', false)),
      jsonb_build_object('id','e_approval_end','source','approval','target','end','label','response.approved')
    ),
    'viewport', jsonb_build_object('x',0,'y',0,'zoom',0.85)
  ),
  '{}'::jsonb,
  jsonb_build_object('trigger_channels', jsonb_build_array('webhook'), 'auto_run_on_message', false),
  jsonb_build_object('seed', true, 'template', 'support_triage_resolution')
FROM ids
ON CONFLICT (workspace_id, slug) DO NOTHING;


-- =============================================================================
-- WORKFLOW 2 — Conversational Research Assistant (Telegram)
-- =============================================================================
-- Telegram message in → Router classifies → branch:
--   small_talk    → Composer (no research) → telegram-send
--   research_query → Researcher (web_search) → Composer → telegram-send
-- =============================================================================

WITH ids AS (
  SELECT
    (SELECT id FROM agents WHERE workspace_id = :ws_id AND slug = 'research-router-agent')   AS r_router,
    (SELECT id FROM agents WHERE workspace_id = :ws_id AND slug = 'research-web-agent')      AS r_research,
    (SELECT id FROM agents WHERE workspace_id = :ws_id AND slug = 'research-composer-agent') AS r_composer
)
INSERT INTO workflows (
  workspace_id, created_by, name, slug, description, status,
  graph_json, compiled_graph, settings, metadata
)
SELECT
  :ws_id, :usr_id,
  'Conversational Research Assistant',
  'research-assistant-telegram',
  'A Telegram bot you can chat with. Casual messages get an immediate reply; questions that need facts route through a Web Researcher (Tavily) before the Composer replies with cited sources.',
  'published',
  jsonb_build_object(
    'nodes', jsonb_build_array(
      jsonb_build_object('id','start','type','start',
        'position', jsonb_build_object('x',60,'y',220),
        'data', jsonb_build_object('label','Telegram message',
          'config', jsonb_build_object('trigger','telegram'))),
      jsonb_build_object('id','router','type','agent',
        'position', jsonb_build_object('x',280,'y',220),
        'data', jsonb_build_object('label','Conversation Router',
          'config', jsonb_build_object('agentId', ids.r_router::text, 'emits','intent.classified'))),
      jsonb_build_object('id','cond_intent','type','condition',
        'position', jsonb_build_object('x',500,'y',220),
        'data', jsonb_build_object('label','Needs research?',
          'config', jsonb_build_object('expression','state.router.intent == ''research_query''',
                                       'path','router.intent'))),
      jsonb_build_object('id','researcher','type','agent',
        'position', jsonb_build_object('x',720,'y',100),
        'data', jsonb_build_object('label','Web Researcher',
          'config', jsonb_build_object(
            'agentId', ids.r_research::text,
            'emits','research.gathered',
            'input', E'Search query (run web-search exactly once with this): {{router.query}}\n\nIf the query is empty, fall back to the original user message: {{message}}'))),
      jsonb_build_object('id','composer','type','agent',
        'position', jsonb_build_object('x',960,'y',220),
        'data', jsonb_build_object('label','Reply Composer',
          'config', jsonb_build_object(
            'agentId', ids.r_composer::text,
            'emits','reply.sent',
            -- Hand the composer everything it needs in one structured block.
            -- chat_id is surfaced explicitly so the model passes the integer
            -- value (not a literal "state.chat_id" string) into the
            -- telegram-send tool call.
            'input', E'Telegram chat_id (pass this exact integer to telegram-send): {{chat_id}}\n\nUser intent: {{router.intent}}\n\nOriginal user message:\n{{message}}\n\nResearch snippets (only present for research_query intent):\n{{researcher.content}}'))),
      jsonb_build_object('id','end','type','end',
        'position', jsonb_build_object('x',1180,'y',220),
        'data', jsonb_build_object('label','Done'))
    ),
    'edges', jsonb_build_array(
      jsonb_build_object('id','e_start_router','source','start','target','router'),
      jsonb_build_object('id','e_router_cond','source','router','target','cond_intent','label','intent.classified'),
      jsonb_build_object('id','e_cond_research','source','cond_intent','target','researcher','label','research',
        'condition', jsonb_build_object('kind','equals','path','router.intent','value','research_query')),
      jsonb_build_object('id','e_cond_small_talk','source','cond_intent','target','composer','label','small_talk',
        'condition', jsonb_build_object('kind','equals','path','router.intent','value','small_talk')),
      jsonb_build_object('id','e_research_composer','source','researcher','target','composer','label','research.gathered'),
      jsonb_build_object('id','e_composer_end','source','composer','target','end','label','reply.sent')
    ),
    'viewport', jsonb_build_object('x',0,'y',0,'zoom',0.9)
  ),
  '{}'::jsonb,
  jsonb_build_object('trigger_channels', jsonb_build_array('telegram'), 'auto_run_on_message', true),
  jsonb_build_object('seed', true, 'template', 'research_assistant_telegram')
FROM ids
ON CONFLICT (workspace_id, slug) DO NOTHING;


COMMIT;
