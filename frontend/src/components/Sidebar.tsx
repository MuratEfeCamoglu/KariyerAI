import { Briefcase, FileSearch, LogOut, ScrollText, Users, type LucideIcon } from "lucide-react";
import { NavLink, useNavigate } from "react-router";

import { useLogout } from "../hooks/useAuth.ts";
import { useUsers } from "../hooks/useUsers.ts";
import { ROLE_LABELS } from "../lib/constants.ts";
import type { User, UserRole } from "../types/user.ts";

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  roles: UserRole[];
}

const NAV_ITEMS: NavItem[] = [
  { to: "/jobs", label: "İlanlar", icon: Briefcase, roles: ["recruiter"] },
  { to: "/users", label: "Kullanıcılar", icon: Users, roles: ["admin"] },
  { to: "/audit", label: "Denetim", icon: ScrollText, roles: ["admin"] },
  { to: "/cv-checks", label: "CV Değerlendirmelerim", icon: FileSearch, roles: ["seeker"] },
];

interface SidebarProps {
  user: User;
}

export function Sidebar({ user }: SidebarProps) {
  const logout = useLogout();
  const navigate = useNavigate();
  // Onay kuyruğu rozeti yalnızca admin içindir; diğer roller /users'ı çağırmaz (403).
  const users = useUsers({ enabled: user.role === "admin" });
  const pendingCount = users.data?.filter((item) => !item.is_approved).length ?? 0;
  const items = NAV_ITEMS.filter((item) => item.roles.includes(user.role));

  const handleLogout = () => {
    logout.mutate(undefined, {
      onSettled: () => {
        void navigate("/login", { replace: true });
      },
    });
  };

  return (
    <aside className="sticky top-0 flex h-screen w-18 shrink-0 flex-col border-r border-line bg-surface xl:w-62">
      <div className="flex h-16 items-center px-4 xl:px-6">
        <span className="text-lg font-semibold text-brand-700">
          <span className="xl:hidden">K</span>
          <span className="hidden xl:inline">KariyerAI</span>
        </span>
      </div>

      <nav aria-label="Ana menü" className="flex-1 space-y-1 px-3">
        {items.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            title={label}
            className={({ isActive }) =>
              `flex h-10 items-center gap-3 rounded-md px-3 text-sm font-medium focus-visible:outline-2 focus-visible:outline-accent-500 ${isActive ? "bg-brand-50 text-brand-700" : "text-ink-muted hover:bg-fill-muted hover:text-ink"}`
            }
          >
            <Icon size={20} strokeWidth={1.75} aria-hidden="true" />
            <span className="hidden xl:inline">{label}</span>
            {to === "/users" && pendingCount > 0 && (
              <span
                aria-label={`${String(pendingCount)} onay bekleyen`}
                className="ml-auto rounded-full bg-accent-500 px-2 py-0.5 text-xs font-medium text-white"
              >
                {pendingCount}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-line p-3">
        <div className="mb-2 hidden px-3 xl:block">
          <p className="truncate text-sm font-medium text-ink">{user.full_name}</p>
          <span className="mt-1 inline-block rounded-full bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700">
            {ROLE_LABELS[user.role]}
          </span>
        </div>
        <button
          type="button"
          onClick={handleLogout}
          aria-label="Çıkış yap"
          className="flex h-10 w-full items-center gap-3 rounded-md px-3 text-sm font-medium text-ink-muted hover:bg-fill-muted hover:text-ink focus-visible:outline-2 focus-visible:outline-accent-500"
        >
          <LogOut size={20} strokeWidth={1.75} aria-hidden="true" />
          <span className="hidden xl:inline">Çıkış</span>
        </button>
      </div>
    </aside>
  );
}
