# KariyerAI

İK ekipleri için AI destekli CV değerlendirme aracı. CV'leri (PDF/DOCX) okur, yapılandırır, ilan
kriterlerine göre 0–100 arası **kanıtlı** uyum puanı verir ve adayları sıralar. **Son kararı her
zaman İK uzmanı verir**; sistem otomatik eleme yapmaz ve başvuru durumunu kendisi değiştirmez.

- Kapsam, mimari, veri modeli, puanlama formülü: [ISKELET.md](ISKELET.md)
- Geliştirme komutları ve kod kuralları: [CLAUDE.md](CLAUDE.md)
- AI agent çalışma sözleşmesi: [AGENT.md](AGENT.md)
- Arayüz tasarımı: [docs/TASARIM.md](docs/TASARIM.md)

## Neler yapar?

| | |
|---|---|
| **İlanlar** | Zorunlu/tercih edilen beceriler, minimum deneyim ve eğitim, dil seviyeleri |
| **CV yükleme** | Tek seferde 1–20 PDF/DOCX (≤ 5 MB); tür içerikten doğrulanır, aynı CV aynı ilana iki kez yüklenemez |
| **AI ayrıştırma** | CV → yapılandırılmış veri (beceriler, deneyim, eğitim, diller). Yaş, cinsiyet, medeni hal, din, uyruk, fotoğraf **hiç çıkarılmaz** |
| **Puanlama** | Puan kodda, sabit formülle hesaplanır (zorunlu beceri 40 · deneyim 25 · eğitim 15 · dil 10 · tercih edilen 10). AI yalnızca "kriter karşılanıyor mu + CV'den birebir alıntı" döner; alıntı CV'de bulunamazsa kalem karşılanmamış sayılır. AI'a giden metinde ad, e-posta, telefon ve adres yoktur |
| **Sıralama** | Puana göre sıralı liste, filtreler, işlem sürerken otomatik yenileme, başarısız CV için "Yeniden dene" |
| **Aday detayı** | Kalem kalem puan kırılımı ve kanıtlar, AI özeti, ayrıştırılmış CV, durum akışı, notlar, durum geçmişi |
| **KVKK** | Admin bir adayı tüm verisi ve CV dosyasıyla kalıcı olarak silebilir; loglarda ve denetim kaydında kişisel veri tutulmaz |
| **Denetim kaydı** | Giriş, ilan, yükleme, ayrıştırma, puanlama, durum değişikliği ve silme olayları (admin) |

## Gereksinimler

- Python 3.12 + [uv](https://docs.astral.sh/uv/)
- Node.js 24 LTS + npm

## Kurulum ve çalıştırma

Backend (`backend/` içinde):

```bash
uv sync
copy .env.example .env        # macOS/Linux: cp .env.example .env
uv run alembic upgrade head
uv run python -m app.cli create-admin --email admin@example.com   # şifre gizli girişle sorulur
uv run python -m app.cli seed-demo                                 # isteğe bağlı: demo ilanı + 20 sentetik aday
uv run fastapi dev app/main.py   # http://localhost:8000 · sağlık: /api/health · docs: /docs
```

Frontend (`frontend/` içinde, ayrı terminalde):

```bash
npm install
npm run dev     # http://localhost:5173 — /api istekleri :8000'e proxy'lenir
```

Tarayıcıda http://localhost:5173 adresine gidip yönetici hesabıyla giriş yapın. Diğer İK
kullanıcılarını **Kullanıcılar** sayfasından ekleyebilirsiniz.

### LLM sağlayıcısı (`backend/.env` → `LLM_PROVIDER`)

| Değer | Ne zaman | Gerekenler |
|---|---|---|
| `fake` (varsayılan) | Geliştirme, test, demo | Hiçbir şey; ağa çıkmaz, deterministik. Gerçek bir ayrıştırıcı değildir |
| `anthropic` | **Gerçek CV'lerle kullanım** | `ANTHROPIC_API_KEY` (ücretli). Model: `LLM_MODEL`, varsayılan `claude-sonnet-5-5` |
| `groq` | Geliştirme/eval, **yalnızca sentetik veri** — önerilen ücretsiz seçenek | `GROQ_API_KEY` (console.groq.com, kart gerekmez). Model `openai/gpt-oss-120b`. Ücretsiz katman: günde 1.000 istek, dakikada 8.000 token |
| `gemini` | Geliştirme/eval, **yalnızca sentetik veri** | `GEMINI_API_KEY` (Google AI Studio ücretsiz katmanı; günde model başına 20 istek). Ücretsiz katmanda gönderilen içerik sağlayıcının ürün geliştirmesinde kullanılabilir; gerçek aday CV'si gönderilmez (KVKK) |

> Canlıya almadan önce: aday CV'lerinin yurt dışındaki bir LLM sağlayıcısında işlenmesi için
> şirketin hukuk birimi onayı ve aday aydınlatma metni gerekir (ISKELET R3, V4).

## AI ayrıştırma değerlendirmesi

`backend/evals/cvs/` altında 10 sentetik CV ve elle etiketlenmiş beklenen beceriler vardır. Beceri
recall'unu (hedef ≥ %80) ve ayrıştırma süresini (p95 ≤ 30 sn) ölçer:

```bash
# backend/ içinde — gerçek API çağrısı yapar
uv run python -m evals.run                                  # Claude (ANTHROPIC_API_KEY, ücretli)
uv run python -m evals.run --provider groq --delay 12       # Groq ücretsiz katman
uv run python -m evals.run --provider gemini --delay 15     # Gemini ücretsiz katman (günlük kota)
```

| Tarih | Model | Beceri recall'u | p95 ayrıştırma |
|---|---|---|---|
| 2026-10-16 | `openai/gpt-oss-120b` (Groq) | **%96,3** (eksik: İş hukuku, Vergi mevzuatı, SMMM) | **2,5 sn** |
| 2026-10-16 | `gemini-3.5-flash` | **%100** (10/10 CV) | **16,5 sn** |
| — | `claude-sonnet-5-5` | henüz ölçülmedi (API anahtarı gerekli) | — |

## Performans (ISKELET §5)

2026-10-16, geliştirme makinesi (Windows 11), `fastapi run`, yerel SQLite. Liste ölçümü
`seed-demo --applications 500` verisiyle, yükleme ölçümleri 20 sentetik DOCX ile yapıldı.

| Hedef | Sınır | Ölçülen | Not |
|---|---|---|---|
| Başvuru listesi API, 500 kayıt | p95 ≤ 500 ms | **p95 129 ms** (medyan 21 ms) | 60 istek; sayfa, puan ve durum filtreleriyle |
| 20 CV yükleme yanıtı (F4f) | ≤ 40 sn | **0,31 sn** | Ayrıştırma arka planda sürer |
| 20 CV'nin tamamen işlenmesi (B1) | ≤ 5 dk | **0,62 sn** | Sahte LLM ile; gerçek LLM süresini içermez |
| 20 CV'nin tamamen işlenmesi (B1), gerçek LLM | ≤ 5 dk | **7,0 dk** ✗ — 20/20 başarılı | Groq ücretsiz katmanı: darboğaz dakikalık 8.000 token kotası (ilk CV'ler 6–7 sn'de bitti, sonrası kotaya göre ~21 sn arayla). Ücretli katmanda kota kalkınca hedefin altında kalması beklenir; Claude ile ölçülmedi |
| Tek CV ayrıştırma (F5c) | p95 ≤ 30 sn | **p95 16,5 sn** | Gemini eval'i (10 CV) |
| Tek CV puanlama | ≤ 15 sn | **6,8 sn** | Gemini, 1 sentetik CV (tek ölçüm) |
| Frontend ilk yükleme JS | gzip ≤ 300 KB | **≈ 130 KB** | `npm run build` çıktısı |

B1, canlıda kullanılacak `anthropic` sağlayıcısıyla (ücretli, kotası yüksek) yeniden ölçülmelidir.
Ücretsiz katmanlardaki ölçüm uygulamanın kota sınırına takıldığında da işleri kaybetmeden
(429'da bekleyip yeniden deneyerek) tamamladığını gösterir.

## Demo verisi

```bash
uv run python -m app.cli seed-demo                      # 1 ilan + 20 sentetik aday
uv run python -m app.cli seed-demo --applications 500   # performans ölçümü için
```

LLM çağrısı yapmaz. Adaylar uydurmadır (`@example.com`), puanlar gerçek formül ve kanıt
doğrulamasıyla hesaplanır.

## Doğrulama

```bash
# backend/
uv run ruff check . && uv run ruff format --check . && uv run mypy app && uv run pytest
# frontend/
npm run lint && npm run format:check && npm run typecheck && npm run test && npm run build
```

Testler gerçek LLM'e istek atmaz (`LLM_PROVIDER=fake`). CI her push'ta bu komutları çalıştırır.
