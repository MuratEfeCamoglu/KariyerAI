import { Navigate, Outlet } from "react-router";

import { useCurrentUser } from "../hooks/useAuth.ts";
import { homePathFor } from "../lib/constants.ts";

/** RequireAuth'un içinde kullanılır; işveren sayfaları yalnızca İK uzmanınındır (admin ve iş arayan yönlenir). */
export function RequireRecruiter() {
  const { data: user } = useCurrentUser();
  if (user && user.role !== "recruiter") {
    return <Navigate to={homePathFor(user.role)} replace />;
  }
  return <Outlet />;
}
