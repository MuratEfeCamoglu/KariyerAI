import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { AuditLogEntry } from "../types/audit.ts";
import { adminUser, jsonResponse, mockApi, recruiterUser, renderRoute } from "./testUtils.tsx";
import type { User } from "../types/user.ts";

const entries: AuditLogEntry[] = [
  {
    id: 3,
    actor_id: 1,
    actor_name: "Ayşe Yönetici",
    action: "application.status",
    entity_type: "application",
    entity_id: 7,
    payload: { from: "new", to: "reviewing" },
    created_at: "2026-10-15T10:00:00Z",
  },
  {
    id: 2,
    actor_id: null,
    actor_name: null,
    action: "score.result",
    entity_type: "application",
    entity_id: 7,
    payload: { status: "done", score: 73, model: "fake", prompt: "score_v1" },
    created_at: "2026-10-15T09:30:00Z",
  },
];

function mockSession(user: User) {
  mockApi((_method, path) => {
    if (path === "/auth/me") return jsonResponse(200, user);
    if (path === "/audit") return jsonResponse(200, entries);
    if (path === "/jobs") return jsonResponse(200, []);
    return undefined;
  });
}

describe("AuditPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("admin kayıtları Türkçe eylem adlarıyla görür ve filtreler", async () => {
    mockSession(adminUser);
    renderRoute("/audit");

    expect(await screen.findByText("Durum değişikliği", { selector: "td" })).toBeInTheDocument();
    expect(screen.getByText("Sistem")).toBeInTheDocument();
    expect(
      screen.getByText("durum: Tamamlandı · puan: 73 · model: fake · prompt: score_v1"),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Denetim" })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Eylem"), { target: { value: "score.result" } });

    expect(screen.queryByText("Durum değişikliği", { selector: "td" })).not.toBeInTheDocument();
    expect(screen.getByText("Puanlama sonucu", { selector: "td" })).toBeInTheDocument();
  });

  it("admin olmayanı ilanlara yönlendirir", async () => {
    mockSession(recruiterUser);
    const router = renderRoute("/audit");

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/jobs");
    });
    expect(screen.queryByRole("link", { name: "Denetim" })).not.toBeInTheDocument();
  });
});
