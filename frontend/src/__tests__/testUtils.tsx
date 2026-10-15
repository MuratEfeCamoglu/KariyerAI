import { QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { vi } from "vitest";

import { createQueryClient } from "../lib/queryClient.ts";
import { routes } from "../router.tsx";
import type { User } from "../types/user.ts";

export const adminUser: User = {
  id: 1,
  email: "admin@example.com",
  full_name: "Ayşe Yönetici",
  role: "admin",
  is_active: true,
  created_at: "2026-10-15T10:00:00Z",
};

export const recruiterUser: User = {
  id: 2,
  email: "ik@example.com",
  full_name: "Mehmet Uzman",
  role: "recruiter",
  is_active: true,
  created_at: "2026-10-15T10:00:00Z",
};

export function jsonResponse(status: number, body?: unknown): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

type Handler = (method: string, path: string, body: unknown) => Response | undefined;

/** `fetch`'i taklit eder; eşleşmeyen istek testin hatalı olduğunu gösterir (404 + uyarı). */
export function mockApi(handler: Handler) {
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    const method = init?.method ?? "GET";
    const body: unknown = typeof init?.body === "string" ? JSON.parse(init.body) : undefined;
    const response = handler(method, url.replace(/^\/api/, ""), body);
    return Promise.resolve(response ?? jsonResponse(404, { detail: `mock yok: ${method} ${url}` }));
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

export function renderRoute(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  const queryClient = createQueryClient();
  queryClient.setDefaultOptions({ queries: { retry: false } });
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return router;
}
