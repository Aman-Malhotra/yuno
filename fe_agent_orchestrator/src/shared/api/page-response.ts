import { z } from "zod";

/**
 * Matches the backend's generic `PageResponse[T]` shape:
 *   { items: T[], total: number, page: number, page_size: number }
 *
 * Use the factory to build a typed schema for any item type without
 * re-spelling the wrapper.
 */
export function pageResponseSchema<T>(itemSchema: z.ZodType<T>) {
  return z.object({
    items: z.array(itemSchema),
    total: z.number(),
    page: z.number(),
    page_size: z.number(),
  });
}

export type PageResponse<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};
