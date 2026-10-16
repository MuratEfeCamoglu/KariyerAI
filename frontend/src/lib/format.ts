const dateFormatter = new Intl.DateTimeFormat("tr-TR", {
  day: "numeric",
  month: "short",
  year: "numeric",
});

const dateTimeFormatter = new Intl.DateTimeFormat("tr-TR", {
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
});

export function formatDate(iso: string): string {
  return dateFormatter.format(new Date(iso));
}

export function formatDateTime(iso: string): string {
  return dateTimeFormatter.format(new Date(iso));
}

/** Türkçe "İ/ı" harflerini doğru küçülterek arama ve tekrar kontrolü için anahtar üretir. */
export function foldText(text: string): string {
  return text.toLocaleLowerCase("tr-TR").replace(/ı/g, "i").replace(/\s+/g, " ").trim();
}
