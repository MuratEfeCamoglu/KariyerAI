import { createBrowserRouter, type RouteObject } from "react-router";

import { AppLayout } from "./components/AppLayout.tsx";
import { HomeRedirect } from "./components/HomeRedirect.tsx";
import { RouteError } from "./components/RouteError.tsx";
import { RequireAdmin } from "./components/RequireAdmin.tsx";
import { RequireAuth } from "./components/RequireAuth.tsx";
import { RequireSeeker } from "./components/RequireSeeker.tsx";
import { RequireStaff } from "./components/RequireStaff.tsx";
import { ApplicationDetailPage } from "./pages/ApplicationDetailPage.tsx";
import { AuditPage } from "./pages/AuditPage.tsx";
import { CvCheckDetailPage } from "./pages/CvCheckDetailPage.tsx";
import { CvCheckFormPage } from "./pages/CvCheckFormPage.tsx";
import { CvChecksPage } from "./pages/CvChecksPage.tsx";
import { JobDetailPage } from "./pages/JobDetailPage.tsx";
import { JobFormPage } from "./pages/JobFormPage.tsx";
import { JobsPage } from "./pages/JobsPage.tsx";
import { LoginPage } from "./pages/LoginPage.tsx";
import { RegisterPage } from "./pages/RegisterPage.tsx";
import { UsersPage } from "./pages/UsersPage.tsx";

export const routes: RouteObject[] = [
  {
    // Beklenmeyen hatada boş ekran yerine anlaşılır mesaj.
    errorElement: <RouteError />,
    children: [
      { path: "/login", element: <LoginPage /> },
      { path: "/register", element: <RegisterPage /> },
      {
        element: <RequireAuth />,
        children: [
          {
            element: <AppLayout />,
            children: [
              {
                element: <RequireStaff />,
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
              {
                element: <RequireSeeker />,
                children: [
                  { path: "/cv-checks", element: <CvChecksPage /> },
                  { path: "/cv-checks/new", element: <CvCheckFormPage /> },
                  { path: "/cv-checks/:id", element: <CvCheckDetailPage /> },
                ],
              },
            ],
          },
        ],
      },
      { path: "*", element: <HomeRedirect /> },
    ],
  },
];

export const router = createBrowserRouter(routes);
