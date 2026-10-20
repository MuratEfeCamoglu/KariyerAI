# CV Geliştirme (İş Arayan Tarafı) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** İş arayanların kendi kaydolup CV'lerini kendi girdikleri iş kriterlerine göre değerlendirtebildiği ve eksiklik raporu aldığı ikinci bir uygulama tarafı eklemek.

**Architecture:** Yeni `seeker` rolü ve ayrı `cv_checks` tablosu; işveren tabloları ve puanlama formülü değişmez. Ayrıştırma/puanlama mevcut `cv_parser.parse_cv` + `scoring.evaluate` ile, eksik listesi `services/cv_gaps.py` içinde puan kırılımından kodla üretilir (yeni prompt yok). Frontend'de rol bazlı rota korumaları ve dört yeni sayfa.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic, pytest · React 19, TanStack Query 5, React Router 7, Vitest.

**Spec:** `docs/superpowers/specs/2026-10-19-cv-gelistirme-design.md`

## Global Constraints
- Kullanıcıya görünen metinler ve API hataları Türkçe; kod adları İngilizce. Kavram adı `CVCheck` (tablo `cv_checks`).
- Puan yalnızca `scoring.py` formülüyle; `scoring.py` ve prompt dosyaları değişmez.
- Loglarda/audit payload'unda yalnızca id, durum, puan, model, prompt sürümü.
- İş arayan verisi `candidates`/`applications` tablolarına girmez.
- Testler `LLM_PROVIDER=fake`; CV'ler `tests/fixtures/` altındaki sentetik dosyalar.
- Kayıt sınırı: IP başına 60 sn'de 5 kayıt denemesi → 429. Günlük sınır: kullanıcı başına son 24 saatte 10 değerlendirme → 429.
- Öneri cümleleri "sahipsen" dilinde; adayı olmayan beceriyi yazmaya yönlendirmez.
- İş arayan uyarısı (sabit): "Bu değerlendirme yapay zekâ desteklidir; işverenlerin değerlendirmesi farklı olabilir."

## Review Focus
1. Seeker oturumuyla her işveren ucu (`/jobs*`, `/applications*`, `/notes*`, `/candidates*`) 403 dönmeli — tek bir unutulan `CurrentUser` veri sızıntısıdır. → Task 1 parametrik test.
2. Başka kullanıcının `cv_check` id'si: GET/DELETE/retry 404 (403 değil; varlık sızmasın). → Task 2.
3. Kayıt isteğinde `role: "admin"` gönderilirse yok sayılmalı, hesap `seeker` olmalı. → Task 1.
4. Kriter JSON'u bozuk/eksik gönderilirse 422 ve alan bazlı hata (`required_skills` anahtarıyla) dönmeli, dosya diske yazılmamalı. → Task 2.
5. Seeker işveren rotasına (`/jobs`) gittiğinde `/cv-checks`'e, staff `/cv-checks`'e gittiğinde `/jobs`'a yönlenmeli; giriş sonrası ana sayfa role göre. → Task 4.

---

### Task 1: Seeker rolü, kayıt ucu, işveren uçlarının daraltılması

**Files:**
- Modify: `backend/app/models/user.py` (`UserRole.SEEKER = "seeker"`; enum CHECK kısıtı yok, migration gerekmez)
- Modify: `backend/app/core/deps.py` (`require_staff`, `StaffUser`)
- Modify: `backend/app/api/jobs.py`, `applications.py`, `candidates.py` (`CurrentUser` → `StaffUser`)
- Modify: `backend/app/core/security.py` (`register_rate_limiter = LoginRateLimiter(max_failures=5)`)
- Modify: `backend/app/schemas/auth.py` (`RegisterRequest{email, full_name, password}`)
- Modify: `backend/app/services/auth.py` (`register(db, *, email, full_name, password, client_key) -> User`)
- Modify: `backend/app/api/auth.py` (`POST /auth/register` → 201 + cookie; cookie kurulumu ortak `_set_session_cookie`)
- Modify: `backend/tests/conftest.py` (`seeker`, `seeker_client` fixture; `register_rate_limiter.reset()`)
- Test: `backend/tests/api/test_register.py`, `backend/tests/api/test_seeker_access.py`

**Interfaces — Produces:** `StaffUser`, `UserRole.SEEKER`, fixture `seeker_client` (e-posta `aday@example.com`, şifre `SEEKER_PASSWORD = "seeker-password-123"`).

- [ ] Testler: `test_register_creates_seeker_and_sets_cookie` (201, `role == "seeker"`, ardından `/auth/me` 200), `test_register_ignores_role_field` (`role: "admin"` gönderilir → seeker), `test_register_duplicate_email_409` ("Bu e-posta ile kayıtlı bir hesap var"), `test_register_short_password_422`, `test_register_rate_limited_429` (6. istek), `test_register_writes_audit` (`user.register`, payload'da e-posta yok). `test_seeker_forbidden_on_staff_endpoints` — parametrik: `GET /api/jobs`, `POST /api/jobs`, `GET /api/jobs/1`, `GET /api/jobs/1/applications`, `POST /api/jobs/1/cvs`, `GET /api/applications/1`, `PATCH /api/applications/1/status`, `DELETE /api/notes/1`, `GET /api/candidates/1/cv`, `GET /api/users`, `GET /api/audit` → hepsi 403.
- [ ] Çalıştır: `uv run pytest tests/api/test_register.py tests/api/test_seeker_access.py` → FAIL.
- [ ] Uygula. Rate limiter her kayıt denemesini (başarılı/başarısız) `record_failure` ile sayar; blokluysa 429 "Çok fazla kayıt denemesi. Lütfen bir dakika sonra tekrar deneyin."
- [ ] Çalıştır: tüm `uv run pytest` → PASS.
- [ ] Commit: `feat(auth): iş arayan rolü ve kayıt ucu eklendi`

### Task 2: `cv_checks` modeli, servis, pipeline ve API

**Files:**
- Create: `backend/app/models/cv_check.py` (`CVCheck`, spec §5.2 kolonları; `owner_id` FK `users.id` `ondelete="CASCADE"`, index)
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/20261019_<rev>_add_cv_checks_table.py` (autogenerate)
- Create: `backend/app/schemas/cv_check.py` (`CVCheckCriteria`, `CVCheckListItem`, `CVCheckOut`, `Gap` — Gap Task 3'te doldurulur)
- Create: `backend/app/services/cv_checks.py`
- Modify: `backend/app/services/pipeline.py` (`process_cv_check`, `unfinished_cv_check_ids`, `requeue_unfinished` her ikisini de kuyruğa alır)
- Create: `backend/app/api/cv_checks.py`; Modify: `backend/app/main.py`
- Test: `backend/tests/api/test_cv_checks.py`, `backend/tests/unit/test_cv_check_pipeline.py`

**Interfaces — Consumes:** `SeekerUser` (bu task `deps.py`'ye `require_seeker` ekler), `cv_extract.detect_kind/extract_text`, `FileStorage`, `cv_parser.parse_cv`, `scoring.evaluate(job: Job, ...)`.
**Produces:**
- `CVCheckCriteria`: `title: Title`, `job_text: Description = ""`, `required_skills: RequiredSkills`, `preferred_skills: PreferredSkills`, `min_experience_years: ExperienceYears`, `min_education`, `languages: Languages` (tipler `schemas/job.py`'den).
- `cv_checks.create_check(db, storage, *, owner_id: int, criteria: CVCheckCriteria, file: IncomingFile) -> CVCheck`
- `cv_checks.list_checks(db, owner_id) -> list[CVCheck]` (yeniden eskiye)
- `cv_checks.get_check(db, *, check_id, owner_id) -> CVCheck` (yoksa/başkasınınsa `NotFoundError("Değerlendirme bulunamadı")`)
- `cv_checks.retry_check(db, *, check_id, owner_id) -> int`, `cv_checks.delete_check(db, storage, *, check_id, owner_id) -> None`
- `cv_checks.criteria_job(check: CVCheck) -> Job` — kaydedilmemiş `Job` (puanlama için)
- `pipeline.process_cv_check(check_id, session_factory, llm_factory=get_llm_client) -> None`
- Uçlar: spec §5.4. `POST /cv-checks` form alanları `criteria` (JSON metni) + `file`.

- [ ] Testler (API): `test_create_check_returns_202_and_processes` (fake LLM ile arka plan biter; GET'te `score_status == "done"`, `score` int), `test_create_check_invalid_criteria_422` (`required_skills: []` → `detail[0].loc == ["body","required_skills"]`, upload dizini boş), `test_create_check_bad_json_422`, `test_create_check_unsupported_file_422`, `test_create_check_scanned_pdf_marks_failed` (parse_error = NO_TEXT), `test_daily_limit_429` (10 kayıt varken 11.), `test_list_returns_only_own_checks`, `test_get_other_users_check_404`, `test_delete_removes_file_and_row` (+ başkasınınki 404), `test_retry_failed_score` (202) ve `test_retry_extraction_error_409`, `test_staff_cannot_use_cv_checks_403`, `test_unauthenticated_401`, `test_seeker_check_not_in_staff_lists` (oluşturduktan sonra `candidates` tablosu boş).
- [ ] Testler (birim): `test_process_cv_check_parse_failure_sets_score_failed`, `test_unfinished_cv_checks_requeued`.
- [ ] Çalıştır → FAIL. Uygula. Router `criteria` metnini `CVCheckCriteria.model_validate_json` ile doğrular; `pydantic.ValidationError` → `RequestValidationError`, `loc` başına `"body"` konur (JSON kökü hatası için `["body","criteria"]`). Dosya doğrulama/çıkarma kuralları ve mesajları `candidates.py` ile aynı (sabitler oradan import edilir). Audit: `cv_check.create`, `cv_check.parse`, `cv_check.score`, `cv_check.retry`, `cv_check.delete`.
- [ ] `uv run alembic revision --autogenerate -m "add_cv_checks_table"`; `tests/unit/test_migrations.py` geçmeli.
- [ ] Çalıştır: `uv run pytest` → PASS. Commit: `feat(cv): iş arayan CV değerlendirmeleri eklendi`

### Task 3: Eksiklik raporu (`cv_gaps`)

**Files:**
- Create: `backend/app/services/cv_gaps.py`
- Modify: `backend/app/schemas/cv_check.py` (`Gap`), `backend/app/api/cv_checks.py` (detayda `gaps`)
- Test: `backend/tests/unit/test_cv_gaps.py`

**Produces:** `GapKind = Literal["required_skill","experience","education","language","preferred_skill"]`; `Gap{kind, criterion: str, status: str, message: str}`; `build_gaps(breakdown: ScoreBreakdown) -> list[Gap]` sırası: zorunlu beceriler → deneyim → eğitim → diller → tercih edilen.

Mesajlar (birebir):
- Beceri `no_evidence`: `"CV'nde '{x}' kanıtı bulunamadı. Bu beceriye sahipsen, kullandığın işi veya projeyi açıkça yaz."`
- Beceri `unverified`: `"'{x}' için gösterilen alıntı CV metninde bulunamadı. Bu beceriyi kullandığın yeri net bir cümleyle yaz."`
- Dil `no_evidence`/`unverified`: `"CV'nde {x} bilgisi bulunamadı. Bu dili biliyorsan seviyesiyle (ör. {lvl}) ekle."`
- Dil `level_unknown`: `"{x} seviyen CV'de yazmıyor; seviyeni (ör. {lvl}) belirt."`
- Dil `level_insufficient`: `"İlan {x} için {lvl} istiyor, CV'nde {cand} görünüyor."`
- Deneyim (aday < istenen): `"İlan en az {req} yıl deneyim istiyor; CV'nden hesaplanan {cand} yıl. Tarihleri eksik deneyimlerin varsa başlangıç ve bitiş tarihlerini ekle."` (`cand` virgüllü bir ondalık: `3,2`)
- Eğitim (aday < istenen): `"İlan en az {req_label} istiyor; CV'nde {cand_label} görünüyor."` (aday yoksa `"eğitim bilgisi bulunamadı"`); etiketler frontend `EDUCATION_LABELS` ile aynı Türkçe.

- [ ] Testler: `test_no_gaps_when_all_met`, `test_required_skill_no_evidence_message`, `test_unverified_message`, `test_experience_gap_partial` (req 5, cand 3.2 → "3,2"), `test_experience_zero_required_no_gap`, `test_education_one_below` / `test_education_missing`, `test_language_level_unknown|insufficient|missing`, `test_order_required_first_preferred_last`.
- [ ] Çalıştır → FAIL → uygula → PASS. Commit: `feat(scoring): iş arayan için eksiklik raporu eklendi`

### Task 4: Frontend

**Files:**
- Modify: `frontend/src/types/user.ts` (`"seeker"`, `RegisterRequest`), `lib/constants.ts` (`ROLE_LABELS.seeker = "İş arayan"`, `SEEKER_DISCLAIMER`, `homePathFor(role)`, `CV_CHECK_ACTION_LABELS` audit etiketleri), `api/auth.ts` (`register`), `hooks/useAuth.ts` (`useRegister`)
- Create: `types/cvCheck.ts`, `api/cvChecks.ts` (multipart `FormData`, `apiFetch` ile), `hooks/useCvChecks.ts` (işlenirken 5 sn yenileme)
- Create: `components/RequireStaff.tsx`, `components/RequireSeeker.tsx`; Modify: `router.tsx`, `Sidebar.tsx` (seeker menüsü: "CV Değerlendirmeleri" → `/cv-checks`), `pages/LoginPage.tsx` (rol bazlı yönlendirme + "Hesabın yok mu? Kayıt ol" bağlantısı)
- Create: `pages/RegisterPage.tsx`, `pages/CvChecksPage.tsx`, `pages/CvCheckFormPage.tsx`, `pages/CvCheckDetailPage.tsx`, `components/GapList.tsx`
- Reuse: `ChipInput`, `TextField`, `ScoreRing`, `BandBadge`, `ScoreBreakdown`, `EvidenceQuote`, `ProcessingBadge`, `ConfirmDeleteModal`. JobFormPage'deki kriter alanları gerekiyorsa `components/CriteriaFields.tsx`'e çıkarılıp iki formda kullanılır.
- Test: `__tests__/RegisterPage.test.tsx`, `__tests__/CvCheckFormPage.test.tsx`, `__tests__/CvCheckDetailPage.test.tsx`, `__tests__/routeGuards.test.tsx` (genişlet)

- [ ] Testler: kayıt formu başarılıda `/cv-checks`'e gider, 409 mesajını gösterir; form dosya seçilmeden gönderilmez ("CV dosyası seçin"), alan hatası `required_skills` altında görünür; detay sayfası eksikleri sırayla, uyarı metnini ve kanıtları gösterir, işlenirken "İşleniyor" rozeti; rota korumaları (seeker `/jobs` → `/cv-checks`, recruiter `/cv-checks` → `/jobs`, seeker `/users` → `/cv-checks`).
- [ ] `npm run test` → FAIL → uygula → PASS.
- [ ] `npm run dev` ile kayıt → yeni değerlendirme → rapor akışı elle denenir.
- [ ] Commit: `feat(ui): iş arayan kayıt ve CV değerlendirme sayfaları eklendi`

### Task 5: Dokümanlar ve tam doğrulama

**Files:** `ISKELET.md` (1.4, spec §6), `CLAUDE.md` (proje tanımı, `CVCheck` kavramı), `README.md` (iş arayan akışı kısa bölüm)

- [ ] Spec §6'daki değişiklikleri yaz (F13 kayıt, F14 değerlendirme, F15 eksiklik raporu kabul kriterleriyle).
- [ ] Tam doğrulama: backend `ruff check .`, `ruff format --check .`, `mypy app`, `pytest`; frontend `lint`, `format:check`, `typecheck`, `test`, `build` — hepsi hatasız; boş DB'de `uv run alembic upgrade head`.
- [ ] Commit: `docs: iki taraflı uygulama (iş arayan tarafı) dokümanlara işlendi`
