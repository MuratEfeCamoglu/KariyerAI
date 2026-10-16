import { JOB_STATUS_LABELS } from "../lib/constants.ts";
import type { JobStatus } from "../types/job.ts";

const STATUS_CLASSES: Record<JobStatus, string> = {
  open: "bg-accent-50 text-accent-700",
  closed: "bg-fill-muted text-ink-muted",
};

export function JobStatusBadge({ status }: { status: JobStatus }) {
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_CLASSES[status]}`}
    >
      {JOB_STATUS_LABELS[status]}
    </span>
  );
}
