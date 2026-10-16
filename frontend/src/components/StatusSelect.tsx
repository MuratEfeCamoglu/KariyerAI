import { useId } from "react";

import { APPLICATION_STATUS_LABELS, APPLICATION_STATUS_OPTIONS } from "../lib/constants.ts";
import type { ApplicationStatus } from "../types/application.ts";

interface StatusSelectProps {
  value: ApplicationStatus;
  onChange: (status: ApplicationStatus) => void;
  disabled?: boolean;
}

/** F9: 6 durum arasında serbest geçiş; değişikliği yalnızca kullanıcı yapar. */
export function StatusSelect({ value, onChange, disabled = false }: StatusSelectProps) {
  const id = useId();
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-xs font-medium text-ink-subtle">
        Başvuru durumu
      </label>
      <select
        id={id}
        value={value}
        disabled={disabled}
        onChange={(event) => {
          onChange(event.target.value as ApplicationStatus);
        }}
        className="h-10 rounded-md border border-line-strong bg-surface px-3 text-sm text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-500 disabled:opacity-50"
      >
        {APPLICATION_STATUS_OPTIONS.map((status) => (
          <option key={status} value={status}>
            {APPLICATION_STATUS_LABELS[status]}
          </option>
        ))}
      </select>
    </div>
  );
}
