import { createBrowserRouter, Navigate, type RouteObject } from "react-router";

import { LoginPage } from "./pages/LoginPage.tsx";

// Korumalı rotalar ve /jobs ana sayfası Aşama 1–2'de eklenir; şimdilik her yol girişe yönlenir.
export const routes: RouteObject[] = [
  { path: "/login", element: <LoginPage /> },
  { path: "*", element: <Navigate to="/login" replace /> },
];

export const router = createBrowserRouter(routes);
