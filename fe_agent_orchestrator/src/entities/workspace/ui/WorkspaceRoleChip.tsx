import { Chip } from "@/shared/ui";
import type { WorkspaceRole } from "../model/workspace.types";

const toneByRole: Record<WorkspaceRole, "accent" | "ok" | "warn" | "default"> = {
  owner: "accent",
  admin: "warn",
  member: "ok",
  viewer: "default",
};

export function WorkspaceRoleChip({ role }: { role: WorkspaceRole }) {
  return <Chip tone={toneByRole[role]}>{role}</Chip>;
}
