import { PageHeader } from "../components/PageHeader.tsx";

// İlan listesi Aşama 2'de (F3) doldurulur; şimdilik girişten sonraki ana sayfa iskeleti.
export function JobsPage() {
  return (
    <>
      <PageHeader title="İlanlar" />
      <div className="rounded-lg border border-line bg-surface p-8 text-sm text-ink-muted shadow-xs">
        Henüz ilan yok.
      </div>
    </>
  );
}
