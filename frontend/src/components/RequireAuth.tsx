import { LoaderCircle } from "lucide-react";
import { Navigate, Outlet, useLocation } from "react-router";

import { useCurrentUser } from "../hooks/useAuth.ts";

export function RequireAuth() {
  const { data: user, isPending, isError } = useCurrentUser();
  const location = useLocation();

  if (isPending) {
    return (
      <div className="flex min-h-screen items-center justify-center" role="status">
        <LoaderCircle size={24} strokeWidth={1.75} className="animate-spin text-ink-subtle" />
        <span className="sr-only">Yükleniyor</span>
      </div>
    );
  }
  if (isError) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-ink-muted">
        Sunucuya ulaşılamadı. Lütfen sayfayı yenileyin.
      </div>
    );
  }
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <Outlet />;
}
