import { ApiService } from "@/shared/api";
import type { WorkspaceId } from "@/entities/workspace";

import { costsResponseWireSchema, toCostsSummary } from "../model/cost.schema";
import type { CostsSummary } from "../model/cost.types";

class CostService extends ApiService {
  constructor() {
    super("/workspaces");
  }

  /** GET /workspaces/{ws}/costs/agents?since=... */
  perAgent = async (workspaceId: WorkspaceId, since?: string): Promise<CostsSummary> => {
    const qs = since ? `?since=${encodeURIComponent(since)}` : "";
    const wire = await this._get(`/${workspaceId}/costs/agents${qs}`, costsResponseWireSchema);
    return toCostsSummary(wire);
  };
}

export const costApi = new CostService();
