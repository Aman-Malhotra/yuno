import { z } from "zod";

import { ApiService } from "@/shared/api";
import type { WorkspaceId } from "@/entities/workspace";

import {
  memoryGraphWireSchema,
  memoryListResponseWireSchema,
  toMemoryGraph,
  toMemoryList,
} from "../model/memory.schema";
import type {
  MemoryGraph,
  MemoryGraphParams,
  MemoryId,
  MemoryListParams,
  MemoryListResponse,
} from "../model/memory.types";

class MemoryService extends ApiService {
  constructor() {
    super("/workspaces");
  }

  /** GET /workspaces/{ws}/memories?user_id=...&username=...&limit=... */
  list = async ({
    workspaceId,
    userId,
    username,
    limit = 100,
  }: MemoryListParams): Promise<MemoryListResponse> => {
    const q = new URLSearchParams();
    q.set("user_id", userId);
    if (username) q.set("username", username);
    q.set("limit", String(limit));
    const wire = await this._get(`/${workspaceId}/memories/?${q.toString()}`, memoryListResponseWireSchema);
    return toMemoryList(wire);
  };

  /** GET /workspaces/{ws}/memories/graph?user_id=... */
  graph = async ({ workspaceId, userId }: MemoryGraphParams): Promise<MemoryGraph> => {
    const q = new URLSearchParams();
    q.set("user_id", userId);
    const wire = await this._get(`/${workspaceId}/memories/graph?${q.toString()}`, memoryGraphWireSchema);
    return toMemoryGraph(wire);
  };

  /** DELETE /workspaces/{ws}/memories/{id} → 204. */
  delete = async (workspaceId: WorkspaceId, memoryId: MemoryId): Promise<void> => {
    await this._delete(`/${workspaceId}/memories/${memoryId}`, z.unknown());
  };
}

export const memoryApi = new MemoryService();
