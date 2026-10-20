import { screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  adminUser,
  jsonResponse,
  mockApi,
  recruiterUser,
  renderRoute,
  seekerUser,
} from "./testUtils.tsx";
import type { User } from "../types/user.ts";

function mockSession(user: User | null) {
  mockApi((_method, path) => {
    if (path === "/auth/me") {
      return user ? jsonResponse(200, user) : jsonResponse(401, { detail: "x" });
    }
    if (path === "/users") return jsonResponse(200, [adminUser, recruiterUser]);
    if (path === "/cv-checks") return jsonResponse(200, []);
    if (path === "/jobs") return jsonResponse(200, []);
    return undefined;
  });
}

describe("rota korumaları", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("oturumsuz kullanıcıyı korumalı sayfadan girişe yönlendirir", async () => {
    mockSession(null);
    const router = renderRoute("/jobs");

    expect(await screen.findByRole("heading", { name: "Giriş yap" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/login");
  });

  it("kök yolu oturumlu kullanıcı için ilanlara yönlendirir", async () => {
    mockSession(recruiterUser);
    const router = renderRoute("/");

    expect(await screen.findByRole("heading", { name: "İlanlar" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/jobs");
  });

  it("admin olmayanı /users sayfasından ilanlara yönlendirir ve menüde göstermez", async () => {
    mockSession(recruiterUser);
    const router = renderRoute("/users");

    expect(await screen.findByRole("heading", { name: "İlanlar" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/jobs");
    expect(screen.queryByRole("link", { name: "Kullanıcılar" })).not.toBeInTheDocument();
  });

  it("admin kullanıcılar sayfasını görür", async () => {
    mockSession(adminUser);
    renderRoute("/users");

    expect(await screen.findByRole("heading", { name: "Kullanıcılar" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Kullanıcılar" })).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("Mehmet Uzman")).toBeInTheDocument();
    });
  });

  it("admini /jobs sayfasından kullanıcılara yönlendirir ve menüde İlanlar göstermez", async () => {
    mockSession(adminUser);
    const router = renderRoute("/jobs");

    expect(await screen.findByRole("heading", { name: "Kullanıcılar" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/users");
    expect(screen.queryByRole("link", { name: "İlanlar" })).not.toBeInTheDocument();
  });

  it("admini /applications/1 sayfasından kullanıcılara yönlendirir", async () => {
    mockSession(adminUser);
    const router = renderRoute("/applications/1");

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/users");
    });
  });

  it("kök yolu admin için kullanıcılara yönlendirir", async () => {
    mockSession(adminUser);
    const router = renderRoute("/");

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/users");
    });
  });

  it("admin menüsünde onay bekleyen sayısı rozeti görünür", async () => {
    mockApi((_method, path) => {
      if (path === "/auth/me") return jsonResponse(200, adminUser);
      if (path === "/users") {
        return jsonResponse(200, [
          adminUser,
          { ...recruiterUser, id: 8, is_approved: false },
          { ...recruiterUser, id: 9, is_approved: false },
        ]);
      }
      return undefined;
    });
    renderRoute("/users");

    expect(await screen.findByLabelText("2 onay bekleyen")).toBeInTheDocument();
  });

  it("giriş yapmış kullanıcı /login'e gelirse ilanlara gider", async () => {
    mockSession(recruiterUser);
    const router = renderRoute("/login");

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/jobs");
    });
  });

  it("iş arayanı işveren sayfalarından değerlendirmelerine yönlendirir", async () => {
    mockSession(seekerUser);
    const router = renderRoute("/jobs");

    expect(await screen.findByRole("heading", { name: "CV Değerlendirmelerim" })).toBeVisible();
    expect(router.state.location.pathname).toBe("/cv-checks");
  });

  it("iş arayanı /users sayfasından değerlendirmelerine yönlendirir", async () => {
    mockSession(seekerUser);
    const router = renderRoute("/users");

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/cv-checks");
    });
  });

  it("İK uzmanını iş arayan sayfasından ilanlara yönlendirir", async () => {
    mockSession(recruiterUser);
    const router = renderRoute("/cv-checks");

    expect(await screen.findByRole("heading", { name: "İlanlar" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/jobs");
  });

  it("kök yolu iş arayan için değerlendirmelere yönlendirir", async () => {
    mockSession(seekerUser);
    const router = renderRoute("/");

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/cv-checks");
    });
  });
});
