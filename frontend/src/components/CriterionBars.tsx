import { SCORE_WEIGHTS } from "../lib/constants.ts";
import type { ItemPoints } from "../types/application.ts";

/** Tablodaki 5 kalemlik mini puan çubukları; dolgu brand-700 (bant rengi değil, TASARIM §3). */
export function CriterionBars({ points }: { points: ItemPoints }) {
  return (
    <ul className="flex flex-col gap-1" aria-label="Kalem puanları">
      {SCORE_WEIGHTS.map(({ key, label, weight }) => {
        const value = points[key];
        const percent = Math.min(100, Math.max(0, (value / weight) * 100));
        const description = `${label}: ${value.toLocaleString("tr-TR")}/${String(weight)}`;
        return (
          <li key={key} title={description} className="flex items-center">
            <span className="sr-only">{description}</span>
            <span
              className="h-1.5 w-16 overflow-hidden rounded-full bg-fill-muted"
              aria-hidden="true"
            >
              <span
                className="block h-full rounded-full bg-brand-700"
                style={{ width: `${String(percent)}%` }}
              />
            </span>
          </li>
        );
      })}
    </ul>
  );
}
