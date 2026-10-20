import { Navigate, Outlet } from "react-router";

import { useCurrentUser } from "../hooks/useAuth.ts";

/** RequireAuth'un içinde kullanılır; işveren kullanıcıları iş arayan sayfalarına giremez. */
export function RequireSeeker() {
  const { data: user } = useCurrentUser();
  if (user?.role !== "seeker") {
    return <Navigate to="/jobs" replace />;
  }
  return <Outlet />;
}
