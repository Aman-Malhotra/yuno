import { z } from "zod";

import { ApiService } from "@/shared/api";
import type { WorkspaceId } from "@/entities/workspace";

import {
  toWorkspaceCredentialSummary,
  workspaceCredentialListWireSchema,
  workspaceCredentialWireSchema,
} from "../model/workspace-llm-provider.schema";
import type {
  CreateWorkspaceCredentialInput,
  UpdateWorkspaceCredentialInput,
  WorkspaceCredentialId,
  WorkspaceCredentialSummary,
} from "../model/workspace-llm-provider.types";

/**
 * Workspace-scoped LLM provider credentials — shared default keys every
 * agent in the workspace can inherit. Backend mounts these at
 * `/workspaces/{ws}/llm-providers/`.
 *
 * The raw `api_key` never leaves the backend — list/detail responses
 * surface only `last4` so the UI can disambiguate without leaking secrets.
 */
class WorkspaceLlmProviderService extends ApiService {
  constructor() {
    super("/workspaces");
  }

  list = async (workspaceId: WorkspaceId): Promise<WorkspaceCredentialSummary[]> => {
    const wire = await this._get(
      `/${workspaceId}/llm-providers/`,
      workspaceCredentialListWireSchema,
    );
    return wire.items.map(toWorkspaceCredentialSummary);
  };

  create = async (
    workspaceId: WorkspaceId,
    input: CreateWorkspaceCredentialInput,
  ): Promise<WorkspaceCredentialSummary> => {
    const wire = await this._post(
      `/${workspaceId}/llm-providers/`,
      {
        provider: input.provider,
        api_key: input.apiKey,
        base_url: input.baseUrl,
        organization: input.organization,
      },
      workspaceCredentialWireSchema,
    );
    return toWorkspaceCredentialSummary(wire);
  };

  update = async (
    workspaceId: WorkspaceId,
    credentialId: WorkspaceCredentialId,
    input: UpdateWorkspaceCredentialInput,
  ): Promise<WorkspaceCredentialSummary> => {
    const body: Record<string, unknown> = {};
    if (input.apiKey !== undefined) body.api_key = input.apiKey;
    if (input.baseUrl !== undefined) body.base_url = input.baseUrl;
    if (input.organization !== undefined) body.organization = input.organization;
    const wire = await this._patch(
      `/${workspaceId}/llm-providers/${credentialId}`,
      body,
      workspaceCredentialWireSchema,
    );
    return toWorkspaceCredentialSummary(wire);
  };

  delete = async (
    workspaceId: WorkspaceId,
    credentialId: WorkspaceCredentialId,
  ): Promise<void> => {
    await this._delete(`/${workspaceId}/llm-providers/${credentialId}`, z.unknown());
  };
}

export const workspaceLlmProviderApi = new WorkspaceLlmProviderService();
