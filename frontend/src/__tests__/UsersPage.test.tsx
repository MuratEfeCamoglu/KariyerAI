import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { adminUser, jsonResponse, mockApi, recruiterUser, renderRoute } from "./testUtils.tsx";

describe("UsersPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("adminin kendi satırında aktiflik anahtarını devre dışı bırakır", async () => {
    mockApi((_method, path) => {
      if (path === "/auth/me") return jsonResponse(200, adminUser);
      if (path === "/users") return jsonResponse(200, [adminUser, recruiterUser]);
      return undefined;
    });
    renderRoute("/users");

    const ownSwitch = await screen.findByRole("switch", { name: "Ayşe Yönetici aktif" });
    expect(ownSwitch).toBeDisabled();
    expect(screen.getByRole("switch", { name: "Mehmet Uzman aktif" })).toBeEnabled();
  });

  it("başka kullanıcıyı pasifleştirir", async () => {
    const fetchMock = mockApi((method, path) => {
      if (path === "/auth/me") return jsonResponse(200, adminUser);
      if (path === "/users") return jsonResponse(200, [adminUser, recruiterUser]);
      if (method === "PATCH" && path === "/users/2") {
        return jsonResponse(200, { ...recruiterUser, is_active: false });
      }
      return undefined;
    });
    renderRoute("/users");

    fireEvent.click(await screen.findByRole("switch", { name: "Mehmet Uzman aktif" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/users/2",
        expect.objectContaining({ method: "PATCH", body: JSON.stringify({ is_active: false }) }),
      );
    });
  });

  it("kullanıcı ekleme formunda alan bazlı 422 hatasını gösterir", async () => {
    mockApi((method, path) => {
      if (path === "/auth/me") return jsonResponse(200, adminUser);
      if (method === "GET" && path === "/users") return jsonResponse(200, [adminUser]);
      if (method === "POST" && path === "/users") {
        return jsonResponse(422, {
          detail: [
            {
              loc: ["body", "password"],
              msg: "Value error, Şifre en az 10 karakter olmalı",
              type: "value_error",
            },
          ],
        });
      }
      return undefined;
    });
    renderRoute("/users");

    fireEvent.click(await screen.findByRole("button", { name: "Kullanıcı ekle" }));
    const dialog = screen.getByRole("dialog", { name: "Kullanıcı ekle" });
    fireEvent.change(within(dialog).getByLabelText("Ad soyad"), { target: { value: "Zeynep" } });
    fireEvent.change(within(dialog).getByLabelText("E-posta"), {
      target: { value: "z@example.com" },
    });
    fireEvent.change(within(dialog).getByLabelText("Geçici şifre"), { target: { value: "kisa" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Kullanıcı ekle" }));

    expect(await within(dialog).findByText("Şifre en az 10 karakter olmalı")).toBeInTheDocument();
  });

  it("yeni kullanıcı başarıyla eklenince modal kapanır", async () => {
    let users = [adminUser];
    const newUser = { ...recruiterUser, id: 3, full_name: "Zeynep Yeni", email: "z@example.com" };
    mockApi((method, path) => {
      if (path === "/auth/me") return jsonResponse(200, adminUser);
      if (method === "GET" && path === "/users") return jsonResponse(200, users);
      if (method === "POST" && path === "/users") {
        users = [adminUser, newUser];
        return jsonResponse(201, newUser);
      }
      return undefined;
    });
    renderRoute("/users");

    fireEvent.click(await screen.findByRole("button", { name: "Kullanıcı ekle" }));
    const dialog = screen.getByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText("Ad soyad"), {
      target: { value: "Zeynep Yeni" },
    });
    fireEvent.change(within(dialog).getByLabelText("E-posta"), {
      target: { value: "z@example.com" },
    });
    fireEvent.change(within(dialog).getByLabelText("Geçici şifre"), {
      target: { value: "gecici-sifre-1" },
    });
    fireEvent.click(within(dialog).getByRole("button", { name: "Kullanıcı ekle" }));

    expect(await screen.findByText("Zeynep Yeni")).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
