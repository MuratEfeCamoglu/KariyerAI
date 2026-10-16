# Aday Aydınlatma Metni — TASLAK

> **Bu bir taslaktır; hukuki görüş değildir.** Uygulamanın teknik olarak ne yaptığını doğru
> anlatmak için hazırlanmıştır. Şirketin hukuk birimi veya KVKK danışmanı tarafından gözden
> geçirilip onaylanmadan adaylara sunulmamalıdır (ISKELET R3, V4).
> Köşeli parantezli alanlar şirkete göre doldurulmalıdır. Kanun ve yönetmelik atıfları
> hukuk birimince güncel mevzuata göre doğrulanmalıdır.

---

## [ŞİRKET UNVANI] İşe Alım Süreci Kişisel Verilerin İşlenmesine İlişkin Aydınlatma Metni

6698 sayılı Kişisel Verilerin Korunması Kanunu ("KVKK") uyarınca, veri sorumlusu sıfatıyla
[ŞİRKET UNVANI] ("Şirket") olarak, iş başvurunuz kapsamında kişisel verilerinizi aşağıda
açıklanan şekilde işlemekteyiz.

### 1. İşlenen kişisel veriler

- **Kimlik ve iletişim:** Özgeçmişinizde yer alan ad soyad, e-posta adresi, telefon numarası.
- **Mesleki bilgiler:** Eğitim, iş deneyimi, beceriler, sertifikalar, yabancı dil bilgisi.
- **Başvuru süreci bilgileri:** Başvurunuzun durumu, İK uzmanlarının değerlendirme notları,
  sistemin ürettiği uyum puanı ve gerekçesi.

Yaş, doğum tarihi, cinsiyet, medeni hal, din, uyruk, sağlık bilgisi ve fotoğraf gibi bilgiler
değerlendirme sistemi tarafından **çıkarılmaz, saklanmaz ve puanlamada kullanılmaz**.
Özgeçmişinizde bu bilgilere yer vermemenizi öneririz.

### 2. İşleme amaçları

Başvurunuzun ilanın gerekliliklerine göre değerlendirilmesi, adaylar arasında karşılaştırma
yapılması, işe alım sürecinin yürütülmesi ve kayıt altına alınması.

### 3. Hukuki sebepler

[HUKUK BİRİMİ BELİRLEYECEK — örneğin: bir sözleşmenin kurulmasıyla doğrudan ilgili olması
(KVKK m. 5/2-c), Şirketin meşru menfaati (KVKK m. 5/2-f).]

### 4. Yapay zekâ destekli değerlendirme

- Özgeçmişiniz, bir yapay zekâ hizmeti yardımıyla yapılandırılır ve ilan kriterleriyle
  karşılaştırılır. Sistem her kriter için özgeçmişinizden **birebir alıntı** ile gerekçe
  gösterir; alıntı doğrulanamazsa kriter karşılanmamış sayılır.
- Uyum puanı yapay zekâ tarafından değil, şeffaf ve sabit bir formülle hesaplanır.
- Puanlama için yapay zekâya gönderilen metinden adınız, e-posta adresiniz, telefon numaranız,
  web bağlantılarınız, doğum tarihi bilgisi ve adres satırları **çıkarılır**.
- **Sonuç yalnızca bir öneridir.** Başvurunuz hakkındaki her karar bir İK uzmanı tarafından
  verilir; sistem hiçbir başvuruyu otomatik olarak elemez veya reddetmez.
- KVKK m. 11/1-g uyarınca, münhasıran otomatik sistemlerle analiz edilmesi nedeniyle aleyhinize
  bir sonuç doğduğunu düşünürseniz buna itiraz edebilirsiniz.

### 5. Aktarım

- Özgeçmiş metniniz, yapay zekâ analizi için hizmet sağlayıcımız [SAĞLAYICI ADI, ÜLKE — kurulumda
  kullanılan: Groq Inc., ABD ve/veya Google LLC (Gemini API), ABD] tarafından işlenmektedir. Bu aktarım **yurt dışına** yapılmaktadır.
  [HUKUK BİRİMİ BELİRLEYECEK — KVKK m. 9 kapsamındaki aktarım dayanağı (ör. standart sözleşme
  ve Kurul'a bildirimi) ile sağlayıcının veri saklama ve model eğitimi koşulları.]
- Verileriniz bunun dışında yalnızca işe alım sürecinde görevli Şirket çalışanlarıyla
  paylaşılır.

### 6. Saklama süresi ve silme

Verileriniz [SÜRE — ör. başvuru sonuçlandıktan sonra X ay] süreyle saklanır. Talebiniz üzerine
özgeçmiş dosyanız, başvuru kayıtlarınız ve değerlendirme notları kalıcı olarak silinir; sistem
kayıtlarında yalnızca kişisel veri içermeyen "aday kaydı silindi" bilgisi tutulur.

### 7. Haklarınız (KVKK m. 11)

Kişisel verilerinizin işlenip işlenmediğini öğrenme, işlenmişse bilgi talep etme, amacına uygun
kullanılıp kullanılmadığını öğrenme, aktarıldığı üçüncü kişileri bilme, eksik veya yanlış
işlenmişse düzeltilmesini, silinmesini veya yok edilmesini isteme, otomatik analiz sonucu
aleyhinize bir sonuca itiraz etme ve zarara uğramanız hâlinde giderilmesini talep etme
haklarına sahipsiniz.

Başvurularınızı [BAŞVURU KANALI — ör. kvkk@sirket.com veya posta adresi] üzerinden
iletebilirsiniz.

---

### Teknik ekip için: bu metindeki taahhütlerin uygulamadaki karşılığı

| Metindeki ifade | Uygulamadaki karşılığı |
|---|---|
| Korunan özellikler çıkarılmaz | `schemas/parsed_cv.py` (şemada alan yok, fazla alanlar atılır) · `parse_v1.md` |
| Puanlamada kişisel bilgiler çıkarılır | `services/anonymizer.py` (F6d, birim testli) |
| Birebir alıntı, doğrulanamazsa karşılanmamış | `services/scoring.py` `verify_evidence` (F6c) |
| Puan formülle hesaplanır | `services/scoring.py` (§3.5) |
| Otomatik eleme yok | Durum yalnızca `PATCH /applications/{id}/status` ile değişir (F9, testli) |
| Talep üzerine kalıcı silme | `DELETE /candidates/{id}` (F11, dosyanın silindiği testli) |
| Sistem kayıtlarında kişisel veri yok | `services/audit.py` + audit payload testleri (F12) |
| Saklama süresi | **Uygulamada yok** — otomatik saklama süresi "Sonraki Sürümler"de (ISKELET §2.2); şimdilik elle silme |
