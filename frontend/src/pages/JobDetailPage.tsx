import { Pencil, Trash2 } from "lucide-react";
import { useState, type ReactNode } from "react";
import { Link, useNavigate, useParams } from "react-router";

import { ApiError } from "../api/client.ts";
import { Button } from "../components/Button.tsx";
import { EmptyState } from "../components/EmptyState.tsx";
import { JobStatusBadge } from "../components/JobStatusBadge.tsx";
import { Modal } from "../components/Modal.tsx";
import { useDeleteJob, useJob } from "../hooks/useJobs.ts";
import { EDUCATION_LABELS } from "../lib/constants.ts";
import { formatDate } from "../lib/format.ts";
import type { Job } from "../types/job.ts";

function Chips({ items, emptyText }: { items: string[]; emptyText: string }) {
  if (items.length === 0) {
    return <span className="text-sm text-ink-subtle">{emptyText}</span>;
  }
  return (
    <ul className="flex flex-wrap gap-2">
      {items.map((item) => (
        <li key={item} className="rounded-full bg-brand-50 px-2.5 py-0.5 text-sm text-brand-700">
          {item}
        </li>
      ))}
    </ul>
  );
}

function Criterion({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt className="mb-1 text-xs font-medium text-ink-subtle">{label}</dt>
      <dd className="text-sm text-ink">{children}</dd>
    </div>
  );
}

function DeleteJobModal({ job, onClose }: { job: Job; onClose: () => void }) {
  const navigate = useNavigate();
  const deleteJob = useDeleteJob();
  const errorMessage =
    deleteJob.error instanceof ApiError
      ? deleteJob.error.message
      : deleteJob.error
        ? "Beklenmeyen bir hata oluştu."
        : null;

  return (
    <Modal title="İlanı sil" onClose={onClose}>
      <p className="text-sm text-ink-muted">
        <span className="font-medium text-ink">{job.title}</span> ilanı kalıcı olarak silinecek.
        Başvurusu olan ilanlar silinemez; bunun yerine ilanı kapatabilirsiniz.
      </p>
      {errorMessage && (
        <p role="alert" className="mt-3 rounded-md bg-danger-bg px-3 py-2 text-sm text-danger">
          {errorMessage}
        </p>
      )}
      <div className="mt-6 flex justify-end gap-2">
        <Button variant="secondary" onClick={onClose}>
          Vazgeç
        </Button>
        <Button
          variant="danger"
          loading={deleteJob.isPending}
          onClick={() => {
            deleteJob.mutate(job.id, {
              onSuccess: () => {
                void navigate("/jobs", { replace: true });
              },
            });
          }}
        >
          Sil
        </Button>
      </div>
    </Modal>
  );
}

export function JobDetailPage() {
  const id = Number(useParams().id);
  const job = useJob(id);
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  if (job.isPending) {
    return <p className="text-sm text-ink-muted">Yükleniyor…</p>;
  }
  if (job.isError) {
    return (
      <EmptyState
        title={job.error.message}
        action={
          <Link to="/jobs" className="text-sm font-medium text-accent-700 hover:underline">
            İlanlara dön
          </Link>
        }
      />
    );
  }

  const data = job.data;
  return (
    <>
      <nav aria-label="Konum" className="mb-2 text-sm text-ink-subtle">
        <Link to="/jobs" className="hover:text-ink hover:underline">
          İlanlar
        </Link>
        <span aria-hidden="true"> / </span>
        <span className="text-ink-muted">{data.title}</span>
      </nav>

      <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-[1.75rem] leading-9 font-semibold text-ink">{data.title}</h1>
            <JobStatusBadge status={data.status} />
          </div>
          <p className="mt-1 text-sm text-ink-muted">
            {data.department ? `${data.department} · ` : ""}
            {formatDate(data.created_at)} tarihinde oluşturuldu
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            to={`/jobs/${String(id)}/edit`}
            className="inline-flex h-10 items-center gap-2 rounded-md border border-line-strong bg-surface px-4 text-sm font-medium text-ink hover:bg-fill-muted focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-500"
          >
            <Pencil size={16} strokeWidth={1.75} aria-hidden="true" />
            Düzenle
          </Link>
          <Button
            variant="secondary"
            onClick={() => {
              setConfirmingDelete(true);
            }}
          >
            <Trash2 size={16} strokeWidth={1.75} aria-hidden="true" />
            Sil
          </Button>
        </div>
      </header>

      <section className="mb-6 rounded-lg border border-line bg-surface p-6 shadow-xs">
        <h2 className="mb-4 text-lg font-semibold text-ink">Kriterler</h2>
        <dl className="grid gap-5 md:grid-cols-2">
          <Criterion label="Zorunlu beceriler">
            <Chips items={data.required_skills} emptyText="—" />
          </Criterion>
          <Criterion label="Tercih edilen beceriler">
            <Chips items={data.preferred_skills} emptyText="Yok" />
          </Criterion>
          <Criterion label="Minimum deneyim">
            {data.min_experience_years === 0
              ? "Aranmıyor"
              : `${String(data.min_experience_years)} yıl`}
          </Criterion>
          <Criterion label="Minimum eğitim">{EDUCATION_LABELS[data.min_education]}</Criterion>
          <Criterion label="Diller">
            <Chips
              items={data.languages.map((item) => `${item.language} · ${item.level}`)}
              emptyText="Aranmıyor"
            />
          </Criterion>
        </dl>
        {data.description && (
          <div className="mt-6 border-t border-line pt-4">
            <h3 className="mb-1 text-xs font-medium text-ink-subtle">Açıklama</h3>
            <p className="text-sm whitespace-pre-line text-ink">{data.description}</p>
          </div>
        )}
      </section>

      <section>
        <h2 className="mb-3 text-lg font-semibold text-ink">Başvurular</h2>
        <EmptyState title="Henüz başvuru yok" />
      </section>

      {confirmingDelete && (
        <DeleteJobModal
          job={data}
          onClose={() => {
            setConfirmingDelete(false);
          }}
        />
      )}
    </>
  );
}
