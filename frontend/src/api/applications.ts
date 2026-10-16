import type {
  ApplicationDetail,
  ApplicationFilters,
  ApplicationList,
  ApplicationStatus,
  Note,
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

export function getApplication(id: number): Promise<ApplicationDetail> {
  return apiFetch<ApplicationDetail>(`/applications/${String(id)}`);
}

export function changeStatus(id: number, status: ApplicationStatus): Promise<ApplicationDetail> {
  return apiFetch<ApplicationDetail>(`/applications/${String(id)}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export function addNote(applicationId: number, body: string): Promise<Note> {
  return apiFetch<Note>(`/applications/${String(applicationId)}/notes`, {
    method: "POST",
    body: JSON.stringify({ body }),
  });
}

export function deleteNote(noteId: number): Promise<void> {
  return apiFetch<undefined>(`/notes/${String(noteId)}`, { method: "DELETE" });
}

/** Dosya indirme tarayıcıya bırakılır (cookie aynı origin'de); bu yalnızca adresi üretir. */
export function cvDownloadUrl(candidateId: number): string {
  return `/api/candidates/${String(candidateId)}/cv`;
}

/** F11 (KVKK): yalnızca admin; aday, başvuruları, notları ve CV dosyası kalıcı olarak silinir. */
export function deleteCandidate(candidateId: number): Promise<void> {
  return apiFetch<undefined>(`/candidates/${String(candidateId)}`, { method: "DELETE" });
}
