export interface UploadFileResult {
  filename: string;
  status: "accepted" | "rejected";
  application_id: number | null;
  /** Reddedilen dosyanın kendi kodu: 422 geçersiz, 409 tekrar. */
  error_code: number | null;
  detail: string | null;
}

export interface UploadResponse {
  application_ids: number[];
  files: UploadFileResult[];
}
