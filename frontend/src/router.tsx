import { createBrowserRouter, Navigate, type RouteObject } from "react-router";

import { AppLayout } from "./components/AppLayout.tsx";
import { RouteError } from "./components/RouteError.tsx";
import { RequireAdmin } from "./components/RequireAdmin.tsx";
import { RequireAuth } from "./components/RequireAuth.tsx";
import { ApplicationDetailPage } from "./pages/ApplicationDetailPage.tsx";
import { AuditPage } from "./pages/AuditPage.tsx";
import { JobDetailPage } from "./pages/JobDetailPage.tsx";
import { JobFormPage } from "./pages/JobFormPage.tsx";
import { JobsPage } from "./pages/JobsPage.tsx";
import { LoginPage } from "./pages/LoginPage.tsx";
import { UsersPage } from "./pages/UsersPage.tsx";

export const routes: RouteObject[] = [
  {
    // Beklenmeyen hatada boş ekran yerine anlaşılır mesaj.
    errorElement: <RouteError />,
    children: [
      { path: "/login", element: <LoginPage /> },
      {
        element: <RequireAuth />,
        children: [
          {
            element: <AppLayout />,
            children: [
              { path: "/jobs", element: <JobsPage /> },
              { path: "/jobs/new", element: <JobFormPage /> },
              { path: "/jobs/:id", element: <JobDetailPage /> },
              { path: "/jobs/:id/edit", element: <JobFormPage /> },
              { path: "/applications/:id", element: <ApplicationDetailPage /> },
              {
                element: <RequireAdmin />,
                children: [
                  { path: "/users", element: <UsersPage /> },
                  { path: "/audit", element: <AuditPage /> },
                ],
              },
            ],
          },
        ],
      },
      { path: "*", element: <Navigate to="/jobs" replace /> },
    ],
  },
];

export const router = createBrowserRouter(routes);
