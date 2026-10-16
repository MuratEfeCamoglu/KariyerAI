import { CircleAlert, Download, Info } from "lucide-react";
import type { ReactNode } from "react";
import { Link, useParams } from "react-router";

import { cvDownloadUrl } from "../api/applications.ts";
import { ApiError } from "../api/client.ts";
import { BandBadge } from "../components/BandBadge.tsx";
import { EmptyState } from "../components/EmptyState.tsx";
import { NotesPanel } from "../components/NotesPanel.tsx";
import { ProcessingBadge } from "../components/ProcessingBadge.tsx";
import { RetryButton } from "../components/RetryButton.tsx";
import { ScoreBreakdown } from "../components/ScoreBreakdown.tsx";
import { ScoreRing } from "../components/ScoreRing.tsx";
import { StatusHistory } from "../components/StatusHistory.tsx";
import { StatusSelect } from "../components/StatusSelect.tsx";
import { useApplication, useChangeStatus } from "../hooks/useApplications.ts";
import { useCurrentUser } from "../hooks/useAuth.ts";
import { AI_DISCLAIMER, EDUCATION_LABELS } from "../lib/constants.ts";
import type { ApplicationDetail } from "../types/application.ts";

function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-lg border border-line bg-surface p-6 shadow-xs">
      <h2 className="mb-4 text-lg font-semibold text-ink">{title}</h2>
      {children}
    </section>
  );
}

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

function ParsedCvCard({ detail }: { detail: ApplicationDetail }) {
  const parsed = detail.candidate.parsed;
  if (parsed === null) {
    return null;
  }
  return (
    <Card title="Ayrıştırılmış CV">
      <dl className="space-y-5 text-sm">
        {parsed.summary && (
          <div>
            <dt className="mb-1 text-xs font-medium text-ink-subtle">Özet</dt>
            <dd className="text-ink">{parsed.summary}</dd>
          </div>
        )}
        <div>
          <dt className="mb-1 text-xs font-medium text-ink-subtle">Deneyim</dt>
          <dd>
            {parsed.experiences.length === 0 ? (
              <span className="text-ink-muted">Bulunamadı</span>
            ) : (
              <ul className="space-y-2">
                {parsed.experiences.map((item, index) => (
                  <li key={index}>
                    <p className="font-medium text-ink">
                      {item.title}
                      {item.company && (
                        <span className="font-normal text-ink-muted"> · {item.company}</span>
                      )}
                    </p>
                    <p className="text-xs text-ink-subtle">
                      {item.start ?? "?"} – {item.end === "present" ? "halen" : (item.end ?? "?")}
                    </p>
                    {item.description && (
                      <p className="mt-0.5 text-ink-muted">{item.description}</p>
                    )}
                  </li>
                ))}
              </ul>
            )}
            <p className="mt-2 text-xs text-ink-subtle">
              Toplam deneyim: {parsed.total_experience_years.toLocaleString("tr-TR")} yıl
              (tarihlerden hesaplandı; çakışan dönemler bir kez sayıldı)
            </p>
          </dd>
        </div>
        <div>
          <dt className="mb-1 text-xs font-medium text-ink-subtle">Eğitim</dt>
          <dd>
            {parsed.education.length === 0 ? (
              <span className="text-ink-muted">Bulunamadı</span>
            ) : (
              <ul className="space-y-1">
                {parsed.education.map((item, index) => (
                  <li key={index} className="text-ink">
                    {EDUCATION_LABELS[item.level]}
                    {item.field && ` · ${item.field}`}
                    {item.school && <span className="text-ink-muted"> · {item.school}</span>}
                    {item.end_year !== null && (
                      <span className="text-ink-subtle"> · {item.end_year}</span>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </dd>
        </div>
        <div>
          <dt className="mb-1 text-xs font-medium text-ink-subtle">Beceriler</dt>
          <dd>
            {parsed.skills.length === 0 ? (
              <span className="text-ink-muted">Bulunamadı</span>
            ) : (
              <ul className="flex flex-wrap gap-1.5">
                {parsed.skills.map((skill) => (
                  <li
                    key={skill}
                    className="rounded-full bg-fill-muted px-2.5 py-0.5 text-xs text-ink"
                  >
                    {skill}
                  </li>
                ))}
              </ul>
            )}
          </dd>
        </div>
        <div>
          <dt className="mb-1 text-xs font-medium text-ink-subtle">Diller</dt>
          <dd className="text-ink">
            {parsed.languages.length === 0
              ? "Bulunamadı"
              : parsed.languages
                  .map((item) => `${item.language}${item.level ? ` (${item.level})` : ""}`)
                  .join(", ")}
          </dd>
        </div>
      </dl>
    </Card>
  );
}

export function ApplicationDetailPage() {
  const id = Number(useParams().id);
  const application = useApplication(id);
  const changeStatus = useChangeStatus(id);
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
        </div>
      </header>

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

          <ParsedCvCard detail={detail} />
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
