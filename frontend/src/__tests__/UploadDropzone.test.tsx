import { QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../api/client.ts";
import { uploadCvs } from "../api/jobs.ts";
import { UploadDropzone } from "../components/UploadDropzone.tsx";
import { createQueryClient } from "../lib/queryClient.ts";
import type { UploadResponse } from "../types/upload.ts";

vi.mock("../api/jobs.ts", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api/jobs.ts")>()),
  uploadCvs: vi.fn(),
}));

const uploadMock = vi.mocked(uploadCvs);

function pdf(name: string, size = 1024): File {
  return new File([new Uint8Array(size)], name, { type: "application/pdf" });
}

function renderDropzone(disabled = false) {
  render(
    <QueryClientProvider client={createQueryClient()}>
      <UploadDropzone jobId={5} disabled={disabled} />
    </QueryClientProvider>,
  );
}

function choose(files: File[]) {
  fireEvent.change(screen.getByLabelText("CV dosyaları"), { target: { files } });
}

describe("UploadDropzone", () => {
  beforeEach(() => {
    uploadMock.mockReset();
  });
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("dosyaları yükler ve dosya bazlı sonucu gösterir", async () => {
    const response: UploadResponse = {
      application_ids: [11],
      files: [
        {
          filename: "a.pdf",
          status: "accepted",
          application_id: 11,
          error_code: null,
          detail: null,
        },
        {
          filename: "b.pdf",
          status: "rejected",
          application_id: null,
          error_code: 409,
          detail: "Bu CV bu ilana zaten yüklendi",
        },
      ],
    };
    uploadMock.mockResolvedValue(response);
    renderDropzone();

    choose([pdf("a.pdf"), pdf("b.pdf")]);

    const list = await screen.findByRole("list", { name: "Yüklenen dosyalar" });
    expect(await within(list).findByText("Yüklendi")).toBeInTheDocument();
    expect(within(list).getByText("Reddedildi: Bu CV bu ilana zaten yüklendi")).toBeInTheDocument();
    expect(uploadMock).toHaveBeenCalledWith(5, expect.any(Array), expect.any(Function));
  });

  it("5 MB'tan büyük dosyayı göndermeden reddeder", async () => {
    uploadMock.mockResolvedValue({
      application_ids: [1],
      files: [
        {
          filename: "ok.pdf",
          status: "accepted",
          application_id: 1,
          error_code: null,
          detail: null,
        },
      ],
    });
    renderDropzone();

    choose([pdf("buyuk.pdf", 5 * 1024 * 1024 + 1), pdf("ok.pdf")]);

    expect(await screen.findByText("Reddedildi: Dosya 5 MB'tan büyük")).toBeInTheDocument();
    expect(await screen.findByText("Yüklendi")).toBeInTheDocument();
    const sent = uploadMock.mock.calls[0]?.[1] ?? [];
    expect(sent.map((file) => file.name)).toEqual(["ok.pdf"]);
  });

  it("20'den fazla dosyada yükleme yapmadan uyarır", () => {
    renderDropzone();

    choose(Array.from({ length: 21 }, (_, i) => pdf(`cv${String(i)}.pdf`)));

    expect(screen.getByRole("alert")).toHaveTextContent("en fazla 20 dosya");
    expect(uploadMock).not.toHaveBeenCalled();
  });

  it("istek bütünüyle başarısızsa nedeni her dosyada gösterir", async () => {
    uploadMock.mockRejectedValue(new ApiError(409, "Kapalı ilana CV yüklenemez"));
    renderDropzone();

    choose([pdf("a.pdf")]);

    expect(await screen.findByText("Reddedildi: Kapalı ilana CV yüklenemez")).toBeInTheDocument();
  });

  it("kapalı ilanda devre dışıdır", () => {
    renderDropzone(true);

    expect(screen.getByText("Kapalı ilana CV yüklenemez.")).toBeInTheDocument();
    expect(screen.getByLabelText("CV dosyaları")).toBeDisabled();
  });
});
