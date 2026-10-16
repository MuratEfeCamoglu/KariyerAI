import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ApplicationDetail } from "../types/application.ts";
import {
  adminUser,
  jsonResponse,
  mockApi,
  recruiterUser,
  renderRoute,
  requestBody,
} from "./testUtils.tsx";

function detail(overrides: Partial<ApplicationDetail> = {}): ApplicationDetail {
  return {
    id: 7,
    job: { id: 4, title: "Backend Geliştirici", status: "open" },
    candidate: {
      id: 11,
      full_name: "Deniz Arslan",
      email: "deniz@example.com",
      phone: "+90 555 000 11 22",
      original_filename: "deniz.pdf",
      parse_status: "done",
      parse_error: null,
      parsed: {
        full_name: "Deniz Arslan",
        email: "deniz@example.com",
        phone: null,
        summary: "Backend geliştirici.",
        skills: ["Python", "FastAPI"],
        experiences: [
          {
            title: "Backend Developer",
            company: "Örnek A.Ş.",
            start: "2021-03",
            end: "present",
            description: null,
          },
        ],
        education: [
          { level: "bachelor", field: "Bilgisayar", school: "Örnek Üniversitesi", end_year: 2018 },
        ],
        languages: [{ language: "English", level: "C1" }],
        total_experience_years: 5.6,
      },
    },
    status: "reviewing",
    score: 73,
    score_breakdown: {
      required_skills: {
        weight: 40,
        points: 20,
        met: 1,
        total: 2,
        items: [
          {
            criterion: "Python",
            met: true,
            status: "verified",
            evidence: "Built Python services",
            required_level: null,
            candidate_level: null,
          },
          {
            criterion: "Kubernetes",
            met: false,
            status: "unverified",
            evidence: null,
            required_level: null,
            candidate_level: null,
          },
        ],
      },
      experience: {
        weight: 25,
        points: 25,
        required_years: 3,
        candidate_years: 5.6,
        records: [
          { title: "Backend Developer", company: "Örnek A.Ş.", start: "2021-03", end: "present" },
        ],
      },
      education: {
        weight: 15,
        points: 15,
        required: "bachelor",
        candidate: "bachelor",
        records: [
          { level: "bachelor", field: "Bilgisayar", school: "Örnek Üniversitesi", end_year: 2018 },
        ],
      },
      languages: {
        weight: 10,
        points: 0,
        met: 0,
        total: 1,
        items: [
          {
            criterion: "German",
            met: false,
            status: "level_insufficient",
            evidence: "German (A2)",
            required_level: "B1",
            candidate_level: "A2",
          },
        ],
      },
      preferred_skills: { weight: 10, points: 10, met: 0, total: 0, items: [] },
    },
    ai_summary: "Python için kanıt var, Kubernetes için yok.",
    llm_model: "gemini-3.5-flash",
    prompt_version: "score_v1",
    score_status: "done",
    score_error: null,
    created_at: "2026-10-15T09:00:00Z",
    updated_at: "2026-10-15T09:00:00Z",
    notes: [
      {
        id: 1,
        body: "Kendi notum",
        author_id: recruiterUser.id,
        author_name: "Mehmet Uzman",
        created_at: "2026-10-15T10:00:00Z",
      },
      {
        id: 2,
        body: "Başkasının notu",
        author_id: adminUser.id,
        author_name: "Ayşe Yönetici",
        created_at: "2026-10-15T09:30:00Z",
      },
    ],
    status_history: [
      {
        from_status: "new",
        to_status: "reviewing",
        actor_id: 2,
        actor_name: "Mehmet Uzman",
        created_at: "2026-10-15T09:10:00Z",
      },
    ],
    ...overrides,
  };
}

function mockDetail(data: ApplicationDetail) {
  return mockApi((method, path, body) => {
    if (path === "/auth/me") return jsonResponse(200, recruiterUser);
    if (method === "GET" && path === "/applications/7") return jsonResponse(200, data);
    if (method === "PATCH" && path === "/applications/7/status") {
      const { status } = body as { status: ApplicationDetail["status"] };
      return jsonResponse(200, { ...data, status });
    }
    if (method === "POST" && path === "/applications/7/notes") {
      return jsonResponse(201, {
        id: 3,
        body: "Yeni",
        author_id: 2,
        author_name: "Mehmet Uzman",
        created_at: "2026-10-15T11:00:00Z",
      });
    }
    if (method === "DELETE" && path === "/notes/1") return new Response(null, { status: 204 });
    return undefined;
  });
}

describe("ApplicationDetailPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("puanı, kırılımı, kanıtları ve sabit uyarıyı gösterir", async () => {
    mockDetail(detail());
    renderRoute("/applications/7");

    expect(await screen.findByRole("heading", { name: "Deniz Arslan" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Puan 73, Orta uyum" })).toBeInTheDocument();
    expect(screen.getByRole("note")).toHaveTextContent(
      "Bu puan bir öneridir; karar İK uzmanına aittir.",
    );

    expect(screen.getByText("40 × 1/2 karşılanan")).toBeInTheDocument();
    expect(screen.getByText("Kanıt doğrulanamadı")).toBeInTheDocument();
    expect(screen.getByText("Seviye yetersiz")).toBeInTheDocument();
    expect(screen.getByText("German (istenen B1, CV'de A2)")).toBeInTheDocument();
    // Kanıttaki kriter ifadesi vurgulanır.
    expect(screen.getByText("Python", { selector: "mark" })).toBeInTheDocument();
    expect(screen.getByText("25 × min(1, 5,6 / 3 yıl)")).toBeInTheDocument();
    expect(screen.getByText("Kriter yok — 10 puanın tamamı verilir")).toBeInTheDocument();

    expect(screen.getByText(/Model: gemini-3.5-flash · Prompt: score_v1/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /CV'yi indir/ })).toHaveAttribute(
      "href",
      "/api/candidates/11/cv",
    );
  });

  it("durumu değiştirir", async () => {
    const fetchMock = mockDetail(detail());
    renderRoute("/applications/7");

    fireEvent.change(await screen.findByLabelText("Başvuru durumu"), {
      target: { value: "interview" },
    });

    await waitFor(() => {
      const call = fetchMock.mock.calls.find(([, init]) => init?.method === "PATCH");
      expect(requestBody(call?.[1])).toEqual({ status: "interview" });
    });
    expect(screen.getByText("Yeni →")).toBeInTheDocument();
  });

  it("not silme düğmesini yalnızca yazara gösterir ve not ekler", async () => {
    const fetchMock = mockDetail(detail());
    renderRoute("/applications/7");

    const notes = (await screen.findByRole("heading", { name: "Notlar" })).closest(
      "section",
    ) as HTMLElement;
    expect(within(notes).getAllByRole("button", { name: "Notu sil" })).toHaveLength(1);

    fireEvent.change(within(notes).getByLabelText("Not ekle"), { target: { value: "Yeni" } });
    fireEvent.click(within(notes).getByRole("button", { name: "Not ekle" }));
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/applications/7/notes",
        expect.objectContaining({ method: "POST", body: JSON.stringify({ body: "Yeni" }) }),
      );
    });

    fireEvent.click(within(notes).getByRole("button", { name: "Notu sil" }));
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/notes/1",
        expect.objectContaining({ method: "DELETE" }),
      );
    });
  });

  it("işlenmekte olan başvuruda puan yerine işlem durumunu gösterir", async () => {
    mockDetail(
      detail({ score: null, score_breakdown: null, ai_summary: null, score_status: "processing" }),
    );
    renderRoute("/applications/7");

    expect(await screen.findByText("İşleniyor")).toBeInTheDocument();
    expect(screen.getByRole("note")).toBeInTheDocument();
  });

  it("başarısız başvuruda nedeni ve yeniden dene düğmesini gösterir", async () => {
    mockDetail(
      detail({
        score: null,
        score_breakdown: null,
        ai_summary: null,
        score_status: "failed",
        score_error: "Puanlama servisine ulaşılamadı",
      }),
    );
    renderRoute("/applications/7");

    expect(await screen.findByText("Puanlama servisine ulaşılamadı")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Yeniden dene" })).toBeInTheDocument();
  });
});
