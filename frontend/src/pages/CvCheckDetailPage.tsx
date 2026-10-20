import { CircleAlert, Info, RotateCcw, Trash2 } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router";

import { ApiError } from "../api/client.ts";
import { BandBadge } from "../components/BandBadge.tsx";
import { Button } from "../components/Button.tsx";
import { Card } from "../components/Card.tsx";
import { EmptyState } from "../components/EmptyState.tsx";
import { EvidenceQuote } from "../components/EvidenceQuote.tsx";
import { GapList } from "../components/GapList.tsx";
import { Modal } from "../components/Modal.tsx";
import { ParsedCvCard } from "../components/ParsedCvCard.tsx";
import { ProcessingBadge } from "../components/ProcessingBadge.tsx";
import { ScoreBreakdown } from "../components/ScoreBreakdown.tsx";
import { ScoreRing } from "../components/ScoreRing.tsx";
import {
  isProcessing,
  useCvCheck,
  useDeleteCvCheck,
  useRetryCvCheck,
} from "../hooks/useCvChecks.ts";
import { SEEKER_DISCLAIMER } from "../lib/constants.ts";
import type { CriterionResult } from "../types/application.ts";
import type { CvCheck } from "../types/cvCheck.ts";

function StatusPanel({ check }: { check: CvCheck }) {
  const retry = useRetryCvCheck(check.id);
  if (isProcessing(check)) {
    return (
      <div className="flex items-center gap-3 text-sm text-ink-muted">
        <ProcessingBadge status={check.parse_status === "pending" ? "pending" : "processing"} />
        CV'n işleniyor; sonuç hazır olunca bu sayfa kendini yeniler.
      </div>
    );
  }
  const reason =
    check.parse_status === "failed"
      ? (check.parse_error ?? "Ayrıştırma başarısız")
      : (check.score_error ?? "Değerlendirme başarısız");
  const retryError = retry.error instanceof ApiError ? retry.error.message : null;
  return (
    <div className="space-y-2 text-sm text-ink-muted">
      <div className="flex flex-wrap items-center gap-3">
        <CircleAlert size={18} strokeWidth={1.75} aria-hidden="true" />
        <span>{reason}</span>
        <Button
          variant="secondary"
          size="sm"
          loading={retry.isPending}
          onClick={() => {
            retry.mutate();
          }}
        >
          <RotateCcw size={14} strokeWidth={1.75} aria-hidden="true" />
          Yeniden dene
        </Button>
      </div>
      {retryError && (
        <p role="alert" className="text-xs text-danger">
          {retryError}
        </p>
      )}
    </div>
  );
}

function strengthsOf(check: CvCheck): CriterionResult[] {
  const breakdown = check.score_breakdown;
  if (breakdown === null) return [];
  return [
    ...breakdown.required_skills.items,
    ...breakdown.languages.items,
    ...breakdown.preferred_skills.items,
  ].filter((item) => item.met);
}

function DeleteDialog({
  pending,
  onConfirm,
  onClose,
}: {
  pending: boolean;
  onConfirm: () => void;
  onClose: () => void;
}) {
  return (
    <Modal title="Değerlendirmeyi sil" onClose={onClose}>
      <p className="text-sm text-ink-muted">
        Bu değerlendirme ve yüklediğin CV dosyası kalıcı olarak silinir. Bu işlem geri alınamaz.
      </p>
      <div className="mt-6 flex justify-end gap-2">
        <Button variant="secondary" onClick={onClose}>
          Vazgeç
        </Button>
        <Button variant="danger" loading={pending} onClick={onConfirm}>
          Kalıcı olarak sil
        </Button>
      </div>
    </Modal>
  );
}

export function CvCheckDetailPage() {
  const id = Number(useParams().id);
  const query = useCvCheck(id);
  const remove = useDeleteCvCheck();
  const navigate = useNavigate();
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  if (query.isPending) {
    return <p className="text-sm text-ink-muted">Yükleniyor…</p>;
  }
  if (query.isError) {
    return (
      <EmptyState
        title={query.error.message}
        action={
          <Link to="/cv-checks" className="text-sm font-medium text-accent-700 hover:underline">
            Değerlendirmelerime dön
          </Link>
        }
      />
    );
  }

  const check = query.data;
  const done = check.score_breakdown !== null && !isProcessing(check);
  const strengths = strengthsOf(check);

  return (
    <>
      <nav aria-label="Konum" className="mb-2 text-sm text-ink-subtle">
        <Link to="/cv-checks" className="hover:text-ink hover:underline">
          CV Değerlendirmelerim
        </Link>
        <span aria-hidden="true"> / </span>
        <span className="text-ink-muted">{check.title}</span>
      </nav>

      <header className="mb-4 flex flex-wrap items-center gap-6 rounded-lg border border-line bg-surface p-6 shadow-xs">
        {check.score !== null && done ? (
          <ScoreRing score={check.score} size="lg" />
        ) : (
          <span
            className="h-[104px] w-[104px] rounded-full border-8 border-line"
            aria-hidden="true"
          />
        )}
        <div className="min-w-0 flex-1">
          <h1 className="text-[1.75rem] leading-9 font-semibold text-ink">{check.title}</h1>
          <p className="mt-1 text-sm text-ink-muted">{check.original_filename}</p>
          {check.score !== null && done && (
            <div className="mt-2">
              <BandBadge score={check.score} label />
            </div>
          )}
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="text-danger"
          onClick={() => {
            setConfirmingDelete(true);
          }}
        >
          <Trash2 size={14} strokeWidth={1.75} aria-hidden="true" />
          Sil
        </Button>
      </header>

      {confirmingDelete && (
        <DeleteDialog
          pending={remove.isPending}
          onClose={() => {
            setConfirmingDelete(false);
          }}
          onConfirm={() => {
            remove.mutate(check.id, {
              onSuccess: () => {
                void navigate("/cv-checks", { replace: true });
              },
            });
          }}
        />
      )}

      <div
        role="note"
        className="sticky top-0 z-10 mb-6 flex items-center gap-2 rounded-md border border-info/20 bg-info-bg px-4 py-2.5 text-sm text-info"
      >
        <Info size={16} strokeWidth={1.75} aria-hidden="true" />
        {SEEKER_DISCLAIMER}
      </div>

      {!done ? (
        <Card title="Durum">
          <StatusPanel check={check} />
        </Card>
      ) : (
        <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
          <div className="space-y-6">
            <Card title="Geliştirilecek noktalar">
              <GapList gaps={check.gaps} />
            </Card>
            {check.ai_summary && (
              <Card title="AI özeti">
                <p className="text-sm text-ink">{check.ai_summary}</p>
              </Card>
            )}
            {check.score_breakdown && (
              <Card title="Puan kırılımı">
                <ScoreBreakdown breakdown={check.score_breakdown} />
              </Card>
            )}
          </div>
          <div className="space-y-6">
            <Card title="Güçlü yanların">
              {strengths.length === 0 ? (
                <p className="text-sm text-ink-muted">Kanıtlı karşılanan beceri bulunamadı.</p>
              ) : (
                <ul className="space-y-3 text-sm">
                  {strengths.map((item) => (
                    <li key={item.criterion}>
                      <p className="font-medium text-ink">{item.criterion}</p>
                      {item.evidence && (
                        <p className="mt-0.5 text-ink-muted">
                          <EvidenceQuote text={item.evidence} highlight={item.criterion} />
                        </p>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </Card>
            {check.parsed && <ParsedCvCard parsed={check.parsed} />}
          </div>
        </div>
      )}
    </>
  );
}
