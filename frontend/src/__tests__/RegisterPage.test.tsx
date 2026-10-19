import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { jsonResponse, mockApi, renderRoute, requestBody, seekerUser } from "./testUtils.tsx";

function fillAndSubmit() {
  fireEvent.change(screen.getByLabelText("Ad soyad"), { target: { value: "Can Aday" } });
  fireEvent.change(screen.getByLabelText("E-posta"), { target: { value: "aday@example.com" } });
  fireEvent.change(screen.getByLabelText("Şifre"), { target: { value: "aday-sifresi-123" } });
  fireEvent.click(screen.getByRole("button", { name: "Hesap oluştur" }));
}

describe("RegisterPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("kayıt sonrası iş arayanın değerlendirme sayfasına gider", async () => {
    let registered = false;
    const fetchMock = mockApi((method, path) => {
      if (path === "/auth/me") {
        return registered ? jsonResponse(200, seekerUser) : jsonResponse(401, { detail: "x" });
      }
      if (method === "POST" && path === "/auth/register") {
        registered = true;
        return jsonResponse(201, seekerUser);
      }
      if (path === "/cv-checks") return jsonResponse(200, []);
      return undefined;
    });
    const router = renderRoute("/register");
    await screen.findByRole("heading", { name: "Kayıt ol" });

    fillAndSubmit();

    expect(await screen.findByRole("heading", { name: "CV Değerlendirmelerim" })).toBeVisible();
    expect(router.state.location.pathname).toBe("/cv-checks");
    const call = fetchMock.mock.calls.find(([url]) => url === "/api/auth/register");
    expect(requestBody(call?.[1])).toEqual({
      full_name: "Can Aday",
      email: "aday@example.com",
      password: "aday-sifresi-123",
    });
  });

  it("kayıtlı e-postada sunucu mesajını gösterir", async () => {
    mockApi((method, path) => {
      if (path === "/auth/me") return jsonResponse(401, { detail: "x" });
      if (method === "POST" && path === "/auth/register") {
        return jsonResponse(409, { detail: "Bu e-posta adresiyle bir kullanıcı zaten var" });
      }
      return undefined;
    });
    renderRoute("/register");
    await screen.findByRole("heading", { name: "Kayıt ol" });

    fillAndSubmit();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Bu e-posta adresiyle bir kullanıcı zaten var",
    );
  });

  it("kısa şifre hatasını alanın altında gösterir", async () => {
    mockApi((method, path) => {
      if (path === "/auth/me") return jsonResponse(401, { detail: "x" });
      if (method === "POST" && path === "/auth/register") {
        return jsonResponse(422, {
          detail: [{ loc: ["body", "password"], msg: "Şifre en az 10 karakter olmalı" }],
        });
      }
      return undefined;
    });
    renderRoute("/register");
    await screen.findByRole("heading", { name: "Kayıt ol" });

    fillAndSubmit();

    await waitFor(() => {
      expect(screen.getByText("Şifre en az 10 karakter olmalı")).toBeInTheDocument();
    });
  });

  it("giriş sayfasında kayıt bağlantısı vardır", async () => {
    mockApi((_method, path) =>
      path === "/auth/me" ? jsonResponse(401, { detail: "x" }) : undefined,
    );
    renderRoute("/login");

    expect(await screen.findByRole("link", { name: "Kayıt ol" })).toHaveAttribute(
      "href",
      "/register",
    );
  });
});
