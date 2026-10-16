import { Plus, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router";

import { BandBadge } from "../components/BandBadge.tsx";
import { EmptyState } from "../components/EmptyState.tsx";
import { JobStatusBadge } from "../components/JobStatusBadge.tsx";
import { PageHeader } from "../components/PageHeader.tsx";
import { useJobs } from "../hooks/useJobs.ts";
import { foldText, formatDate } from "../lib/format.ts";
import type { JobStatus } from "../types/job.ts";

type StatusFilter = "all" | JobStatus;

const STATUS_FILTERS: { value: StatusFilter; label: string }[] = [
  { value: "all", label: "Tümü" },
  { value: "open", label: "Açık" },
  { value: "closed", label: "Kapalı" },
];

function NewJobLink() {
  return (
    <Link
      to="/jobs/new"
      className="inline-flex h-10 items-center gap-2 rounded-md bg-brand-700 px-4 text-sm font-medium text-white hover:bg-brand-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-500"
    >
      <Plus size={16} strokeWidth={1.75} aria-hidden="true" />
      Yeni ilan
    </Link>
  );
}

export function JobsPage() {
  const jobs = useJobs();
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");

  const visibleJobs = useMemo(() => {
    const needle = foldText(query);
    return (jobs.data ?? []).filter(
      (job) =>
        (statusFilter === "all" || job.status === statusFilter) &&
        (needle === "" || foldText(`${job.title} ${job.department}`).includes(needle)),
    );
  }, [jobs.data, query, statusFilter]);

  if (jobs.isPending) {
    return (
      <>
        <PageHeader title="İlanlar" />
        <p className="text-sm text-ink-muted">Yükleniyor…</p>
      </>
    );
  }
  if (jobs.isError) {
    return (
      <>
        <PageHeader title="İlanlar" />
        <p className="text-sm text-ink-muted">İlanlar yüklenemedi. Lütfen sayfayı yenileyin.</p>
      </>
    );
  }

  if (jobs.data.length === 0) {
    return (
      <>
        <PageHeader title="İlanlar" />
        <EmptyState
          title="Henüz ilan yok — ilk ilanını oluştur"
          description="İlan oluşturduktan sonra CV yükleyip adayları sıralayabilirsiniz."
          action={<NewJobLink />}
        />
      </>
    );
  }

  return (
    <>
      <PageHeader title="İlanlar" actions={<NewJobLink />} />

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="relative w-full max-w-xs">
          <Search
            size={16}
            strokeWidth={1.75}
            aria-hidden="true"
            className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-ink-subtle"
          />
          <input
            type="search"
            aria-label="İlan ara"
            placeholder="Başlık veya departman ara"
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
            }}
            className="h-10 w-full rounded-md border border-line-strong bg-surface pr-3 pl-9 text-sm placeholder:text-ink-subtle focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-500"
          />
        </div>
        <div
          role="radiogroup"
          aria-label="Durum"
          className="inline-flex rounded-md bg-fill-muted p-1"
        >
          {STATUS_FILTERS.map(({ value, label }) => (
            <button
              key={value}
              type="button"
              role="radio"
              aria-checked={statusFilter === value}
              onClick={() => {
                setStatusFilter(value);
              }}
              className={`h-8 rounded-sm px-3 text-sm font-medium focus-visible:outline-2 focus-visible:outline-accent-500 ${statusFilter === value ? "bg-surface text-ink shadow-xs" : "text-ink-muted hover:text-ink"}`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {visibleJobs.length === 0 ? (
        <EmptyState title="Aramanızla eşleşen ilan yok" />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-line bg-surface shadow-xs">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-line bg-fill-muted text-xs font-medium text-ink-muted">
              <tr>
                <th className="px-4 py-3">İlan</th>
                <th className="px-4 py-3">Durum</th>
                <th className="px-4 py-3 text-right">Başvuru</th>
                <th className="px-4 py-3 text-center">En yüksek</th>
                <th className="px-4 py-3 text-center">Ortalama</th>
                <th className="px-4 py-3">Oluşturulma</th>
              </tr>
            </thead>
            <tbody>
              {visibleJobs.map((job) => (
                <tr key={job.id} className="border-b border-line last:border-0 hover:bg-canvas">
                  <td className="px-4 py-3">
                    <Link
                      to={`/jobs/${String(job.id)}`}
                      className="font-medium text-ink hover:text-accent-700 hover:underline focus-visible:outline-2 focus-visible:outline-accent-500"
                    >
                      {job.title}
                    </Link>
                    {job.department && (
                      <p className="mt-0.5 text-xs text-ink-subtle">{job.department}</p>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <JobStatusBadge status={job.status} />
                  </td>
                  <td className="px-4 py-3 text-right text-ink">{job.application_count}</td>
                  <td className="px-4 py-3 text-center">
                    <BandBadge score={job.top_score} />
                  </td>
                  <td className="px-4 py-3 text-center">
                    <BandBadge score={job.avg_score} />
                  </td>
                  <td className="px-4 py-3 text-ink-muted">{formatDate(job.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
