interface FastApiFieldError {
  loc: (string | number)[];
  msg: string;
}

export class ApiError extends Error {
  readonly status: number;
  /** 422 yanıtlarında alan adı → Türkçe hata mesajı. */
  readonly fieldErrors: Record<string, string>;

  constructor(status: number, message: string, fieldErrors: Record<string, string> = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}

function isFieldErrorList(value: unknown): value is FastApiFieldError[] {
  return Array.isArray(value) && value.every((item) => typeof item === "object" && item !== null);
}

async function toApiError(response: Response): Promise<ApiError> {
  let detail: unknown = null;
  try {
    detail = ((await response.json()) as { detail?: unknown }).detail;
  } catch {
    // Gövdesi JSON olmayan hata (ör. proxy 502) genel mesaja düşer.
  }

  if (typeof detail === "string") {
    return new ApiError(response.status, detail);
  }
  if (isFieldErrorList(detail)) {
    const fieldErrors: Record<string, string> = {};
    for (const error of detail) {
      // ["body", "languages", 0, "level"] → "languages.0.level"
      const field = error.loc.slice(error.loc[0] === "body" ? 1 : 0).join(".");
      fieldErrors[field] ??= error.msg.replace(/^Value error, /, "");
    }
    return new ApiError(response.status, "Formda hatalı alanlar var", fieldErrors);
  }
  return new ApiError(response.status, "Beklenmeyen bir hata oluştu. Lütfen tekrar deneyin.");
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (typeof init.body === "string") {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`/api${path}`, { ...init, headers, credentials: "same-origin" });
  if (!response.ok) {
    throw await toApiError(response);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

/** Alanın kendi hatası ya da alt öğelerinden ilkinin hatası (ör. "required_skills.3"). */
export function getFieldError(error: unknown, field: string): string | undefined {
  if (!(error instanceof ApiError)) {
    return undefined;
  }
  const exact = error.fieldErrors[field];
  if (exact !== undefined) {
    return exact;
  }
  const nestedKey = Object.keys(error.fieldErrors).find((key) => key.startsWith(`${field}.`));
  return nestedKey === undefined ? undefined : error.fieldErrors[nestedKey];
}
