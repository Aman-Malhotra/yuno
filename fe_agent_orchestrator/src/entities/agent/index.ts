export type {
  AgentId,
  AgentStatus,
  AgentSummary,
  AgentDetail,
  CreateAgentInput,
  UpdateAgentInput,
  ProviderCredentialsInput,
  AgentCapabilities,
  ProviderCapability,
  ModelCatalogEntry,
  ProviderConfigField,
  FieldSpec,
  ToolCapability,
  ToolEntryShape,
  ProviderCredentialsShape,
} from "./model/agent.types";
export {
  agentStatusSchema,
  agentSummaryWireSchema,
  agentDetailWireSchema,
  agentCapabilitiesWireSchema,
  toAgentSummary,
  toAgentDetail,
  toAgentCapabilities,
} from "./model/agent.schema";
export { agentApi } from "./api/agent.service";
export {
  useAgentsInWorkspace,
  useAgent,
  useAgentCapabilities,
  useAgentCapabilitiesForWorkspace,
  useCreateAgent,
  useUpdateAgent,
  agentQueryKeys,
} from "./api/agent.queries";
export { AgentCard } from "./ui/AgentCard";
