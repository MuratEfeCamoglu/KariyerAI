import { useMemo, useState } from "react";

import { PageHeader } from "../components/PageHeader.tsx";
import { useAuditLogs } from "../hooks/useAudit.ts";
import {
  APPLICATION_STATUS_LABELS,
  AUDIT_ACTION_LABELS,
  JOB_STATUS_LABELS,
  PROCESSING_STATUS_LABELS,
  ROLE_LABELS,
} from "../lib/constants.ts";
import { formatDateTime } from "../lib/format.ts";

function actionLabel(action: string): string {
  return AUDIT_ACTION_LABELS[action] ?? action;
}

const PAYLOAD_LABELS: Record<string, string> = {
  from: "önceki",
  to: "yeni",
  status: "durum",
  score: "puan",
  model: "model",
  prompt: "prompt",
  job_id: "ilan",
  candidate_id: "aday",
  parse_status: "ayrıştırma",
  fields: "alanlar",
  role: "rol",
  is_active: "aktif",
  password_changed: "şifre değişti",
  application_count: "başvuru sayısı",
  step: "adım",
};

// Başvuru, işlem ve ilan durumları ile roller; anahtarlar birbiriyle çakışmaz.
const VALUE_LABELS: Record<string, string> = {
  ...APPLICATION_STATUS_LABELS,
  ...PROCESSING_STATUS_LABELS,
  ...JOB_STATUS_LABELS,
  ...ROLE_LABELS,
};

function formatValue(value: unknown): string {
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "boolean") return value ? "evet" : "hayır";
  if (typeof value === "string") return VALUE_LABELS[value] ?? value;
  return String(value);
}

function formatPayload(payload: Record<string, unknown>): string {
  return Object.entries(payload)
    .map(([key, value]) => `${PAYLOAD_LABELS[key] ?? key}: ${formatValue(value)}`)
    .join(" · ");
}

/** F12: son 500 kayıt; payload yalnızca id/durum/puan/model içerir (kişisel veri yok). */
export function AuditPage() {
  const logs = useAuditLogs();
  const [action, setAction] = useState("");

  const actions = useMemo(
    () => [...new Set((logs.data ?? []).map((entry) => entry.action))].sort(),
    [logs.data],
  );
  const visible = (logs.data ?? []).filter((entry) => action === "" || entry.action === action);

  return (
    <>
      <PageHeader title="Denetim kaydı" />
      <div className="mb-4 flex items-center gap-3">
        <label htmlFor="audit-action" className="text-sm font-medium text-ink">
          Eylem
        </label>
        <select
          id="audit-action"
          value={action}
          onChange={(event) => {
            setAction(event.target.value);
          }}
          className="h-10 rounded-md border border-line-strong bg-surface px-3 text-sm"
        >
          <option value="">Tümü</option>
          {actions.map((item) => (
            <option key={item} value={item}>
              {actionLabel(item)}
            </option>
          ))}
        </select>
        <span className="text-xs text-ink-subtle">Son 500 kayıt, yeniden eskiye</span>
      </div>

      {logs.isPending ? (
        <p className="text-sm text-ink-muted">Yükleniyor…</p>
      ) : logs.isError ? (
        <p className="text-sm text-ink-muted">Denetim kaydı yüklenemedi.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-line bg-surface shadow-xs">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-line bg-fill-muted text-xs font-medium text-ink-muted">
              <tr>
                <th className="px-4 py-3">Zaman</th>
                <th className="px-4 py-3">Kullanıcı</th>
                <th className="px-4 py-3">Eylem</th>
                <th className="px-4 py-3">Kayıt</th>
                <th className="px-4 py-3">Ayrıntı</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((entry) => (
                <tr key={entry.id} className="border-b border-line last:border-0">
                  <td className="px-4 py-2.5 whitespace-nowrap text-ink-muted">
                    {formatDateTime(entry.created_at)}
                  </td>
                  <td className="px-4 py-2.5 text-ink">{entry.actor_name ?? "Sistem"}</td>
                  <td className="px-4 py-2.5 text-ink">{actionLabel(entry.action)}</td>
                  <td className="px-4 py-2.5 whitespace-nowrap text-ink-muted">
                    {entry.entity_type} #{entry.entity_id ?? "—"}
                  </td>
                  <td className="px-4 py-2.5 text-xs text-ink-muted">
                    {formatPayload(entry.payload)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
