import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SEEKER_DISCLAIMER } from "../lib/constants.ts";
import type { CvCheck } from "../types/cvCheck.ts";
import { jsonResponse, mockApi, renderRoute, seekerUser } from "./testUtils.tsx";

const DONE_CHECK: CvCheck = {
  id: 7,
  title: "Backend Geliştirici",
  original_filename: "cv.pdf",
  score: 68,
  parse_status: "done",
  score_status: "done",
  created_at: "2026-10-19T10:00:00Z",
  job_text: "",
  required_skills: ["Python", "Kubernetes"],
  preferred_skills: [],
  min_experience_years: 5,
  min_education: "none",
  languages: [],
  parse_error: null,
  score_error: null,
  parsed: null,
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
          evidence: "Skills: Python, FastAPI",
          required_level: null,
          candidate_level: null,
        },
        {
          criterion: "Kubernetes",
          met: false,
          status: "no_evidence",
          evidence: null,
          required_level: null,
          candidate_level: null,
        },
      ],
    },
    experience: { weight: 25, points: 16, required_years: 5, candidate_years: 3.2, records: [] },
    education: { weight: 15, points: 15, required: "none", candidate: null, records: [] },
    languages: { weight: 10, points: 10, met: 0, total: 0, items: [] },
    preferred_skills: { weight: 10, points: 10, met: 0, total: 0, items: [] },
  },
  ai_summary: "Python deneyimi güçlü.",
  llm_model: "fake",
  prompt_version: "score_v1",
  gaps: [
    {
      kind: "required_skill",
      criterion: "Kubernetes",
      status: "no_evidence",
      message: "CV'nde 'Kubernetes' kanıtı bulunamadı.",
    },
    {
      kind: "experience",
      criterion: "5 yıl deneyim",
      status: "below_requirement",
      message: "İlan en az 5 yıl deneyim istiyor; CV'nden hesaplanan 3,2 yıl.",
    },
  ],
};

function seekerSession(extra: (method: string, path: string) => Response | undefined) {
  return mockApi((method, path) => {
    if (path === "/auth/me") return jsonResponse(200, seekerUser);
    return extra(method, path);
  });
}

describe("CV değerlendirme sayfaları", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("rapor eksikleri sırayla, uyarıyı ve güçlü yanları gösterir", async () => {
    seekerSession((_m, path) =>
      path === "/cv-checks/7" ? jsonResponse(200, DONE_CHECK) : undefined,
    );
    renderRoute("/cv-checks/7");

    const gaps = await screen.findByRole("list", { name: "Eksikler" });
    const items = gaps.querySelectorAll("li");
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent("Kubernetes");
    expect(items[1]).toHaveTextContent("3,2 yıl");
    expect(screen.getByRole("note")).toHaveTextContent(SEEKER_DISCLAIMER);
    expect(screen.getByRole("heading", { name: "Güçlü yanların" })).toBeInTheDocument();
    expect(screen.getAllByText("Python").length).toBeGreaterThan(0);
  });

  it("işlenirken İşleniyor rozetini gösterir", async () => {
    seekerSession((_m, path) =>
      path === "/cv-checks/7"
        ? jsonResponse(200, {
            ...DONE_CHECK,
            parse_status: "processing",
            score_status: "pending",
            score: null,
            score_breakdown: null,
            gaps: [],
          })
        : undefined,
    );
    renderRoute("/cv-checks/7");

    expect(await screen.findByText("İşleniyor")).toBeInTheDocument();
    expect(screen.getByRole("note")).toHaveTextContent(SEEKER_DISCLAIMER);
  });

  it("dosya seçilmeden form gönderilmez", async () => {
    const fetchMock = seekerSession(() => undefined);
    renderRoute("/cv-checks/new");
    await screen.findByRole("heading", { name: "Yeni değerlendirme" });

    fireEvent.click(screen.getByRole("button", { name: "Değerlendir" }));

    expect(await screen.findByText("CV dosyası seçin")).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([url]) => url === "/api/cv-checks")).toBe(false);
  });

  it("sunucu alan hatasını ilgili alanın altında gösterir ve multipart gönderir", async () => {
    const fetchMock = seekerSession((method, path) =>
      method === "POST" && path === "/cv-checks"
        ? jsonResponse(422, {
            detail: [{ loc: ["body", "required_skills"], msg: "En az 1 öğe eklenmeli" }],
          })
        : undefined,
    );
    renderRoute("/cv-checks/new");
    await screen.findByRole("heading", { name: "Yeni değerlendirme" });

    fireEvent.change(screen.getByLabelText("İş başlığı"), { target: { value: "Backend" } });
    const file = new File(["%PDF-1.4"], "cv.pdf", { type: "application/pdf" });
    fireEvent.change(screen.getByLabelText(/CV dosyası/), { target: { files: [file] } });
    fireEvent.click(screen.getByRole("button", { name: "Değerlendir" }));

    expect(await screen.findByText("En az 1 öğe eklenmeli")).toBeInTheDocument();
    const call = fetchMock.mock.calls.find(([url]) => url === "/api/cv-checks");
    const body = call?.[1]?.body;
    expect(body).toBeInstanceOf(FormData);
    const raw = (body as FormData).get("criteria");
    expect(typeof raw).toBe("string");
    const criteria: unknown = JSON.parse(raw as string);
    expect(criteria).toMatchObject({ title: "Backend", required_skills: [] });
  });

  it("liste boşken başlangıç çağrısı gösterir", async () => {
    seekerSession((_m, path) => (path === "/cv-checks" ? jsonResponse(200, []) : undefined));
    renderRoute("/cv-checks");

    expect(await screen.findByText("Henüz değerlendirme yok")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByRole("link", { name: "CV Değerlendirmelerim" })).toBeInTheDocument();
    });
    expect(screen.queryByRole("link", { name: "İlanlar" })).not.toBeInTheDocument();
  });
});
