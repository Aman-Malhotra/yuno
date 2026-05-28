import { lazy, Suspense } from "react";

const RouterDevtools = import.meta.env.DEV
  ? lazy(() =>
      import("@tanstack/router-devtools").then((m) => ({
        default: m.TanStackRouterDevtools,
      })),
    )
  : null;

export function DevTools() {
  if (!RouterDevtools) return null;
  return (
    <Suspense fallback={null}>
      <RouterDevtools position="bottom-right" />
    </Suspense>
  );
}
