import { Navigate, Outlet } from "react-router";

import { useCurrentUser } from "../hooks/useAuth.ts";
import { homePathFor } from "../lib/constants.ts";

/** RequireAuth'un içinde kullanılır; admin olmayanı rolünün ana sayfasına yönlendirir. */
export function RequireAdmin() {
  const { data: user } = useCurrentUser();
  if (user && user.role !== "admin") {
    return <Navigate to={homePathFor(user.role)} replace />;
  }
  return <Outlet />;
}
