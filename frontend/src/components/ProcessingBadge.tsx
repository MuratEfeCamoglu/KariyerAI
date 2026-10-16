import { Clock, LoaderCircle } from "lucide-react";

import { PROCESSING_STATUS_LABELS } from "../lib/constants.ts";

export function ProcessingBadge({ status }: { status: "pending" | "processing" }) {
  const Icon = status === "processing" ? LoaderCircle : Clock;
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-info-bg px-2.5 py-0.5 text-xs font-medium whitespace-nowrap text-info">
      <Icon
        size={12}
        strokeWidth={2}
        aria-hidden="true"
        className={status === "processing" ? "animate-spin motion-reduce:animate-none" : ""}
      />
      {PROCESSING_STATUS_LABELS[status]}
    </span>
  );
}
