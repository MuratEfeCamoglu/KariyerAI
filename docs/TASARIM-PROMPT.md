# KariyerAI — Görsel Tasarım Promptu

Aşağıdaki promptu Claude Design, Figma AI, v0, Lovable, Galileo vb. bir UI tasarım aracına olduğu gibi yapıştır. Ekranlar ve kurallar ISKELET.md §2.1 (F1–F12) ve §3.5 ile uyumludur.

---

```
"KariyerAI" adlı, Türkçe arayüzlü, masaüstü öncelikli (1440 px tasarım genişliği, 768 px'te bozulmayan) bir B2B SaaS web uygulaması için yüksek kaliteli UI tasarımı üret. Ürün, şirket içi İK uzmanlarının yüklenen CV'leri yapay zekâ ile ilan kriterlerine göre puanlayıp sıraladığı bir araçtır. Son kararı her zaman insan verir; tasarım AI'ı "karar verici" değil "kanıt sunan asistan" olarak konumlamalı.

MARKA VE TON
- Kişilik: güvenilir, sakin, profesyonel, şeffaf. Abartılı "AI büyüsü" efektleri (parıltı, neon, mor gradyan) YOK.
- Renkler: birincil derin lacivert-petrol (#0F3D56 civarı), ikincil sıcak turkuaz vurgu (#14B8A6 civarı), nötr arka plan #F7F8FA, kartlar beyaz, metin #1F2937.
- Puan bantları (yalnızca bunlar): ≥75 "Yüksek uyum" yeşil (#16A34A), 50–74 "Orta uyum" amber (#D97706), <50 "Düşük uyum" nötr gri (#6B7280). Kırmızı ASLA puan için kullanılmaz; "uygun değil", "başarısız" gibi yargı ifadeleri yok.
- Tipografi: Inter (Türkçe karakterleri ı, ş, ğ, İ tam destekli); başlıklar 600, gövde 400, 14–16 px gövde; sayılar tabular-nums.
- 8 px ızgara, 8–12 px köşe yuvarlaklığı, ince 1 px kenarlıklar, çok hafif gölgeler. WCAG 2.1 AA kontrast (metin ≥ 4.5:1).
- İkonlar: Lucide tarzı ince çizgi ikonlar.

GENEL YERLEŞİM
- Solda daraltılabilir dikey menü: logo "KariyerAI", İlanlar, (yalnızca admin) Kullanıcılar, Denetim Kaydı; altta kullanıcı adı + rol rozeti + çıkış.
- Üstte sayfa başlığı + breadcrumb + sağda birincil eylem düğmesi.

TASARLANACAK EKRANLAR
1. Giriş: ortalanmış kart; e-posta, şifre, "Giriş yap"; hata durumu "E-posta veya şifre hatalı". Sol yarıda sade bir illüstrasyon/marka alanı.
2. İlanlar listesi (ana sayfa): tablo/kart — ilan başlığı, departman, durum (Açık/Kapalı rozet), başvuru sayısı, en yüksek puan, ortalama puan, oluşturulma tarihi; arama + durum filtresi; "Yeni ilan" düğmesi. Boş durum: "Henüz ilan yok — ilk ilanını oluştur" illüstrasyonlu.
3. İlan oluştur/düzenle formu: başlık, departman, açıklama (textarea), zorunlu beceriler ve tercih edilen beceriler (etiket/chip girişi), minimum deneyim yılı (sayı), minimum eğitim (açılır liste: Yok, Lise, Ön lisans, Lisans, Yüksek lisans, Doktora), diller (dil + A1–C2 seviye satırları, "Dil ekle"). Sağda yapışkan bilgi kutusu: puan ağırlıkları "Zorunlu beceriler 40 · Deneyim 25 · Eğitim 15 · Diller 10 · Tercih edilen 10". Alan bazlı hata mesajları.
4. İlan detayı + aday sıralaması (EN ÖNEMLİ EKRAN):
   - Üstte ilan özeti (kriter chip'leri) ve "CV yükle" sürükle-bırak alanı ("PDF veya DOCX, en fazla 20 dosya, dosya başına 5 MB").
   - Yükleme sonrası dosya bazlı ilerleme listesi (yüklendi / reddedildi + neden).
   - Sıralı aday tablosu: sıra no, aday adı, büyük dairesel puan rozeti (0–100, bant renginde), bant etiketi, 5 kalemin mini yatay çubukları, son pozisyon, toplam deneyim yılı, başvuru durumu (renkli rozet), yüklenme zamanı.
   - Satır durumları: "İşleniyor" (iskelet/spinner rozet), "Başarısız" (gri uyarı ikonu + neden + "Yeniden dene" düğmesi).
   - Filtreler: minimum puan kaydırıcısı, durum çoklu seçim, işlem durumu; sayfalama (50/sayfa).
5. Başvuru (aday) detayı:
   - Üst şerit: aday adı, iletişim, büyük puan göstergesi ve bant, durum değiştirme açılır menüsü (Yeni, İnceleniyor, Kısa liste, Mülakat, İşe alındı, Reddedildi), "Orijinal CV'yi indir".
   - Sabit, dikkat çekici ama sakin bilgi bandı: "Bu puan bir öneridir; karar İK uzmanına aittir."
   - Puan kırılımı kartı: her kalem için ağırlık/elde edilen puan çubuğu; beceri ve dil kalemlerinde her kriter satırı ✓/✗ + CV'den tırnak içinde, vurgulu kanıt alıntısı; kanıtı doğrulanamayanlar için "Kanıt doğrulanamadı" soluk etiketi. Deneyim ve eğitim kalemlerinde hesaplamaya giren pozisyon/okul kayıtları.
   - AI özeti kartı (2–4 cümle, küçük "AI tarafından üretildi · model · prompt v1" künyesi).
   - Ayrıştırılmış CV: deneyim zaman çizelgesi, eğitim, beceri chip'leri, diller.
   - Sağ sütun: notlar (ekle/sil, yazar + zaman) ve durum geçmişi zaman çizelgesi.
6. Kullanıcılar (admin): tablo (ad, e-posta, rol, aktif/pasif anahtarı), "Kullanıcı ekle" modalı.
7. Denetim kaydı (admin): zaman, kullanıcı, eylem, varlık; eylem türüne göre filtre. Kişisel veri gösterilmez, yalnızca id'ler.
8. Silme onayı modalı (admin, KVKK): "Bu adayın tüm verileri ve CV dosyası kalıcı olarak silinecek. Bu işlem geri alınamaz." + aday id'sini yazarak onaylama.

BİLEŞEN KÜTÜPHANESİ (ayrı bir sayfada göster)
Düğmeler (birincil/ikincil/hayalet/tehlike), girişler, chip/etiket girişi, rozetler (puan bantları, başvuru durumları, işlem durumları), puan halkası (3 boyut), kalem çubuğu, tablo satırı durumları, toast'lar, boş durumlar, iskelet yükleyiciler, modal.

ÇIKTI
Her ekranın açık tema masaüstü görünümü + İlan detayı ve Aday detayı için 768 px görünümü; gerçekçi ama uydurma Türkçe aday adları ve yazılım/pazarlama ilanı içerikleri kullan. Tasarım token'larını (renk, tipografi, aralık, köşe) ayrı bir tablo olarak ver ki Tailwind 4 `@theme` değişkenlerine aktarılabilsin.
```
