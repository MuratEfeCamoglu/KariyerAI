import { SCORE_BAND_LABELS, scoreBand, type ScoreBand } from "../lib/constants.ts";

const BAND_CLASSES: Record<ScoreBand, string> = {
  high: "bg-band-high-bg text-band-high-text",
  mid: "bg-band-mid-bg text-band-mid-text",
  low: "bg-band-low-bg text-band-low-text",
};

/** Puanı bant renginde gösterir; puan yoksa nötr tire. */
export function BandBadge({ score }: { score: number | null }) {
  if (score === null) {
    return <span className="text-ink-subtle">—</span>;
  }
  const rounded = Math.round(score);
  const band = scoreBand(rounded);
  return (
    <span
      title={SCORE_BAND_LABELS[band]}
      className={`inline-flex min-w-9 justify-center rounded-full px-2 py-0.5 text-xs font-semibold ${BAND_CLASSES[band]}`}
    >
      <span className="sr-only">{`${SCORE_BAND_LABELS[band]}: `}</span>
      {rounded}
    </span>
  );
}
