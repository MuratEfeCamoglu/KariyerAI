import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../api/client.ts";
import { uploadCvs } from "../api/jobs.ts";

interface FakeXhrConfig {
  status: number;
  body: unknown;
  progress?: [number, number];
}

function stubXhr({ status, body, progress }: FakeXhrConfig) {
  const sent: { method?: string; url?: string; form?: FormData } = {};

  class FakeXhr {
    status = 0;
    responseText = "";
    upload: { onprogress: ((event: ProgressEvent) => void) | null } = { onprogress: null };
    onload: (() => void) | null = null;
    onerror: (() => void) | null = null;

    open(method: string, url: string) {
      sent.method = method;
      sent.url = url;
    }

    send(form: FormData) {
      sent.form = form;
      if (progress) {
        this.upload.onprogress?.({
          lengthComputable: true,
          loaded: progress[0],
          total: progress[1],
        } as ProgressEvent);
      }
      this.status = status;
      this.responseText = JSON.stringify(body);
      this.onload?.();
    }
  }

  vi.stubGlobal("XMLHttpRequest", FakeXhr);
  return sent;
}

describe("uploadCvs", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("dosyaları 'files' alanında gönderir ve ilerlemeyi bildirir", async () => {
    const sent = stubXhr({
      status: 202,
      body: { application_ids: [1], files: [] },
      progress: [50, 200],
    });
    const onProgress = vi.fn();

    const result = await uploadCvs(9, [new File(["x"], "cv.pdf")], onProgress);

    expect(result.application_ids).toEqual([1]);
    expect(sent).toMatchObject({ method: "POST", url: "/api/jobs/9/cvs" });
    expect(sent.form?.getAll("files")).toHaveLength(1);
    expect(onProgress).toHaveBeenCalledWith(25);
  });

  it("hiçbir dosya kabul edilmese de dosya bazlı sonucu döner", async () => {
    stubXhr({
      status: 409,
      body: {
        detail: "Bu CV bu ilana zaten yüklendi",
        application_ids: [],
        files: [{ filename: "a.pdf", status: "rejected", error_code: 409 }],
      },
    });

    const result = await uploadCvs(9, [new File(["x"], "a.pdf")]);

    expect(result.files[0]?.status).toBe("rejected");
  });

  it("dosya bazlı sonuç yoksa ApiError fırlatır", async () => {
    stubXhr({ status: 409, body: { detail: "Kapalı ilana CV yüklenemez" } });

    await expect(uploadCvs(9, [new File(["x"], "a.pdf")])).rejects.toEqual(
      new ApiError(409, "Kapalı ilana CV yüklenemez"),
    );
  });
});
