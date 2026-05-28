import { z } from "zod";
import type {
  MemoryEntry,
  MemoryGraph,
  MemoryGraphEdge,
  MemoryGraphNode,
  MemoryId,
  MemoryListResponse,
} from "./memory.types";

const memoryIdSchema = z
  .string()
  .min(1)
  .transform((s) => s as MemoryId);

export const memoryEntryWireSchema = z.object({
  id: memoryIdSchema,
  memory: z.string(),
  user_id: z.string().nullable().optional(),
  agent_id: z.string().nullable().optional(),
  hash: z.string().nullable().optional(),
  metadata: z.record(z.string(), z.unknown()).default({}),
  score: z.number().nullable().optional(),
  categories: z.array(z.string()).default([]),
  created_at: z.string().nullable().optional(),
  updated_at: z.string().nullable().optional(),
});

export const memoryListResponseWireSchema = z.object({
  items: z.array(memoryEntryWireSchema),
  total: z.number(),
});

export const memoryGraphNodeWireSchema = z.object({
  id: z.string(),
  label: z.string(),
  type: z.string().nullable().optional(),
});

export const memoryGraphEdgeWireSchema = z.object({
  source: z.string(),
  target: z.string(),
  label: z.string(),
});

export const memoryGraphWireSchema = z.object({
  nodes: z.array(memoryGraphNodeWireSchema),
  edges: z.array(memoryGraphEdgeWireSchema),
});

export function toMemoryEntry(w: z.infer<typeof memoryEntryWireSchema>): MemoryEntry {
  return {
    id: w.id,
    memory: w.memory,
    userId: w.user_id ?? undefined,
    agentId: w.agent_id ?? undefined,
    metadata: w.metadata ?? {},
    score: w.score ?? undefined,
    categories: w.categories ?? [],
    createdAt: w.created_at ?? undefined,
    updatedAt: w.updated_at ?? undefined,
  };
}

export function toMemoryList(w: z.infer<typeof memoryListResponseWireSchema>): MemoryListResponse {
  return {
    items: w.items.map(toMemoryEntry),
    total: w.total,
  };
}

export function toMemoryGraphNode(w: z.infer<typeof memoryGraphNodeWireSchema>): MemoryGraphNode {
  return { id: w.id, label: w.label, type: w.type ?? undefined };
}

export function toMemoryGraphEdge(w: z.infer<typeof memoryGraphEdgeWireSchema>): MemoryGraphEdge {
  return { source: w.source, target: w.target, label: w.label };
}

export function toMemoryGraph(w: z.infer<typeof memoryGraphWireSchema>): MemoryGraph {
  return {
    nodes: w.nodes.map(toMemoryGraphNode),
    edges: w.edges.map(toMemoryGraphEdge),
  };
}
