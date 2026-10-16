const dateFormatter = new Intl.DateTimeFormat("tr-TR", {
  day: "numeric",
  month: "short",
  year: "numeric",
});

export function formatDate(iso: string): string {
  return dateFormatter.format(new Date(iso));
}

/** Türkçe "İ/ı" harflerini doğru küçülterek arama ve tekrar kontrolü için anahtar üretir. */
export function foldText(text: string): string {
  return text.toLocaleLowerCase("tr-TR").replace(/ı/g, "i").replace(/\s+/g, " ").trim();
}
