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
- **Kaynak:** delik (`modulbaglanti` hacmi = 351.35, %5 tol).
- **Kural:** Önce her parçanın kendi `modulbaglanti`-hacimli delikleri arasından
  **kulp (tutamak) çiftleri** ayıklanır (bkz. Kulp bölümü, ~192mm ±%5) — kulp
  delikleri modül bağlantısı SAYILMAZ. Kalan (kulp OLMAYAN) delikler TÜM
  parçalar arasında havuzlanır ve **TAM `MODUL_BAGLANTI_MESAFE` (18mm) ±%0.1**
  mesafede olan ikililer eşleştirilir (`detect_modul_baglanti_pairs`); her
  eşleşen çift = 1 modül-modül bağlantı aparatı.
  - **Neden kesin mesafe (eski yöntem yerine):** eski `pair_count` "en yakın
    komşu, 200mm eşik altında" mantığıyla greedy eşleştiriyordu — bu, gerçekte
    birbirine bağlı OLMAYAN ama tesadüfen en yakın düşen delikleri de (görsel
    teşhis + `diag_modul_mesafe.py` ölçümü: gerçek çiftler TAM 18.000mm, bir
    sonraki en yakın alakasız mesafe 101-136mm+) yanlışlıkla çift sayıyordu
    (bkz. `Algoritmaların_testi.md`). Gerçek modül-modül bağlantı delikleri
    arasında net bir mesafe imzası (tam 18mm) olduğu için kesin-mesafe
    eşleştirmesi bu hatayı ortadan kaldırır; eşi (tam 18mm'de) bulunamayan
    delik artık YANLIŞ bir komşuya eşlenmek yerine eşleşmemiş kalır.
- **Adet:** eşleşen **çift** sayısı (her çift = 1 aparat).

### Raf pimi
- **Kaynak:** delik (`rafpimi` = 234).
- **Kural:** her raf pimi = **3 delik** → adet = `rafpimi deliği sayısı / 3`.
- **Adet:** `counts["rafpimi"] // 3`.

### Linco Gövde / Linco Kapak / Linco Dübel / Minifix
- **Kaynak:** delik (`linco` = 9680).
- **Kural:** Linco Gövde = Linco Kapak = Minifix = `linco delik sayısı + Mert tamponu`
  (değişmez). **Linco Dübel** = `linco delik sayısı + Mert tamponu − 2 × uzun linco pimi`
  (bkz. Uzun Linco Pimi).
  - **Mert tedarik tamponu (2026-09-01):** linco adedine göre ≤20 → +1, 21–99 → +2,
    100+ → +3. Mert'in yazdığı sınıflar 21-49'u kapsamıyordu; Kerem kararıyla o aralık
    +2 kabul edildi, 100 sınırı +3'e sayıldı.
- **Adet:** Gövde/Kapak/Minifix = tamponlu linco; Dübel = tamponlu linco − 2×uzun pim.
  Gram (Minifix/Linco/Linco Kapak) da tamponlu sayıdan — adet ile tutarlı.
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
- **Kaynak:** geometri (`agacvidasi` deliklerinin oluşturduğu **dikdörtgen**).
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
  ray tespiti ayak tespitinden ÖNCE, aynı `agacvidasi` havuzu üzerinde çalışıyordu; bu
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
- **Kaynak:** doğrudan delik (3 tanıma yolu, aşağıda) + L bağlantı türetmesi.
- **Kural:** `(agacvidasi havuzundaki tüm delik sayısı, ayak dahil) + 4 × L bağlantı seti`.
- **Tanıma — 3 yol, hepsi aynı havuza girer (2026-09-01):** Ağaç vidası deliğinde
  üründen ürüne değişmeyen şey hacim değil **kesit alanıdır** (çap sabit 2.46 mm,
  derinlik değişken → hacim değişken):
  1. **Standart kör delik:** hacim `agacvidasi` = 14.57, %5 (eski yol, değişmedi).
  2. **Karşıya çıkan delik:** hacim `agacvidasiTam` = 83.2121, **%1** (18mm panel ×
     4.6229 mm² kesit). %1 katı: band [82.38, 84.04], iki ray bandının ([80.02, 81.63]
     / [84.07, 85.76]) tam arasına sıkışıyor — genişletme.
  3. **Değişken derinlikli kör delik:** hacim bandıyla yakalanamaz;
     `agac_vidasi_degisken_mi()` boolean boşluğunun bbox'undan tanır. Boşluk parçanın
     LOKAL ekseninde durduğundan iki yanal bbox kenarı ≈ çap (2.46 ±%5), üçüncü kenar =
     derinlik (1–40 mm), `hacim/derinlik` ≈ sabit kesit (`AGAC_VIDA_KESIT_MM2` = 4.627,
     ±%1.5). Ray-cast/yön tespiti gerekmez; derinlik < çap olan sığ deliklerde de çalışır
     (en-uzun-eksen varsayımı YOK). Sıra önemli: `is_ray_hole()`'dan SONRA denenir —
     bilinen ray hacim bandları önce ayıklanır; kaçan bir ray deliği bile kesit denetimine
     takılır (ray kesiti ≈ 4.718, bandın dışında).
  - **Dairesellik için RANSAC gerekmez:** yanal kenarların d×d çıkması + kesit denetimi
    birlikte A/d² ≈ 0.765 oranını (16-gen silindir) zorlar; kare kanal (1.0) ve
    eşkenar-dörtgen profil (0.5) elenir — doğrulandı (test 5).
  - **Ölçüm kanıtı (2026-09-01, `delik bulma.blend`, pipeline boolean'ı ile):** kör örnek
    13.83 mm³ / 2.988 mm → 4.629 mm²; karşıya çıkan 83.2121/18 → 4.6229; delik ağzı kapak
    yüzeyi 4.632. Teşhis sayaçları JSON `_ham` içinde: `_agacvida_tam`, `_agacvida_degisken`.
- **Not (DÜZELTİLDİ):** Ray delikleri ağaç vidasıyla AYNI delik DEĞİL — kendine özgü bir
  hacme sahipler (bkz. Ray Seti → `RAY_DELIK_HACIM`). Eskiden "ray delikleri de ahşap
  vidası boyutunda" varsayılıp ray'ler `agacvidasi` havuzunda aranıyordu; bu yüzden
  rastgele aralıklı GERÇEK ağaç vidaları tesadüfen bir ray desenine uyup yanlışlıkla
  ray sayılabiliyor, ağaç vidası sayımından haksız yere düşülebiliyordu (kanıt:
  `hacim_bul_raporu.txt`, Object_23 — ray'e ait delikler `[BİLİNMİYOR]`, hiçbir
  CATEGORIES hacmiyle eşleşmiyor). Artık ray tespiti ayrı bir havuzda çalıştığı için
  ağaç vidası havuzuna hiç dokunmaz.
- **Şimdiki sabit:** L bağlantı = 2 (sipariş başına) → +8.

### Ray Seti (çekmece rayı)
- **Kaynak:** geometri — `agacvidasi` DEĞİL, kendine özgü **`RAY_DELIK_HACIM`** (≈84.92,
  %2 tolerans) hacim bandındaki deliklerin ray deseninden tespiti.
- **Keşif (kritik düzeltme):** `hacim_bul.py` ile Object_23 taranınca ray'e ait 3 delik
  CATEGORIES'teki hiçbir hacimle eşleşmedi (`[BİLİNMİYOR]`, hacimler: 84.9189/84.9188/
  84.9175) — yani ray delikleri ağaç vidası (14.57) ile AYNI delik değilmiş. Eski
  algoritma ray'i `agacvidasi` havuzunda arıyordu; bu yüzden gerçek ağaç vidaları
  tesadüfen bir ray-aralık desenine uyup yanlış ray boyu buluyordu (ör. gerçek 55cm ray
  25cm bulunuyordu). Düzeltme: ray artık SADECE `RAY_DELIK_HACIM` bandındaki delikler
  arasından aranır; bu havuz `agacvidasi`/ayarlı ayak havuzuyla hiç kesişmez.
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
  delikler ağaç vidası sayımına EKLENMEZ (zaten agacvidasi hacminde değiller);
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
- **Kaynak:** adet türetme (askılık flanşından), boy geometri (karşılıklı flanş çifti).
- **Adet (değişmedi):** **her 2 askılık flanşı için 1 boru** → `askılık flanşı // 2`.
- **Boy kuralı (Kerem, 2026-09-29):** Her flanş, eşkenar üçgeninin **ağırlık merkezi**
  (dünya, mm) ve üstünde durduğu **panel** ile saklanır. İki flanş **birbirine bakar**
  (= 1 boru) ⇔ (1) farklı panellerde ve **aynı modülde** (modül üyeliği
  `module_segmenter.segment()` ataması; parça adı anlamı kullanılmaz, modülü
  bilinmeyen flanş eşleşmez), (2) iki panelin de normali (bbox ince ekseni) aynı eksen,
  **X ya da Y**, (3) merkezler diğer iki koordinatta `ASKILIK_HIZA_TOL_MM` = **15 mm**
  içinde, (4) paneller o eksende ayrık ve her flanş kendi panelinin öbür panele bakan
  (iç) yüzünde. Adaylar iç yüzler arası eksen boşluğu küçükten büyüğe greedy eşlenir,
  her flanş bir kez (duvar | bölme | duvar dizisinde doğru komşu).
  - **Boy** = iki panelin **iç yüzlerinin orta noktaları** arası **Öklid** mesafesi
    − `ASKILIK_KESINTI_MM` (**1 cm**), sonra **tam cm'ye yarım-yukarı** yuvarlanır
    (`math.floor(x + 0.5)`; Python `round` 64.5'i 64 yapar, kullanılmaz).
    Ör. 700 mm gövde, 18 mm duvarlar: 664 − 10 = 654 mm → **65 cm**.
  - Paneller farklı boy/derinlikteyse yüz merkezleri kayar ve Öklid mesafesi eksen
    boşluğundan uzun çıkar — kural bilerek böyle (Kerem); korpus raporu bunları listeler.
- **Tutarlılık:** eşleşen çift sayısı `flanş // 2`'den farklıysa (ya da eşsiz flanş
  kaldıysa) adet YİNE `flanş // 2`; JSON `askilik_eslesme.tutarli = false`, eşsiz
  flanşlar nedeniyle (`karsi_flans_yok` / `modul_yok`) listelenir, `[UYARI]` basılır.
  PDF'te boyu bulunamayan boru `?` olur.
- **JSON:** `askilik_borulari` = `[{uzunluk_cm, modul, eksen, ham_mm, eksen_boslugu_mm,
  flanslar, panolar}]` (büyükten küçüğe); `askilik_eslesme` = `{flans, eslesen_boru,
  beklenen_boru, tutarli, eslesmeyen_flanslar}`.
- **PDF + panel (Kerem, 2026-09-30):** her boy ayrı parça satırı: "Askılık Borusu 96 cm"
  → o boydaki adet; boyu bulunamayanlar "Askılık Borusu ? cm" satırında. Satır toplamı
  her zaman `adet["Askılık Borusu"]`. Özet tabloda satırlar (Ray Seti gibi) o sayfadaki
  siparişlerde geçen boylardan kurulur. Panel checklist anahtarı `boru:<boy>`
  (`boru:96`, `boru:?`). Eski (`askilik_borulari` içermeyen) JSON'lar düz
  "Askılık Borusu" satırında adetle kalır.
- **Bilinen FBX eksiği:** bazı siparişlerde flanş vida delikleri yalnız bir duvarda
  modellenmiş (ör. 9259-2: sol duvarda 2 flanş, sağ duvarda hiç delik yok; FBX'te 2
  boru mesh'i var). Bu siparişlerde hem adet (flanş // 2) eksik çıkar hem boy bulunamaz.
- Kod: `module_ayirici/askilik.py` (saf Python; `eslestir`, `boru_boyu_cm`,
  `boy_satirlari`), `parca_sayim.find_equilateral_flanges`. Testler:
  `python3 tests/test_askilik.py`, Blender `tests/test_askilik_blender.py`, korpus
  `tests/askilik_korpus.py` + `tests/askilik_korpus_karsilastir.py`.

### L Bağlantı Seti (duvar bağlantı braketi)
- **Kural (Kerem, 2026-09-29):** **2 × modül sütunu** (set + vidası + dübeli tek satırda).
  Sütun = önden bakınca aynı yatay aralıkta üst üste duran modüller (1–3 modül); her
  sütunun en üst modülüne bir sol + bir sağ braket.
- **Kaynak:** geometri, parça adı kullanılmaz (`Object_N` siparişlerde de çalışır).
  `module_ayirici/module_segmenter.py` modülleri (gövdeleri) 18 mm panel temaslarından
  ayırır; `module_ayirici/sutunlar.py` plan izdüşümü (x ve y) dar olanın en az
  `SUTUN_ORTUSME_ORANI` = 0.5'i kadar örtüşen modülleri aynı sütuna koyar. Korpusta
  (471 modül) modül çiftlerinin x örtüşme oranı ya ~0 (yan yana) ya tam 1.0 (üst üste).
- **Yedek:** ayırıcı yüklenemez/hata verir/hiç modül bulamazsa `L_BAGLANTI_ADET` = 2;
  JSON'da `moduller.kaynak = "yedek_sabit"` ve `moduller.hata` görünür.
- **JSON:** `moduller` = `{kaynak, braket, modul_sayisi, sutun_sayisi, sutunlar, kutular, ...}`.
- Bölünmüş siparişte (ör. 9360-1/-2) her FBX kendi sütunlarını sayar; toplam doğru çıkar.

### Allen (anahtar)
- **Kaynak:** türetme (ayarlı ayaktan).
- **Kural:** siparişte **≥ 1 ayarlı ayak varsa 1**, yoksa **0**.

### Tıpalar
- **Kaynak:** doğrudan delik (`tipa` = 1392.7481 mm³, %1 tolerans).
- **Kural:** `tipa` bandındaki (≈1392.75 mm³) delik sayısı. Eski kural ("her ayarlı ayak
  için 1 tıpa", ayarlı ayaktan türetme) kaldırıldı — tıpa artık kendi deliğinin bandından
  sayılıyor (karar 2026-09-01).
- **Adet:** `counts["tipa"]` (banda giren delik sayısı).
- **Renk:** artık uygulanıyor — bkz. aşağıdaki "Renk (Linco/Linco Kapak/Tıpa)" bölümü.

### Renk (Linco Gövde/Linco Kapak/Tıpa)
- **Kaynak:** `renkler/<sipariş>.json` (Mert'in FBX'le birlikte yüklediği, parça başına
  `user_data.renk` kodu içeren ayrı dosya — dosyadaki diğer alanlar kullanılmaz).
- **Kod:** `"0"` = Beyaz, `"1"` = Meşe, `"2"` = Gri.
- **Sipariş rengi:** siparişteki parçalar arasında **en çok geçen kod** (siparişin
  tamamı için TEK renk; parça bazında değil).
- **Kural (sipariş rengine göre parça rengi):**
  | Sipariş rengi | Linco (Gövde/Kapak) | Tıpa |
  |---|---|---|
  | Beyaz | Beyaz | Beyaz |
  | Meşe | Siyah | Kahverengi |
  | Gri | Siyah | Siyah |
- Minifix ve Linco Dübel görünür olmadığından renk etiketlenmez.
- `renkler/<sipariş>.json` henüz yüklenmemişse (veya tanınmayan kod içeriyorsa) JSON'da
  `"renk": null` kalır; PDF/panel bunu sessizce atlar (miktar hesabı etkilenmez).

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
- **Mert tedarik tamponu (2026-09-01):** bu toplam **× 1.25**, en yakın tam sayıya yuvarlanır
  (Python `round`, yarıda çift sayıya yuvarlar). Mevcut hesapta ek bir arttırma yoktu,
  override edilecek bir şey yok.
- Ayarlanabilir sabitler `parca_sayim.py` başında. Aralık (150 mm) orijinal 0.15 m
  kuralının mm karşılığı; gerçek sayımla kıyaslayıp ince ayar yapılabilir.

---

## Ertelenen parçalar (Eksikler.md — Mert / ileri faz)

| Parça | Öngörülen kural | Durum |
|-------|-----------------|-------|
| Askılık flanşı | eşkenar üçgen tespiti (yukarıda) | ✅ entegre |
| Askılık borusu | adet flanşı/2, boy karşılıklı flanş çiftinden (yukarıda) | ✅ entegre |
| Ray (Set) | ağaç vidası deliği deseni + kalibrasyon (yukarıda) | ✅ entegre |
| L Bağlantı Seti | 2 × modül sütunu, geometriden (yukarıda) | ✅ entegre |
| L Modül Uzun Linco Pimi | birbirine dayalı linco çifti (~43 mm, yukarıda) | ✅ entegre |
| **Ağaç vidası** | delik sayısı + 4×L (yukarıda) | ✅ entegre |
| Renkli parça (renk ayrımı) | Mert entegrasyonu | ⛔ ertelendi |
| Kontroller (Arkalıkları bantla, Çivili ayak çak, Makina modülü ayağı, Rayları monte et) | EVET/HAYIR bayrağı | ⛔ ertelendi |
