import type { Job, JobInput, JobListItem } from "../types/job.ts";
import { apiFetch } from "./client.ts";

export function listJobs(): Promise<JobListItem[]> {
  return apiFetch<JobListItem[]>("/jobs");
}

export function getJob(id: number): Promise<Job> {
  return apiFetch<Job>(`/jobs/${String(id)}`);
}

export function createJob(body: JobInput): Promise<Job> {
  return apiFetch<Job>("/jobs", { method: "POST", body: JSON.stringify(body) });
}

export function updateJob(id: number, body: Partial<JobInput>): Promise<Job> {
  return apiFetch<Job>(`/jobs/${String(id)}`, { method: "PATCH", body: JSON.stringify(body) });
}

export function deleteJob(id: number): Promise<void> {
  return apiFetch<undefined>(`/jobs/${String(id)}`, { method: "DELETE" });
}
