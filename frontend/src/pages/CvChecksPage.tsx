import { CircleAlert, Plus } from "lucide-react";
import { Link } from "react-router";

import { BandBadge } from "../components/BandBadge.tsx";
import { EmptyState } from "../components/EmptyState.tsx";
import { PageHeader } from "../components/PageHeader.tsx";
import { ProcessingBadge } from "../components/ProcessingBadge.tsx";
import { isProcessing, useCvChecks } from "../hooks/useCvChecks.ts";
import { formatDateTime } from "../lib/format.ts";
import type { CvCheckListItem } from "../types/cvCheck.ts";

const newLinkClass =
  "inline-flex h-10 items-center gap-2 rounded-md bg-brand-700 px-4 text-sm font-medium text-white hover:bg-brand-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-500";

function ResultCell({ check }: { check: CvCheckListItem }) {
  if (isProcessing(check)) {
    return (
      <ProcessingBadge
        status={
          check.parse_status === "pending" && check.score_status === "pending"
            ? "pending"
            : "processing"
        }
      />
    );
  }
  if (check.parse_status === "failed" || check.score_status === "failed") {
    return (
      <span className="inline-flex items-center gap-1 text-sm text-ink-muted">
        <CircleAlert size={14} strokeWidth={1.75} aria-hidden="true" />
        Başarısız
      </span>
    );
  }
  return <BandBadge score={check.score} label />;
}

export function CvChecksPage() {
  const checks = useCvChecks();

  return (
    <>
      <PageHeader
        title="CV Değerlendirmelerim"
        actions={
          <Link to="/cv-checks/new" className={newLinkClass}>
            <Plus size={16} strokeWidth={1.75} aria-hidden="true" />
            Yeni değerlendirme
          </Link>
        }
      />

      {checks.isPending ? (
        <p className="text-sm text-ink-muted">Yükleniyor…</p>
      ) : checks.isError ? (
        <EmptyState title={checks.error.message} />
      ) : checks.data.length === 0 ? (
        <EmptyState
          title="Henüz değerlendirme yok"
          description="CV'ni yükle, hedeflediğin işin kriterlerini gir; CV'nde neyin eksik olduğunu gösterelim."
          action={
            <Link to="/cv-checks/new" className={newLinkClass}>
              İlk değerlendirmeyi başlat
            </Link>
          }
        />
      ) : (
        <div className="overflow-hidden rounded-lg border border-line bg-surface shadow-xs">
          <table className="w-full text-sm">
            <thead className="bg-fill-muted text-left text-xs font-medium text-ink-muted">
              <tr>
                <th className="px-4 py-3">Hedef iş</th>
                <th className="px-4 py-3">CV</th>
                <th className="px-4 py-3">Sonuç</th>
                <th className="px-4 py-3">Tarih</th>
              </tr>
            </thead>
            <tbody>
              {checks.data.map((check) => (
                <tr key={check.id} className="border-t border-line hover:bg-fill-muted/50">
                  <td className="px-4 py-3">
                    <Link
                      to={`/cv-checks/${String(check.id)}`}
                      className="font-medium text-ink hover:underline"
                    >
                      {check.title}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-ink-muted">{check.original_filename}</td>
                  <td className="px-4 py-3">
                    <ResultCell check={check} />
                  </td>
                  <td className="px-4 py-3 text-ink-muted">{formatDateTime(check.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
