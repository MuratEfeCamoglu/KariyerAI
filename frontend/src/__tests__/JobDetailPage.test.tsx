import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { JobListItem } from "../types/job.ts";
import { jsonResponse, mockApi, recruiterUser, renderRoute } from "./testUtils.tsx";

const job: JobListItem = {
  id: 3,
  title: "Mobil Geliştirici",
  department: "Ürün",
  description: "Flutter ekibi için.",
  required_skills: ["Flutter", "Dart"],
  preferred_skills: ["Firebase"],
  min_experience_years: 0,
  min_education: "associate",
  languages: [{ language: "İngilizce", level: "C1" }],
  status: "closed",
  created_by: 2,
  created_at: "2026-10-15T09:00:00Z",
  updated_at: "2026-10-15T09:00:00Z",
  application_count: 0,
  top_score: null,
  avg_score: null,
};

describe("JobDetailPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("ilan kriterlerini gösterir", async () => {
    mockApi((_method, path) => {
      if (path === "/auth/me") return jsonResponse(200, recruiterUser);
      if (path === "/jobs/3") return jsonResponse(200, job);
      return undefined;
    });
    renderRoute("/jobs/3");

    expect(await screen.findByRole("heading", { name: "Mobil Geliştirici" })).toBeInTheDocument();
    expect(screen.getByText("Kapalı")).toBeInTheDocument();
    expect(screen.getByText("Flutter")).toBeInTheDocument();
    expect(screen.getByText("Firebase")).toBeInTheDocument();
    expect(screen.getByText("Ön lisans")).toBeInTheDocument();
    expect(screen.getByText("Aranmıyor")).toBeInTheDocument();
    expect(screen.getByText("İngilizce · C1")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Düzenle" })).toHaveAttribute("href", "/jobs/3/edit");
    // Kapalı ilana CV yüklenemez (F3); yükleme alanı devre dışıdır.
    expect(screen.getByLabelText("CV dosyaları")).toBeDisabled();
    expect(screen.getByText("0 başvuru")).toBeInTheDocument();
  });

  it("açık ilanda başvuru sayısını gösterir ve yüklemeye izin verir", async () => {
    mockApi((_method, path) => {
      if (path === "/auth/me") return jsonResponse(200, recruiterUser);
      if (path === "/jobs/3") {
        return jsonResponse(200, { ...job, status: "open", application_count: 4 });
      }
      return undefined;
    });
    renderRoute("/jobs/3");

    expect(await screen.findByText("4 başvuru")).toBeInTheDocument();
    expect(screen.getByLabelText("CV dosyaları")).toBeEnabled();
    expect(screen.queryByText("Henüz başvuru yok")).not.toBeInTheDocument();
  });

  it("olmayan ilan için hata gösterir", async () => {
    mockApi((_method, path) => {
      if (path === "/auth/me") return jsonResponse(200, recruiterUser);
      if (path === "/jobs/99") return jsonResponse(404, { detail: "İlan bulunamadı" });
      return undefined;
    });
    renderRoute("/jobs/99");

    expect(await screen.findByText("İlan bulunamadı")).toBeInTheDocument();
  });

  it("onaydan sonra ilanı silip listeye döner", async () => {
    const fetchMock = mockApi((method, path) => {
      if (path === "/auth/me") return jsonResponse(200, recruiterUser);
      if (method === "GET" && path === "/jobs/3") return jsonResponse(200, job);
      if (method === "DELETE" && path === "/jobs/3") return new Response(null, { status: 204 });
      if (method === "GET" && path === "/jobs") return jsonResponse(200, []);
      return undefined;
    });
    const router = renderRoute("/jobs/3");

    fireEvent.click(await screen.findByRole("button", { name: "Sil" }));
    const dialog = screen.getByRole("dialog", { name: "İlanı sil" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Sil" }));

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/jobs");
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/jobs/3",
      expect.objectContaining({ method: "DELETE" }),
    );
  });

  it("silme 409 dönerse nedeni modalda gösterir", async () => {
    mockApi((method, path) => {
      if (path === "/auth/me") return jsonResponse(200, recruiterUser);
      if (method === "GET" && path === "/jobs/3") return jsonResponse(200, job);
      if (method === "DELETE" && path === "/jobs/3") {
        return jsonResponse(409, { detail: "Başvurusu olan ilan silinemez" });
      }
      return undefined;
    });
    renderRoute("/jobs/3");

    fireEvent.click(await screen.findByRole("button", { name: "Sil" }));
    const dialog = screen.getByRole("dialog", { name: "İlanı sil" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Sil" }));

    expect(await within(dialog).findByRole("alert")).toHaveTextContent(
      "Başvurusu olan ilan silinemez",
    );
  });
});
