import type { LoginRequest, User } from "../types/user.ts";
import { ApiError, apiFetch } from "./client.ts";

export function login(body: LoginRequest): Promise<User> {
  return apiFetch<User>("/auth/login", { method: "POST", body: JSON.stringify(body) });
}

export function logout(): Promise<void> {
  return apiFetch<undefined>("/auth/logout", { method: "POST" });
}

/** Oturum yoksa `null` döner; 401 burada hata değil, "giriş yapılmamış" bilgisidir. */
export async function getMe(): Promise<User | null> {
  try {
    return await apiFetch<User>("/auth/me");
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      return null;
    }
    throw error;
  }
}
