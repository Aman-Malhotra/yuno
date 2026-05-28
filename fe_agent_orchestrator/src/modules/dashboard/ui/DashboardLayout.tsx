import type { ReactNode } from "react";
import { useAuth } from "@/app/auth";
import { TopNav, UserChip } from "@/shared/ui";
import { dashboardNav } from "../config/dashboard.config";

export function DashboardLayout({ children }: { children: ReactNode }) {
  const { user } = useAuth();

  return (
    <div className="flex min-h-screen flex-col">
      <TopNav tabs={dashboardNav} right={user ? <UserChip user={user} /> : null} />
      <main className="flex-1">{children}</main>
    </div>
  );
}
