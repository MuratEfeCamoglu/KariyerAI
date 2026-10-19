import type { CvCheck, CvCheckCriteria, CvCheckListItem } from "../types/cvCheck.ts";
import { apiFetch } from "./client.ts";

export function listCvChecks(): Promise<CvCheckListItem[]> {
  return apiFetch<CvCheckListItem[]>("/cv-checks");
}

export function getCvCheck(id: number): Promise<CvCheck> {
  return apiFetch<CvCheck>(`/cv-checks/${String(id)}`);
}

/** Kriterler multipart içinde JSON metni olarak gider; dosya tek CV'dir. */
export function createCvCheck(input: {
  criteria: CvCheckCriteria;
  file: File;
}): Promise<CvCheckListItem> {
  const form = new FormData();
  form.append("criteria", JSON.stringify(input.criteria));
  form.append("file", input.file);
  return apiFetch<CvCheckListItem>("/cv-checks", { method: "POST", body: form });
}

export function retryCvCheck(id: number): Promise<{ id: number }> {
  return apiFetch<{ id: number }>(`/cv-checks/${String(id)}/retry`, { method: "POST" });
}

export function deleteCvCheck(id: number): Promise<void> {
  return apiFetch<undefined>(`/cv-checks/${String(id)}`, { method: "DELETE" });
}
