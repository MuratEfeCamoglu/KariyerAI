import { CircleAlert, Download, Info, Trash2 } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router";

import { cvDownloadUrl } from "../api/applications.ts";
import { ApiError } from "../api/client.ts";
import { BandBadge } from "../components/BandBadge.tsx";
import { Button } from "../components/Button.tsx";
import { Card } from "../components/Card.tsx";
import { ConfirmDeleteModal } from "../components/ConfirmDeleteModal.tsx";
import { EmptyState } from "../components/EmptyState.tsx";
import { NotesPanel } from "../components/NotesPanel.tsx";
import { ParsedCvCard } from "../components/ParsedCvCard.tsx";
import { ProcessingBadge } from "../components/ProcessingBadge.tsx";
import { RetryButton } from "../components/RetryButton.tsx";
import { ScoreBreakdown } from "../components/ScoreBreakdown.tsx";
import { ScoreRing } from "../components/ScoreRing.tsx";
import { StatusHistory } from "../components/StatusHistory.tsx";
import { StatusSelect } from "../components/StatusSelect.tsx";
import { useApplication, useChangeStatus, useDeleteCandidate } from "../hooks/useApplications.ts";
import { useCurrentUser } from "../hooks/useAuth.ts";
import { AI_DISCLAIMER } from "../lib/constants.ts";
import type { ApplicationDetail } from "../types/application.ts";

function ProcessingState({ detail }: { detail: ApplicationDetail }) {
  const { candidate } = detail;
  if (candidate.parse_status === "failed" || detail.score_status === "failed") {
    const reason =
      candidate.parse_status === "failed"
        ? (candidate.parse_error ?? "Ayrıştırma başarısız")
        : (detail.score_error ?? "Puanlama başarısız");
    return (
      <div className="flex flex-wrap items-center gap-3 text-sm text-ink-muted">
        <CircleAlert size={18} strokeWidth={1.75} aria-hidden="true" />
        <span>{reason}</span>
        <RetryButton applicationId={detail.id} />
      </div>
    );
  }
  const status = candidate.parse_status !== "done" ? candidate.parse_status : detail.score_status;
  return (
    <div className="flex items-center gap-3 text-sm text-ink-muted">
      <ProcessingBadge status={status === "pending" ? "pending" : "processing"} />
      CV işleniyor; puan hazır olunca bu sayfa kendini yeniler.
    </div>
  );
}

export function ApplicationDetailPage() {
  const id = Number(useParams().id);
  const application = useApplication(id);
  const changeStatus = useChangeStatus(id);
  const deleteCandidate = useDeleteCandidate();
  const navigate = useNavigate();
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const { data: currentUser } = useCurrentUser();

  if (application.isPending) {
    return <p className="text-sm text-ink-muted">Yükleniyor…</p>;
  }
  if (application.isError) {
    return (
      <EmptyState
        title={application.error.message}
        action={
          <Link to="/jobs" className="text-sm font-medium text-accent-700 hover:underline">
            İlanlara dön
          </Link>
        }
      />
    );
  }

  const detail = application.data;
  const { candidate } = detail;
  const name = candidate.full_name ?? `Aday #${String(candidate.id)}`;
  const contact = [candidate.email, candidate.phone].filter(Boolean).join(" · ");
  const statusError = changeStatus.error instanceof ApiError ? changeStatus.error.message : null;

  return (
    <>
      <nav aria-label="Konum" className="mb-2 text-sm text-ink-subtle">
        <Link to="/jobs" className="hover:text-ink hover:underline">
          İlanlar
        </Link>
        <span aria-hidden="true"> / </span>
        <Link to={`/jobs/${String(detail.job.id)}`} className="hover:text-ink hover:underline">
          {detail.job.title}
        </Link>
        <span aria-hidden="true"> / </span>
        <span className="text-ink-muted">{name}</span>
      </nav>

      <header className="mb-4 flex flex-wrap items-center gap-6 rounded-lg border border-line bg-surface p-6 shadow-xs">
        {detail.score !== null ? (
          <ScoreRing score={detail.score} size="lg" />
        ) : (
          <span
            className="h-[104px] w-[104px] rounded-full border-8 border-line"
            aria-hidden="true"
          />
        )}
        <div className="min-w-0 flex-1">
          <h1 className="text-[1.75rem] leading-9 font-semibold text-ink">{name}</h1>
          {contact && <p className="mt-1 text-sm text-ink-muted">{contact}</p>}
          <div className="mt-2 flex flex-wrap items-center gap-3">
            {detail.score !== null && <BandBadge score={detail.score} label />}
            <a
              href={cvDownloadUrl(candidate.id)}
              download
              className="inline-flex items-center gap-1.5 text-sm font-medium text-accent-700 hover:underline"
            >
              <Download size={16} strokeWidth={1.75} aria-hidden="true" />
              CV'yi indir ({candidate.original_filename})
            </a>
          </div>
        </div>
        <div className="w-56">
          <StatusSelect
            value={detail.status}
            disabled={changeStatus.isPending}
            onChange={(status) => {
              changeStatus.mutate(status);
            }}
          />
          {statusError && (
            <p role="alert" className="mt-1 text-xs text-danger">
              {statusError}
            </p>
          )}
          {currentUser?.role === "admin" && (
            <Button
              variant="ghost"
              size="sm"
              className="mt-2 text-danger"
              onClick={() => {
                setConfirmingDelete(true);
              }}
            >
              <Trash2 size={14} strokeWidth={1.75} aria-hidden="true" />
              Adayı sil (KVKK)
            </Button>
          )}
        </div>
      </header>

      {confirmingDelete && (
        <ConfirmDeleteModal
          candidateId={candidate.id}
          pending={deleteCandidate.isPending}
          error={deleteCandidate.error}
          onClose={() => {
            setConfirmingDelete(false);
          }}
          onConfirm={() => {
            deleteCandidate.mutate(candidate.id, {
              onSuccess: () => {
                void navigate(`/jobs/${String(detail.job.id)}`, { replace: true });
              },
            });
          }}
        />
      )}

      {/* AGENT.md: bu uyarı kaldırılamaz; sayfa kaydırılsa da görünür kalır. */}
      <div
        role="note"
        className="sticky top-0 z-10 mb-6 flex items-center gap-2 rounded-md border border-info/20 bg-info-bg px-4 py-2.5 text-sm text-info"
      >
        <Info size={16} strokeWidth={1.75} aria-hidden="true" />
        {AI_DISCLAIMER}
      </div>

      <div className="grid gap-6 xl:grid-cols-[1fr_340px]">
        <div className="space-y-6">
          <Card title="Puan kırılımı">
            {detail.score_breakdown ? (
              <ScoreBreakdown breakdown={detail.score_breakdown} />
            ) : (
              <ProcessingState detail={detail} />
            )}
          </Card>

          {detail.ai_summary && (
            <Card title="AI özeti">
              <p className="text-sm text-ink">{detail.ai_summary}</p>
              <p className="mt-3 text-xs text-ink-subtle">
                Model: {detail.llm_model ?? "—"} · Prompt: {detail.prompt_version ?? "—"} · Bu özet
                öneri niteliğindedir.
              </p>
            </Card>
          )}

          {detail.candidate.parsed && <ParsedCvCard parsed={detail.candidate.parsed} />}
        </div>

        <div className="space-y-6">
          {currentUser && (
            <NotesPanel applicationId={id} notes={detail.notes} currentUserId={currentUser.id} />
          )}
          <StatusHistory changes={detail.status_history} />
        </div>
      </div>
    </>
  );
}
