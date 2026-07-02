# Parça Türetme Kuralları — Adaptx Otonom Kit

Her kit parçasının **adedinin nasıl hesaplandığı**. Sayım motoru (Faz 1+) bu kuralları
uygular. Kaynak türleri:
- **delik** → tahtadaki oyuk hacminden sayılır (bkz. `hacimler.md`).
- **dummy** → parçanın kendi hacminden sayılır.
- **türetme** → başka bir parçanın adedinden hesaplanır.
- **geometri** → parça konumlarından/geometriden hesaplanır.

---

## Odak parçalar (şu an çalışılan)

### Menteşe tabanı
- **Kaynak:** delik (`menteseTabani`, hacim ölçülecek).
- **Adet:** tespit edilen menteşe tabanı deliği sayısı (tüm parçalar toplamı).

### Frenli menteşe
- **Kaynak:** türetme (menteşe tabanından).
- **Kural:** *En az 1 menteşe tabanı bulunan her parça* için **1** frenli menteşe.
  Bir parçada birden çok menteşe tabanı olsa bile o parçadan yalnızca 1 frenli çıkar.
- **Adet:** `menteşe tabanı içeren parça sayısı`.

### Frensiz menteşe
- **Kaynak:** türetme.
- **Adet:** `toplam menteşe tabanı − frenli menteşe`.
- **Doğrulama:** `frenli + frensiz == toplam menteşe tabanı`.

### Modülleri birbirine bağlama aparatı
- **Kaynak:** delik (`modulbaglanti` = 351.35), A–B çift eşleştirmesi (mevcut).
- **Adet:** eşleşen **A–B çift** sayısı (her çift = 1 aparat).

### Raf pimi
- **Kaynak:** delik (`rafpimi` = 234).
- **Kural:** her raf pimi = **3 delik** → adet = `rafpimi deliği sayısı / 3`.
- **Adet:** `counts["rafpimi"] // 3`.

### Linco Gövde / Linco Kapak / Linco Dübel / Minifix
- **Kaynak:** delik (`linco` = 9680).
- **Kural:** Linco Gövde = Linco Kapak = Minifix = `linco delik sayısı` (değişmez).
  **Linco Dübel** = `linco delik sayısı − 2 × uzun linco pimi` (bkz. Uzun Linco Pimi).
- **Adet:** Gövde/Kapak/Minifix = linco delik sayısı; Dübel = linco − 2×uzun pim.
- Not: `pim` (936, Linco Dübel deliği) çapraz kontrol için kullanılabilir.
- Not: Renk ayrımı (BEYAZ/GRİ) ertelendi (Eksikler.md — Mert entegrasyonu).

### Uzun Linco Pimi (L Modül)
- **Kaynak:** geometri (iki AYRI parçadaki birbirine dayalı + yönü hizalı `linco` delikleri).
- **Mesafe kuralı:** Farklı iki modülün birbirine dayanan (abutting) linco gövde
  delikleri ~**43 mm** (`LONG_LINCO_MESAFE=0.043` birim, ±%25 → [32, 54] mm) mesafededir.
- **Yön + eksen kuralı (görsel teşhiste bulunan düzeltmeler):** Tek başına mesafe (hatta
  işaretsiz yön) yetersizdi — iki gerçek çiftin ARASINA giren alakasız bağlar ve **aynı
  yöne bakan** çiftler de sayıldı (`linco_uzun_pim_teshis.py` görsel doğrulaması). Bu
  yüzden her linco deliğinin **İŞARETLİ delme yönü** kullanılır: delik boşluğunun
  merkezinden 6 eksende `ray_cast`, panele çarpmayan yön = deliğin açıldığı yön
  (`hole_signed_direction()`). `conn = b − a`, `conn_hat` birim iken bir çift geçerli
  olması için (mesafeye ek):
  1. **A deliği B'ye bakar:** `dir_A · conn_hat >= LONG_LINCO_ALIGN_MIN` (0.9)
  2. **B deliği A'ya bakar:** `dir_B · conn_hat <= −LONG_LINCO_ALIGN_MIN`
  3. **Bağlantı doğrusu eksene paralel (90° katı):** `max|conn_hat bileşeni| >=
     LONG_LINCO_AXIS_MIN` (0.985 ≈ cos 10°) — diagonal/çapraz bağları eler.
- Her çift (mesafe **ve** 1–2–3 uyan) = **1 uzun linco pimi**. En yakın+geçerli çift önce
  eşleşir (greedy), her delik en fazla bir kez kullanılır; yalnızca **farklı parçalar**
  arası çiftler değerlendirilir.
- **Dübel etkisi:** Bu iki deliğe normal linco dübeli yerine tek uzun pim konur →
  **her uzun pim, Linco Dübel sayımından 2 düşer** (Gövde/Kapak/Minifix dokunulmaz).
- **Adet:** tespit edilen geçerli linco çifti sayısı. JSON'da `_uzun_linco`.
- **Ölçüm/teşhis araçları:**
  - `linco_mesafe_bul.py` (2 parça seçip parçalar-arası linco mesafeleri):
    abutting çift ~0.043 birim, çapraz komşu ~0.068 → mesafe eşiğinin kaynağı.
  - `linco_uzun_pim_teshis.py` (tüm sahne, geniş pencere 15–90mm): her adayın orta
    noktasına isimli Empty koyar; etiketler `MATCH` / `near` (mesafe) / `axis_bad`
    (eksene hizasız) / `face_bad` (karşılıklı değil) — viewport'ta gözle doğrulama içindir.
- Sabitler `parca_sayim.py`: `LONG_LINCO_MESAFE`, `LONG_LINCO_TOL`, `LONG_LINCO_ALIGN_MIN`,
  `LONG_LINCO_AXIS_MIN`.

### Ayarlı ayak
- **Kaynak:** delik grubu (`ahsapcivisi`).
- **Kural (orijinal delikbulma.py ile birebir):** Bir parçada **TAM 4** ağaç vidası deliği
  varsa → **1** ayarlı ayak (`part_ahsap == 4`). 4 değilse 0.
- **Adet:** koşulu sağlayan parça sayısı.
- **Hacim:** `ahsapcivisi = 19.48`, `TOLERANCE = %5` (güncel delikbulma.py). 8990'da doğrulandı.

### Ağaç vidası (kit adedi)
- **Kaynak:** doğrudan delik (`ahsapcivisi` = 14.57, %5) + L bağlantı türetmesi.
- **Kural:** `(ray dışı ağaç vidası deliği sayısı) + 4 × L bağlantı seti`.
- **Not:** Ray delikleri de ahşap vidası boyutundadır; ray deseni tespit edilip bu
  delikler ağaç vidası sayımından **çıkarılır** (bkz. Ray Seti).
- **Şimdiki sabit:** L bağlantı = 2 (sipariş başına) → +8.

### Ray Seti (çekmece rayı)
- **Kaynak:** geometri (`ahsapcivisi` deliklerinin ray deseninden tespiti).
- **Kalibrasyon:** kulp deliği modelde `0.192` birim ↔ gerçek `192 mm` → **1 birim = 1000 mm**
  (`RAY_SCALE_MM = 1000`).
- **Kural:** Bir parçadaki ahşap vidası delikleri arasından **doğrusal** olup ardışık
  aralıkları bir ray boyu desenine (aşağıdaki tablo, ±`RAY_TOL_MM`=8 mm) uyanlar = 1 ray.
  Önce 3-delikli raylar, sonra kalan deliklerde 2-delikli raylar (greedy).
- **Ray boyu → delik aralıkları (mm):** 55cm[149,222], 50cm[150,161], 45cm[152,102],
  40cm[129,82], 35cm[77,83], 30cm[109], 25cm[188].
- **Adet:** aynı boydaki sol+sağ 2 ray = 1 set → **her boy için set = o boydaki ray // 2**.
  JSON'da `ray_setleri` (ör. `{"55cm": 2, "30cm": 1}`). PDF'te her boy **ayrı satır**
  ("Ray Seti 55cm", "Ray Seti 30cm"…); hiç ray yoksa tek "Ray Seti" = 0 satırı.
- Tespit edilen raylar bu delikleri ağaç vidası havuzundan çıkarır.
- Sabitler `parca_sayim.py`: `RAY_SCALE_MM`, `RAY_TOL_MM`, `RAY_COLINEAR_TOL_MM`, `RAY_GAPS`.

### Askılık flanşı
- **Kaynak:** geometri (ağaç vidası deliklerinden).
- **Kural:** Bir parçadaki ağaç vidası deliklerinin 3'lü kombinasyonlarından, kenarları
  **%2 toleransla eşit** ve açıları **59–61°** (eşkenar, ~60°) olan üçgen = **1 askılık
  flanşı**. Her delik en fazla bir üçgende kullanılır (greedy).
- **Adet:** tüm parçalardaki eşkenar üçgen sayısı toplamı.
- Sabitler `parca_sayim.py`: `FLANS_KENAR_TOL=0.02`, `FLANS_ACI_LO/HI=59/61`.

### Askılık borusu
- **Kaynak:** türetme (askılık flanşından).
- **Kural:** **her 2 askılık flanşı için 1 boru** → `askılık flanşı // 2`.

### L Bağlantı Seti
- **Kural (şimdilik):** her sipariş için **sabit 2** (set + vidası + dübeli tek satırda).
- İleride modelden tespit edilebilir (Mert ile).

### Allen (anahtar)
- **Kaynak:** türetme (ayarlı ayaktan).
- **Kural:** siparişte **≥ 1 ayarlı ayak varsa 1**, yoksa **0**.

### Tıpalar
- **Kaynak:** türetme (ayarlı ayaktan).
- **Kural:** **her ayarlı ayak için 1 tıpa**.
- **Adet:** `ayarlı ayak sayısı`.
- Not: Renk ayrımı (Beyaz/Siyah/Kahverengi) ertelendi (Eksikler.md — Mert entegrasyonu);
  şimdilik toplam tıpa adedi hesaplanır.

### Kulp
- **Kaynak:** delik çifti (`modulbaglanti` hacmi = 351.35, %5 tol).
- **Kural:** Bir parçadaki modulbaglanti-hacimli delikler arasında **~192 mm ± %5**
  mesafede olan çiftler = kulp. Her çift = 1 kulp. Eşleşmeyen delikler gerçek
  modül bağlantı havuzuna geçer.
- **Sabitler:** `KULP_DELIK_MESAFE=0.192 m`, `KULP_DELIK_TOL=0.05`.
- **Adet:** parça-başına tespit edilen kulp çifti toplamı.

### Kulp vidası
- **Kaynak:** türetme (kulptan).
- **Kural:** **her kulp için 2 kulp vidası**.
- **Adet:** `2 × kulp`.

### Arkalık çivisi
- **Kaynak:** kalınlık-tabanlı arkalık tespiti (delik değil).
- **Kural:** En kısa kenarı `ARKALIK_MAX_KALINLIK` (8 mm) altında olan her parça = arkalık
  paneli (ölçüm: arkalık 5 mm, gövde 18 mm). Her arkalık panelinin çevresine
  `CIVI_ARALIK_MM` (150 mm) aralıkla çivi: `2·ceil(W/150) + 2·ceil(H/150)`.
- **Adet:** tüm arkalık panellerinin çivi toplamı (8974'te 7 panel → 114).
- Ayarlanabilir sabitler `parca_sayim.py` başında. Aralık (150 mm) orijinal 0.15 m
  kuralının mm karşılığı; gerçek sayımla kıyaslayıp ince ayar yapılabilir.

---

## Ertelenen parçalar (Eksikler.md — Mert / ileri faz)

| Parça | Öngörülen kural | Durum |
|-------|-----------------|-------|
| Askılık flanşı | eşkenar üçgen tespiti (yukarıda) | ✅ entegre |
| Askılık borusu | flanşı/2 (yukarıda) | ✅ entegre |
| Ray (Set) | ahşap vidası deliği deseni + kalibrasyon (yukarıda) | ✅ entegre |
| L Bağlantı Seti | şimdilik sabit **2** (yukarıda) | 🟡 geçici |
| L Modül Uzun Linco Pimi | birbirine dayalı linco çifti (~43 mm, yukarıda) | ✅ entegre |
| **Ağaç vidası** | delik sayısı + 4×L (yukarıda) | ✅ entegre |
| Renkli parça (renk ayrımı) | Mert entegrasyonu | ⛔ ertelendi |
| Kontroller (Arkalıkları bantla, Çivili ayak çak, Makina modülü ayağı, Rayları monte et) | EVET/HAYIR bayrağı | ⛔ ertelendi |
