import { CheckCircle2, CircleAlert, FileUp, LoaderCircle } from "lucide-react";
import { useId, useState, type DragEvent } from "react";

import { ApiError, getFieldError } from "../api/client.ts";
import { useUploadCvs } from "../hooks/useJobs.ts";
import { UPLOAD_LIMITS } from "../lib/constants.ts";

type RowState = { kind: "uploading" } | { kind: "accepted" } | { kind: "rejected"; reason: string };

interface Row {
  key: string;
  name: string;
  state: RowState;
}

interface UploadDropzoneProps {
  jobId: number;
  disabled?: boolean;
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return getFieldError(error, "files") ?? error.message;
  }
  return "Beklenmeyen bir hata oluştu.";
}

export function UploadDropzone({ jobId, disabled = false }: UploadDropzoneProps) {
  const inputId = useId();
  const upload = useUploadCvs(jobId);
  const [rows, setRows] = useState<Row[]>([]);
  const [progress, setProgress] = useState<number | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const busy = upload.isPending;

  const start = (selected: File[]) => {
    if (disabled || busy || selected.length === 0) {
      return;
    }
    if (selected.length > UPLOAD_LIMITS.maxFiles) {
      setNotice(`Tek seferde en fazla ${String(UPLOAD_LIMITS.maxFiles)} dosya yükleyebilirsiniz.`);
      return;
    }
    setNotice(null);

    // Büyük dosyayı boşuna göndermemek için boyut tarayıcıda da kontrol edilir; tür kontrolü
    // (dosya içeriğine göre) yalnızca sunucuda yapılır (F4c).
    const stamp = Date.now();
    const initialRows: Row[] = selected.map((file, index) => ({
      key: `${String(stamp)}-${String(index)}`,
      name: file.name,
      state:
        file.size > UPLOAD_LIMITS.maxFileBytes
          ? { kind: "rejected", reason: "Dosya 5 MB'tan büyük" }
          : { kind: "uploading" },
    }));
    const toSend = selected.filter((file) => file.size <= UPLOAD_LIMITS.maxFileBytes);
    setRows(initialRows);
    if (toSend.length === 0) {
      return;
    }

    setProgress(0);
    const pendingKeys = initialRows
      .filter((row) => row.state.kind === "uploading")
      .map((r) => r.key);
    upload.mutate(
      { files: toSend, onProgress: setProgress },
      {
        onSuccess: (response) => {
          const byKey = new Map(pendingKeys.map((key, index) => [key, response.files[index]]));
          setRows((current) =>
            current.map((row) => {
              const result = byKey.get(row.key);
              if (result === undefined) return row;
              return {
                ...row,
                state:
                  result.status === "accepted"
                    ? { kind: "accepted" }
                    : { kind: "rejected", reason: result.detail ?? "Dosya reddedildi" },
              };
            }),
          );
        },
        onError: (error) => {
          const reason = errorMessage(error);
          setRows((current) =>
            current.map((row) =>
              row.state.kind === "uploading"
                ? { ...row, state: { kind: "rejected", reason } }
                : row,
            ),
          );
        },
        onSettled: () => {
          setProgress(null);
        },
      },
    );
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);
    start(Array.from(event.dataTransfer.files));
  };

  return (
    <div>
      <div
        onDragOver={(event) => {
          event.preventDefault();
          if (!disabled) setDragging(true);
        }}
        onDragLeave={() => {
          setDragging(false);
        }}
        onDrop={handleDrop}
        aria-disabled={disabled}
        className={`flex flex-col items-center rounded-lg border-2 border-dashed px-6 py-8 text-center transition-colors ${
          disabled
            ? "cursor-not-allowed border-line bg-fill-muted"
            : dragging
              ? "border-accent-500 bg-accent-50"
              : "border-line-strong bg-surface"
        }`}
      >
        <FileUp
          size={24}
          strokeWidth={1.75}
          aria-hidden="true"
          className={disabled ? "text-ink-subtle" : "text-brand-700"}
        />
        {disabled ? (
          <p className="mt-2 text-sm text-ink-muted">Kapalı ilana CV yüklenemez.</p>
        ) : (
          <>
            <p className="mt-2 text-sm text-ink">
              CV dosyalarını buraya sürükleyin veya{" "}
              <label
                htmlFor={inputId}
                className="cursor-pointer font-medium text-accent-700 underline-offset-2 hover:underline"
              >
                bilgisayardan seçin
              </label>
            </p>
            <p className="mt-1 text-xs text-ink-subtle">
              PDF veya DOCX, en fazla 20 dosya, dosya başına 5 MB
            </p>
          </>
        )}
        <input
          id={inputId}
          type="file"
          multiple
          accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          disabled={disabled || busy}
          aria-label="CV dosyaları"
          className="sr-only"
          onChange={(event) => {
            start(Array.from(event.target.files ?? []));
            // Aynı dosya tekrar seçilebilsin diye değer sıfırlanır.
            event.target.value = "";
          }}
        />
      </div>

      {notice && (
        <p role="alert" className="mt-2 text-sm text-danger">
          {notice}
        </p>
      )}

      {rows.length > 0 && (
        <ul
          aria-label="Yüklenen dosyalar"
          className="mt-4 divide-y divide-line rounded-lg border border-line bg-surface"
        >
          {rows.map((row) => (
            <li
              key={row.key}
              className="flex items-center justify-between gap-4 px-4 py-2.5 text-sm"
            >
              <span className="truncate text-ink">{row.name}</span>
              {row.state.kind === "uploading" && (
                <span className="flex shrink-0 items-center gap-1.5 text-ink-muted">
                  <LoaderCircle
                    size={16}
                    strokeWidth={1.75}
                    className="animate-spin motion-reduce:animate-none"
                    aria-hidden="true"
                  />
                  Yükleniyor{progress === null ? "" : ` %${String(progress)}`}
                </span>
              )}
              {row.state.kind === "accepted" && (
                <span className="flex shrink-0 items-center gap-1.5 text-band-high-text">
                  <CheckCircle2 size={16} strokeWidth={1.75} aria-hidden="true" />
                  Yüklendi
                </span>
              )}
              {row.state.kind === "rejected" && (
                <span className="flex shrink-0 items-center gap-1.5 text-ink-muted">
                  <CircleAlert size={16} strokeWidth={1.75} aria-hidden="true" />
                  Reddedildi: {row.state.reason}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
