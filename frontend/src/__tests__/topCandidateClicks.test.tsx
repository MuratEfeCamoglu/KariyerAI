import { fireEvent, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { jsonResponse, mockApi, recruiterUser, renderRoute } from "./testUtils.tsx";

const job = {
  id: 4,
  title: "Backend Geliştirici",
  department: "",
  description: "",
  required_skills: ["Python"],
  preferred_skills: [],
  min_experience_years: 0,
  min_education: "none",
  languages: [],
  status: "open",
  created_by: 2,
  created_at: "2026-10-15T09:00:00Z",
  updated_at: "2026-10-15T09:00:00Z",
  application_count: 2,
  top_score: 91,
  avg_score: 70,
};

const row = (id: number, name: string, score: number) => ({
  id,
  candidate_id: id,
  candidate_name: name,
  score,
  item_points: null,
  last_position: null,
  total_experience_years: null,
  status: "new",
  parse_status: "done",
  parse_error: null,
  score_status: "done",
  score_error: null,
  created_at: "2026-10-15T09:30:00Z",
});

describe("B4: en yüksek puanlı adaya en fazla 3 tıklama", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("giriş → ilanlar → ilan → ilk sıradaki aday", async () => {
    let loggedIn = false;
    mockApi((method, path) => {
      if (path === "/auth/me") {
        return loggedIn ? jsonResponse(200, recruiterUser) : jsonResponse(401, { detail: "x" });
      }
      if (method === "POST" && path === "/auth/login") {
        loggedIn = true;
        return jsonResponse(200, recruiterUser);
      }
      if (path === "/jobs") return jsonResponse(200, [job]);
      if (path === "/jobs/4") return jsonResponse(200, job);
      if (path.startsWith("/jobs/4/applications")) {
        return jsonResponse(200, {
          items: [row(21, "En İyi Aday", 91), row(22, "İkinci Aday", 49)],
          total: 2,
          page: 1,
          page_size: 50,
          processing_count: 0,
        });
      }
      return undefined;
    });
    const router = renderRoute("/login");
    fireEvent.change(await screen.findByLabelText("E-posta"), {
      target: { value: "ik@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Şifre"), { target: { value: "sifre-12345" } });
    fireEvent.click(screen.getByRole("button", { name: "Giriş yap" }));

    // Giriş sonrası ilanlar sayfası açılır; tıklama sayımı buradan başlar.
    let clicks = 0;
    fireEvent.click(await screen.findByRole("link", { name: "Backend Geliştirici" }));
    clicks += 1;
    const [first] = await screen.findAllByRole("link", { name: /Aday$/ });
    expect(first).toHaveTextContent("En İyi Aday");
    fireEvent.click(first as HTMLElement);
    clicks += 1;

    expect(router.state.location.pathname).toBe("/applications/21");
    expect(clicks).toBeLessThanOrEqual(3);
  });
});
