import type { Job, JobInput, JobListItem } from "../types/job.ts";
import type { UploadResponse } from "../types/upload.ts";
import { ApiError, apiFetch, errorFromBody } from "./client.ts";

export function listJobs(): Promise<JobListItem[]> {
  return apiFetch<JobListItem[]>("/jobs");
}

export function getJob(id: number): Promise<JobListItem> {
  return apiFetch<JobListItem>(`/jobs/${String(id)}`);
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

function isUploadResponse(body: unknown): body is UploadResponse {
  return typeof body === "object" && body !== null && "files" in body && "application_ids" in body;
}

/**
 * CV yükler. `fetch` yükleme ilerlemesi vermediği için XHR kullanılır.
 * Hiçbir dosya kabul edilmese de (409/422) yanıt dosya bazlı sonuç içeriyorsa sonuç döner;
 * yalnızca istek bütünüyle başarısızsa (oturum yok, kapalı ilan vb.) ApiError fırlatılır.
 */
export function uploadCvs(
  jobId: number,
  files: File[],
  onProgress?: (percent: number) => void,
): Promise<UploadResponse> {
  return new Promise((resolve, reject) => {
    const form = new FormData();
    for (const file of files) {
      form.append("files", file, file.name);
    }

    const xhr = new XMLHttpRequest();
    xhr.open("POST", `/api/jobs/${String(jobId)}/cvs`);
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };
    xhr.onload = () => {
      let body: unknown = null;
      try {
        body = JSON.parse(xhr.responseText);
      } catch {
        // JSON olmayan gövde aşağıda genel hataya düşer.
      }
      if (isUploadResponse(body)) {
        resolve(body);
      } else {
        reject(errorFromBody(xhr.status, body));
      }
    };
    xhr.onerror = () => {
      reject(new ApiError(0, "Sunucuya ulaşılamadı. Bağlantınızı kontrol edin."));
    };
    xhr.send(form);
  });
}
