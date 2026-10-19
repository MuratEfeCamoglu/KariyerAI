import { Navigate } from "react-router";

import { useCurrentUser } from "../hooks/useAuth.ts";
import { homePathFor } from "../lib/constants.ts";

/** Bilinmeyen adres: oturum varsa rolün ana sayfasına, yoksa girişe. */
export function HomeRedirect() {
  const { data: user, isPending } = useCurrentUser();
  if (isPending) {
    return null;
  }
  return <Navigate to={user ? homePathFor(user.role) : "/login"} replace />;
}
