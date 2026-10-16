import { Check } from "lucide-react";

import { APPLICATION_STATUS_CLASSES, APPLICATION_STATUS_LABELS } from "../lib/constants.ts";
import type { ApplicationStatus } from "../types/application.ts";

export function StatusBadge({ status }: { status: ApplicationStatus }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium whitespace-nowrap ${APPLICATION_STATUS_CLASSES[status]}`}
    >
      {status === "hired" && <Check size={12} strokeWidth={2} aria-hidden="true" />}
      {APPLICATION_STATUS_LABELS[status]}
    </span>
  );
}
