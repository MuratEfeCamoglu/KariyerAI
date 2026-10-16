import { fireEvent, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { JobListItem } from "../types/job.ts";
import { jsonResponse, mockApi, recruiterUser, renderRoute } from "./testUtils.tsx";

function job(overrides: Partial<JobListItem>): JobListItem {
  return {
    id: 1,
    title: "Backend Geliştirici",
    department: "Teknoloji",
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
    application_count: 0,
    top_score: null,
    avg_score: null,
    ...overrides,
  };
}

function mockJobs(jobs: JobListItem[]) {
  mockApi((_method, path) => {
    if (path === "/auth/me") return jsonResponse(200, recruiterUser);
    if (path === "/jobs") return jsonResponse(200, jobs);
    return undefined;
  });
}

describe("JobsPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("ilan yokken boş durumu ve oluşturma bağlantısını gösterir", async () => {
    mockJobs([]);
    renderRoute("/jobs");

    expect(await screen.findByText("Henüz ilan yok — ilk ilanını oluştur")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Yeni ilan" })).toHaveAttribute("href", "/jobs/new");
  });

  it("ilanları başvuru sayısı ve bant renkli puanlarla listeler", async () => {
    mockJobs([
      job({
        id: 1,
        title: "Backend Geliştirici",
        application_count: 12,
        top_score: 83,
        avg_score: 61.4,
      }),
      job({ id: 2, title: "Veri Analisti", status: "closed", department: "Finans" }),
    ]);
    renderRoute("/jobs");

    const row = (await screen.findByRole("link", { name: "Backend Geliştirici" })).closest("tr");
    expect(row).not.toBeNull();
    const cells = within(row as HTMLElement);
    expect(cells.getByText("12")).toBeInTheDocument();
    expect(cells.getByText("83")).toBeInTheDocument();
    expect(cells.getByText("Yüksek uyum:", { exact: false })).toBeInTheDocument();
    expect(cells.getByText("61")).toBeInTheDocument();
    expect(cells.getByText("Orta uyum:", { exact: false })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Backend Geliştirici" })).toHaveAttribute(
      "href",
      "/jobs/1",
    );
  });

  it("arama ve durum filtresiyle süzer", async () => {
    mockJobs([
      job({ id: 1, title: "Backend Geliştirici" }),
      job({ id: 2, title: "Veri Analisti", status: "closed", department: "İnsan Kaynakları" }),
    ]);
    renderRoute("/jobs");
    await screen.findByRole("link", { name: "Backend Geliştirici" });

    fireEvent.change(screen.getByLabelText("İlan ara"), { target: { value: "insan" } });
    expect(screen.queryByRole("link", { name: "Backend Geliştirici" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Veri Analisti" })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("İlan ara"), { target: { value: "" } });
    fireEvent.click(screen.getByRole("radio", { name: "Açık" }));
    expect(screen.getByRole("link", { name: "Backend Geliştirici" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Veri Analisti" })).not.toBeInTheDocument();
  });

  it("eşleşme yoksa ayrı boş durum gösterir", async () => {
    mockJobs([job({})]);
    renderRoute("/jobs");
    await screen.findByRole("link", { name: "Backend Geliştirici" });

    fireEvent.change(screen.getByLabelText("İlan ara"), { target: { value: "pazarlama" } });

    expect(screen.getByText("Aramanızla eşleşen ilan yok")).toBeInTheDocument();
  });
});
