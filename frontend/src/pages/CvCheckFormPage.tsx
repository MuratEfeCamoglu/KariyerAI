import { useId, useState, type SubmitEvent } from "react";
import { Link, useNavigate } from "react-router";

import { ApiError, getFieldError } from "../api/client.ts";
import { Button } from "../components/Button.tsx";
import { Card } from "../components/Card.tsx";
import { CriteriaFields, type CriteriaInput } from "../components/CriteriaFields.tsx";
import { FieldMessage } from "../components/FieldMessage.tsx";
import { PageHeader } from "../components/PageHeader.tsx";
import { TextField } from "../components/TextField.tsx";
import { useCreateCvCheck } from "../hooks/useCvChecks.ts";
import { JOB_LIMITS, UPLOAD_LIMITS } from "../lib/constants.ts";

const EMPTY_CRITERIA: CriteriaInput = {
  required_skills: [],
  preferred_skills: [],
  min_experience_years: 0,
  min_education: "none",
  languages: [],
};

const ACCEPTED = ".pdf,.docx";

function fileProblem(file: File | null): string | undefined {
  if (file === null) return "CV dosyası seçin";
  if (!/\.(pdf|docx)$/i.test(file.name)) return "Yalnızca PDF ve DOCX dosyaları kabul edilir";
  if (file.size > UPLOAD_LIMITS.maxFileBytes) return "Dosya 5 MB'tan büyük";
  return undefined;
}

export function CvCheckFormPage() {
  const navigate = useNavigate();
  const create = useCreateCvCheck();
  const [title, setTitle] = useState("");
  const [jobText, setJobText] = useState("");
  const [criteria, setCriteria] = useState<CriteriaInput>(EMPTY_CRITERIA);
  const [file, setFile] = useState<File | null>(null);
  const [fileTouched, setFileTouched] = useState(false);
  const jobTextId = useId();
  const fileId = useId();

  const localFileError = fileTouched ? fileProblem(file) : undefined;
  const fileError = localFileError ?? getFieldError(create.error, "file");

  const handleSubmit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFileTouched(true);
    if (file === null || fileProblem(file) !== undefined) {
      return;
    }
    create.mutate(
      {
        criteria: {
          ...criteria,
          title: title.trim(),
          job_text: jobText,
          languages: criteria.languages.map((item) => ({
            ...item,
            language: item.language.trim(),
          })),
        },
        file,
      },
      {
        onSuccess: (check) => {
          void navigate(`/cv-checks/${String(check.id)}`);
        },
      },
    );
  };

  const error = create.error;
  const summary =
    error instanceof ApiError
      ? Object.keys(error.fieldErrors).length > 0
        ? "Formda hatalı alanlar var. Lütfen işaretli alanları düzeltin."
        : error.message
      : error
        ? "Beklenmeyen bir hata oluştu."
        : null;

  return (
    <>
      <PageHeader title="Yeni değerlendirme" />
      <form onSubmit={handleSubmit} noValidate className="max-w-3xl space-y-6">
        {summary && (
          <div
            role="alert"
            className="rounded-md border border-danger/20 bg-danger-bg px-4 py-3 text-sm text-danger"
          >
            {summary}
          </div>
        )}

        <Card title="Hedef iş">
          <div className="space-y-4">
            <TextField
              label="İş başlığı"
              required
              placeholder="Ör. Backend Geliştirici"
              maxLength={JOB_LIMITS.titleMax}
              value={title}
              error={getFieldError(error, "title")}
              onChange={(event) => {
                setTitle(event.target.value);
              }}
            />
            <div>
              <label htmlFor={jobTextId} className="mb-1 block text-sm font-medium text-ink">
                İlan metni (isteğe bağlı)
              </label>
              <textarea
                id={jobTextId}
                rows={4}
                maxLength={JOB_LIMITS.descriptionMax}
                value={jobText}
                onChange={(event) => {
                  setJobText(event.target.value);
                }}
                className="w-full rounded-md border border-line-strong bg-surface px-3 py-2 text-sm text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-500"
              />
              <p className="mt-1 text-xs text-ink-subtle">
                Yalnızca senin notun olarak saklanır; değerlendirme aşağıdaki kriterlere göre
                yapılır.
              </p>
            </div>
          </div>
        </Card>

        <Card title="İlanın kriterleri">
          <div className="space-y-4">
            <CriteriaFields
              value={criteria}
              error={error}
              onChange={(patch) => {
                setCriteria((current) => ({ ...current, ...patch }));
              }}
            />
          </div>
        </Card>

        <Card title="CV">
          <label htmlFor={fileId} className="mb-1 block text-sm font-medium text-ink">
            CV dosyası (PDF veya DOCX, en fazla 5 MB)
          </label>
          <input
            id={fileId}
            type="file"
            accept={ACCEPTED}
            onChange={(event) => {
              setFile(event.target.files?.[0] ?? null);
              setFileTouched(true);
            }}
            className="block w-full text-sm text-ink file:mr-3 file:h-9 file:rounded-md file:border file:border-line-strong file:bg-surface file:px-3 file:text-sm file:font-medium file:text-ink hover:file:bg-fill-muted"
          />
          <FieldMessage error={fileError} />
        </Card>

        <div className="flex justify-end gap-2">
          <Link
            to="/cv-checks"
            className="inline-flex h-10 items-center rounded-md border border-line-strong bg-surface px-4 text-sm font-medium text-ink hover:bg-fill-muted focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-500"
          >
            Vazgeç
          </Link>
          <Button type="submit" loading={create.isPending}>
            Değerlendir
          </Button>
        </div>
      </form>
    </>
  );
}
