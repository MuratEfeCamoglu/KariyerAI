# KariyerAI — Arayüz Tasarımı (geliştirici devri)

> Kaynak tasarım: Claude Design kanvası "KariyerAI — UI Tasarımı"
> https://claude.ai/artifact/DzHUXg8zteFELbkAkEordN (özel; erişim için sahibinden paylaşım iste)
> Tasarım ISKELET.md F1–F12 ve §3.5 ile hizalandı. Çelişkide **ISKELET.md geçerlidir**; bu dosya yalnızca görünüşü tanımlar.

Kanvastaki panolar çalıştırılabilir kod değildir, görsel referanstır. Uygulama CLAUDE.md'deki yığınla
(React 19 + TS + Tailwind 4) sıfırdan yazılır; değerler aşağıdaki token'lardan gelir.

---

## 1. Tasarım token'ları → `frontend/src/index.css`

Aşama 0'da Vite iskeleti kurulunca bu blok `src/index.css`'e olduğu gibi konur
(CLAUDE.md: `tailwind.config.ts` yok, tüm değerler `@theme`'den).

```css
@import "tailwindcss";

@theme {
  /* Tipografi */
  --font-sans: "Inter", ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, monospace;
  --text-xs: 0.75rem;    --text-xs--line-height: 1rem;       /* 12 / 16 */
  --text-sm: 0.875rem;   --text-sm--line-height: 1.25rem;    /* 14 / 20 */
  --text-base: 1rem;     --text-base--line-height: 1.5rem;   /* 16 / 24 */
  --text-lg: 1.125rem;   --text-lg--line-height: 1.75rem;    /* 18 / 28 */
  --text-xl: 1.25rem;    --text-xl--line-height: 1.75rem;    /* 20 / 28 */
  --text-2xl: 1.5rem;    --text-2xl--line-height: 2rem;      /* 24 / 32 */
  --text-3xl: 2rem;      --text-3xl--line-height: 2.5rem;    /* 32 / 40 */
  --text-score: 2.25rem; --text-score--line-height: 1;       /* puan halkası L */

  /* Marka */
  --color-brand-900: #0A2A3B;
  --color-brand-700: #0F3D56;   /* birincil */
  --color-brand-600: #155270;   /* birincil hover */
  --color-brand-100: #CFE3EC;
  --color-brand-50:  #E8F0F4;
  --color-accent-500: #14B8A6;  /* odak halkası, ilerleme, dekor — METİN İÇİN KULLANILMAZ (2.5:1) */
  --color-accent-700: #0F766E;  /* vurgu metni / bağlantı (5.5:1) */
  --color-accent-50:  #F0FDFA;

  /* Nötr */
  --color-canvas: #F7F8FA;
  --color-surface: #FFFFFF;
  --color-ink: #1F2937;
  --color-ink-muted: #4B5563;
  --color-ink-subtle: #6B7280;
  --color-line: #E5E7EB;
  --color-line-strong: #D1D5DB;
  --color-fill-muted: #F3F4F6;

  /* Puan bantları (ISKELET §3.5) — grafik tonu / metin tonu / zemin */
  --color-band-high: #16A34A;  --color-band-high-text: #15803D;  --color-band-high-bg: #F0FDF4;
  --color-band-mid:  #D97706;  --color-band-mid-text:  #B45309;  --color-band-mid-bg:  #FFFBEB;
  --color-band-low:  #6B7280;  --color-band-low-text:  #4B5563;  --color-band-low-bg:  #F3F4F6;

  /* Geri bildirim */
  --color-info: #1D4ED8;     --color-info-bg: #EFF6FF;
  --color-danger: #B91C1C;   --color-danger-bg: #FEF2F2;   /* yalnızca yıkıcı eylem + form hatası; puanda ASLA */

  /* Köşe, gölge, aralık */
  --radius-sm: 6px;  --radius-md: 8px;  --radius-lg: 12px;
  --shadow-xs: 0 1px 2px rgb(16 24 40 / 0.05);
  --shadow-sm: 0 2px 6px rgb(16 24 40 / 0.06);
  --shadow-lg: 0 12px 32px rgb(16 24 40 / 0.12);
  --spacing: 0.25rem; /* tasarımda yalnızca çift adımlar: 8 px ızgara */
}

@layer base {
  html { font-family: var(--font-sans); font-variant-numeric: tabular-nums; }
  body { background: var(--color-canvas); color: var(--color-ink); }
}
```

Font: Inter (400/500/600) — `@fontsource/inter` (onaylandı, CLAUDE.md yığınında). `src/main.tsx`'te:
`import "@fontsource/inter/400.css"; import "@fontsource/inter/500.css"; import "@fontsource/inter/600.css";`

Kurallar:
- Metin kontrastı ≥ 4.5:1. Bant renklerinin `-text` tonu metin, düz tonu yalnızca halka/nokta içindir.
- Kontrol yüksekliği 40 px (sm 32, lg 48); köşe: giriş/düğme `rounded-md`, kart/modal `rounded-lg`, rozet/chip `rounded-full`.
- Kart: `bg-surface border border-line rounded-lg shadow-xs`. Odak: `outline-2 outline-accent-500 outline-offset-2`.
- İkonlar: `lucide-react` (onaylandı, CLAUDE.md yığınında); çizgi kalınlığı `strokeWidth={1.75}`, boyut 16/20 px. Yalnızca ikonlu düğmede `aria-label` zorunlu.

## 2. Sabitler → `frontend/src/lib/constants.ts`

| Kavram | Değer → etiket / renk |
|---|---|
| Puan bandı | `>= 75` "Yüksek uyum" (band-high) · `50–74` "Orta uyum" (band-mid) · `< 50` "Düşük uyum" (band-low) |
| `application.status` | `new` Yeni (info) · `reviewing` İnceleniyor (brand-50/brand-700) · `shortlisted` Kısa liste (accent-50/accent-700) · `interview` Mülakat (#F5F3FF/#5B21B6) · `hired` İşe alındı (band-high-bg/text + onay ikonu) · `rejected` Reddedildi (fill-muted/ink-muted) |
| `parse_status` / `score_status` | `pending` Kuyrukta · `processing` İşleniyor (dönen ikon) · `done` Tamamlandı · `failed` Başarısız (gri uyarı ikonu — kırmızı değil) |
| `job.status` | `open` Açık (accent) · `closed` Kapalı (gri) |
| `user.role` | `admin` Admin · `recruiter` İK Uzmanı |
| `min_education` | none Yok · high_school Lise · associate Ön lisans · bachelor Lisans · master Yüksek lisans · phd Doktora |
| Kalem adları / ağırlıklar | Zorunlu beceriler 40 · Deneyim 25 · Eğitim 15 · Diller 10 · Tercih edilen 10 |
| Sabit uyarı | "Bu puan bir öneridir; karar İK uzmanına aittir." (kaldırılamaz — AGENT.md) |

Yargı ifadesi yok: "uygun değil", "başarısız aday" vb. kullanılmaz. "Başarısız" yalnızca işlem (ayrıştırma/puanlama) durumu içindir.

## 3. Bileşenler → `frontend/src/components/`

| Bileşen | Props (öneri) | Durumlar / notlar |
|---|---|---|
| `Sidebar` | `collapsed`, `user` | 248 px / 72 px ikon şeridi; Kullanıcılar + Denetim yalnızca `admin`; altta ad + rol rozeti + çıkış |
| `PageHeader` | `title`, `breadcrumb`, `actions` | Başlık 28/36 600; sağda birincil eylem |
| `Button` | `variant: primary\|secondary\|ghost\|danger`, `size`, `loading` | default, hover, focus, disabled, loading (spinner + metin) |
| `ScoreRing` | `score`, `size: sm(36)\|md(52)\|lg(104)` | Halka bant renginde, sayı her zaman `ink`; `aria-label="Puan 83, Yüksek uyum"` |
| `BandBadge`, `StatusBadge`, `ProcessingBadge` | `score` / `status` | Hepsi constants.ts'ten |
| `CriterionBar` | `label`, `weight`, `points` | 8 px çubuk, dolgu `brand-700` (bant rengi değil); mini sürüm 5×6 px tabloda |
| `ScoreBreakdown` | `breakdown` | Kalem başlığında formül metni (ör. "40 × 3/4 karşılanan"); her kriter: ✓ / ✗ / "Kanıt doğrulanamadı" |
| `EvidenceQuote` | `text`, `highlight`, `source` | Alıntı “…”, eşleşen ifade `bg-accent-50`/koyu metin ile vurgulu |
| `UploadDropzone` | `jobId`, `disabled` (kapalı ilan) | "PDF veya DOCX, en fazla 20 dosya, dosya başına 5 MB"; altında dosya bazlı liste: yükleniyor % / yüklendi / reddedildi + neden |
| `ApplicationsTable` | filtreler, sayfa | Satır: sıra, ad (bağlantı), ScoreRing md + BandBadge, mini kalem çubukları, son pozisyon, deneyim, durum, yükleme zamanı. `processing` → iskelet hücreler + ProcessingBadge; `failed` → neden + "Yeniden dene" |
| `StatusSelect` | `value`, `onChange` | 6 durum, serbest geçiş (F9) |
| `ChipInput` | `value: string[]`, `max` | Enter ile ekle, × ile sil, öneri listesi |
| `NotesPanel`, `StatusHistory` | — | Not silme ikonu yalnızca yazara görünür |
| `Modal`, `ConfirmDeleteModal` | — | Silme: aday id'si yazılınca "Kalıcı olarak sil" etkinleşir |
| `Toast`, `EmptyState`, `Skeleton` | — | Toast sağ üst, 5 sn; iskelet `prefers-reduced-motion`'da durur |

## 4. Sayfalar → `frontend/src/pages/` (kanvastaki pano adıyla)

| Sayfa | Pano | Özellik | Not |
|---|---|---|---|
| `LoginPage` | 1 · Giriş | F1 | Sol yarı marka paneli; hata: "E-posta veya şifre hatalı". Şifre sıfırlama bağlantısı YOK (§2.3) — "yöneticinize başvurun" metni |
| `JobsPage` | 2 · İlanlar, 2b boş durum | F3 | Arama + Açık/Kapalı segment; en yüksek / ortalama puan bant renkli rozet; boş: "Henüz ilan yok — ilk ilanını oluştur" |
| `JobFormPage` | 3 · İlan formu | F3 | Alan bazlı 422 hataları alanın altında + üstte özet; sağda yapışkan ağırlık kutusu; açıklama sayacı /5000; durum Açık/Kapalı |
| `JobDetailPage` | 4 · İlan detayı (+768) | F4, F6, F7 | Kriter chip'leri, dropzone, sıralı tablo, filtreler (min puan kaydırıcı, durum çoklu seçim, işlem durumu), 50/sayfa, 5 sn otomatik yenileme, "Yeniden puanla" |
| `ApplicationDetailPage` | 5 · Aday detayı (+768), 8 · Silme modalı | F8–F11 | Üst şerit (ad, iletişim, ScoreRing lg, durum, CV indir, admin için sil), yapışkan uyarı bandı, kırılım, AI özeti (künye: model + prompt sürümü), ayrıştırılmış CV, notlar, durum geçmişi |
| `UsersPage` | 6 · Kullanıcılar, 6b modal | F2 | Rol açılır listesi, aktif/pasif anahtarı (kendi satırında devre dışı), "Kullanıcı ekle": ad, e-posta, geçici şifre (≥10), rol — e-posta daveti YOK |
| `AuditPage` | 7 · Denetim kaydı | F12 | Son 500 kayıt, eylem türü filtresi; yalnızca id/durum/puan/model — kişisel veri yok |

Yerleşim: `Sidebar` + içerik (`max-w-[1280px] mx-auto px-10 py-8`). 768 px'te sidebar 72 px şeride
daralır, aday detayında sağ sütun alta iner, geniş tablolar `overflow-x-auto` kutuda kayar.

## 5. Kanvasta ISKELET'e göre düzeltilenler (bilgi)

- Doğrulanamayan kanıt **karşılanmamış** sayılır (F6c) — örnek aday puanları formülle yeniden hesaplandı.
- Deneyimde staj ayrımı yok; tüm dönemler, çakışmalar bir kez sayılarak (§3.4).
- Şifre sıfırlama, e-posta daveti, CSV dışa aktarma kaldırıldı (§2.3 / F12).
- Id'ler sayısal; model adı kurulumdaki LLM'e göre (ör. `openai/gpt-oss-120b`), prompt `score_v1`.
