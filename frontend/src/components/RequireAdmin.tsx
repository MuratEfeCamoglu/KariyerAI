import { Navigate, Outlet } from "react-router";

import { useCurrentUser } from "../hooks/useAuth.ts";

/** RequireAuth'un içinde kullanılır; admin olmayanı ana sayfaya yönlendirir (ISKELET §3.2). */
export function RequireAdmin() {
  const { data: user } = useCurrentUser();
  if (user?.role !== "admin") {
    return <Navigate to="/jobs" replace />;
  }
  return <Outlet />;
}
