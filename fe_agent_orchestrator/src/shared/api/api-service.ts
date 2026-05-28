import type { z } from "zod";
import { httpRequest } from "./http-client";

/**
 * Base class for typed API service classes (industry-standard pattern,
 * similar to Angular HttpClient services or NestJS service classes on the
 * backend).
 *
 * Subclasses declare a resource path (e.g. `/agents`) and call the protected
 * `_get` / `_post` / `_patch` / `_put` / `_delete` helpers with sub-paths
 * relative to that resource. The absolute URL is always built from
 * `env.API_BASE_URL` (single source — see `src/app/config/env.ts`) — services
 * and consumers never hard-code hosts.
 *
 * The leading underscore on helpers marks them as internal transport methods
 * and lets subclasses expose CRUD verbs (`list`, `create`, `update`, `delete`
 * etc.) without naming collisions.
 *
 * Every response is validated through a Zod schema so the boundary is
 * type-safe and changes to the backend contract fail loudly at the call site
 * rather than corrupting downstream UI.
 *
 * Example:
 *   class AgentService extends ApiService {
 *     constructor() { super("/agents"); }
 *     list = () => this._get("", agentListSchema);
 *     getById = (id: AgentId) => this._get(`/${id}`, agentSchema);
 *     create = (input: CreateAgentInput) => this._post("", input, agentSchema);
 *     delete = (id: AgentId) => this._delete(`/${id}`, z.void());
 *   }
 *   export const agentApi = new AgentService();
 */
export abstract class ApiService {
  protected constructor(protected readonly resourcePath: string) {
    if (!resourcePath.startsWith("/")) {
      throw new Error(`ApiService resourcePath must start with "/", got: ${resourcePath}`);
    }
  }

  private buildPath(subPath: string): string {
    if (subPath.length > 0 && !subPath.startsWith("/") && !subPath.startsWith("?")) {
      return `${this.resourcePath}/${subPath}`;
    }
    return `${this.resourcePath}${subPath}`;
  }

  protected _get<T>(subPath: string, schema: z.ZodType<T>, init?: RequestInit): Promise<T> {
    return httpRequest(this.buildPath(subPath), schema, { ...init, method: "GET" });
  }

  protected _post<T>(subPath: string, body: unknown, schema: z.ZodType<T>, init?: RequestInit): Promise<T> {
    return httpRequest(this.buildPath(subPath), schema, {
      ...init,
      method: "POST",
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  }

  protected _patch<T>(subPath: string, body: unknown, schema: z.ZodType<T>, init?: RequestInit): Promise<T> {
    return httpRequest(this.buildPath(subPath), schema, {
      ...init,
      method: "PATCH",
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  }

  protected _put<T>(subPath: string, body: unknown, schema: z.ZodType<T>, init?: RequestInit): Promise<T> {
    return httpRequest(this.buildPath(subPath), schema, {
      ...init,
      method: "PUT",
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  }

  protected _delete<T>(subPath: string, schema: z.ZodType<T>, init?: RequestInit): Promise<T> {
    return httpRequest(this.buildPath(subPath), schema, { ...init, method: "DELETE" });
  }
}
