import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { jsonResponse, mockApi, recruiterUser, renderRoute } from "./testUtils.tsx";

function fillAndSubmit(email: string, password: string) {
  fireEvent.change(screen.getByLabelText("E-posta"), { target: { value: email } });
  fireEvent.change(screen.getByLabelText("Şifre"), { target: { value: password } });
  fireEvent.click(screen.getByRole("button", { name: "Giriş yap" }));
}

describe("LoginPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("İK kaydı bilgisini ve nötr kayıt bağlantısını gösterir", async () => {
    mockApi((_method, path) => {
      if (path === "/auth/me") return jsonResponse(401, { detail: "x" });
      return undefined;
    });
    renderRoute("/login");

    await screen.findByRole("heading", { name: "Giriş yap" });
    expect(
      screen.getByText("İK uzmanları da kaydolabilir; hesaplar yönetici onayıyla açılır."),
    ).toBeInTheDocument();
    expect(screen.getByText(/Hesabın yok mu\?/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Kayıt ol" })).toBeInTheDocument();
  });

  it("başarılı girişte ilanlar sayfasına yönlendirir", async () => {
    let loggedIn = false;
    const fetchMock = mockApi((method, path) => {
      if (path === "/auth/me") {
        return loggedIn ? jsonResponse(200, recruiterUser) : jsonResponse(401, { detail: "x" });
      }
      if (method === "POST" && path === "/auth/login") {
        loggedIn = true;
        return jsonResponse(200, recruiterUser);
      }
      return undefined;
    });
    const router = renderRoute("/login");

    await screen.findByRole("heading", { name: "Giriş yap" });
    fillAndSubmit("ik@example.com", "dogru-sifre-123");

    expect(await screen.findByRole("heading", { name: "İlanlar" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/jobs");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/auth/login",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ email: "ik@example.com", password: "dogru-sifre-123" }),
      }),
    );
  });

  it("yanlış şifrede genel hata mesajını gösterir", async () => {
    mockApi((method, path) => {
      if (path === "/auth/me") return jsonResponse(401, { detail: "Oturum açmanız gerekiyor" });
      if (method === "POST" && path === "/auth/login") {
        return jsonResponse(401, { detail: "E-posta veya şifre hatalı" });
      }
      return undefined;
    });
    renderRoute("/login");

    await screen.findByRole("heading", { name: "Giriş yap" });
    fillAndSubmit("ik@example.com", "yanlis-sifre-1");

    expect(await screen.findByRole("alert")).toHaveTextContent("E-posta veya şifre hatalı");
  });

  it("çok fazla denemede sunucunun 429 mesajını gösterir", async () => {
    mockApi((method, path) => {
      if (path === "/auth/me") return jsonResponse(401, { detail: "x" });
      if (method === "POST" && path === "/auth/login") {
        return jsonResponse(429, { detail: "Çok fazla başarısız giriş denemesi." });
      }
      return undefined;
    });
    renderRoute("/login");

    await screen.findByRole("heading", { name: "Giriş yap" });
    fillAndSubmit("ik@example.com", "yanlis-sifre-1");

    expect(await screen.findByRole("alert")).toHaveTextContent("Çok fazla başarısız");
  });

  it("şifre sıfırlama bağlantısı yerine yöneticiye yönlendirir", async () => {
    mockApi((_method, path) =>
      path === "/auth/me" ? jsonResponse(401, { detail: "x" }) : undefined,
    );
    renderRoute("/login");

    expect(await screen.findByText(/Yöneticinize başvurun/)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.queryByRole("link", { name: /şifre/i })).not.toBeInTheDocument();
    });
  });

  it("onay bekleyen İK hesabında sunucunun 403 mesajını gösterir", async () => {
    mockApi((method, path) => {
      if (path === "/auth/me") return jsonResponse(401, { detail: "x" });
      if (method === "POST" && path === "/auth/login") {
        return jsonResponse(403, { detail: "Hesabınız yönetici onayı bekliyor" });
      }
      return undefined;
    });
    renderRoute("/login");

    await screen.findByRole("heading", { name: "Giriş yap" });
    fillAndSubmit("ik@example.com", "dogru-sifre-123");

    expect(await screen.findByRole("alert")).toHaveTextContent("Hesabınız yönetici onayı bekliyor");
  });
});
