import { Outlet } from "react-router";

import { useCurrentUser } from "../hooks/useAuth.ts";
import { Sidebar } from "./Sidebar.tsx";

export function AppLayout() {
  const { data: user } = useCurrentUser();
  // RequireAuth bu bileşeni yalnızca oturum varken render eder.
  if (!user) {
    return null;
  }

  return (
    <div className="flex min-h-screen bg-canvas">
      <Sidebar user={user} />
      <main className="min-w-0 flex-1">
        <div className="mx-auto max-w-[1280px] px-10 py-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
