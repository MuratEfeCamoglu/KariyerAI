import { Check, X } from "lucide-react";
import type { ReactNode } from "react";

import { EDUCATION_LABELS, EVIDENCE_STATUS_LABELS } from "../lib/constants.ts";
import type {
  CriterionResult,
  ListComponent,
  ScoreBreakdown as Breakdown,
} from "../types/application.ts";
import { EvidenceQuote } from "./EvidenceQuote.tsx";

function formatPoints(value: number): string {
  return value.toLocaleString("tr-TR", { maximumFractionDigits: 1 });
}

function CriterionBar({ points, weight }: { points: number; weight: number }) {
  const percent = Math.min(100, Math.max(0, (points / weight) * 100));
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-fill-muted" aria-hidden="true">
      <div className="h-full rounded-full bg-brand-700" style={{ width: `${String(percent)}%` }} />
    </div>
  );
}

function Section({
  title,
  points,
  weight,
  formula,
  children,
}: {
  title: string;
  points: number;
  weight: number;
  formula: string;
  children: ReactNode;
}) {
  return (
    <section className="border-b border-line py-4 first:pt-0 last:border-0 last:pb-0">
      <div className="mb-1 flex items-baseline justify-between gap-3">
        <h3 className="text-sm font-semibold text-ink">{title}</h3>
        <span className="text-sm font-semibold text-ink tabular-nums">
          {formatPoints(points)} / {weight}
        </span>
      </div>
      <CriterionBar points={points} weight={weight} />
      <p className="mt-1 text-xs text-ink-subtle">{formula}</p>
      <div className="mt-3">{children}</div>
    </section>
  );
}

function CriterionItem({ item }: { item: CriterionResult }) {
  const level =
    item.required_level !== null
      ? ` (istenen ${item.required_level}${item.candidate_level ? `, CV'de ${item.candidate_level}` : ""})`
      : "";
  return (
    <li className="py-1.5">
      <div className="flex items-start gap-2 text-sm">
        {item.met ? (
          <Check
            size={16}
            strokeWidth={2}
            className="mt-0.5 shrink-0 text-band-high-text"
            aria-hidden="true"
          />
        ) : (
          <X
            size={16}
            strokeWidth={2}
            className="mt-0.5 shrink-0 text-ink-subtle"
            aria-hidden="true"
          />
        )}
        <span className="font-medium text-ink">
          {item.criterion}
          {level}
        </span>
        <span
          className={`ml-auto shrink-0 text-xs ${item.met ? "text-band-high-text" : "text-ink-muted"}`}
        >
          {item.met ? "Karşılandı" : EVIDENCE_STATUS_LABELS[item.status]}
        </span>
      </div>
      {item.evidence && <EvidenceQuote text={item.evidence} highlight={item.criterion} />}
    </li>
  );
}

function ListSection({ title, component }: { title: string; component: ListComponent }) {
  const formula =
    component.total === 0
      ? `Kriter yok — ${String(component.weight)} puanın tamamı verilir`
      : `${String(component.weight)} × ${String(component.met)}/${String(component.total)} karşılanan`;
  return (
    <Section title={title} points={component.points} weight={component.weight} formula={formula}>
      {component.items.length > 0 && (
        <ul className="divide-y divide-line">
          {component.items.map((item) => (
            <CriterionItem key={item.criterion} item={item} />
          ))}
        </ul>
      )}
    </Section>
  );
}

function period(start: string | null, end: string | null): string {
  const to = end === "present" ? "halen" : (end ?? "?");
  return `${start ?? "?"} – ${to}`;
}

/** F8 / B3: kalem kalem puan kırılımı; her kalem kanıtını ya da açık bir ibareyi gösterir. */
export function ScoreBreakdown({ breakdown }: { breakdown: Breakdown }) {
  const { experience, education } = breakdown;
  const experienceFormula =
    experience.required_years === 0
      ? "Deneyim şartı yok — 25 puanın tamamı verilir"
      : `25 × min(1, ${formatPoints(experience.candidate_years)} / ${String(experience.required_years)} yıl)`;
  const educationFormula =
    education.required === "none"
      ? "Eğitim şartı yok — 15 puanın tamamı verilir"
      : `İstenen: ${EDUCATION_LABELS[education.required]} · CV'de: ${education.candidate ? EDUCATION_LABELS[education.candidate] : "belirtilmemiş"} (eşit/üstü 15, bir alt 7, daha düşük 0)`;

  return (
    <div>
      <ListSection title="Zorunlu beceriler" component={breakdown.required_skills} />
      <Section
        title="Deneyim"
        points={experience.points}
        weight={experience.weight}
        formula={experienceFormula}
      >
        {experience.records.length === 0 ? (
          <p className="text-sm text-ink-muted">CV'de tarihli deneyim kaydı bulunamadı.</p>
        ) : (
          <ul className="space-y-1 text-sm text-ink">
            {experience.records.map((record, index) => (
              <li key={index}>
                <span className="font-medium">{record.title}</span>
                {record.company && <span className="text-ink-muted"> · {record.company}</span>}
                <span className="text-ink-subtle"> · {period(record.start, record.end)}</span>
              </li>
            ))}
          </ul>
        )}
      </Section>
      <Section
        title="Eğitim"
        points={education.points}
        weight={education.weight}
        formula={educationFormula}
      >
        {education.records.length === 0 ? (
          <p className="text-sm text-ink-muted">CV'de eğitim kaydı bulunamadı.</p>
        ) : (
          <ul className="space-y-1 text-sm text-ink">
            {education.records.map((record, index) => (
              <li key={index}>
                <span className="font-medium">{EDUCATION_LABELS[record.level]}</span>
                {record.field && <span> · {record.field}</span>}
                {record.school && <span className="text-ink-muted"> · {record.school}</span>}
                {record.end_year !== null && (
                  <span className="text-ink-subtle"> · {record.end_year}</span>
                )}
              </li>
            ))}
          </ul>
        )}
      </Section>
      <ListSection title="Diller" component={breakdown.languages} />
      <ListSection title="Tercih edilen beceriler" component={breakdown.preferred_skills} />
    </div>
  );
}
