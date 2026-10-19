import { Navigate, Outlet } from "react-router";

import { useCurrentUser } from "../hooks/useAuth.ts";

/** RequireAuth'un içinde kullanılır; iş arayan işveren sayfalarına giremez. */
export function RequireStaff() {
  const { data: user } = useCurrentUser();
  if (user?.role === "seeker") {
    return <Navigate to="/cv-checks" replace />;
  }
  return <Outlet />;
}
