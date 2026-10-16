import { SCORE_BAND_LABELS, scoreBand, type ScoreBand } from "../lib/constants.ts";

type Size = "sm" | "md" | "lg";

const SIZES: Record<Size, { box: number; stroke: number; text: string }> = {
  sm: { box: 36, stroke: 3, text: "text-xs" },
  md: { box: 52, stroke: 4, text: "text-base" },
  lg: { box: 104, stroke: 8, text: "text-score" },
};

// Halka bant renginde (grafik tonu); sayı her zaman ink (TASARIM §1 kontrast kuralı).
const RING_CLASSES: Record<ScoreBand, string> = {
  high: "stroke-band-high",
  mid: "stroke-band-mid",
  low: "stroke-band-low",
};

interface ScoreRingProps {
  score: number;
  size?: Size;
}

export function ScoreRing({ score, size = "md" }: ScoreRingProps) {
  const { box, stroke, text } = SIZES[size];
  const band = scoreBand(score);
  const radius = (box - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const filled = (Math.min(Math.max(score, 0), 100) / 100) * circumference;

  return (
    <span
      role="img"
      aria-label={`Puan ${String(score)}, ${SCORE_BAND_LABELS[band]}`}
      className="relative inline-flex shrink-0 items-center justify-center"
      style={{ width: box, height: box }}
    >
      <svg
        width={box}
        height={box}
        viewBox={`0 0 ${String(box)} ${String(box)}`}
        aria-hidden="true"
      >
        <circle
          cx={box / 2}
          cy={box / 2}
          r={radius}
          fill="none"
          strokeWidth={stroke}
          className="stroke-line"
        />
        <circle
          cx={box / 2}
          cy={box / 2}
          r={radius}
          fill="none"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${String(filled)} ${String(circumference)}`}
          transform={`rotate(-90 ${String(box / 2)} ${String(box / 2)})`}
          className={RING_CLASSES[band]}
        />
      </svg>
      <span aria-hidden="true" className={`absolute font-semibold text-ink ${text}`}>
        {score}
      </span>
    </span>
  );
}
