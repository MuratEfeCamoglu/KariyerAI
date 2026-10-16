import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Job } from "../types/job.ts";
import { jsonResponse, mockApi, recruiterUser, renderRoute, requestBody } from "./testUtils.tsx";

const savedJob: Job = {
  id: 7,
  title: "Veri Analisti",
  department: "Finans",
  description: "",
  required_skills: ["SQL"],
  preferred_skills: [],
  min_experience_years: 2,
  min_education: "bachelor",
  languages: [{ language: "İngilizce", level: "B2" }],
  status: "open",
  created_by: 2,
  created_at: "2026-10-15T09:00:00Z",
  updated_at: "2026-10-15T09:00:00Z",
};

function addChip(label: string, text: string) {
  const input = screen.getByLabelText(label);
  fireEvent.change(input, { target: { value: text } });
  fireEvent.keyDown(input, { key: "Enter" });
}

describe("JobFormPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("yeni ilanı oluşturup detay sayfasına gider", async () => {
    const fetchMock = mockApi((method, path) => {
      if (path === "/auth/me") return jsonResponse(200, recruiterUser);
      if (method === "POST" && path === "/jobs") return jsonResponse(201, savedJob);
      if (method === "GET" && path === "/jobs/7") return jsonResponse(200, savedJob);
      return undefined;
    });
    const router = renderRoute("/jobs/new");

    fireEvent.change(await screen.findByLabelText("Başlık"), {
      target: { value: "  Veri Analisti " },
    });
    fireEvent.change(screen.getByLabelText("Departman"), { target: { value: "Finans" } });
    addChip("Zorunlu beceriler", "SQL");
    fireEvent.change(screen.getByLabelText("Minimum deneyim (yıl)"), { target: { value: "2" } });
    fireEvent.change(screen.getByLabelText("Minimum eğitim"), { target: { value: "bachelor" } });
    fireEvent.click(screen.getByRole("button", { name: "Dil ekle" }));
    fireEvent.change(screen.getByLabelText("Dil 1"), { target: { value: "İngilizce" } });
    fireEvent.change(screen.getByLabelText("Dil 1 seviyesi"), { target: { value: "B2" } });
    fireEvent.click(screen.getByRole("button", { name: "İlanı oluştur" }));

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/jobs/7");
    });
    const [, init] = fetchMock.mock.calls.find(([url]) => url === "/api/jobs") ?? [];
    expect(requestBody(init)).toEqual({
      title: "Veri Analisti",
      department: "Finans",
      description: "",
      required_skills: ["SQL"],
      preferred_skills: [],
      min_experience_years: 2,
      min_education: "bachelor",
      languages: [{ language: "İngilizce", level: "B2" }],
      status: "open",
    });
  });

  it("422 hatalarını alanların altında ve üstte özet olarak gösterir", async () => {
    mockApi((method, path) => {
      if (path === "/auth/me") return jsonResponse(200, recruiterUser);
      if (method === "POST" && path === "/jobs") {
        return jsonResponse(422, {
          detail: [
            { loc: ["body", "title"], msg: "En az 3 karakter olmalı", type: "string_too_short" },
            {
              loc: ["body", "required_skills"],
              msg: "En az 1 öğe eklenmeli",
              type: "too_short",
            },
          ],
        });
      }
      return undefined;
    });
    renderRoute("/jobs/new");

    fireEvent.change(await screen.findByLabelText("Başlık"), { target: { value: "ab" } });
    fireEvent.click(screen.getByRole("button", { name: "İlanı oluştur" }));

    expect(await screen.findByText("En az 3 karakter olmalı")).toBeInTheDocument();
    expect(screen.getByText("En az 1 öğe eklenmeli")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("Formda 2 hatalı alan var");
    expect(screen.getByLabelText("Başlık")).toHaveAttribute("aria-invalid", "true");
  });

  it("düzenlemede mevcut değerleri yükler ve PATCH gönderir", async () => {
    const fetchMock = mockApi((method, path) => {
      if (path === "/auth/me") return jsonResponse(200, recruiterUser);
      if (method === "GET" && path === "/jobs/7") return jsonResponse(200, savedJob);
      if (method === "PATCH" && path === "/jobs/7") {
        return jsonResponse(200, { ...savedJob, status: "closed" });
      }
      return undefined;
    });
    const router = renderRoute("/jobs/7/edit");

    expect(await screen.findByLabelText("Başlık")).toHaveValue("Veri Analisti");
    expect(screen.getByText("SQL")).toBeInTheDocument();
    expect(screen.getByLabelText("Dil 1")).toHaveValue("İngilizce");

    fireEvent.click(screen.getByRole("radio", { name: "Kapalı" }));
    fireEvent.click(screen.getByRole("button", { name: "Kaydet" }));

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/jobs/7");
    });
    const patchCall = fetchMock.mock.calls.find(([, init]) => init?.method === "PATCH");
    expect(requestBody(patchCall?.[1])).toMatchObject({ status: "closed" });
  });
});
