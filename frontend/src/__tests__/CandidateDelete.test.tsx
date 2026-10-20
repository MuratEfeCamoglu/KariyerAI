import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import { RouteError } from "../components/RouteError.tsx";
import type { User } from "../types/user.ts";
import { adminUser, jsonResponse, mockApi, recruiterUser, renderRoute } from "./testUtils.tsx";

const detail = {
  id: 7,
  job: { id: 4, title: "Backend Geliştirici", status: "open" },
  candidate: {
    id: 11,
    full_name: "Deniz Arslan",
    email: null,
    phone: null,
    original_filename: "cv.pdf",
    parse_status: "done",
    parse_error: null,
    parsed: null,
  },
  status: "new",
  score: 60,
  score_breakdown: null,
  ai_summary: null,
  llm_model: null,
  prompt_version: null,
  score_status: "done",
  score_error: null,
  created_at: "2026-10-15T09:00:00Z",
  updated_at: "2026-10-15T09:00:00Z",
  notes: [],
  status_history: [],
};

function mockAs(user: User) {
  return mockApi((method, path) => {
    if (path === "/auth/me") return jsonResponse(200, user);
    if (path === "/users") return jsonResponse(200, []);
    if (path === "/applications/7") return jsonResponse(200, detail);
    if (method === "DELETE" && path === "/candidates/11")
      return new Response(null, { status: 204 });
    if (path === "/jobs/4") {
      return jsonResponse(200, {
        ...detail.job,
        department: "",
        description: "",
        required_skills: ["Python"],
        preferred_skills: [],
        min_experience_years: 0,
        min_education: "none",
        languages: [],
        created_by: 1,
        created_at: detail.created_at,
        updated_at: detail.updated_at,
        application_count: 0,
        top_score: null,
        avg_score: null,
      });
    }
    if (path.startsWith("/jobs/4/applications")) {
      return jsonResponse(200, {
        items: [],
        total: 0,
        page: 1,
        page_size: 50,
        processing_count: 0,
      });
    }
    return undefined;
  });
}

describe("F11: aday silme", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("İK uzmanı, aday numarasını yazınca kalıcı olarak siler ve ilana döner", async () => {
    const fetchMock = mockAs(recruiterUser);
    const router = renderRoute("/applications/7");

    fireEvent.click(await screen.findByRole("button", { name: "Adayı sil (KVKK)" }));
    const dialog = screen.getByRole("dialog", { name: "Aday verisini kalıcı olarak sil" });
    const confirm = within(dialog).getByRole("button", { name: "Kalıcı olarak sil" });
    expect(confirm).toBeDisabled();

    fireEvent.change(within(dialog).getByLabelText(/aday numarasını yazın/), {
      target: { value: "12" },
    });
    expect(confirm).toBeDisabled();
    fireEvent.change(within(dialog).getByLabelText(/aday numarasını yazın/), {
      target: { value: "11" },
    });
    expect(confirm).toBeEnabled();
    fireEvent.click(confirm);

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/jobs/4");
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/candidates/11",
      expect.objectContaining({ method: "DELETE" }),
    );
  });

  it("admin başvuru sayfasına giremez, kullanıcılara yönlenir", async () => {
    mockAs(adminUser);
    const router = renderRoute("/applications/7");

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/users");
    });
    expect(screen.queryByRole("button", { name: "Adayı sil (KVKK)" })).not.toBeInTheDocument();
  });
});

describe("RouteError", () => {
  it("beklenmeyen hatada boş ekran yerine mesaj gösterir", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    function Broken(): never {
      throw new Error("bozuk bileşen");
    }
    const router = createMemoryRouter([
      { path: "/", element: <Broken />, errorElement: <RouteError /> },
    ]);

    render(<RouterProvider router={router} />);

    expect(
      await screen.findByRole("heading", { name: "Beklenmeyen bir hata oluştu" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "İlanlara dön" })).toHaveAttribute("href", "/jobs");
    vi.restoreAllMocks();
  });
});
