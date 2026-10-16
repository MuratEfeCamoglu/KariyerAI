import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AUTO_REFRESH_MS, refetchIntervalFor } from "../hooks/useApplications.ts";
import type { ApplicationList, ApplicationRow } from "../types/application.ts";
import type { JobListItem } from "../types/job.ts";
import { jsonResponse, mockApi, recruiterUser, renderRoute } from "./testUtils.tsx";

const job: JobListItem = {
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
  application_count: 3,
  top_score: 83,
  avg_score: 60,
};

function row(overrides: Partial<ApplicationRow>): ApplicationRow {
  return {
    id: 1,
    candidate_id: 1,
    candidate_name: "Deniz Arslan",
    score: 83,
    item_points: {
      required_skills: 26.7,
      experience: 25,
      education: 15,
      languages: 10,
      preferred_skills: 6,
    },
    last_position: "Senior Backend Developer",
    total_experience_years: 4.2,
    status: "shortlisted",
    parse_status: "done",
    parse_error: null,
    score_status: "done",
    score_error: null,
    created_at: "2026-10-15T09:30:00Z",
    ...overrides,
  };
}

function listOf(items: ApplicationRow[], extra: Partial<ApplicationList> = {}): ApplicationList {
  return {
    items,
    total: items.length,
    page: 1,
    page_size: 50,
    processing_count: 0,
    ...extra,
  };
}

function mockJobPage(list: (url: string) => ApplicationList) {
  return mockApi((method, path) => {
    if (path === "/auth/me") return jsonResponse(200, recruiterUser);
    if (path === "/jobs/4") return jsonResponse(200, job);
    if (method === "GET" && path.startsWith("/jobs/4/applications")) {
      return jsonResponse(200, list(path));
    }
    if (method === "POST" && path === "/applications/3/retry") {
      return jsonResponse(202, { application_ids: [3] });
    }
    if (method === "POST" && path === "/jobs/4/rescore") {
      return jsonResponse(202, { application_ids: [1] });
    }
    return undefined;
  });
}

describe("ApplicationsTable", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("puanlı, işlenen ve başarısız satırları gösterir", async () => {
    mockJobPage(() =>
      listOf(
        [
          row({ id: 1 }),
          row({
            id: 2,
            candidate_name: null,
            candidate_id: 9,
            score: null,
            item_points: null,
            parse_status: "processing",
            score_status: "pending",
          }),
          row({
            id: 3,
            candidate_name: "Elif Kaya",
            score: null,
            item_points: null,
            parse_status: "failed",
            parse_error: "AI çıktısı beklenen biçimde değil",
            score_status: "failed",
            score_error: "Ayrıştırma başarısız",
          }),
        ],
        { processing_count: 1 },
      ),
    );
    renderRoute("/jobs/4");

    const table = await screen.findByRole("table");
    const rows = within(table).getAllByRole("row").slice(1);
    expect(
      within(rows[0] as HTMLElement).getByRole("img", { name: "Puan 83, Yüksek uyum" }),
    ).toBeInTheDocument();
    expect(within(rows[0] as HTMLElement).getByText("Yüksek uyum")).toBeInTheDocument();
    expect(
      within(rows[0] as HTMLElement).getByText("Zorunlu beceriler: 26,7/40"),
    ).toBeInTheDocument();
    expect(within(rows[0] as HTMLElement).getByText("4,2 yıl")).toBeInTheDocument();
    expect(within(rows[0] as HTMLElement).getByText("Kısa liste")).toBeInTheDocument();

    expect(within(rows[1] as HTMLElement).getByText("Aday #9")).toBeInTheDocument();
    expect(within(rows[1] as HTMLElement).getByText("İşleniyor")).toBeInTheDocument();

    expect(
      within(rows[2] as HTMLElement).getByText("AI çıktısı beklenen biçimde değil"),
    ).toBeInTheDocument();
    expect(screen.getByText(/1 CV işleniyor/)).toBeInTheDocument();
    expect(screen.getByText("Bu puan bir öneridir; karar İK uzmanına aittir.")).toBeInTheDocument();
  });

  it("başarısız satırda yeniden denemeyi çağırır", async () => {
    const fetchMock = mockJobPage(() =>
      listOf([
        row({
          id: 3,
          score: null,
          item_points: null,
          score_status: "failed",
          score_error: "Puanlama servisine ulaşılamadı",
        }),
      ]),
    );
    renderRoute("/jobs/4");

    fireEvent.click(await screen.findByRole("button", { name: "Yeniden dene" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/applications/3/retry",
        expect.objectContaining({ method: "POST" }),
      );
    });
  });

  it("filtreleri sorguya yansıtır ve sayfayı başa alır", async () => {
    const fetchMock = mockJobPage(() => listOf([row({})], { total: 120 }));
    renderRoute("/jobs/4");
    await screen.findByText("Sayfa 1 / 3 · 120 başvuru");

    fireEvent.click(screen.getByRole("button", { name: "Sonraki sayfa" }));
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/jobs/4/applications?page=2", expect.anything());
    });

    fireEvent.click(screen.getByRole("button", { name: "Mülakat" }));
    fireEvent.change(screen.getByLabelText(/Minimum puan/), { target: { value: "60" } });
    fireEvent.change(screen.getByLabelText("İşlem durumu"), { target: { value: "failed" } });

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/jobs/4/applications?page=1&min_score=60&status=interview&parse_status=failed",
        expect.anything(),
      );
    });
  });

  it("yeniden puanla düğmesi ilanı yeniden puanlatır", async () => {
    const fetchMock = mockJobPage(() => listOf([row({})]));
    renderRoute("/jobs/4");

    fireEvent.click(await screen.findByRole("button", { name: "Yeniden puanla" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/jobs/4/rescore",
        expect.objectContaining({ method: "POST" }),
      );
    });
  });

  it("filtre sonucu boşsa ayrı mesaj gösterir", async () => {
    mockJobPage((url) => (url.includes("min_score") ? listOf([]) : listOf([row({})])));
    renderRoute("/jobs/4");
    await screen.findByRole("table");

    fireEvent.change(screen.getByLabelText(/Minimum puan/), { target: { value: "95" } });

    expect(await screen.findByText("Filtrelerle eşleşen başvuru yok")).toBeInTheDocument();
  });
});

describe("otomatik yenileme (F7d)", () => {
  it("işlenen kayıt varken 5 sn'de bir yeniler, kalmayınca durur", () => {
    expect(refetchIntervalFor(listOf([], { processing_count: 2 }))).toBe(AUTO_REFRESH_MS);
    expect(AUTO_REFRESH_MS).toBe(5000);
    expect(refetchIntervalFor(listOf([], { processing_count: 0 }))).toBe(false);
    expect(refetchIntervalFor(undefined)).toBe(false);
  });
});
