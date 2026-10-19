import { useId, useState, type ReactNode, type SubmitEvent } from "react";
import { Link, useNavigate, useParams } from "react-router";

import { ApiError, getFieldError } from "../api/client.ts";
import { Button } from "../components/Button.tsx";
import { CriteriaFields } from "../components/CriteriaFields.tsx";
import { FieldMessage } from "../components/FieldMessage.tsx";
import { PageHeader } from "../components/PageHeader.tsx";
import { TextField } from "../components/TextField.tsx";
import { useCreateJob, useJob, useUpdateJob } from "../hooks/useJobs.ts";
import { JOB_LIMITS, JOB_STATUS_LABELS, SCORE_WEIGHTS } from "../lib/constants.ts";
import type { Job, JobInput, JobStatus } from "../types/job.ts";

const EMPTY_JOB: JobInput = {
  title: "",
  department: "",
  description: "",
  required_skills: [],
  preferred_skills: [],
  min_experience_years: 0,
  min_education: "none",
  languages: [],
  status: "open",
};

function toJobInput(job: Job): JobInput {
  return {
    title: job.title,
    department: job.department,
    description: job.description,
    required_skills: job.required_skills,
    preferred_skills: job.preferred_skills,
    min_experience_years: job.min_experience_years,
    min_education: job.min_education,
    languages: job.languages,
    status: job.status,
  };
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-lg border border-line bg-surface p-6 shadow-xs">
      <h2 className="mb-4 text-lg font-semibold text-ink">{title}</h2>
      <div className="space-y-4">{children}</div>
    </section>
  );
}

interface JobFormProps {
  initial: JobInput;
  submitLabel: string;
  cancelTo: string;
  error: unknown;
  pending: boolean;
  onSubmit: (value: JobInput) => void;
}

function JobForm({ initial, submitLabel, cancelTo, error, pending, onSubmit }: JobFormProps) {
  const [form, setForm] = useState<JobInput>(initial);
  const descriptionId = useId();

  const set = <K extends keyof JobInput>(key: K, value: JobInput[K]) => {
    setForm((current) => ({ ...current, [key]: value }));
  };
  const update = (patch: Partial<JobInput>) => {
    setForm((current) => ({ ...current, ...patch }));
  };
  const fieldError = (field: string) => getFieldError(error, field);

  const handleSubmit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit({
      ...form,
      title: form.title.trim(),
      department: form.department.trim(),
      languages: form.languages.map((item) => ({ ...item, language: item.language.trim() })),
    });
  };

  const fieldErrorCount = error instanceof ApiError ? Object.keys(error.fieldErrors).length : 0;
  const summary =
    error instanceof ApiError
      ? fieldErrorCount > 0
        ? `Formda ${String(fieldErrorCount)} hatalı alan var. Lütfen işaretli alanları düzeltin.`
        : error.message
      : error
        ? "Beklenmeyen bir hata oluştu."
        : null;

  return (
    <form onSubmit={handleSubmit} noValidate className="grid gap-6 lg:grid-cols-[1fr_280px]">
      <div className="space-y-6">
        {summary && (
          <div
            role="alert"
            className="rounded-md border border-danger/20 bg-danger-bg px-4 py-3 text-sm text-danger"
          >
            {summary}
          </div>
        )}

        <Section title="Temel bilgiler">
          <TextField
            label="Başlık"
            required
            maxLength={JOB_LIMITS.titleMax}
            value={form.title}
            error={fieldError("title")}
            onChange={(event) => {
              set("title", event.target.value);
            }}
          />
          <TextField
            label="Departman"
            maxLength={JOB_LIMITS.departmentMax}
            value={form.department}
            error={fieldError("department")}
            onChange={(event) => {
              set("department", event.target.value);
            }}
          />
          <div>
            <div className="mb-1 flex items-baseline justify-between">
              <label htmlFor={descriptionId} className="text-sm font-medium text-ink">
                Açıklama
              </label>
              <span className="text-xs text-ink-subtle">
                {form.description.length}/{JOB_LIMITS.descriptionMax}
              </span>
            </div>
            <textarea
              id={descriptionId}
              rows={5}
              maxLength={JOB_LIMITS.descriptionMax}
              value={form.description}
              onChange={(event) => {
                set("description", event.target.value);
              }}
              className={`w-full rounded-md border bg-surface px-3 py-2 text-sm text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-500 ${fieldError("description") === undefined ? "border-line-strong" : "border-danger"}`}
            />
            <FieldMessage error={fieldError("description")} />
          </div>
        </Section>

        <Section title="Değerlendirme kriterleri">
          <CriteriaFields value={form} error={error} onChange={update} />
        </Section>

        <Section title="Durum">
          <div
            role="radiogroup"
            aria-label="İlan durumu"
            className="inline-flex rounded-md bg-fill-muted p-1"
          >
            {(["open", "closed"] as JobStatus[]).map((status) => (
              <button
                key={status}
                type="button"
                role="radio"
                aria-checked={form.status === status}
                onClick={() => {
                  set("status", status);
                }}
                className={`h-8 rounded-sm px-4 text-sm font-medium focus-visible:outline-2 focus-visible:outline-accent-500 ${form.status === status ? "bg-surface text-ink shadow-xs" : "text-ink-muted hover:text-ink"}`}
              >
                {JOB_STATUS_LABELS[status]}
              </button>
            ))}
          </div>
          <p className="text-xs text-ink-subtle">Kapalı ilana CV yüklenemez.</p>
        </Section>

        <div className="flex justify-end gap-2">
          <Link
            to={cancelTo}
            className="inline-flex h-10 items-center rounded-md border border-line-strong bg-surface px-4 text-sm font-medium text-ink hover:bg-fill-muted focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-500"
          >
            Vazgeç
          </Link>
          <Button type="submit" loading={pending}>
            {submitLabel}
          </Button>
        </div>
      </div>

      <aside className="lg:sticky lg:top-8 lg:self-start">
        <div className="rounded-lg border border-line bg-surface p-5 shadow-xs">
          <h2 className="text-sm font-semibold text-ink">Puan ağırlıkları</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {SCORE_WEIGHTS.map(({ key, label, weight }) => (
              <li key={key} className="flex justify-between text-ink-muted">
                <span>{label}</span>
                <span className="font-medium text-ink">{weight}</span>
              </li>
            ))}
          </ul>
          <p className="mt-3 border-t border-line pt-3 text-xs text-ink-subtle">
            Ağırlıklar tüm ilanlarda sabittir. Kriter yoksa o kalemin puanı tam verilir.
          </p>
        </div>
      </aside>
    </form>
  );
}

function NewJob() {
  const navigate = useNavigate();
  const createJob = useCreateJob();

  return (
    <>
      <PageHeader title="Yeni ilan" />
      <JobForm
        initial={EMPTY_JOB}
        submitLabel="İlanı oluştur"
        cancelTo="/jobs"
        error={createJob.error}
        pending={createJob.isPending}
        onSubmit={(value) => {
          createJob.mutate(value, {
            onSuccess: (job) => {
              void navigate(`/jobs/${String(job.id)}`);
            },
          });
        }}
      />
    </>
  );
}

function EditJob({ id }: { id: number }) {
  const navigate = useNavigate();
  const job = useJob(id);
  const updateJob = useUpdateJob(id);

  if (job.isPending) {
    return <p className="text-sm text-ink-muted">Yükleniyor…</p>;
  }
  if (job.isError) {
    return <p className="text-sm text-ink-muted">{job.error.message}</p>;
  }

  return (
    <>
      <PageHeader title="İlanı düzenle" />
      <JobForm
        initial={toJobInput(job.data)}
        submitLabel="Kaydet"
        cancelTo={`/jobs/${String(id)}`}
        error={updateJob.error}
        pending={updateJob.isPending}
        onSubmit={(value) => {
          updateJob.mutate(value, {
            onSuccess: () => {
              void navigate(`/jobs/${String(id)}`);
            },
          });
        }}
      />
    </>
  );
}

export function JobFormPage() {
  const { id } = useParams();
  return id === undefined ? <NewJob /> : <EditJob id={Number(id)} />;
}
