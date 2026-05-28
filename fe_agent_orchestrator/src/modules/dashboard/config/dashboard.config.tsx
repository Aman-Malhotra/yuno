import type { IconComponent } from "@/shared/ui";

/**
 * Top-nav tab config. Empty for now — the landing page itself (workspaces
 * grid) is the only navigation surface. Add tabs back here as the product
 * grows and they're actually needed.
 */
export type DashboardNavTab = {
  to: string;
  label: string;
  icon: IconComponent;
};

export const dashboardNav: DashboardNavTab[] = [];
