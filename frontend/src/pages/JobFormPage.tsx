import { Plus, Trash2 } from "lucide-react";
import { useId, useState, type ReactNode, type SubmitEvent } from "react";
import { Link, useNavigate, useParams } from "react-router";

import { ApiError, getFieldError } from "../api/client.ts";
import { Button } from "../components/Button.tsx";
import { ChipInput } from "../components/ChipInput.tsx";
import { PageHeader } from "../components/PageHeader.tsx";
import { TextField } from "../components/TextField.tsx";
import { useCreateJob, useJob, useUpdateJob } from "../hooks/useJobs.ts";
import {
  EDUCATION_LABELS,
  EDUCATION_OPTIONS,
  JOB_LIMITS,
  JOB_STATUS_LABELS,
  LANGUAGE_LEVELS,
  SCORE_WEIGHTS,
} from "../lib/constants.ts";
import type {
  EducationLevel,
  Job,
  JobInput,
  JobLanguage,
  JobStatus,
  LanguageLevel,
} from "../types/job.ts";

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

// Genişlik içermez: aynı öğeye w-full ile başka bir genişlik verilince w-full kazanıyordu.
const fieldBaseClass =
  "h-10 rounded-md border bg-surface px-3 text-sm text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-500";
const selectClass = `${fieldBaseClass} w-full`;

function FieldMessage({ error }: { error: string | undefined }) {
  return error === undefined ? null : <p className="mt-1 text-xs text-danger">{error}</p>;
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
  const experienceId = useId();
  const educationId = useId();

  const set = <K extends keyof JobInput>(key: K, value: JobInput[K]) => {
    setForm((current) => ({ ...current, [key]: value }));
  };
  const setLanguage = (index: number, patch: Partial<JobLanguage>) => {
    set(
      "languages",
      form.languages.map((item, i) => (i === index ? { ...item, ...patch } : item)),
    );
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
          <ChipInput
            label="Zorunlu beceriler"
            placeholder="Ör. Python"
            max={JOB_LIMITS.skillsMax}
            value={form.required_skills}
            error={fieldError("required_skills")}
            onChange={(value) => {
              set("required_skills", value);
            }}
          />
          <ChipInput
            label="Tercih edilen beceriler"
            placeholder="Ör. Docker"
            max={JOB_LIMITS.skillsMax}
            value={form.preferred_skills}
            error={fieldError("preferred_skills")}
            onChange={(value) => {
              set("preferred_skills", value);
            }}
          />
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor={experienceId} className="mb-1 block text-sm font-medium text-ink">
                Minimum deneyim (yıl)
              </label>
              <input
                id={experienceId}
                type="number"
                min={0}
                max={JOB_LIMITS.experienceMax}
                step={1}
                value={form.min_experience_years}
                onChange={(event) => {
                  set("min_experience_years", event.target.valueAsNumber || 0);
                }}
                className={`${selectClass} ${fieldError("min_experience_years") === undefined ? "border-line-strong" : "border-danger"}`}
              />
              <FieldMessage error={fieldError("min_experience_years")} />
            </div>
            <div>
              <label htmlFor={educationId} className="mb-1 block text-sm font-medium text-ink">
                Minimum eğitim
              </label>
              <select
                id={educationId}
                value={form.min_education}
                onChange={(event) => {
                  set("min_education", event.target.value as EducationLevel);
                }}
                className={`${selectClass} border-line-strong`}
              >
                {EDUCATION_OPTIONS.map((level) => (
                  <option key={level} value={level}>
                    {EDUCATION_LABELS[level]}
                  </option>
                ))}
              </select>
              <FieldMessage error={fieldError("min_education")} />
            </div>
          </div>

          <fieldset>
            <div className="mb-1 flex items-baseline justify-between">
              <legend className="text-sm font-medium text-ink">Diller</legend>
              <span className="text-xs text-ink-subtle">
                {form.languages.length}/{JOB_LIMITS.languagesMax}
              </span>
            </div>
            <div className="space-y-2">
              {form.languages.map((item, index) => (
                <div key={index} className="flex gap-2">
                  <input
                    aria-label={`Dil ${String(index + 1)}`}
                    placeholder="Ör. İngilizce"
                    value={item.language}
                    onChange={(event) => {
                      setLanguage(index, { language: event.target.value });
                    }}
                    className={`${fieldBaseClass} min-w-0 flex-1 ${getFieldError(error, `languages.${String(index)}`) === undefined ? "border-line-strong" : "border-danger"}`}
                  />
                  <select
                    aria-label={`Dil ${String(index + 1)} seviyesi`}
                    value={item.level}
                    onChange={(event) => {
                      setLanguage(index, { level: event.target.value as LanguageLevel });
                    }}
                    className={`${fieldBaseClass} w-24 shrink-0 border-line-strong`}
                  >
                    {LANGUAGE_LEVELS.map((level) => (
                      <option key={level} value={level}>
                        {level}
                      </option>
                    ))}
                  </select>
                  <Button
                    variant="ghost"
                    aria-label={`Dil ${String(index + 1)} kaldır`}
                    onClick={() => {
                      set(
                        "languages",
                        form.languages.filter((_, i) => i !== index),
                      );
                    }}
                  >
                    <Trash2 size={16} strokeWidth={1.75} />
                  </Button>
                </div>
              ))}
            </div>
            <FieldMessage error={fieldError("languages")} />
            <Button
              variant="secondary"
              size="sm"
              className="mt-2"
              disabled={form.languages.length >= JOB_LIMITS.languagesMax}
              onClick={() => {
                set("languages", [...form.languages, { language: "", level: "B1" }]);
              }}
            >
              <Plus size={16} strokeWidth={1.75} aria-hidden="true" />
              Dil ekle
            </Button>
          </fieldset>
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
