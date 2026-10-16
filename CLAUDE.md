# KariyerAI

## Proje
İK ekipleri için AI destekli CV değerlendirme aracı: CV'leri (PDF/DOCX) okur, yapılandırır, ilan kriterlerine göre 0–100 arası kanıtlı uyum puanı verir ve adayları sıralar. Son kararı her zaman İK uzmanı verir; sistem otomatik eleme yapmaz.
- Kapsam, özellikler (F1–F12), veri modeli, API, puanlama formülü: @ISKELET.md (çelişkide ISKELET.md geçerlidir)
- Agent yetkileri, yasaklar, görev döngüsü, "bitti" tanımı: @AGENT.md

## Teknoloji Yığını
- **Backend:** Python 3.12, FastAPI (`fastapi[standard]`), SQLAlchemy 2 (sync), Alembic, SQLite (WAL), pydantic-settings, `google-genai` SDK (Gemini), httpx (Groq API ve HTTP), pypdf, python-docx, filetype, bcrypt, PyJWT
- **Frontend:** Node 24 LTS, React 19, TypeScript (strict), Vite, Tailwind CSS 4, TanStack Query 5, React Router 7, `lucide-react` (ikonlar), `@fontsource/inter` (font)
- **Arayüz tasarımı:** docs/TASARIM.md (token'lar, bileşenler, sayfalar)
- **Test:** pytest + httpx TestClient (backend), Vitest + Testing Library (frontend)
- **Kalite:** ruff (lint+format), mypy (backend); ESLint + Prettier, `tsc --noEmit` (frontend)
- **Paket yöneticileri:** `uv` (backend), `npm` (frontend)

## Komutlar
Backend (`backend/` içinde):
- Kurulum: `uv sync` → `copy .env.example .env` (macOS/Linux: `cp`) → `uv run alembic upgrade head`
- İlk admin: `uv run python -m app.cli create-admin --email admin@example.com` (şifre gizli girişle sorulur)
- Demo verisi: `uv run python -m app.cli seed-demo` (performans testi için: `--applications 500`)
- Geliştirme: `uv run fastapi dev app/main.py` (http://localhost:8000, docs: /docs)
- Test: `uv run pytest`
- Lint/format: `uv run ruff check .` ve `uv run ruff format --check .`
- Tip kontrolü: `uv run mypy app`
- Migration oluştur: `uv run alembic revision --autogenerate -m "add_jobs_table"` (mesaj snake_case, İngilizce)
- AI değerlendirme (gerçek API anahtarı ister, ücretsiz kotayı harcar): `uv run python -m evals.run --delay 12` (Groq) · `--provider gemini --delay 15`

Frontend (`frontend/` içinde):
- Kurulum: `npm install`
- Geliştirme: `npm run dev` (http://localhost:5173, `/api` → :8000 proxy)
- Test: `npm run test` (Vitest, tek seferlik `vitest run`)
- Lint/format: `npm run lint` ve `npm run format:check`
- Tip kontrolü: `npm run typecheck`
- Build: `npm run build`

**Tam doğrulama** (her görev sonunda, AGENT.md "bitti" tanımı):
backend'de `ruff check`, `ruff format --check`, `mypy app`, `pytest`; frontend'de `lint`, `format:check`, `typecheck`, `test`, `build` — hepsi hatasız.

## Ortam Değişkenleri (`backend/.env`)
- `DATABASE_URL=sqlite:///./data/kariyerai.db`
- `JWT_SECRET` — en az 32 karakter, repoya girmez
- `LLM_PROVIDER=groq|gemini|fake` — `.env.example`'da varsayılan `fake` (anahtarsız çalışır); testlerde her zaman `fake`. Groq ve Gemini hem gerçek hem test verisiyle kullanılır; **Anthropic/Claude API kullanılmaz**. Gerçek aday verisi için KVKK koşulları: ISKELET R3.
- `GROQ_API_KEY` — yalnızca `.env`'de; `GROQ_MODEL=openai/gpt-oss-120b`
- `GEMINI_API_KEY` — yalnızca `.env`'de; `GEMINI_MODEL=gemini-3.5-flash`
- `UPLOAD_DIR=./data/uploads`
- `COOKIE_SECURE=false` — canlıda (HTTPS arkasında) `true`; `true` iken `.env.example`'daki örnek `JWT_SECRET` ile uygulama başlamaz

## Kod Kuralları
**Genel**
- Klasör yapısı ISKELET.md §4 ile birebir aynıdır; yeni üst düzey klasör açma.
- Kod, değişken, dosya adları İngilizce; kullanıcıya görünen metinler ve API hata mesajları Türkçe.
- Kavram adları her yerde aynı: `Job` (ilan), `Candidate` (aday), `Application` (başvuru = aday × ilan), `Note`, `AuditLog`, `ParsedCV`.
- Yorumu "ne" için değil "neden" için yaz; açık kodu yorumlama.

**Backend**
- Katmanlar: `api/` (HTTP + yetki) → `services/` (iş mantığı) → `models/` (DB). Router'da iş mantığı, serviste `Request`/`HTTPException` olmaz; servisler alan hataları (`NotFoundError`, `ConflictError` vb. `app/core/errors.py`) fırlatır, `main.py`'deki handler HTTP koduna çevirir.
- Her uç için Pydantic istek/yanıt şeması `schemas/` altında; ORM nesnesi doğrudan döndürülmez.
- Tüm tip ipuçları zorunlu (`mypy` temiz).
- LLM'e yalnızca `app/llm/factory.get_llm_client()` üzerinden erişilir; servisler `GroqClient`/`GeminiClient`'ı doğrudan import etmez.
- Prompt metinleri yalnızca `app/llm/prompts/*.md` dosyalarında; prompt değişirse dosya sürümü artar (`score_v2.md`) ve `prompt_version` alanına yazılır.
- Puan sayısı yalnızca `services/scoring.py`'deki formülle üretilir (ISKELET.md §3.5); LLM çıktısından sayı alınmaz.
- Şema değişikliği = Alembic migration. Elle SQL ile tablo değiştirme.
- Loglarda yalnızca id'ler; CV metni, ad, e-posta, telefon loglanmaz.

**Frontend**
- Sunucu verisi yalnızca TanStack Query ile (`src/api/` modülleri + `hooks/`); bileşen içinde doğrudan `fetch` yok.
- Fonksiyon bileşenleri, adlandırılmış export; dosya adı bileşen adıyla aynı (`ScoreBadge.tsx`).
- Stil yalnızca Tailwind sınıflarıyla; renk/aralık/font değerleri `src/index.css` içindeki `@theme` token'larından (Tailwind 4; `tailwind.config.ts` yok).
- Durum etiketleri ve puan bantları `src/lib/constants.ts`'te tek yerde (ISKELET.md §3.5 bantları).
- `any` yasak; backend şemalarının karşılığı `src/types/` altında.

**Test**
- Her yeni servis fonksiyonu için birim test; her yeni uç için en az bir başarılı ve bir hata (401/403/404/422) API testi.
- `services/scoring.py` için her kalemde sınır değer testleri (0, kısmi, tam).
- Testler `LLM_PROVIDER=fake` ile çalışır, ağa çıkmaz; test CV'leri yalnızca `tests/fixtures/` altındaki sentetik dosyalar.

## Çalışma Kuralları
- Bir görev = bir ISKELET.md özelliği (F#) veya aşama adımı. Başlamadan kabul kriterini oku.
- Her değişiklikten sonra ilgili testleri, görev bitiminde tam doğrulamayı çalıştır.
- Kapsam dışı (ISKELET.md §2.3) bir ihtiyaç görürsen uygulama; rapora "öneri" olarak yaz.
- Commit mesajı: Conventional Commits, Türkçe açıklama — `feat(scoring): kanıt doğrulaması eklendi`. Tür: `feat|fix|refactor|test|docs|chore`. Kapsam: `auth|users|jobs|cv|parse|scoring|ui|infra`.
- Bir commit tek mantıksal değişiklik içerir; testleri geçmeyen kod commit edilmez.

## Önemli Notlar
- Windows'ta geliştiriliyor: yol birleştirmede `pathlib` kullan, shell'e özgü script yazma.
- `backend/data/` (DB + yüklenen CV'ler) `.gitignore`'dadır; asla commit edilmez.
- SQLite bağlantısında `PRAGMA journal_mode=WAL` ve `foreign_keys=ON` açılır (`core/db.py`).
- `FakeLLMClient` deterministik çıktı verir: CV metninde geçen ilan becerilerini "karşılandı" sayar ve geçtiği cümleyi kanıt olarak döndürür; testler buna dayanır.
- AI çıktısı her zaman öneridir: arayüzde "Bu puan bir öneridir; karar İK uzmanına aittir." uyarısını kaldırma.
