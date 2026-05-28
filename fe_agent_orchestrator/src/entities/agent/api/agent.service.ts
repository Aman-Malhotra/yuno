import { ApiService, httpRequest, pageResponseSchema, type PageResponse } from "@/shared/api";
import type { WorkspaceId } from "@/entities/workspace";
import {
  agentCapabilitiesWireSchema,
  agentDetailWireSchema,
  agentSummaryWireSchema,
  toAgentCapabilities,
  toAgentDetail,
  toAgentSummary,
} from "../model/agent.schema";
import type {
  AgentCapabilities,
  AgentDetail,
  AgentId,
  AgentSummary,
  CreateAgentInput,
  UpdateAgentInput,
} from "../model/agent.types";

type ListParams = { page?: number; pageSize?: number };

class AgentService extends ApiService {
  constructor() {
    super("/workspaces");
  }

  /** GET /api/v1/workspaces/{ws}/agents/ */
  listInWorkspace = async (workspaceId: WorkspaceId, params: ListParams = {}): Promise<PageResponse<AgentSummary>> => {
    const q = new URLSearchParams();
    if (params.page) q.set("page", String(params.page));
    if (params.pageSize) q.set("page_size", String(params.pageSize));
    const qs = q.toString();
    const wire = await this._get(
      `/${workspaceId}/agents/${qs ? `?${qs}` : ""}`,
      pageResponseSchema(agentSummaryWireSchema),
    );
    return { ...wire, items: wire.items.map(toAgentSummary) };
  };

  /** POST /api/v1/workspaces/{ws}/agents/ */
  create = async (workspaceId: WorkspaceId, input: CreateAgentInput): Promise<AgentDetail> => {
    // Build skills_config.tools from the selected slugs per ToolEntryShape.
    // Backend treats this blob as opaque, but the shape we use here matches
    // what the runtime expects when resolving tool calls.
    const skillsConfig =
      input.toolSlugs && input.toolSlugs.length > 0
        ? { tools: input.toolSlugs.map((slug) => ({ name: slug, options: {} })) }
        : undefined;

    const body = {
      name: input.name,
      role: input.role,
      system_prompt: input.systemPrompt,
      model_provider: input.modelProvider,
      model_name: input.modelName,
      description: input.description,
      temperature: input.temperature,
      max_tokens: input.maxTokens,
      top_p: input.topP,
      skills_config: skillsConfig,
      memory_config: input.memoryConfig,
      schedule_config: input.scheduleConfig,
      guardrails_config: input.guardrailsConfig,
      interaction_rules: input.interactionRules,
      limits_config: input.limitsConfig,
      provider_credentials: input.providerCredentials
        ? {
            api_key: input.providerCredentials.apiKey,
            base_url: input.providerCredentials.baseUrl,
            organization: input.providerCredentials.organization,
          }
        : undefined,
    };
    const wire = await this._post(`/${workspaceId}/agents/`, body, agentDetailWireSchema);
    return toAgentDetail(wire);
  };

  /** GET /api/v1/workspaces/{ws}/agents/{id} */
  getById = async (workspaceId: WorkspaceId, agentId: AgentId): Promise<AgentDetail> => {
    const wire = await this._get(`/${workspaceId}/agents/${agentId}`, agentDetailWireSchema);
    return toAgentDetail(wire);
  };

  /**
   * PATCH /api/v1/workspaces/{ws}/agents/{id} — partial update.
   *
   * NOTE: as of this commit, `PATCH /agents/{id}` isn't published in
   * openapi.yaml (only GET + POST list). Frontend is wired against the
   * assumed shape — fields are optional, body mirrors CreateAgentRequest.
   * When backend ships the endpoint, just verify the response schema; no
   * UI changes needed.
   */
  update = async (workspaceId: WorkspaceId, agentId: AgentId, input: UpdateAgentInput): Promise<AgentDetail> => {
    const body: Record<string, unknown> = {};
    if (input.name !== undefined) body.name = input.name;
    if (input.role !== undefined) body.role = input.role;
    if (input.systemPrompt !== undefined) body.system_prompt = input.systemPrompt;
    if (input.modelProvider !== undefined) body.model_provider = input.modelProvider;
    if (input.modelName !== undefined) body.model_name = input.modelName;
    if (input.description !== undefined) body.description = input.description;
    if (input.temperature !== undefined) body.temperature = input.temperature;
    if (input.maxTokens !== undefined) body.max_tokens = input.maxTokens;
    if (input.topP !== undefined) body.top_p = input.topP;
    if (input.toolSlugs !== undefined) {
      body.skills_config = {
        tools: input.toolSlugs.map((slug) => ({ name: slug, options: {} })),
      };
    }
    if (input.memoryConfig !== undefined) body.memory_config = input.memoryConfig;
    if (input.scheduleConfig !== undefined) body.schedule_config = input.scheduleConfig;
    if (input.guardrailsConfig !== undefined) body.guardrails_config = input.guardrailsConfig;
    if (input.interactionRules !== undefined) body.interaction_rules = input.interactionRules;
    if (input.limitsConfig !== undefined) body.limits_config = input.limitsConfig;
    if (input.providerCredentials) {
      body.provider_credentials = {
        api_key: input.providerCredentials.apiKey,
        base_url: input.providerCredentials.baseUrl,
        organization: input.providerCredentials.organization,
      };
    }
    const wire = await this._patch(`/${workspaceId}/agents/${agentId}`, body, agentDetailWireSchema);
    return toAgentDetail(wire);
  };

  /**
   * GET /api/v1/agents/capabilities — global (not workspace-scoped), so it
   * skips the service's base path and goes straight through `httpRequest`.
   * Powers the "Create agent" form UI.
   */
  getCapabilities = async (): Promise<AgentCapabilities> => {
    const wire = await httpRequest("/agents/capabilities", agentCapabilitiesWireSchema);
    return toAgentCapabilities(wire);
  };

  /**
   * GET /api/v1/workspaces/{ws}/agents/capabilities — same shape as the global
   * endpoint, but `is_configured` flips true when the WORKSPACE has a default
   * credential for the provider (in addition to the user-vault check).
   * The agent-create form should call this so users can see which providers
   * will inherit a key from the workspace.
   */
  getCapabilitiesForWorkspace = async (
    workspaceId: WorkspaceId,
  ): Promise<AgentCapabilities> => {
    const wire = await this._get(
      `/${workspaceId}/agents/capabilities`,
      agentCapabilitiesWireSchema,
    );
    return toAgentCapabilities(wire);
  };
}

export const agentApi = new AgentService();
