import type { WorkspaceId } from "@/entities/workspace";

/** mem0's row id for a single long-term memory. Opaque string from backend. */
export type MemoryId = string & { readonly __brand: "MemoryId" };

export interface MemoryEntry {
  id: MemoryId;
  memory: string;
  userId?: string;
  agentId?: string;
  metadata: Record<string, unknown>;
  /** Cosine similarity when returned from `search`. Undefined for `list`. */
  score?: number;
  categories: string[];
  createdAt?: string;
  updatedAt?: string;
}

export interface MemoryListResponse {
  items: MemoryEntry[];
  total: number;
}

export interface MemoryGraphNode {
  id: string;
  label: string;
  type?: string;
}

export interface MemoryGraphEdge {
  source: string;
  target: string;
  label: string;
}

export interface MemoryGraph {
  nodes: MemoryGraphNode[];
  edges: MemoryGraphEdge[];
}

export interface MemoryListParams {
  workspaceId: WorkspaceId;
  /** Channel-side stable id — Telegram numeric user id for the demo bot. */
  userId: string;
  username?: string;
  limit?: number;
}

export interface MemoryGraphParams {
  workspaceId: WorkspaceId;
  userId: string;
}
