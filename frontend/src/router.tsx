import { createBrowserRouter, Navigate, type RouteObject } from "react-router";

import { AppLayout } from "./components/AppLayout.tsx";
import { RequireAdmin } from "./components/RequireAdmin.tsx";
import { RequireAuth } from "./components/RequireAuth.tsx";
import { JobsPage } from "./pages/JobsPage.tsx";
import { LoginPage } from "./pages/LoginPage.tsx";
import { UsersPage } from "./pages/UsersPage.tsx";

export const routes: RouteObject[] = [
  { path: "/login", element: <LoginPage /> },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <AppLayout />,
        children: [
          { path: "/jobs", element: <JobsPage /> },
          {
            element: <RequireAdmin />,
            children: [{ path: "/users", element: <UsersPage /> }],
          },
        ],
      },
    ],
  },
  { path: "*", element: <Navigate to="/jobs" replace /> },
];

export const router = createBrowserRouter(routes);
