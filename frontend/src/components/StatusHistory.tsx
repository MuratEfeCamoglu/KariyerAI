import { APPLICATION_STATUS_LABELS } from "../lib/constants.ts";
import { formatDateTime } from "../lib/format.ts";
import type { StatusChange } from "../types/application.ts";

export function StatusHistory({ changes }: { changes: StatusChange[] }) {
  return (
    <section className="rounded-lg border border-line bg-surface p-5 shadow-xs">
      <h2 className="mb-3 text-base font-semibold text-ink">Durum geçmişi</h2>
      {changes.length === 0 ? (
        <p className="text-sm text-ink-muted">Durum henüz değiştirilmedi.</p>
      ) : (
        <ol className="space-y-3">
          {changes.map((change, index) => (
            <li key={index} className="text-sm">
              <p className="text-ink">
                {APPLICATION_STATUS_LABELS[change.from_status]} →{" "}
                <span className="font-medium">{APPLICATION_STATUS_LABELS[change.to_status]}</span>
              </p>
              <p className="text-xs text-ink-subtle">
                {change.actor_name ?? "Bilinmeyen kullanıcı"} · {formatDateTime(change.created_at)}
              </p>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
