# KariyerAI — Çoklu İşveren: Kendi Kaydolan, Birbirinden Yalıtılmış İK Uzmanları

> Durum: kullanıcı tarafından onaylandı (2026-10-20); uygulandı
> Bu doküman onaylanınca ISKELET.md (sürüm 1.5), CLAUDE.md ve README buna göre güncellenir.
> Önceki adım: [CV geliştirme](2026-10-19-cv-gelistirme-design.md) (`feat/cv-gelistirme` dalı). Bu iş o dalın üstüne kurulur.

## 1. Amaç ve neden

KariyerAI'nin işveren tarafı bugün tek bir şirketin İK ekibine kapalıdır: hesapları admin açar ve her İK kullanıcısı tüm ilanları ve adayları görür. Kullanıcı (proje sahibi) uygulamayı herkese açmak istiyor. Bunun için:

- **Şirket hesabı yok.** İK uzmanı, iş arayan gibi **kendi e-postasıyla kaydolur** (kullanıcının sözü: "Şirketin değil İK'nın mail ile girmesi gerek").
- **Her İK uzmanının çalışma alanı kapalıdır.** Aynı şirketten iki kişi kaydolsa bile birbirlerinin ilanlarını, adaylarını, başvurularını ve notlarını **görmez**.
- **Admin İK verisini görmez.** Admin yalnızca hesapları yönetir.
- **İK hesabını admin onaylar.** Onay gelene kadar hesap giriş yapamaz. Böylece LLM kotası tanınmayan kişilerce harcanmaz.

ISKELET §2.2'deki "çoklu işveren" maddesi bu dokümanla şirket değil **kullanıcı başına yalıtım** olarak yeniden tanımlanır.

## 2. Hedefler, hedef olmayanlar, kaçınılacaklar

**Hedefler**
- Kayıt ekranında "İş arıyorum / İşe alım yapıyorum" seçimi.
- İK kaydı → "onay bekliyor" hesabı → admin onaylar/reddeder → onaylanan uzman kendi alanında çalışır.
- Tüm işveren uçları ve ekranları yalnızca giriş yapan İK uzmanının kendi verisini gösterir.
- Admin: kullanıcı yönetimi + onay kuyruğu + yalnızca hesap olaylarını içeren denetim kaydı.

**Hedef olmayanlar**
- Şirket/ekip kavramı, ekip içinde ilan paylaşma, davet bağlantısı.
- E-posta bildirimi, e-posta doğrulama, şifre sıfırlama e-postası (ISKELET §2.3).
- Admin'in İK verisine "salt okunur" erişimi veya kullanıcı adına giriş (impersonation).

**Kaçınılacaklar (çalışsa bile başarısızlık sayılır)**
- Bir İK uzmanının başka bir uzmanın ilanını, adayını, başvurusunu, notunu, CV dosyasını veya denetim kaydını **herhangi bir yoldan** görmesi ya da varlığını öğrenmesi (liste, detay, indirme, sayım, hata mesajı farkı).
- Admin'in API veya arayüz üzerinden İK verisine erişebilmesi.
- Onaylanmamış İK hesabının herhangi bir işveren ucunu çağırabilmesi veya LLM işlemi başlatabilmesi.

## 3. Kullanıcı akışı

1. **Kayıt (`/register`):** Ad, e-posta, şifre ve hesap türü (iş arıyorum / işe alım yapıyorum).
   - İş arayan: bugünkü gibi hesap açılır, cookie set edilir, `/cv-checks`'e gider (F13 değişmez).
   - İK: hesap **onay bekliyor** durumunda açılır, cookie **set edilmez**. Sayfa "Başvurunuz alındı. Yönetici onayladıktan sonra giriş yapabilirsiniz." mesajını gösterir ve giriş sayfasına bağlantı verir.
2. **Onay bekleyen hesapla giriş:** Şifre doğruysa 403 "Hesabınız yönetici onayı bekliyor". Şifre yanlışsa bugünkü genel 401 mesajı döner. Böylece mesaj farkı yalnızca şifreyi bilen kişiye görünür.
3. **Admin (`/users`):** Sayfanın üstünde "Onay bekleyenler" bölümü (ad, e-posta, kayıt tarihi, **Onayla** / **Reddet**). Altında bugünkü kullanıcı listesi. Bekleyen yoksa bölüm gizlenir. Sidebar'daki "Kullanıcılar" bağlantısında bekleyen sayısı rozet olarak görünür.
   - Onayla → hesap aktifleşir, kişi giriş yapabilir.
   - Reddet → hesap kalıcı silinir (henüz verisi yoktur), aynı e-postayla yeniden kayıt olunabilir.
4. **Onaylanan İK uzmanı:** Bugünkü işveren deneyimi (ilanlar, CV yükleme, sıralama, detay, notlar), ancak yalnızca kendi verisiyle. Kendi adaylarını KVKK kapsamında kalıcı silebilir (bugün bu yetki admin'deydi).
5. **Admin ana sayfası:** `/users`. Sidebar'da yalnızca "Kullanıcılar" ve "Denetim" görünür. Admin `/jobs*`, `/applications/*` sayfalarına giderse `/users`'a yönlenir.

## 4. Kararlar ve teknik yaklaşım

### 4.1 Roller ve yetki

| Rol | Ne yapar | İşveren uçları | `/users`, `/audit` | `/cv-checks` |
|---|---|---|---|---|
| `admin` | Hesap yönetimi, onay | **403** | ✓ | 403 |
| `recruiter` (onaylı) | Kendi kapalı alanında işe alım | ✓ (yalnızca kendi verisi) | 403 | 403 |
| `recruiter` (onay bekliyor) | — | giriş yapamaz | — | — |
| `seeker` | Kendi CV değerlendirmeleri | 403 | 403 | ✓ |

- `require_staff` / `StaffUser` yerine `require_recruiter` / `RecruiterUser` gelir (yalnızca `recruiter`). Admin işveren uçlarında 403 alır.
- `get_current_user` onaylanmamış kullanıcıyı da reddeder (401), `is_active` kontrolüyle aynı yerde. Normalde bu kişinin token'ı olmaz; bu ikinci savunma hattıdır.
- Admin'in elle oluşturduğu hesaplar (`POST /users`) onaylı açılır.

### 4.2 Veri modeli (onay gerektiren değişiklik — bu dokümanın onayı kapsar)

- `users` tablosuna `is_approved BOOL NOT NULL` eklenir. Migration'da mevcut satırlar için `server_default` true. Yeni kayıtlarda: İK kaydı `false`, diğer her yol `true`.
- Başka tablo değişmez. Sahiplik zaten var:
  - `jobs.created_by` → ilanın sahibi.
  - Başvuru, aday ve not sahipliği ilan üzerinden türetilir: `application.job.created_by`, `candidate → applications → job.created_by` (MVP'de aday başına tek başvuru), `note → application → job.created_by`.
- Bilinçli olarak `owner_id` sütunu eklenmez: tek kaynak `jobs.created_by` olduğundan sahiplik tutarsızlaşamaz.

### 4.3 Yalıtım (her sorgu sahibine göre süzülür)

Kural `cv_checks` ile aynıdır: **başkasının kaydı "bulunamadı" (404) döner**, 403 değil. Böylece kaydın varlığı sızmaz.

| Uç | Değişiklik |
|---|---|
| `GET /jobs` | `created_by == user.id` olanlar |
| `GET/PATCH/DELETE /jobs/{id}`, `POST /jobs/{id}/cvs`, `GET /jobs/{id}/applications`, `POST /jobs/{id}/rescore` | İlan başkasınınsa 404 "İlan bulunamadı" |
| `GET /applications/{id}`, `PATCH .../status`, `POST .../notes`, `POST .../retry` | Başvurunun ilanı başkasınınsa 404 "Başvuru bulunamadı" |
| `DELETE /notes/{id}` | Notun başvurusunun ilanı başkasınınsa 404. Kendi ilanında başkasının notu artık oluşamaz; yazar kontrolü yine de kalır |
| `GET /candidates/{id}/cv`, `DELETE /candidates/{id}` | Adayın başvurusunun ilanı başkasınınsa 404. Silme yetkisi admin'den **adayın sahibi olan İK uzmanına** geçer |

- Süzme servis katmanında yapılır: servis fonksiyonları `owner_id` parametresi alır (`cv_checks` servisindeki gibi). Router yalnızca `user.id`'yi geçirir.
- `ApplicationDetail` içinde notları yazanın adı gösterilir; sahip tek kişi olduğu için yalnızca kendi notları görünür.
- Arka plan işleri (pipeline, açılışta yeniden kuyruğa alma) kullanıcıdan bağımsızdır ve değişmez.

### 4.4 Kayıt ve onay

- `RegisterRequest` alanına `account_type: "seeker" | "recruiter"` eklenir. Varsayılan `"seeker"`, böylece bugünkü istemciler ve testler bozulmaz. Rol hâlâ istekten alınmaz (F13a).
- `POST /auth/register` yanıtı:
  - seeker → bugünkü gibi 201 + `UserOut` + cookie.
  - recruiter → 202 + `{"status": "pending_approval"}`, cookie yok.
- Kayıt hız sınırı (5/dk/IP) her iki tür için ortaktır.
- Yeni uçlar (admin):
  - `POST /users/{id}/approve` → 200 `UserOut`. Kullanıcı zaten onaylıysa 409. Audit: `user.approve`.
  - `POST /users/{id}/reject` → 204. Yalnızca onay bekleyen hesap için; onaylı hesapta 409 ("Yalnızca onay bekleyen hesaplar reddedilebilir"). Kullanıcı satırı silinir. Audit: `user.reject` (`entity_id` = silinen id; payload boş).
  - `GET /users` yanıtındaki `UserOut`'a `is_approved` eklenir. Arayüz onay bekleyenleri buradan ayırır, ayrı liste ucu gerekmez.
- `PATCH /users/{id}` ile onaylanmamış hesabın rolü ya da aktifliği değiştirilebilir, ama bu onay yerine geçmez.

### 4.5 Kota

- İK uzmanı başına **son 24 saatte en fazla 100 CV** yüklenir (kendi ilanlarına bağlı `candidates.created_at` sayılır).
- Bir yükleme isteği sınırı aşacaksa istek **tümüyle** 429 alır: "Günlük CV sınırına ulaştınız (100). Kalan hakkınız: N." Hiçbir dosya diske yazılmaz. Kısmen kabul edilmez; kullanıcı neyin işlendiğini tahmin etmek zorunda kalmasın.
- `DAILY_CV_LIMIT = 100` sabiti `services/candidates.py`'de tutulur. İş arayan sınırı (10) değişmez.

### 4.6 Denetim kaydı

- Kayıt yazımı değişmez: tüm olaylar bugünkü gibi yazılır.
- `GET /audit` (admin) yalnızca `entity_type == "user"` olan kayıtları döner: `auth.login`, `user.create`, `user.update`, `user.approve`, `user.reject`. İlan, aday, başvuru ve `cv_check` olayları admin'e gösterilmez. Son 500 sınırı süzülmüş kayıtlara uygulanır.
- İK uzmanına kendi denetim ekranı bu aşamada **yapılmaz** (başvuru detayındaki durum geçmişi zaten var).

### 4.7 Mevcut veri ve CLI

- Mevcut ilanlar `created_by` sahibinin alanında kalır.
- Admin'in oluşturduğu ilanlar (ör. `seed-demo` ile oluşanlar) admin artık göremeyeceği için erişilemez kalır. Bunun için yeni komut:
  `uv run python -m app.cli transfer-jobs --from admin@example.com --to ik@example.com`
  - Kaynağın tüm ilanlarını hedefe aktarır (`created_by` güncellenir).
  - Hedef aktif, onaylı bir `recruiter` olmalıdır; değilse hata ve çıkış kodu 1.
  - Aktarılan ilan sayısını yazar. Audit: her ilan için `job.transfer` (payload: `{"from_user_id", "to_user_id"}`).
- `seed-demo` artık ilanı ilk aktif admin'e değil, `--owner <e-posta>` ile verilen onaylı İK uzmanına açar. `--owner` verilmezse ilk aktif onaylı recruiter seçilir; o da yoksa "Önce bir İK hesabı oluşturun" hatası verir.
- `create-admin` değişmez.

### 4.8 Arayüz

- `RegisterPage`: hesap türü seçimi (iki seçenekli radyo, varsayılan "İş arıyorum"). İK seçilince başarıda onay bekleme ekranı gösterilir.
- `LoginPage`: 403 mesajı alanın üstünde `role="alert"` ile gösterilir (sunucu mesajı aynen). Giriş sayfasındaki tanıtım metni "İK uzmanları da kaydolabilir; hesaplar yönetici onayıyla açılır" bilgisini içerir.
- `UsersPage`: "Onay bekleyenler" bölümü, Onayla/Reddet düğmeleri. Reddet için sayfa içi onay adımı kullanılır (tarayıcı `confirm()` değil): ilk tıklamada düğme "Emin misiniz? Reddet" olur. Kullanıcı ekleme formundaki rol seçenekleri "İK uzmanı / Admin" olarak kalır.
- `homePathFor`: admin → `/users`, recruiter → `/jobs`, seeker → `/cv-checks`.
- `RequireStaff` → `RequireRecruiter`. Admin işveren sayfalarında `/users`'a yönlenir.
- Sidebar: admin için yalnızca Kullanıcılar (+ bekleyen rozeti) ve Denetim; recruiter için İlanlar.
- `ApplicationDetailPage`'deki "Adayı sil (KVKK)" düğmesi admin yerine İK uzmanına görünür.
- `AuditPage`: yeni etiketler `user.approve` → "Hesap onaylandı", `user.reject` → "Hesap reddedildi", `job.transfer` → "İlan aktarıldı".

## 5. Gizlilik ve güvenlik

- Yalıtım sızıntısı en büyük risk. Her işveren ucu için "başka bir İK uzmanının kaydı → 404" API testi zorunludur (parametrize test, `test_seeker_access.py` örneği gibi). Admin için de her işveren ucunda 403 testi yazılır.
- Hata mesajları kayıt sahibine göre değişmez: başkasının ilanı ile hiç olmayan ilan aynı yanıtı verir.
- Reddedilen hesabın audit kaydında e-posta ya da ad yazılmaz; yalnızca id.
- Loglarda yalnızca id'ler.

## 6. Doküman değişiklikleri (onayla birlikte yapılır)

- **ISKELET.md 1.5:**
  - §1 hedef kullanıcı: admin = hesap yöneticisi; İK uzmanı kendi kaydolur, admin onaylar, verisi kapalıdır.
  - F1(d): admin işveren uçlarında 403.
  - F2: onay/ret.
  - F11: silme yetkisi adayın sahibi olan İK uzmanında.
  - F12: admin'in gördüğü kayıtlar.
  - Yeni **F16 (İK kaydı ve onay)** ve **F17 (çalışma alanı yalıtımı)**.
  - §2.2'den "çoklu işveren" maddesi çıkarılır.
  - §3.3 yeni uçlar ve yetki satırları.
  - §3.4 `users.is_approved`.
  - V5 güncellenir.
  - B4 değişmez.
- **CLAUDE.md:** proje açıklaması ve komutlara `transfer-jobs`, `seed-demo --owner` eklenir.
- **README:** kurulumda ilk İK hesabı nasıl açılır (kayıt + admin onayı ya da admin'in elle oluşturması).

## 7. Doğrulama

- Tam doğrulama (CLAUDE.md) hatasız.
- Yeni migration boş veritabanında `upgrade head` ile çalışır; `downgrade -1` geri alır.
- Elle deneme `LLM_PROVIDER=fake` ile yapılır:
  1. İK kaydı.
  2. Giriş reddi.
  3. Admin onayı.
  4. İK uzmanının ilan açıp CV yüklemesi.
  5. İkinci İK uzmanının ilk uzmanın ilan URL'sine gitmesi → bulunamadı.
  6. Admin'in `/jobs`'a gitmesi → `/users`.

## 8. Builder'a bırakılanlar

- Servis fonksiyonlarının imza ayrıntıları ve sahiplik süzmesinin ortak bir yardımcıya alınıp alınmayacağı.
- Onay bekleyen rozetinin sayısının nereden geldiği (`GET /users` sonucundan türetilmesi yeterlidir).
- Test dosyalarının bölünmesi.

## 9. Benim kararlarım (kullanıcı henüz onaylamadı)

1. Yalıtım için yeni sahiplik sütunu açılmıyor; sahiplik `jobs.created_by` üzerinden türetiliyor.
2. Başkasının kaydına 404 dönülüyor (403 değil).
3. KVKK aday silme yetkisi admin'den adayın sahibi olan İK uzmanına geçiyor.
4. Admin denetim ekranında yalnızca hesap olayları görünüyor.
5. Kota: İK uzmanı başına 24 saatte 100 CV. Sınırı aşan yükleme tümüyle reddediliyor. Yeniden puanlama ve "Yeniden dene" kotaya sayılmıyor. Kriter değişikliğiyle büyük bir ilanın yeniden puanlanması çok LLM çağrısı harcayabilir; bu bilinen bir risk, ileride ayrı sınır konabilir.
6. Reddedilen hesap pasifleştirilmiyor, siliniyor; aynı e-postayla tekrar başvurulabiliyor.
7. Onay bekleyen hesapla, şifre doğruysa 403 ve açık mesaj dönüyor.
8. Mevcut admin ilanları için `transfer-jobs` komutu ekleniyor; `seed-demo` artık bir İK hesabına yazıyor.
9. Kayıt isteğinde `account_type` varsayılanı `seeker`, böylece mevcut istemciler bozulmuyor.
