import { createRootRoute, createRoute, createRouter, Outlet, redirect } from "@tanstack/react-router";

import { getAccessToken } from "@/app/auth";

import { DashboardPage } from "@/modules/dashboard";
import { LoginPage } from "@/modules/login";
import { ProfilePage } from "@/modules/profile";
import {
  WorkspaceAgentCreatePage,
  WorkspaceAgentDetailPage,
  WorkspaceAgentEditPage,
  WorkspaceAgentsPage,
  WorkspaceCostsPage,
  WorkspaceLayout,
  WorkspaceLLMProvidersPage,
  WorkspaceLogsPage,
  WorkspaceMemoriesPage,
  WorkspaceSettingsPage,
  WorkspaceToolCreatePage,
  WorkspaceToolDetailPage,
  WorkspaceToolEditPage,
  WorkspaceToolsPage,
  WorkspaceWorkflowCreatePage,
  WorkspaceWorkflowDetailPage,
  WorkspaceWorkflowSettingsPage,
  WorkspaceWorkflowsPage,
} from "@/modules/workspace";

import { DevTools } from "./DevTools";
import { ProtectedLayout } from "./ProtectedLayout";

const rootRoute = createRootRoute({
  component: () => (
    <>
      <Outlet />
      <DevTools />
    </>
  ),
});

/* ─── Public ──────────────────────────────────────────────────────── */

const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/login",
  validateSearch: (search: Record<string, unknown>) => ({
    redirect: typeof search.redirect === "string" ? search.redirect : undefined,
  }),
  beforeLoad: () => {
    if (getAccessToken()) {
      throw redirect({ to: "/" });
    }
  },
  component: LoginPage,
});

/* ─── Protected shell — guard + dashboard top-nav for non-workspace pages ─── */

const protectedLayoutRoute = createRoute({
  getParentRoute: () => rootRoute,
  id: "protected",
  beforeLoad: ({ location }) => {
    if (!getAccessToken()) {
      throw redirect({
        to: "/login",
        search: { redirect: location.href },
      });
    }
  },
  component: ProtectedLayout,
});

const dashboardRoute = createRoute({
  getParentRoute: () => protectedLayoutRoute,
  path: "/",
  component: DashboardPage,
});

const profileRoute = createRoute({
  getParentRoute: () => protectedLayoutRoute,
  path: "/profile",
  component: ProfilePage,
});

/* ─── Workspace shell — left side panel + nested sub-routes ──────── */

const workspaceLayoutRoute = createRoute({
  getParentRoute: () => protectedLayoutRoute,
  path: "/workspaces/$workspaceId",
  component: WorkspaceLayout,
});

const workspaceIndexRoute = createRoute({
  getParentRoute: () => workspaceLayoutRoute,
  path: "/",
  component: WorkspaceWorkflowsPage,
});

const workspaceWorkflowsTabRoute = createRoute({
  getParentRoute: () => workspaceLayoutRoute,
  path: "/workflows",
  component: WorkspaceWorkflowsPage,
});

const workspaceWorkflowCreateRoute = createRoute({
  getParentRoute: () => workspaceLayoutRoute,
  path: "/workflows/new",
  component: WorkspaceWorkflowCreatePage,
});

const workspaceWorkflowDetailRoute = createRoute({
  getParentRoute: () => workspaceLayoutRoute,
  path: "/workflows/$workflowId",
  component: WorkspaceWorkflowDetailPage,
});

const workspaceWorkflowSettingsRoute = createRoute({
  getParentRoute: () => workspaceLayoutRoute,
  path: "/workflows/$workflowId/settings",
  component: WorkspaceWorkflowSettingsPage,
});

const workspaceAgentsTabRoute = createRoute({
  getParentRoute: () => workspaceLayoutRoute,
  path: "/agents",
  component: WorkspaceAgentsPage,
});

const workspaceAgentCreateRoute = createRoute({
  getParentRoute: () => workspaceLayoutRoute,
  path: "/agents/new",
  component: WorkspaceAgentCreatePage,
});

const workspaceAgentDetailRoute = createRoute({
  getParentRoute: () => workspaceLayoutRoute,
  path: "/agents/$agentId",
  component: WorkspaceAgentDetailPage,
});

const workspaceAgentEditRoute = createRoute({
  getParentRoute: () => workspaceLayoutRoute,
  path: "/agents/$agentId/edit",
  component: WorkspaceAgentEditPage,
});

const workspaceToolsTabRoute = createRoute({
  getParentRoute: () => workspaceLayoutRoute,
  path: "/tools",
  component: WorkspaceToolsPage,
});

const workspaceToolCreateRoute = createRoute({
  getParentRoute: () => workspaceLayoutRoute,
  path: "/tools/new",
  component: WorkspaceToolCreatePage,
});

const workspaceToolDetailRoute = createRoute({
  getParentRoute: () => workspaceLayoutRoute,
  path: "/tools/$toolId",
  component: WorkspaceToolDetailPage,
});

const workspaceToolEditRoute = createRoute({
  getParentRoute: () => workspaceLayoutRoute,
  path: "/tools/$toolId/edit",
  component: WorkspaceToolEditPage,
});

const workspaceLogsTabRoute = createRoute({
  getParentRoute: () => workspaceLayoutRoute,
  path: "/logs",
  component: WorkspaceLogsPage,
  validateSearch: (search: Record<string, unknown>) => ({
    workflowId: typeof search.workflowId === "string" ? search.workflowId : undefined,
  }),
});

const workspaceMemoriesTabRoute = createRoute({
  getParentRoute: () => workspaceLayoutRoute,
  path: "/memories",
  component: WorkspaceMemoriesPage,
});

const workspaceLlmProvidersTabRoute = createRoute({
  getParentRoute: () => workspaceLayoutRoute,
  path: "/llm-providers",
  component: WorkspaceLLMProvidersPage,
});

const workspaceCostsTabRoute = createRoute({
  getParentRoute: () => workspaceLayoutRoute,
  path: "/costs",
  component: WorkspaceCostsPage,
});

const workspaceSettingsTabRoute = createRoute({
  getParentRoute: () => workspaceLayoutRoute,
  path: "/settings",
  component: WorkspaceSettingsPage,
});

const routeTree = rootRoute.addChildren([
  loginRoute,
  protectedLayoutRoute.addChildren([
    dashboardRoute,
    profileRoute,
    workspaceLayoutRoute.addChildren([
      workspaceIndexRoute,
      workspaceWorkflowsTabRoute,
      workspaceWorkflowCreateRoute,
      workspaceWorkflowDetailRoute,
      workspaceWorkflowSettingsRoute,
      workspaceAgentsTabRoute,
      workspaceAgentCreateRoute,
      workspaceAgentDetailRoute,
      workspaceAgentEditRoute,
      workspaceToolsTabRoute,
      workspaceToolCreateRoute,
      workspaceToolDetailRoute,
      workspaceToolEditRoute,
      workspaceLogsTabRoute,
      workspaceMemoriesTabRoute,
      workspaceLlmProvidersTabRoute,
      workspaceCostsTabRoute,
      workspaceSettingsTabRoute,
    ]),
  ]),
]);

export const router = createRouter({ routeTree });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
