import type { User, UserCreate, UserUpdate } from "../types/user.ts";
import { apiFetch } from "./client.ts";

export function listUsers(): Promise<User[]> {
  return apiFetch<User[]>("/users");
}

export function createUser(body: UserCreate): Promise<User> {
  return apiFetch<User>("/users", { method: "POST", body: JSON.stringify(body) });
}

export function updateUser(id: number, body: UserUpdate): Promise<User> {
  return apiFetch<User>(`/users/${String(id)}`, { method: "PATCH", body: JSON.stringify(body) });
}

export function approveUser(id: number): Promise<User> {
  return apiFetch<User>(`/users/${String(id)}/approve`, { method: "POST" });
}

export function rejectUser(id: number): Promise<void> {
  return apiFetch<undefined>(`/users/${String(id)}/reject`, { method: "POST" });
}
