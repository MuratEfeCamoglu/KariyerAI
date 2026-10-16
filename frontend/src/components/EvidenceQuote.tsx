import type { ReactNode } from "react";

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** CV'den birebir alıntı; kriter ifadesi alıntı içinde vurgulanır (TASARIM §3). */
export function EvidenceQuote({ text, highlight }: { text: string; highlight: string }) {
  const parts: ReactNode[] = [];
  const pattern = highlight.trim()
    ? new RegExp(`(${escapeRegExp(highlight.trim())})`, "giu")
    : null;
  const pieces = pattern ? text.split(pattern) : [text];
  pieces.forEach((piece, index) => {
    // split() yakalama grubuyla çağrıldığında eşleşmeler tek indekslerde döner.
    parts.push(
      index % 2 === 1 ? (
        <mark key={index} className="rounded-sm bg-accent-50 px-0.5 font-medium text-ink">
          {piece}
        </mark>
      ) : (
        piece
      ),
    );
  });

  return (
    <blockquote className="mt-1 border-l-2 border-line-strong pl-3 text-sm text-ink-muted">
      “{parts}”
    </blockquote>
  );
}
