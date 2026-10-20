import { CircleCheck, TriangleAlert } from "lucide-react";

import type { Gap, GapKind } from "../types/cvCheck.ts";

const KIND_LABELS: Record<GapKind, string> = {
  required_skill: "Zorunlu beceri",
  experience: "Deneyim",
  education: "Eğitim",
  language: "Dil",
  preferred_skill: "Tercih edilen beceri",
};

/** Sunucu eksikleri önem sırasıyla döner; sıra korunur. */
export function GapList({ gaps }: { gaps: Gap[] }) {
  if (gaps.length === 0) {
    return (
      <p className="flex items-center gap-2 text-sm text-band-high-text">
        <CircleCheck size={18} strokeWidth={1.75} aria-hidden="true" />
        Kriterlerin hepsi CV'nde kanıtlı görünüyor.
      </p>
    );
  }
  return (
    <ol className="space-y-3" aria-label="Eksikler">
      {gaps.map((gap, index) => (
        <li
          key={`${gap.kind}-${String(index)}`}
          className="flex gap-3 rounded-md bg-fill-muted p-3"
        >
          <TriangleAlert
            size={18}
            strokeWidth={1.75}
            aria-hidden="true"
            className="mt-0.5 shrink-0 text-band-mid-text"
          />
          <div className="min-w-0">
            <p className="text-xs font-medium text-ink-subtle">
              {KIND_LABELS[gap.kind]} · {gap.criterion}
            </p>
            <p className="mt-0.5 text-sm text-ink">{gap.message}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}
