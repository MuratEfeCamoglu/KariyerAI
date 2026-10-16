import type { AuditLogEntry } from "../types/audit.ts";
import { apiFetch } from "./client.ts";

export function listAuditLogs(): Promise<AuditLogEntry[]> {
  return apiFetch<AuditLogEntry[]>("/audit");
}
