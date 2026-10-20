# Çoklu İşveren Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** İK uzmanları kendi e-postasıyla kaydolur, admin onaylar, her uzman yalnızca kendi ilan/aday/başvuru/notunu görür; admin yalnızca hesapları yönetir.

**Architecture:** `users.is_approved` sütunu + kayıt türü; `StaffUser` yerine yalnızca `recruiter` kabul eden `RecruiterUser`; işveren servisleri `owner_id` alıp sahipliği `jobs.created_by` üzerinden süzer, başkasının kaydına 404 döner (`cv_checks` deseni). Admin denetim kaydında yalnızca `entity_type == "user"` olayları görür.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic, pytest; React 19, TanStack Query 5, React Router 7, Vitest.

**Spec:** `docs/superpowers/specs/2026-10-20-coklu-isveren-design.md`

## Global Constraints

- Dal: `feat/coklu-isveren` (`feat/cv-gelistirme` üstünde). Push/PR yalnızca kullanıcı onayıyla.
- Başkasının kaydı = hiç olmayan kayıt: aynı 404 ve aynı mesaj ("İlan bulunamadı", "Başvuru bulunamadı", "Aday bulunamadı", "Not bulunamadı").
- Admin tüm işveren uçlarında 403 "Bu işlem için yetkiniz yok".
- Mesajlar birebir: "Hesabınız yönetici onayı bekliyor" (403), "Yalnızca onay bekleyen hesaplar reddedilebilir" (409), "Hesap zaten onaylı" (409), "Günlük CV sınırına ulaştınız (100). Kalan hakkınız: N." (429), "Başvurunuz alındı. Yönetici onayladıktan sonra giriş yapabilirsiniz."
- `DAILY_CV_LIMIT = 100`, pencere 24 saat; iş arayan sınırı 10 değişmez.
- Audit payload'ında kişisel veri yok; yeni eylemler `user.approve`, `user.reject`, `job.transfer`.
- Testler `LLM_PROVIDER=fake`; yeni bağımlılık yok.
- Commit: Conventional Commits, Türkçe; sonuna `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. Bir İK uzmanının başka uzmanın **kapalı/boş** ilanına erişimi (başvurusu olmayan ilan dahil) → 404; `PATCH`/`DELETE` dahil. Task 2'deki parametrize test tüm uçları kapsar.
2. Geçerli cookie'si olan ama `is_approved=false` olan hesap (ör. DB'de elle değiştirilmiş) → `get_current_user` 401. Task 1 testi.
3. Yanlış şifre + onay bekleyen hesap → 403 değil genel 401 (hesap varlığı sızmasın). Task 1 testi.
4. 100 sınırına 5 kala 20 dosyalık yükleme → tamamı 429, diskte dosya yok. Task 3 testi.
5. Admin `/audit`'te başka uzmanın `job.create`/`cv_check.create` kaydını görmez. Task 3 testi.

---

### Task 1: Onay bekleyen İK kaydı ve admin onayı (backend)

**Files:**
- Modify: `backend/app/models/user.py`, `app/schemas/user.py`, `app/schemas/auth.py`, `app/services/users.py`, `app/services/auth.py`, `app/api/auth.py`, `app/api/users.py`, `app/core/deps.py`
- Create: `backend/alembic/versions/<autogen>_add_users_is_approved.py`
- Test: `tests/api/test_register.py`, `tests/api/test_users.py`, `tests/api/test_auth.py`, `tests/conftest.py`

**Interfaces:**
- Produces:
  - `User.is_approved: Mapped[bool]` (`default=True`, migration `server_default=sa.true()`).
  - `UserOut.is_approved: bool`.
  - `RegisterRequest.account_type: Literal["seeker", "recruiter"] = "seeker"`.
  - `users.create_user(..., is_approved: bool = True)`.
  - `users.approve_user(db, *, user_id: int, actor_id: int) -> User`, `users.reject_user(db, *, user_id: int, actor_id: int) -> None`.
  - `auth.register(..., account_type: str) -> User` (recruiter → `is_approved=False`).
  - `PENDING_APPROVAL = "Hesabınız yönetici onayı bekliyor"` in `services/auth.py`.
  - conftest: `pending_recruiter` fixture (bekleyen@example.com, "Deniz Bekler", `RECRUITER_PASSWORD`, `is_approved=False`).

- [ ] **Step 1: Write failing tests**
  - `test_register.py::test_register_recruiter_is_pending` — `POST /api/auth/register` `{..., "account_type": "recruiter"}` → 202, body `{"status": "pending_approval"}`, `"access_token" not in response.cookies`; DB'de kullanıcı `role == recruiter`, `is_approved is False`.
  - `test_register.py::test_register_default_is_seeker` — `account_type` yok → 201, rol seeker (mevcut test yeterliyse `is_approved is True` assert'i ekle).
  - `test_auth.py::test_pending_login_correct_password_403` → 403, `detail == "Hesabınız yönetici onayı bekliyor"`, cookie yok.
  - `test_auth.py::test_pending_login_wrong_password_401` → 401 "E-posta veya şifre hatalı".
  - `test_auth.py::test_unapproved_token_rejected` — recruiter ile giriş yap, DB'de `is_approved=False` yap, `GET /api/auth/me` → 401.
  - `test_users.py::test_approve_pending_user` — admin `POST /api/users/{id}/approve` → 200, `is_approved true`; ardından o kullanıcı giriş 200; audit `user.approve` payload `{}`.
  - `test_users.py::test_approve_already_approved_409` → 409 "Hesap zaten onaylı".
  - `test_users.py::test_reject_pending_user` → 204, kullanıcı DB'de yok, audit `user.reject` `entity_id == id`; aynı e-postayla kayıt tekrar 202.
  - `test_users.py::test_reject_approved_user_409` → 409 "Yalnızca onay bekleyen hesaplar reddedilebilir".
  - `test_users.py::test_approve_reject_require_admin` — recruiter → 403; olmayan id → 404 "Kullanıcı bulunamadı".
  - `test_users.py::test_list_users_includes_is_approved`.

- [ ] **Step 2: Run, expect FAIL** — `uv run pytest tests/api/test_register.py tests/api/test_auth.py tests/api/test_users.py -q`

- [ ] **Step 3: Implement**
  - Model + `uv run alembic revision --autogenerate -m "add_users_is_approved"` (geçici DB'de önce `upgrade head`); `server_default=sa.true()` elle doğrula.
  - `authenticate`: şifre doğru + aktif + `not is_approved` → `PermissionDeniedError(PENDING_APPROVAL)`; rate limiter'a başarısızlık yazma.
  - `get_current_user`: `not user.is_approved` → `AuthenticationError` (aktiflik kontrolüyle aynı satır).
  - `/register`: `status_code=201` sabit kalamaz; seeker'da 201 + cookie, recruiter'da `JSONResponse(202, {"status": "pending_approval"})`. Yanıt modeli `UserOut | PendingRegistration` (`schemas/auth.py`, `status: Literal["pending_approval"]`).
  - `reject_user`: `db.delete(user)`; bekleyen hesabın `user.create` audit satırı (actor None) kalır.

- [ ] **Step 4: Run, expect PASS** — aynı komut + `uv run pytest -q` (regresyon).

- [ ] **Step 5: Commit** — `feat(auth): İK kaydı ve yönetici onayı eklendi`

---

### Task 2: Çalışma alanı yalıtımı ve admin'in işveren uçlarından çıkarılması (backend)

**Files:**
- Modify: `app/core/deps.py`, `app/api/jobs.py`, `app/api/applications.py`, `app/api/candidates.py`, `app/services/jobs.py`, `app/services/applications.py`, `app/services/notes.py`, `app/services/candidates.py`
- Test: Create `tests/api/test_isolation.py`; modify `tests/api/test_seeker_access.py`, `test_application_detail.py`, `test_candidate_delete.py`, `tests/conftest.py`

**Interfaces:**
- Consumes: Task 1 `User.is_approved`.
- Produces:
  - `require_recruiter` / `RecruiterUser` (yalnızca `UserRole.RECRUITER`); `StaffUser` ve `require_staff` kaldırılır.
  - Servis imzalarına `owner_id: int` (keyword) eklenir: `jobs.list_jobs(db, *, owner_id)`, `jobs.get_job(db, job_id, *, owner_id)`, `get_job_with_stats`, `update_job`, `delete_job`; `applications.get_application(db, application_id, *, owner_id)`, `get_detail`, `change_status`, `retry_application`, `list_applications`, `mark_job_for_rescore`; `notes.add_note`, `notes.delete_note`; `candidates.upload_cvs`, `candidates.delete_candidate`, yeni `candidates.get_owned_candidate(db, candidate_id, *, owner_id) -> Candidate`.
  - Ortak yardımcı: `services/jobs.py` içinde `owned_job_ids(owner_id) -> Select` gerekmez; `get_job` sahibine göre `select(Job).where(Job.id == job_id, Job.created_by == owner_id)` yapar, diğerleri `Application.job_id` üzerinden `Job.created_by == owner_id` join'i kullanır.
  - Arka planda çalışan çağrılar (`mark_job_for_rescore` pipeline'dan çağrılıyorsa) için `owner_id` yalnızca API yolunda zorunlu; pipeline sahipliği kontrol etmez.
  - conftest: `other_recruiter` fixture (ik2@example.com, "Elif Başka", `RECRUITER_PASSWORD`) ve `foreign_application(db, other_recruiter, storage) -> Application` fixture (açık ilan + aday + başvuru + bir not, hepsi `other_recruiter`'ın).

- [ ] **Step 1: Write failing tests** (`test_isolation.py`)
  - `test_foreign_resources_return_404` — parametrize: `GET/PATCH/DELETE /jobs/{job}`, `GET /jobs/{job}/applications`, `POST /jobs/{job}/rescore`, `POST /jobs/{job}/cvs` (1 geçerli fixture PDF), `GET /applications/{app}`, `PATCH /applications/{app}/status` `{"status":"reviewing"}`, `POST /applications/{app}/notes` `{"body":"x"}`, `POST /applications/{app}/retry`, `DELETE /notes/{note}`, `GET /candidates/{cand}/cv`, `DELETE /candidates/{cand}` → `recruiter_client` ile hepsi 404; yanıt `detail` hiç olmayan id (`999999`) ile aynı.
  - `test_list_jobs_only_own` — `foreign_application` var, recruiter kendi ilanını açar; `GET /jobs` yalnızca kendi ilanı.
  - `test_foreign_rows_unchanged` — yukarıdaki istekler sonrası yabancı ilan/aday/not DB'de değişmemiş, CV dosyası diskte duruyor.
  - `test_recruiter_can_delete_own_candidate` — recruiter kendi adayını siler → 204, dosya diskte yok, audit `candidate.delete`.
  - `test_seeker_access.py`: listeyi `EMPLOYER_ENDPOINTS` (jobs/applications/notes/candidates) ve `ADMIN_ENDPOINTS` (users/audit) olarak ayır; yeni `test_admin_forbidden_on_employer_endpoints` → `admin_client` ile tüm `EMPLOYER_ENDPOINTS` 403.
  - Admin ile ilan/başvuru kuran mevcut testleri (`test_application_detail.py`, `test_candidate_delete.py`) `recruiter_client` sahipliğine çevir; "admin silebilir" testleri "sahibi olan recruiter silebilir" olur, "recruiter silemez → 403" testi "başka recruiter → 404" olur.

- [ ] **Step 2: Run, expect FAIL** — `uv run pytest tests/api/test_isolation.py tests/api/test_seeker_access.py -q`

- [ ] **Step 3: Implement** — router'lar `RecruiterUser` alır ve `owner_id=user.id` geçirir; `download_cv` sorgusu `candidates.get_owned_candidate`'e taşınır (router'da DB sorgusu kalmaz).

- [ ] **Step 4: Run, expect PASS** — `uv run pytest -q`, `uv run mypy app`

- [ ] **Step 5: Commit** — `feat(jobs): İK uzmanı başına çalışma alanı yalıtımı eklendi`

---

### Task 3: Günlük CV kotası, admin denetim süzmesi, CLI (backend)

**Files:**
- Modify: `app/services/candidates.py`, `app/services/audit.py`, `app/cli.py`, `app/services/demo.py` (yalnızca gerekirse)
- Test: `tests/api/test_upload.py`, `tests/api/test_audit.py` (yoksa oluştur), `tests/unit/test_cli.py`, `tests/unit/test_demo.py`

**Interfaces:**
- Produces:
  - `candidates.DAILY_CV_LIMIT = 100`; `upload_cvs` dosya doğrulamasından **önce** `len(files) > kalan` ise `TooManyRequestsError(f"Günlük CV sınırına ulaştınız ({DAILY_CV_LIMIT}). Kalan hakkınız: {kalan}.")`. Sayım: son 24 saatte `Candidate.created_at`, `Application → Job.created_by == owner_id` join'i ile.
  - `audit.list_recent(db, limit=RECENT_LIMIT)` yalnızca `AuditLog.entity_type == "user"` döner.
  - CLI: `transfer-jobs --from EMAIL --to EMAIL`; `transfer_jobs(from_email: str, to_email: str) -> int` (çıkış kodu). `seed-demo --owner EMAIL` (isteğe bağlı).

- [ ] **Step 1: Write failing tests**
  - `test_upload.py::test_daily_cv_limit` — sahibin ilanlarına bağlı 95 aday DB'de doğrudan oluşturulmuş (`created_at` şimdi); 6 dosyalık yükleme → 429, mesaj "Kalan hakkınız: 5.", `storage` dizini yükleme öncesiyle aynı. 5 dosyalık yükleme → 202.
  - `test_upload.py::test_daily_cv_limit_window` — 100 aday `created_at = now - 25h` → yükleme 202.
  - `test_upload.py::test_daily_cv_limit_per_owner` — `other_recruiter`'ın 100 adayı recruiter'ın kotasını etkilemez.
  - `test_audit.py::test_admin_sees_only_account_events` — recruiter ilan açar ve seeker kaydolur; admin `GET /api/audit` → tüm satırların `entity_type == "user"`, `job.create` yok, `auth.login` var.
  - `test_cli.py::test_transfer_jobs` — admin'in 2 ilanı → recruiter'a; çıkış 0, `created_by` güncel, 2 `job.transfer` audit satırı payload `{"from_user_id", "to_user_id"}`.
  - `test_cli.py::test_transfer_jobs_rejects_non_recruiter_target` — hedef admin, seeker, bekleyen veya olmayan e-posta → çıkış 1.
  - `test_cli.py::test_seed_demo_uses_owner` / `test_seed_demo_defaults_to_first_recruiter` / `test_seed_demo_without_recruiter_fails` (stderr "Önce bir İK hesabı oluşturun").

- [ ] **Step 2: Run, expect FAIL**
- [ ] **Step 3: Implement** — `transfer_jobs` servisi `services/jobs.py`'de: `transfer_jobs(db, *, from_user_id: int, to_user_id: int) -> int`; CLI yalnızca e-posta → kullanıcı çözümler ve hedef rolünü doğrular.
- [ ] **Step 4: Run, expect PASS** — `uv run pytest -q`; `ruff check .`, `ruff format --check .`, `mypy app`.
- [ ] **Step 5: Commit** — `feat(cv): İK uzmanı günlük CV sınırı, admin denetim süzmesi ve ilan aktarma komutu eklendi`

---

### Task 4: Arayüz (frontend)

**Files:**
- Modify: `src/types/user.ts`, `src/api/auth.ts`, `src/api/users.ts`, `src/hooks/useAuth.ts`, `src/hooks/useUsers.ts`, `src/lib/constants.ts`, `src/router.tsx`, `src/components/Sidebar.tsx`, `src/pages/RegisterPage.tsx`, `src/pages/LoginPage.tsx`, `src/pages/UsersPage.tsx`, `src/pages/ApplicationDetailPage.tsx`
- Rename: `src/components/RequireStaff.tsx` → `RequireRecruiter.tsx`
- Test: `__tests__/RegisterPage.test.tsx`, `UsersPage.test.tsx`, `routeGuards.test.tsx`, `CandidateDelete.test.tsx`, `ApplicationDetailPage.test.tsx`, `AuditPage.test.tsx`, `testUtils.tsx`

**Interfaces:**
- Consumes: Task 1–3 API (`account_type`, 202 `{status:"pending_approval"}`, `is_approved`, `/users/{id}/approve`, `/users/{id}/reject`).
- Produces:
  - `User.is_approved: boolean`; `RegisterRequest.account_type: "seeker" | "recruiter"`; `type RegisterResult = User | { status: "pending_approval" }`.
  - `approveUser(id): Promise<User>`, `rejectUser(id): Promise<void>`; hooks `useApproveUser`, `useRejectUser` (ikisi de `["users"]` sorgusunu geçersiz kılar).
  - `homePathFor`: admin → `/users`.
  - `AUDIT_ACTION_LABELS` += `user.approve: "Hesap onaylandı"`, `user.reject: "Hesap reddedildi"`, `job.transfer: "İlan aktarıldı"`.

- [ ] **Step 1: Write failing tests**
  - `RegisterPage`: "İşe alım yapıyorum" seçilip gönderilince istek gövdesi `account_type: "recruiter"`; 202 yanıtında "Başvurunuz alındı. Yönetici onayladıktan sonra giriş yapabilirsiniz." metni ve `/login` bağlantısı; konum `/register`'da kalır. Varsayılan seçimde gövde `account_type: "seeker"`.
  - `LoginPage`: 403 yanıtında `role="alert"` içinde "Hesabınız yönetici onayı bekliyor".
  - `UsersPage`: bekleyen kullanıcı "Onay bekleyenler" listesinde (`role="list"`, name "Onay bekleyenler"); "Onayla" → `POST /api/users/{id}/approve`; "Reddet" ilk tıklamada istek atmaz ve düğme "Emin misiniz? Reddet" olur, ikinci tıklamada `POST /api/users/{id}/reject`. Bekleyen yoksa bölüm yok.
  - `Sidebar`: admin'de "Kullanıcılar" yanında bekleyen sayısı rozeti (`aria-label="2 onay bekleyen"`), "İlanlar" bağlantısı yok.
  - `routeGuards`: admin `/jobs` → `/users`; admin `/applications/1` → `/users`; admin `/` → `/users`; recruiter `/users` → `/jobs` (mevcut).
  - `CandidateDelete` / `ApplicationDetailPage`: silme düğmesi recruiter'a görünür, admin bu sayfaya giremez.

- [ ] **Step 2: Run, expect FAIL** — `npm run test`
- [ ] **Step 3: Implement** — `apiFetch` 202 gövdesini döndürüyor mu kontrol et; `useRegister` başarıda yalnızca `User` dönerse `["auth","me"]`'yi günceller.
- [ ] **Step 4: Run, expect PASS** — `npm run lint`, `format:check`, `typecheck`, `test`, `build`.
- [ ] **Step 5: Commit** — `feat(ui): İK kaydı, onay kuyruğu ve yalıtılmış işveren arayüzü eklendi`

---

### Task 5: Dokümanlar, tam doğrulama, elle deneme

**Files:** `ISKELET.md` (1.5), `CLAUDE.md`, `README.md`, spec durum satırı.

- [ ] **Step 1:** Spec §6'daki ISKELET değişiklikleri (F1d, F2, F11, F12, yeni F16/F17, §2.2, §3.2 rotalar, §3.3 uçlar + "giriş" yetki notu, §3.4 `is_approved`, V5); CLAUDE.md proje açıklaması + `transfer-jobs`/`seed-demo --owner` komutları; README kurulum (ilk İK hesabı).
- [ ] **Step 2:** Tam doğrulama (backend 4 + frontend 5 komut) hatasız; boş DB'de `alembic upgrade head` ve `downgrade -1`.
- [ ] **Step 3:** `LLM_PROVIDER=fake` ile spec §7'deki 6 adımlık elle deneme (yerel dev DB'ye önce `alembic upgrade head`; mevcut admin ilanları için `transfer-jobs`).
- [ ] **Step 4: Commit** — `docs: çoklu işveren (İK kaydı ve yalıtım) dokümanlara işlendi`
