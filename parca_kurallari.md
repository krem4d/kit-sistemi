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
- **Kaynak:** geometri (`ahsapcivisi` deliklerinin oluşturduğu **dikdörtgen**).
- **Kural (GEOMETRİK tespit — sıralı-mesafe listesiyle KIYASLAMAZ):** Bir parçadaki
  ağaç vidası delikleri arasından kenarları **~32 × ~40 mm** (köşegen ~51.22 mm) olan
  bir **dikdörtgen** oluşturan **4'lü** = **1 ayarlı ayak**. Kullanılan teorem: *bir
  paralelkenarın köşegenleri birbirini ortalar; bu köşegenler EŞİT uzunluktaysa şekil
  bir dikdörtgendir.* Adımlar: (1) ~51.22 mm mesafedeki ikili delikleri ADAY köşegen
  say; (2) iki aday köşegen (4 AYRI delik) ORTAK orta noktayı paylaşıyorsa paralelkenar;
  (3) bitişik kenarların 32/40 mm tutup tutmadığını doğrula. Her ölçüm (2 kenar + 2
  köşegen) **bağıl %3** tolerans içinde olmalı (`AYAK_KENAR_TOL_PCT`). En iyi uyan
  dikdörtgen önce eşleşir (greedy); her delik en fazla bir ayakta kullanılır → bir
  parçada 8 vida = 2 ayak da yakalanır.
- **Neden "sıralı 6-mesafe" yöntemi terk edildi:** İlk sürüm, 4 noktanın 6 ikili
  mesafesini sıralayıp beklenen `[32,32,40,40,51.22,51.22]` listesiyle karşılaştırıyordu.
  Bu, hangi mesafenin KENAR hangisinin KÖŞEGEN olduğu bilgisini (topolojiyi) kaybeder →
  gerçek bir ayağı bile yanlış değerlendirebilir. Kanıt (9304-2/Object_18, gerçek FBX
  teşhisi): panelin 12 ağaç vidasından **3'ü** (0,1,2) tam 32.00/40.00/51.22 mm'ye
  uyuyordu ama 4. köşe **ray tespiti tarafından yanlışlıkla 'ray' sanılıp** havuzdan
  çalınmıştı (bkz. aşağıdaki sıralama düzeltmesi) → ayak SIFIR bulunuyordu. Yeni
  köşegen+orta-nokta yöntemi bu topolojiyi doğrudan kullanır, sıralamaya bağlı değildir.
- **Sıralama düzeltmesi (tarihsel — artık yapısal olarak imkansız):** Bir ara sürümde
  ray tespiti ayak tespitinden ÖNCE, aynı `ahsapcivisi` havuzu üzerinde çalışıyordu; bu
  yüzden ray'in geniş/bağlamsız greedy mesafe eşleşmesi gerçek bir ayak köşesini "ray"
  sanıp yutabiliyordu → o ayak 3 köşeye düşüp hiç yakalanamıyordu. Bunu, ayağı ray'den
  ÖNCE ayıklayarak (`extract_ayak_feet()`) geçici olarak düzeltmiştik. Artık ray tespiti
  TAMAMEN AYRI bir delik havuzunda (`RAY_DELIK_HACIM`, bkz. Ray Seti) çalıştığı için bu
  iki havuz hiç kesişmiyor — çalınma yapısal olarak imkansız, sıralama artık önemsiz.
- **Eski "TAM 4 vida" kuralının sorunu (ilk sürüm, artık geçerli değil):** "parçada
  TAM 4 ağaç vidası → 1 ayak" kuralı panele **dağılmış** 4 yapısal vidayı da ayak
  sayıyordu → *olması gerekenden fazla* (9262: **11** sayılıyordu, gerçekte ~1; dağınık
  4'lülerin köşegeni 500–850 mm). Dikdörtgen şekli bu yanlış pozitifleri eler.
- **Kalibrasyon:** `iki_obje_mesafe.py` ile ölçüldü (Object_55): kenarlar 32 mm ve 40 mm,
  köşegen 51.22 mm. Başka ayak modeli çıkarsa sabitler kolayca genişletilir.
- **Adet:** tüm parçalardaki ayak dikdörtgeni sayısı.
- **İzolasyon:** Ayak vidaları ağaç vidası havuzunda KALIR; askılık flanşı sayımı
  DEĞİŞMEZ (yalnızca ayak → dolayısıyla Allen ve Tıpa, ve dolaylı olarak ray/ağaç
  vidası — yalnızca önceden YANLIŞ ray sayılan durumlarda — güncellenir).
- **Sabitler `parca_sayim.py`:** `AYAK_KENAR_A_MM=32`, `AYAK_KENAR_B_MM=40`,
  `AYAK_KENAR_TOL_PCT=0.03`; fonksiyonlar `extract_ayak_feet()` (asıl mantık, ray'den
  önce çağrılır), `count_ayak_feet()` (adet-only kısayol, teşhis/test için).

### Ağaç vidası (kit adedi)
- **Kaynak:** doğrudan delik (`ahsapcivisi` = 14.57, %5) + L bağlantı türetmesi.
- **Kural:** `(ahsapcivisi havuzundaki tüm delik sayısı, ayak dahil) + 4 × L bağlantı seti`.
- **Not (DÜZELTİLDİ):** Ray delikleri ahşap vidasıyla AYNI delik DEĞİL — kendine özgü bir
  hacme sahipler (bkz. Ray Seti → `RAY_DELIK_HACIM`). Eskiden "ray delikleri de ahşap
  vidası boyutunda" varsayılıp ray'ler `ahsapcivisi` havuzunda aranıyordu; bu yüzden
  rastgele aralıklı GERÇEK ağaç vidaları tesadüfen bir ray desenine uyup yanlışlıkla
  ray sayılabiliyor, ağaç vidası sayımından haksız yere düşülebiliyordu (kanıt:
  `hacim_bul_raporu.txt`, Object_23 — ray'e ait delikler `[BİLİNMİYOR]`, hiçbir
  CATEGORIES hacmiyle eşleşmiyor). Artık ray tespiti ayrı bir havuzda çalıştığı için
  ağaç vidası havuzuna hiç dokunmaz.
- **Şimdiki sabit:** L bağlantı = 2 (sipariş başına) → +8.

### Ray Seti (çekmece rayı)
- **Kaynak:** geometri — `ahsapcivisi` DEĞİL, kendine özgü **`RAY_DELIK_HACIM`** (≈84.92,
  %2 tolerans) hacim bandındaki deliklerin ray deseninden tespiti.
- **Keşif (kritik düzeltme):** `hacim_bul.py` ile Object_23 taranınca ray'e ait 3 delik
  CATEGORIES'teki hiçbir hacimle eşleşmedi (`[BİLİNMİYOR]`, hacimler: 84.9189/84.9188/
  84.9175) — yani ray delikleri ahşap vidası (14.57) ile AYNI delik değilmiş. Eski
  algoritma ray'i `ahsapcivisi` havuzunda arıyordu; bu yüzden gerçek ağaç vidaları
  tesadüfen bir ray-aralık desenine uyup yanlış ray boyu buluyordu (ör. gerçek 55cm ray
  25cm bulunuyordu). Düzeltme: ray artık SADECE `RAY_DELIK_HACIM` bandındaki delikler
  arasından aranır; bu havuz `ahsapcivisi`/ayarlı ayak havuzuyla hiç kesişmez.
- **Kalibrasyon:** kulp deliği modelde `0.192` birim ↔ gerçek `192 mm` → **1 birim = 1000 mm**
  (`RAY_SCALE_MM = 1000`).
- **Örüntünün kaynağı (KULLANICI ÖLÇÜMÜ — kesin):** Her ray boyunun delikleri,
  rayla aynı doğrultudaki sabit bir REFERANS NOKTASINA göre ölçüldü. Konumlar
  (`RAY_HOLE_POSITIONS`, mm): 55cm[63,212,434], 50cm[64,214,375], 45cm[64,216,318],
  40cm[64,193,275], 35cm[64,141,224], 30cm[63,172], 25cm[43,231]. Ardışık farklar =
  o boyun **imzası** (`RAY_GAPS`, koddan otomatik türetilir): 55cm[149,222],
  50cm[150,161], 45cm[152,102], 40cm[129,82], 35cm[77,83], 30cm[109], 25cm[188].
  **DİKKAT:** boy ile aralık DOĞRU ORANTILI DEĞİL, her imza unique. (Bir ara ben
  [152,102]'yi yanlışlıkla 55cm sandım — o aslında **45cm**; 55cm = [149,222].)
- **Kural:** Bir parçadaki `RAY_DELIK_HACIM` bandına giren delikler arasından
  **doğrusal** olup ardışık aralıkları bir boyun imzasına (±`RAY_TOL_MM`=8 mm) uyanlar
  = 1 ray. Önce 3-delikli boylar (55–35cm), sonra kalan deliklerde 2-delikli boylar
  (30/25cm), greedy. Eşleştirme `_ray_signature_match()` ile: tüm aralıkları tolerans
  içinde olan boylar arasından **en düşük toplam sapmalı** boy seçilir (ilk-uyan değil;
  55/50/45'in ilk aralığı 149/150/152 çok yakın olduğundan bu ayrımı sağlamlaştırır).
- **Adet:** aynı boydaki sol+sağ 2 ray = 1 set → **her boy için set = o boydaki ray // 2**.
  JSON'da `ray_setleri` (ör. `{"55cm": 2, "30cm": 1}`). PDF'te her boy **ayrı satır**
  ("Ray Seti 55cm", "Ray Seti 30cm"…); hiç ray yoksa tek "Ray Seti" = 0 satırı.
- **İzolasyon:** `RAY_DELIK_HACIM` bandına giren ama hiçbir ray desenine uymayan
  delikler ağaç vidası sayımına EKLENMEZ (zaten ahsapcivisi hacminde değiller);
  ağaç vidası havuzu ray tespitinden bağımsızdır.
- Sabitler `parca_sayim.py`: `RAY_SCALE_MM`, `RAY_TOL_MM`, `RAY_COLINEAR_TOL_MM`,
  `RAY_HOLE_POSITIONS`, `RAY_GAPS` (konumlardan türetilir).

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
  paneli (ölçüm: arkalık 5 mm, gövde 18 mm).
- **İkiye bölünmüş arkalıkların birleştirilmesi:** paketleme için ikiye
  kesilip bantlanan/katlanan arkalıklar FBX'te aynı arkalığa ait İKİ AYRI mesh
  parçası (aynı hacimde) olarak görünür. Çivi sayımından ÖNCE, arkalık
  adayları arasında HEM hacmi `ARKALIK_ESLESME_TOL` (%3) içinde eşleşen HEM DE
  tam bir yüzeyde temas halinde olan çiftler bulunur ve `bpy.ops.object.join`
  ile TEK parçada birleştirilir (`pair_split_arkalik`); çivi sayımı bu
  birleşmiş/tekil nihai parça listesi üzerinden yapılır. Eşleşmeyen adaylar
  zaten tek parça olduğu için oldukları gibi kalır.
  - **Neden sadece hacim yetmiyor:** müşteri aynı boyda 2 AYRI modül sipariş
    edebilir — bu da aynı hacimde 2 arkalık demektir ama bunlar GERÇEKTEN ayrı
    paneldir, birleştirilmemeli. Ek şart: adaylar bir eksende SIFIR boşlukla
    bitişik VE diğer iki eksende TAM örtüşen bir yüzeye sahip olmalı
    (`_tam_yuzey_temasi`, tolerans `ARKALIK_TEMAS_TOL_MM` = 2 mm) — gerçek
    ikiye-kesilmiş yarılar kesim hattı boyunca böyle tam yapışık durur.
- Her (birleşmiş veya tekil) arkalık panelinin çevresine `CIVI_ARALIK_MM`
  (150 mm) aralıkla çivi: `2·ceil(W/150) + 2·ceil(H/150)`.
- **Adet:** tüm arkalık panellerinin (birleştirmeden sonraki) çivi toplamı.
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
