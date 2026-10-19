# KariyerAI — İki Taraflı Uygulama: CV Geliştirme (İş Arayan Tarafı)

> Durum: taslak, kullanıcı onayı bekliyor · 2026-10-19
> Bu doküman onaylanınca ISKELET.md (sürüm 1.4), CLAUDE.md ve AGENT.md buna göre güncellenir.

## 1. Amaç ve neden

KariyerAI bugün tek bir şirketin İK ekibine kapalı bir araç. Kullanıcı (proje sahibi) uygulamanın **iki taraflı** olmasını istiyor:

| Taraf | Kullanıcının adı | Ne yapar |
|---|---|---|
| **İş arayan** | "CV geliştirme" | CV'sini yükler, hedeflediği iş tanımını **kendisi girer**; sistem bu ilana göre CV'sinde **neyin eksik** olduğunu anlatır. |
| **İşveren** | "İşe uygunluk" | Bugünkü KariyerAI: ilan açar, gelen CV'leri ilana göre puanlatır ve sıralatır; karar İK'dadır. |

İşveren tarafı zaten var. Bu doküman **iş arayan tarafını** tanımlar.

## 2. İki ayrı iş, sıra

Kullanıcının "tek şirkete kapalı olmasın" isteği aslında iki bağımsız proje:

1. **CV Geliştirme (bu doküman):** herkesin kayıt olup kendi CV'sini kendi iş tanımına göre değerlendirtebilmesi.
2. **Çoklu işveren (sonraki doküman):** birden fazla şirketin kendi kapalı çalışma alanıyla (ilanları, adayları, kullanıcıları birbirinden ayrı) kullanması. Bu, her tabloya şirket kimliği eklemeyi ve tüm sorgulara yalıtım koymayı gerektirir; ayrı tasarlanır.

Önce 1 yapılır, çünkü kullanıcıya en görünür yeniliği getirir ve mevcut işveren tarafına dokunmadan eklenebilir.

## 3. Hedefler, hedef olmayanlar, kaçınılacaklar

**Hedefler**
- İş arayan e-posta + şifre ile **kendisi kayıt olur** (işveren hesapları bugünkü gibi admin tarafından açılır).
- CV (PDF/DOCX) yükler + hedef iş tanımını girer → birkaç dakika içinde **eksiklik raporu** görür.
- Rapor her maddede kanıta dayanır: "karşılandı" denen beceri CV'den birebir alıntıyla gösterilir (mevcut F6c kuralı).
- Geçmiş değerlendirmelerini listeler, tekrar açar, siler.

**Hedef olmayanlar (bu aşamada)**
- İş arayanın işverenin ilanlarını görmesi veya uygulama içinden başvurması.
- CV'yi sistemin yeniden yazması / CV şablonu üretmesi.
- Çoklu işveren (bkz. §2).

**Kaçınılacaklar (çalışsa bile başarısızlık sayılır)**
- İş arayanın verisinin işveren ekranlarında (aday listesi, denetim, demo) görünmesi.
- İş arayanın işveren uçlarına (`/jobs`, `/applications`, `/candidates`, `/users`, `/audit`) erişebilmesi.
- Önerilerin adayı CV'ye **sahip olmadığı beceriyi yazmaya** yönlendirmesi. Öneri dili hep "bu beceriye sahipsen …" biçimindedir.
- Yaş, cinsiyet vb. korunan özelliklerin rapora girmesi (mevcut yasak aynen geçerli).

## 4. Kullanıcı akışı

1. `/register` → ad, e-posta, şifre (≥ 10 karakter) → hesap `seeker` rolüyle açılır, oturum başlar.
2. `/cv-checks` (iş arayanın ana sayfası) → geçmiş değerlendirmeler listesi + "Yeni değerlendirme".
3. `/cv-checks/new` → iki bölüm:
   - **Hedef iş:** başlık + ilanın kriterleri (zorunlu beceriler, tercih edilen beceriler, min. deneyim yılı, min. eğitim, diller). Alanlar ve sınırlar F3'teki ilan formuyla aynı; bileşenler (`ChipInput` vb.) yeniden kullanılır. İsteğe bağlı "ilan metni" kutusu yalnızca kullanıcının kendi notu olarak saklanır.
   - **CV:** tek dosya, F4 kuralları (PDF/DOCX, ≤ 5 MB, magic bytes, ≥ 200 karakter metin).
4. Gönderince → `/cv-checks/:id`; "İşleniyor" rozeti, 5 sn'de bir yenileme (F7d ile aynı davranış).
5. Bitince **eksiklik raporu**:
   - Üstte uyum puanı (0–100, mevcut formül ve bantlar) ve "Bu puan bir öneridir …" uyarısının iş arayan sürümü: "Bu değerlendirme yapay zekâ desteklidir; işverenlerin değerlendirmesi farklı olabilir."
   - **Eksikler** (öne çıkan bölüm), önem sırasıyla:
     1. CV'de bulunamayan zorunlu beceriler
     2. Deneyim açığı ("İlan 5 yıl istiyor, CV'nden hesaplanan 3,2 yıl")
     3. Eğitim açığı
     4. Eksik ya da seviyesi düşük / seviyesi yazılmamış diller
     5. Bulunamayan tercih edilen beceriler
   - Her eksik için **kodda üretilen** kısa Türkçe öneri (ör. "CV'nde 'Docker' kanıtı bulunamadı. Bu beceriye sahipsen, kullandığın işi veya projeyi açıkça yaz." / "Dil seviyen CV'de yazmıyor; seviyeni (ör. B2) belirt.").
   - **Güçlü yanlar:** karşılanan kalemler, CV'den kanıt alıntısıyla.
   - AI özeti (mevcut puanlama çıktısı).
   - Ayrıştırılmış CV (sistemin CV'den ne okuduğu) — "sistem deneyimimi yanlış okumuş" durumunu iş arayanın görmesi için.
6. Değerlendirme silinebilir (dosya diskten de silinir).

## 5. Kararlar ve teknik yaklaşım

### 5.1 Roller ve yetki
- `UserRole`'a `seeker` eklenir.
- `core/deps.py`'ye `StaffUser` (admin veya recruiter) bağımlılığı eklenir; **tüm mevcut işveren uçları** `CurrentUser` yerine `StaffUser` kullanır → seeker 403 alır. Her uç için 403 testi.
- `POST /api/auth/register` (oturumsuz): yalnızca `seeker` hesabı açar, rol istekten alınmaz. Aynı e-posta → 409. IP başına dakikada 5 kayıt sınırı (giriş sayacına benzer, bellek içi) → 429.
- Frontend: rol bazlı yönlendirme. Seeker `/jobs` vb.'ye giderse `/cv-checks`'e, staff `/cv-checks`'e giderse `/jobs`'a yönlenir. Kenar çubuğu role göre menü gösterir. Giriş sonrası varsayılan sayfa role göre seçilir.

### 5.2 Veri modeli (yeni tablo, mevcut tablolar değişmez)
İş arayan verisi işveren tablolarına (`candidates`, `applications`) **girmez**; böylece §3'teki "işveren ekranlarında görünmesin" kaçınılacağı yapısal olarak sağlanır.

```
cv_checks(id PK, owner_id FK users ON DELETE CASCADE,
          title, job_text TEXT,
          required_skills JSON, preferred_skills JSON, min_experience_years INT,
          min_education ENUM, languages JSON,
          original_filename, stored_path, file_hash, cv_text TEXT,
          parsed_data JSON NULL, parse_status, parse_error NULL,
          score INT NULL, score_breakdown JSON NULL, ai_summary TEXT NULL,
          score_status, score_error NULL, llm_model NULL, prompt_version NULL,
          created_at, updated_at)
```
- Tek Alembic migration: `users.role` enum'una `seeker` + `cv_checks` tablosu.

### 5.3 İşleme
- Yeni `services/cv_checks.py` (oluşturma, listeleme, detay, silme; sahiplik kontrolü → başkasının kaydı 404).
- Ayrıştırma ve puanlama **mevcut** `cv_parser.parse_cv` ve `scoring.evaluate` ile yapılır. `scoring.evaluate` bir `Job` bekliyor; kriterler kaydedilmemiş bir `Job` nesnesine kopyalanarak verilir (puanlama kodu ve formülü değişmez).
- `pipeline.py`'ye `process_cv_check` eklenir: aynı semafor (aynı anda ≤ 5 LLM çağrısı), aynı Türkçe hata mesajları, açılışta yarıda kalanları yeniden kuyruğa alma.
- **Yeni prompt yok.** Eksik listesi ve öneriler, puan kırılımından (`ScoreBreakdown`) kodda deterministik üretilir (`services/cv_gaps.py`). Bu, LLM'e yeni bir iş vermeden ve prompt sürümü açmadan ilerlemeyi sağlar.
- Kota koruması: kullanıcı başına günde en fazla 10 değerlendirme (429, "Günlük değerlendirme sınırına ulaştın"). Ücretsiz LLM kotası herkese açık kayıtla hızla tükenebileceği için.

### 5.4 API
| Metot | Yol | Yetki | Açıklama |
|---|---|---|---|
| POST | `/auth/register` | herkes | seeker hesabı + oturum cookie'si |
| GET | `/cv-checks` | seeker | kendi değerlendirmeleri (yeniden eskiye) |
| POST | `/cv-checks` | seeker | multipart: kriterler (JSON alanı) + tek dosya → 202 |
| GET | `/cv-checks/{id}` | sahibi | detay + hesaplanmış `gaps` listesi |
| POST | `/cv-checks/{id}/retry` | sahibi | başarısız ayrıştırma/puanlamayı yeniden dene → 202 |
| DELETE | `/cv-checks/{id}` | sahibi | kayıt + dosya kalıcı silinir |

### 5.5 Gizlilik ve denetim
- Loglarda yalnızca id; CV metni/ad/e-posta yok (mevcut kural).
- Denetim kaydı: `cv_check.create`, `cv_check.parse`, `cv_check.score`, `cv_check.delete` — payload'da yalnızca id, durum, puan, model, prompt sürümü.
- Puanlamaya giden metin mevcut `anonymizer`'dan geçer.
- Admin, iş arayan değerlendirmelerinin içeriğini görmez (denetim sayfasında yalnızca olay + id).

## 6. Doküman değişiklikleri (onayla birlikte yapılır)
- **ISKELET.md 1.4:** §1 hedef kullanıcıya "İş arayan"; yeni özellikler F13 (kayıt), F14 (CV değerlendirme), F15 (eksiklik raporu) kabul kriterleriyle; §2.3'ten "Aday tarafı portal" maddesi çıkarılıp yerine "adayın uygulama içinden işverene başvurması" konur; "SSO / şifre sıfırlama" kapsam dışı kalır; §3.2 rotalar, §3.3 uçlar, §3.4 `cv_checks` ve `seeker` rolü; çoklu şirket §2.2'ye "planlanıyor" notuyla.
- **CLAUDE.md:** kavram adlarına `CVCheck`; proje tanımı iki taraflı.
- **AGENT.md:** değişiklik yok (kurallar aynen geçerli).

## 7. Doğrulama
- Backend: register (başarılı, 409, 422, 429), seeker'ın her işveren ucunda 403, cv-checks uçlarında 201/202 + 401 + başkasının kaydında 404, günlük sınır 429, silmede dosyanın diskten kalkması, `cv_gaps` için her kalemde sınır değerler (eksik yok / kısmi / hepsi eksik, deneyim tam-kısmi-sıfır, eğitim bir alt/çok alt, dil seviyesi yok/düşük/yeterli).
- Frontend: kayıt sayfası, rol bazlı yönlendirme, form doğrulama, rapor sayfasında eksiklerin ve uyarının görünmesi.
- CLAUDE.md "Tam doğrulama" komutlarının hepsi; arayüz elle denenir.

## 8. Builder'a bırakılanlar
- Sayfa düzeninin ayrıntıları (docs/TASARIM.md token'ları ve mevcut bileşenlerle).
- Öneri cümlelerinin tam metni (yargısız, kısa, "sahipsen" dili).

## 9. Benim kararlarım (kullanıcı henüz onaylamadı)
- İş tanımı **yapılandırılmış form** ile girilir (ilan formunun aynısı), serbest metinden otomatik kriter çıkarma yok — yeni prompt gerektirmesin diye.
- İş arayan verisi ayrı tabloda; işveren tarafı hiç değişmez (yalnızca yetki daraltılır).
- Öneriler LLM'den değil, koddan şablonla.
- Günlük 10 değerlendirme sınırı.
- Çoklu işveren ayrı, sonraki proje.
