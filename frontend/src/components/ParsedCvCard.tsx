import { EDUCATION_LABELS } from "../lib/constants.ts";
import type { ParsedCV } from "../types/application.ts";
import { Card } from "./Card.tsx";

/** Sistemin CV'den ne okuduğu; hem İK hem iş arayan sayfasında gösterilir. */
export function ParsedCvCard({ parsed }: { parsed: ParsedCV }) {
  return (
    <Card title="Ayrıştırılmış CV">
      <dl className="space-y-5 text-sm">
        {parsed.summary && (
          <div>
            <dt className="mb-1 text-xs font-medium text-ink-subtle">Özet</dt>
            <dd className="text-ink">{parsed.summary}</dd>
          </div>
        )}
        <div>
          <dt className="mb-1 text-xs font-medium text-ink-subtle">Deneyim</dt>
          <dd>
            {parsed.experiences.length === 0 ? (
              <span className="text-ink-muted">Bulunamadı</span>
            ) : (
              <ul className="space-y-2">
                {parsed.experiences.map((item, index) => (
                  <li key={index}>
                    <p className="font-medium text-ink">
                      {item.title}
                      {item.company && (
                        <span className="font-normal text-ink-muted"> · {item.company}</span>
                      )}
                    </p>
                    <p className="text-xs text-ink-subtle">
                      {item.start ?? "?"} – {item.end === "present" ? "halen" : (item.end ?? "?")}
                    </p>
                    {item.description && (
                      <p className="mt-0.5 text-ink-muted">{item.description}</p>
                    )}
                  </li>
                ))}
              </ul>
            )}
            <p className="mt-2 text-xs text-ink-subtle">
              Toplam deneyim: {parsed.total_experience_years.toLocaleString("tr-TR")} yıl
              (tarihlerden hesaplandı; çakışan dönemler bir kez sayıldı)
            </p>
          </dd>
        </div>
        <div>
          <dt className="mb-1 text-xs font-medium text-ink-subtle">Eğitim</dt>
          <dd>
            {parsed.education.length === 0 ? (
              <span className="text-ink-muted">Bulunamadı</span>
            ) : (
              <ul className="space-y-1">
                {parsed.education.map((item, index) => (
                  <li key={index} className="text-ink">
                    {EDUCATION_LABELS[item.level]}
                    {item.field && ` · ${item.field}`}
                    {item.school && <span className="text-ink-muted"> · {item.school}</span>}
                    {item.end_year !== null && (
                      <span className="text-ink-subtle"> · {item.end_year}</span>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </dd>
        </div>
        <div>
          <dt className="mb-1 text-xs font-medium text-ink-subtle">Beceriler</dt>
          <dd>
            {parsed.skills.length === 0 ? (
              <span className="text-ink-muted">Bulunamadı</span>
            ) : (
              <ul className="flex flex-wrap gap-1.5">
                {parsed.skills.map((skill) => (
                  <li
                    key={skill}
                    className="rounded-full bg-fill-muted px-2.5 py-0.5 text-xs text-ink"
                  >
                    {skill}
                  </li>
                ))}
              </ul>
            )}
          </dd>
        </div>
        <div>
          <dt className="mb-1 text-xs font-medium text-ink-subtle">Diller</dt>
          <dd className="text-ink">
            {parsed.languages.length === 0
              ? "Bulunamadı"
              : parsed.languages
                  .map((item) => `${item.language}${item.level ? ` (${item.level})` : ""}`)
                  .join(", ")}
          </dd>
        </div>
      </dl>
    </Card>
  );
}
