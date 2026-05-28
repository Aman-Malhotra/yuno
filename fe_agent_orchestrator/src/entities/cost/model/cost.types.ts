import type { AgentId } from "@/entities/agent";

export interface AgentCostRow {
  agentId: AgentId;
  name: string;
  slug: string;
  modelProvider: string;
  modelName: string;
  inputTokens: number;
  outputTokens: number;
  totalTokens: number;
  runCount: number;
  lastSeenAt?: string;
}

export interface CostsSummary {
  items: AgentCostRow[];
  totalInputTokens: number;
  totalOutputTokens: number;
  totalTokens: number;
}
