import type {
  ApplicationFilters,
  ApplicationList,
  QueuedApplications,
} from "../types/application.ts";
import { apiFetch } from "./client.ts";

export function listApplications(
  jobId: number,
  filters: ApplicationFilters,
  page: number,
): Promise<ApplicationList> {
  const params = new URLSearchParams({ page: String(page) });
  if (filters.minScore > 0) {
    params.set("min_score", String(filters.minScore));
  }
  for (const status of filters.statuses) {
    params.append("status", status);
  }
  if (filters.parseStatus !== null) {
    params.set("parse_status", filters.parseStatus);
  }
  return apiFetch<ApplicationList>(`/jobs/${String(jobId)}/applications?${params.toString()}`);
}

export function retryApplication(id: number): Promise<QueuedApplications> {
  return apiFetch<QueuedApplications>(`/applications/${String(id)}/retry`, { method: "POST" });
}

export function rescoreJob(jobId: number): Promise<QueuedApplications> {
  return apiFetch<QueuedApplications>(`/jobs/${String(jobId)}/rescore`, { method: "POST" });
}
