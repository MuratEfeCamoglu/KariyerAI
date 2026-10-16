import { ChevronLeft, ChevronRight, CircleAlert, RefreshCw, RotateCcw } from "lucide-react";
import { useState } from "react";

import { ApiError } from "../api/client.ts";
import { useApplications, useRescoreJob, useRetryApplication } from "../hooks/useApplications.ts";
import {
  AI_DISCLAIMER,
  APPLICATION_STATUS_LABELS,
  APPLICATION_STATUS_OPTIONS,
  PROCESSING_STATUS_LABELS,
  PROCESSING_STATUS_OPTIONS,
} from "../lib/constants.ts";
import { formatDateTime } from "../lib/format.ts";
import type {
  ApplicationFilters,
  ApplicationRow,
  ApplicationStatus,
  ProcessingStatus,
} from "../types/application.ts";
import { BandBadge } from "./BandBadge.tsx";
import { Button } from "./Button.tsx";
import { CriterionBars } from "./CriterionBars.tsx";
import { EmptyState } from "./EmptyState.tsx";
import { ProcessingBadge } from "./ProcessingBadge.tsx";
import { ScoreRing } from "./ScoreRing.tsx";
import { StatusBadge } from "./StatusBadge.tsx";

const NO_FILTERS: ApplicationFilters = { minScore: 0, statuses: [], parseStatus: null };

function hasFilters(filters: ApplicationFilters): boolean {
  return filters.minScore > 0 || filters.statuses.length > 0 || filters.parseStatus !== null;
}

/** Satırın işlem durumu: ayrıştırma hatası önce gelir, sonra puanlama. */
function rowState(
  row: ApplicationRow,
):
  | { kind: "done" }
  | { kind: "busy"; status: "pending" | "processing" }
  | { kind: "failed"; reason: string } {
  if (row.parse_status === "failed") {
    return { kind: "failed", reason: row.parse_error ?? "Ayrıştırma başarısız" };
  }
  if (row.score_status === "failed") {
    return { kind: "failed", reason: row.score_error ?? "Puanlama başarısız" };
  }
  if (row.parse_status !== "done") {
    return { kind: "busy", status: row.parse_status };
  }
  if (row.score_status !== "done") {
    return { kind: "busy", status: row.score_status };
  }
  return { kind: "done" };
}

function RetryButton({ row, jobId }: { row: ApplicationRow; jobId: number }) {
  const retry = useRetryApplication(jobId);
  const error =
    retry.error instanceof ApiError
      ? retry.error.message
      : retry.error
        ? "Yeniden denenemedi"
        : null;
  return (
    <div className="flex flex-col items-start gap-1">
      <Button
        variant="secondary"
        size="sm"
        loading={retry.isPending}
        onClick={() => {
          retry.mutate(row.id);
        }}
      >
        <RotateCcw size={14} strokeWidth={1.75} aria-hidden="true" />
        Yeniden dene
      </Button>
      {error && (
        <span role="alert" className="max-w-56 text-xs text-ink-muted">
          {error}
        </span>
      )}
    </div>
  );
}

function Filters({
  value,
  onChange,
}: {
  value: ApplicationFilters;
  onChange: (next: ApplicationFilters) => void;
}) {
  const toggleStatus = (status: ApplicationStatus) => {
    const statuses = value.statuses.includes(status)
      ? value.statuses.filter((item) => item !== status)
      : [...value.statuses, status];
    onChange({ ...value, statuses });
  };

  return (
    <div className="mb-4 flex flex-wrap items-end gap-x-6 gap-y-3 rounded-lg border border-line bg-surface p-4 shadow-xs">
      <label className="flex flex-col gap-1 text-sm text-ink">
        <span className="font-medium">
          Minimum puan: <span className="tabular-nums">{value.minScore}</span>
        </span>
        <input
          type="range"
          min={0}
          max={100}
          step={5}
          value={value.minScore}
          onChange={(event) => {
            onChange({ ...value, minScore: Number(event.target.value) });
          }}
          className="w-48 accent-brand-700"
        />
      </label>

      <fieldset className="flex flex-col gap-1">
        <legend className="mb-1 text-sm font-medium text-ink">Durum</legend>
        <div className="flex flex-wrap gap-1.5">
          {APPLICATION_STATUS_OPTIONS.map((status) => {
            const selected = value.statuses.includes(status);
            return (
              <button
                key={status}
                type="button"
                aria-pressed={selected}
                onClick={() => {
                  toggleStatus(status);
                }}
                className={`h-7 rounded-full border px-3 text-xs font-medium focus-visible:outline-2 focus-visible:outline-accent-500 ${selected ? "border-brand-700 bg-brand-50 text-brand-700" : "border-line-strong text-ink-muted hover:bg-fill-muted"}`}
              >
                {APPLICATION_STATUS_LABELS[status]}
              </button>
            );
          })}
        </div>
      </fieldset>

      <label className="flex flex-col gap-1 text-sm text-ink">
        <span className="font-medium">İşlem durumu</span>
        <select
          value={value.parseStatus ?? ""}
          onChange={(event) => {
            const next = event.target.value;
            onChange({ ...value, parseStatus: next === "" ? null : (next as ProcessingStatus) });
          }}
          className="h-8 rounded-md border border-line-strong bg-surface px-2 text-sm"
        >
          <option value="">Tümü</option>
          {PROCESSING_STATUS_OPTIONS.map((status) => (
            <option key={status} value={status}>
              {PROCESSING_STATUS_LABELS[status]}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}

interface ApplicationsTableProps {
  jobId: number;
}

export function ApplicationsTable({ jobId }: ApplicationsTableProps) {
  const [filters, setFilters] = useState<ApplicationFilters>(NO_FILTERS);
  const [page, setPage] = useState(1);
  const applications = useApplications(jobId, filters, page);
  const rescore = useRescoreJob(jobId);

  const changeFilters = (next: ApplicationFilters) => {
    setFilters(next);
    setPage(1);
  };

  const data = applications.data;
  const pageCount = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;
  const firstRank = data ? (data.page - 1) * data.page_size : 0;

  return (
    <section aria-labelledby="applications-heading">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 id="applications-heading" className="text-lg font-semibold text-ink">
            Aday sıralaması
          </h2>
          <p className="text-xs text-ink-subtle">{AI_DISCLAIMER}</p>
        </div>
        <div className="flex items-center gap-3">
          {data && data.processing_count > 0 && (
            <span className="text-xs text-ink-muted" aria-live="polite">
              {data.processing_count} CV işleniyor · liste otomatik yenileniyor
            </span>
          )}
          <Button
            variant="secondary"
            size="sm"
            loading={rescore.isPending}
            onClick={() => {
              rescore.mutate();
            }}
          >
            <RefreshCw size={14} strokeWidth={1.75} aria-hidden="true" />
            Yeniden puanla
          </Button>
        </div>
      </div>

      <Filters value={filters} onChange={changeFilters} />

      {applications.isPending ? (
        <p className="text-sm text-ink-muted">Yükleniyor…</p>
      ) : applications.isError ? (
        <p className="text-sm text-ink-muted">Adaylar yüklenemedi.</p>
      ) : data === undefined || data.items.length === 0 ? (
        <EmptyState
          title={hasFilters(filters) ? "Filtrelerle eşleşen başvuru yok" : "Henüz başvuru yok"}
        />
      ) : (
        <>
          <div className="overflow-x-auto rounded-lg border border-line bg-surface shadow-xs">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-line bg-fill-muted text-xs font-medium text-ink-muted">
                <tr>
                  <th className="px-4 py-3">#</th>
                  <th className="px-4 py-3">Aday</th>
                  <th className="px-4 py-3">Uyum puanı</th>
                  <th className="px-4 py-3">Kalemler</th>
                  <th className="px-4 py-3">Son pozisyon</th>
                  <th className="px-4 py-3 text-right">Deneyim</th>
                  <th className="px-4 py-3">Durum</th>
                  <th className="px-4 py-3">Yüklenme</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((row, index) => {
                  const state = rowState(row);
                  return (
                    <tr key={row.id} className="border-b border-line align-middle last:border-0">
                      <td className="px-4 py-3 text-ink-subtle tabular-nums">
                        {firstRank + index + 1}
                      </td>
                      <td className="px-4 py-3 font-medium text-ink">
                        {row.candidate_name ?? `Aday #${String(row.candidate_id)}`}
                      </td>
                      {state.kind === "done" && row.score !== null ? (
                        <>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              <ScoreRing score={row.score} size="md" />
                              <BandBadge score={row.score} label />
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            {row.item_points && <CriterionBars points={row.item_points} />}
                          </td>
                        </>
                      ) : state.kind === "failed" ? (
                        <td className="px-4 py-3" colSpan={2}>
                          <div className="flex items-start gap-3">
                            <span className="flex items-center gap-1.5 text-ink-muted">
                              <CircleAlert size={16} strokeWidth={1.75} aria-hidden="true" />
                              {state.reason}
                            </span>
                            <RetryButton row={row} jobId={jobId} />
                          </div>
                        </td>
                      ) : (
                        <td className="px-4 py-3" colSpan={2}>
                          <div className="flex items-center gap-3">
                            <span
                              className="h-[52px] w-[52px] animate-pulse rounded-full bg-fill-muted motion-reduce:animate-none"
                              aria-hidden="true"
                            />
                            <ProcessingBadge
                              status={state.kind === "busy" ? state.status : "processing"}
                            />
                          </div>
                        </td>
                      )}
                      <td className="px-4 py-3 text-ink-muted">{row.last_position ?? "—"}</td>
                      <td className="px-4 py-3 text-right text-ink-muted tabular-nums">
                        {row.total_experience_years === null
                          ? "—"
                          : `${row.total_experience_years.toLocaleString("tr-TR")} yıl`}
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={row.status} />
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-ink-muted">
                        {formatDateTime(row.created_at)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {pageCount > 1 && (
            <nav
              aria-label="Sayfalama"
              className="mt-3 flex items-center justify-end gap-2 text-sm text-ink-muted"
            >
              <Button
                variant="ghost"
                size="sm"
                aria-label="Önceki sayfa"
                disabled={page <= 1}
                onClick={() => {
                  setPage(page - 1);
                }}
              >
                <ChevronLeft size={16} strokeWidth={1.75} />
              </Button>
              <span>
                Sayfa {page} / {pageCount} · {data.total} başvuru
              </span>
              <Button
                variant="ghost"
                size="sm"
                aria-label="Sonraki sayfa"
                disabled={page >= pageCount}
                onClick={() => {
                  setPage(page + 1);
                }}
              >
                <ChevronRight size={16} strokeWidth={1.75} />
              </Button>
            </nav>
          )}
        </>
      )}
    </section>
  );
}
