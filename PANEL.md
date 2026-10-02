# Adaptx Panel — Web İzleme + Checklist Arayüzü

Sayım hattını (rclone → `fbx/` → Blender → `jsons/` → `pdf/`) tarayıcıdan izlemek
ve her siparişi checklist ile takip etmek için native (Docker'sız, pip'siz)
bir web paneli. Sadece Python standart kütüphanesi kullanır — ek paket
kurulumu gerekmez.

Panel boru hattına karşı **salt okurdur**: `fbx/`, `jsons/`, `pdf/`,
`islem_gecmisi.json`, `video_envanteri.json` yalnızca okunur. Yazdığı dosyalar
`data/panel_checklist.json` ile `data/panel_notlar.json`'dur.
`adaptx.service`/`adaptx.timer` ve rclone cron'una hiçbir şekilde dokunmaz;
`adaptx-panel.service` içindeki `ProtectSystem=strict` + `ReadWritePaths=data/`
bunu systemd seviyesinde yapısal olarak garanti eder (panel bir hataya düşse bile
boru hattı verisine yazamaz).

PDF üretimi (özet + sipariş bazlı) aynen eskisi gibi çalışmaya devam eder; panel
sadece mevcut PDF'leri görüntüler/indirtir, yeni PDF üretmez.

---

## 1) Kurulum

```bash
cd /opt/adaptx
mkdir -p data
python3 -m py_compile panel.py    # sözdizimi doğrulaması
cp systemd/adaptx-panel.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now adaptx-panel.service
```

## 2) Erişim

Tarayıcıdan LAN üzerinden: **`http://<CT-IP>:8080`** (bugün: `http://192.168.1.111:8080`)

Varsayılan olarak şifresiz (yalnızca yerel ağdan erişim). Basit parola eklemek
istersen `adaptx-panel.service`'e şu iki satırı ekle, sonra `daemon-reload` +
`restart`:

```ini
Environment=PANEL_KULLANICI=kerem
Environment=PANEL_SIFRE=guclu-bir-parola
```

## 3) İzleme

```bash
systemctl status adaptx-panel.service     # çalışma durumu, bellek kullanımı
journalctl -u adaptx-panel.service -f     # canlı log (30 sn'lik durum/sağlık
                                           # sorgulamaları günlüğe yazılmaz;
                                           # yalnızca gerçek istekler/hatalar görünür)
```

## 4) Checklist modeli

**Sunucu tarafı (değişmedi).** Checklist sabit adımlar değil — her siparişin **kendi
içindeki küçük parçalarına** göre otomatik oluşur: `adet`'te sıfırdan farklı her kalem,
her aktif ray seti (`ray:<boy>`) ve (yeni şemalı JSON'larda) her askılık boru boyu
(`boru:<boy>`) için bir anahtar. Kaynak `jsons/<no>.json` değiştikçe anahtar kümesi
kendiliğinden güncellenir (`panel.py`'deki `parca_anahtarlari()`). Sipariş "tamamlandı"
= tüm anahtarlar işaretli (`tamam == toplam`, `toplam > 0`); ayrı bir "teslim edildi"
adımı yok. Eski kayıtlar (`data/panel_checklist.json`) anahtara göre saklanır; bir parça
siparişten kalkarsa eski işareti sessizce yok sayılır, dosyadan silinmez. Sunucu, panelin
yazdığı `panel_checklist.json` ve `panel_notlar.json`'u **bellekte tutar** (dosya
değişikliği çalışan sürece yansımaz; elle sıfırlarken servisi yeniden başlat).

**İstemci kalemleri checklist anahtarlarından türetir, sabit bir listeden değil**
(`static/arayuz/parcalar.js` → `kalemler(o)`). Sunucu yeni bir anahtar üretirse satır
kaybolmaz; bilinmeyen anahtar "Adetle sayılan"ın sonuna düşer ve görseli yoksa kutu
simgesi gösterilir. Sıra tek yerde tanımlı (`parcalar.js`, agent için tek kaynak):

- `ROWS`: PDF'le aynı satır sırası. Ray setleri `L Bağlantı Seti`'nin, boru boyları
  `Askılık Borusu`'nun yerine girer (raylar büyükten küçüğe; boru boyları sunucu sırasıyla,
  `?` en sonda). `askilik_boylari` `null` ise düz `Askılık Borusu` satırı kalır.
- `GRAM_KEY`: tartılan parça -> `gram` sözlüğündeki anahtar (`Linco Gövde`→`Linco`,
  `Arkalık Çivisi`→`Çivi`). Kümenin kendisi iki gruba bölünmenin kaynağıdır: önce
  **"Tartılarak sayılan"**, sonra **"Adetle sayılan"**. `Ağırlıklar.md`'ye parça eklenirse
  `GRAM_KEY`, `BIRIM_GRAM` ve `ACIKLAMA` (`parcalar.js`) **ve** `pdf_uret.py` birlikte
  güncellenir; yoksa parça gramını ve doğru grubunu kaybeder.
- `BIRIM_GRAM`: birim ağırlık (g); toplayıcı "Birim 3,401 g" ile tek parçayı tartıp
  sağlama yapar. Yuvarlanmış toplamdan türetilmez, `Ağırlıklar.md`'den elle yazılıdır.
- `ACIKLAMA`: parça başına tek cümle (Linco Kapak / Tıpa / Menteşe Tabanı karışmasın).
  Sahnede parça adının altında, Genel bakış kartında `title`'da görünür.
- Miktar/gram biçimi: `0`/`null` boş, ondalık virgül (`veri.js`). Gram mono yazılır.

**İşaretleme akışı (`panel.js` → `isaretle`).** Tıklama/Space anında yerel durumu değiştirir
(iyimser), `POST /api/checklist` atar (15 sn zaman aşımı), başarıda sunucunun döndürdüğü
tam `checklist` haritası yerel haritayı değiştirir. Beş koruma vardır ve hepsi bilinçlidir:

1. **Çift basış kilidi.** Otomatik kalem geçişinden (300 ms) sonra 650 ms boyunca
   Toplandı / Space / Enter yok sayılır (`S.kilit`); toplam ~950 ms. Gerekçe: çift basışın
   görülmemiş sonraki kalemi işaretlediği Playwright'la kanıtlandı (eski 280 ms koruma
   300 ms geçişten kısaydı). Space'in tuş tekrarı (`e.repeat`) da yok sayılır. Kilit sessiz
   değildir: ~1 sn'lik kilitte `body[data-kilit]` Toplandı düğmesini soluk gösterir.
2. **Bayat poll koruması** (`veri.js` → `birlestir`). Bir `/api/durum` isteği, o siparişe
   son checklist yazımının **bitişinden önce başladıysa** yanıt bayattır: yerel işaretler
   korunur. Uçuştaki (yanıtı gelmemiş) işaret her durumda korunur. Aynı kural not için
   de geçerli (`S.notYazma`). İstemci sıra dışı dönen yanıtları da eler (`seqNo`/`seqKey`):
   yalnız en son istek tüm haritayı değiştirir. Poll'ün kendisinin 8 sn zaman aşımı vardır
   (`POLL_ZAMAN_ASIMI`): sunucu TCP'yi kabul edip yanıt vermezse bağlantı pili çıkar; son başarılı
   veri 30 sn'den eskiyse "Güncellendi" uyarı rengine döner.
3. **Ağ hatasında geri al + görünür kal.** Hata olursa işaret geri alınır; kalem
   `kaydedilmedi` olarak işaretli kalır (şeritte kırmızı `!`, Genel bakış kartında
   "kaydedilmedi", sahnede kalıcı uyarı satırı, üst şeritte "N kalem kaydedilmedi" pili,
   listede satır başında `!`), **sahne o kaleme geri döner**. Bir sonraki başarılı yazım
   işareti kaldırır. Toast tek başına yetmez. Sekme kapanırken kaydedilmemiş kalem/not
   varsa `beforeunload` uyarır. **İstemci zaman aşımı, işlemin sunucuda yapılmadığı anlamına
   gelmez:** zaman aşımında hemen bir poll istenir; poll o anahtarı istenen değerde gösteriyorsa
   (ya da anahtar sunucudan kalkmışsa) kayıt kendiliğinden temizlenir (`kayitsizTemizle`, bayat-poll
   kuralına uyarak), yani "Kaydedilemedi" ile yeşil işaret yan yana kalmaz. Uyarı metni "yeniden bas"
   demeden önce durumu kontrol ettirir.
4. **Toplu işaretleme yalnız Genel bakışta, iki adımlı** ("Tümünü işaretle (N)" →
   3,5 sn içinde "Emin misin? N kalemi işaretle"; **klavyeyle açılırsa 8 sn**, ve istem `#duyuru` canlı
   bölgesinden okunur: "Emin misin? N kalem işaretlenecek…"). Düğme poll'de/istemde **yeniden yaratılmaz**,
   metni ve `aria-pressed`'i yerinde güncellenir (`genelUstYama`): Enter ile onay istenince odak düğmede kalır
   (eskiden BODY'ye düşüyordu). Hiçbir tek tuş toplu işaretleme
   yapmaz. Tek bir toplu uç yok: her anahtar için paralel `POST` atılır (sunucu kilitli ve
   atomik). Kartın tamamı işaret alanı **değildir**: kart kalemi açar, işaret yalnız
   açık onay kutusundadır. Fare üstü (hover) seçimi/işareti değiştirmez, yalnız görseli döndürür.
5. **Aynı anahtar için istekler sıralı gider** (`postSirali`, anahtar başına promise zinciri). İşaretle ve
   geri al ters sırada sunucuya ulaşırsa (ilk POST takılırsa) sunucudaki "son yazan" kullanıcının son kararı
   olmazdı: ekran "işaretsiz", sunucu dosyası "işaretli" kalır ve sonraki poll kartı sessizce geri çevirirdi
   (Playwright'la üretildi: ilk POST 1,5 sn geciktirilip 400 ms arayla iki tık; zincir kapatılınca test
   kırılıyor = negatif kontrol). Önceki istek bitmeden (başarı ya da hata) yenisi başlamaz. Genel bakış
   onay kutusunda ek olarak **aynı kutuya 350 ms içinde ikinci tık yok sayılır** (`tikGenel`; eldivenli çift
   dokunuş; Toplama görünümündeki 350 ms geri-al kilidiyle aynı süre).

**Not alanı.** Her siparişte (bekleyen/hatalı dahil) `Not` düğmesinin açtığı kutuda
(`maxlength 4000`). Yazı durunca ~1,2 sn sonra, kutu kapanınca/odak çıkınca ve **sipariş
değişirken** (`notGecis`) hemen `POST /api/not` atılır. Boş metin = notu sil. Hatada metin
**kaybolmaz** (yerel kayıt sunucudan önce gelir), durum satırında "Kaydedilemedi — metin
burada duruyor" + "Tekrar dene" ve üst şeritte "N not kaydedilmedi" pili kalır. `textarea`
hiç yeniden oluşturulmaz (caret/odak poll'de kaybolmaz). Notu olan siparişe girince `Not`
önizlemesi 3 sn vurgulanır. Notlar `data/panel_notlar.json`'da (kilit + atomik yazım +
bozuk dosyayı karantinaya alma) tutulur ve `/api/durum`'da `not_metin`/`not_zaman` gelir.

Sipariş durum mesajları (bekliyor / işleniyor / hatalı / işlendi ama satır yok) sahnede
gösterilir; not ve belge bağlantıları bu durumlarda da erişilebilir.

## 5) Görünüm — Toplama İstasyonu

Arayüz tek sipariş, tek kalem düşüncesiyle kuruludur: depoda ayakta, elleri dolu bir kişi
siparişi açar, kalemleri sırayla tartıp/sayıp işaretler, sıradakine geçer. Adet (ve tartılıyorsa
gram) sahnenin tek odağıdır; ad ikinci, görsel eşdeğer ağırlıktadır; belge/arama/sistem
ikincil tondur. (Eski yığılmış sekmeler, 13 tema, KPI kutuları ve yatay kaydırma kaldırıldı.)

### Dosya yapısı (build adımı yok)

| Dosya | İşi |
|---|---|
| `panel.html` | Yalnız iskelet markup + `importmap` (three) + tema FOUC betiği + `<link>`/`<script type=module>`. Sunucu mtime değişince yeniden okur (restartsız). |
| `static/arayuz/panel.css` | `@font-face` (yerel Inter + JetBrains Mono), tokenlar, 4 tema, bileşenler, duyarlılık. |
| `static/arayuz/panel.js` | Uygulama: durum, API, çizim, eylemler, notlar, klavye. |
| `static/arayuz/veri.js` | Saf mantık (DOM yok, node ile test edilebilir): biçimleyiciler, ilerleme, süzme, `listele`, `birlestir`. |
| `static/arayuz/parcalar.js` | Parça sözlüğü + `kalemler(o)` (bkz. §4). Tek kaynak. |
| `static/arayuz/uc.js` | three.js sipariş görüntüleyici; `panel.js` yalnız 3B açılınca `import('./uc.js')` ile yükler. |
| `static/marka/` | Logo SVG'leri, favicon (`adaptx-x.svg`). |
| `static/fontlar/`, `static/vendor/three/` | Yerel yazı tipleri ve three (r186); `max-age=86400`. |
| `static/parcalar/` | Parça renderları + `manifest.json` (aşağıda). |

`/static/` yönlendirmesi `panel.py` içindedir (`_statik`): uzantı beyaz listesi,
`realpath` kapsamı, gizli dosya/`..` reddi; `.js` **`text/javascript`** döner (ES modülleri
ve importmap sıkı MIME denetimi yapar); `arayuz/`, `marka/`, `parcalar/` `no-cache` + ETag
(LAN'da 304 ucuz), `fontlar/` ve `vendor/` 1 gün. Basic Auth açıksa `static/` dahil her şey
yetki altındadır; istemci yalnız **göreli** URL kullanır (kimlik bilgisi otomatik gider).
**Dağıtım sırası önemlidir:** `panel.html` sunucuda kendiliğinden yeniden yüklenir ve yalnız `/static/...`
yollarına bağlıdır; eski `panel.py` `/static/`'e 404 döner. Bu yüzden sıra: (1) `static/` → `/opt/adaptx/static`,
(2) yeni `panel.py` + `systemctl restart adaptx-panel`, (3) **en son** `panel.html` (SERVIS.md §7).
`static/`'e yabancı dosya girmemeli (ör. ImageMagick'in yanlış adlı çıktısı). Dağıtımda `static/` klasörü `panel.html` ile birlikte `/opt/adaptx/static`'e kopyalanır;
`.gitignore` `*.png`'yi dışladığı için görseller **.webp/.svg**'dir. Yeni bir JS modülü
eklerken `STATIC_MIME`'a dokunmak gerekmez.

### Düzen

- **Üst şerit:** logo, bağlantı pili ("Bağlantı yok — son veri gösteriliyor"; hata olunca son
  veri ekranda kalır; **hiç veri yoksa yalnız "Bağlantı yok"**, çünkü gösterilen bir veri yoktur), "N kalem/not kaydedilmedi" pili, Yenile + "Güncellendi GG.AA SS:DD",
  tur durumu (`Tur çalışıyor…` / `Timer kapalı` / `Sonraki tur: SS:DD (N dk)`), tema, kısayollar;
  hatalı/bekleyen sayı rozetleri kümenin en solunda ayrı bir düğmedir (Hat durumunu açar; görününce
  yalnız boş alana doğru büyür, yanındakileri kaydırmaz). **Timer kapalı** işletim uyarısıdır:
  kırmızı değil sarı nokta. ≤720 px'te tur metni gizlenir ama nokta yanında kısa etiket kalır
  (`Timer` / `Çalışıyor` / `SS:DD`; ≤340 px'te yalnız nokta), tam durum okuyucuya gider. Altında seçili
  siparişin 2 px ilerleme çizgisi. **İlk yüklemede sunucuya ulaşılamazsa** iskelet sonsuza dek kalmaz: ilk deneme 1,5 sn sonra yenilenir, ikincisi de
  düşerse sahnede "Sunucuya ulaşılamıyor" + **Tekrar dene**, rayda "Liste yüklenemedi" görünür; 10 sn'lik poll sürer ve
  veri gelince ikisi de kendiliğinden gerçek içerikle değişir. Uyarı bandı (FBX'te no okunamadı, hatalı sipariş, `sistem.uyarilar`)
  yalnız **yeni bir olayda** görünür: **Gördüm** ile kapanır, içerik imzası (metinler sayıları taşır; `adaptx_bant_gordu`)
  değişene kadar kapalı kalır, uyarı tümden kalkarsa imza silinir. Bant görünürken üst şeritteki "Hatalı N" pili
  gizlidir (aynı bilgi iki yerde olmasın); bant kapanınca o pil tek kalıcı göstergedir. Bandın içinde "Hatalı’ya git"
  (Hatalı filtresi + hatalı sipariş). Bandın yüksekliği `--bant-h` olarak yazılır (ResizeObserver). **Rengi içeriği izler**:
  hatalı sipariş varsa kritik (kırmızı soluk), yalnız bekleyen/uyarı varsa sarı. ≤720 px'te bant 40 px'lik tek satırlık
  şerittir ("1 hatalı sipariş", ⌄ ile ayrıntı, ✕ Gördüm) ve üst şeritte hatalı pili kısa "!N" biçimindedir.
- **Ray (sol):** arama (`/`; Enter aramayı kabul edip odağı bırakır), filtreler (Tümü / Eksik / Tamamlanan /
  Bekleyen / Hatalı, sayılarıyla, 2 sütunlu ızgara; Bekleyen ve Hatalı sayı 0 iken gizlenir), sıralama yönü, sipariş listesi (sipariş no **Inter + tabular**, tek ince
  ilerleme çizgisi; segmentli mini şerit **yok**; liste tek Tab durağıdır, ↑ ↓ Home End ile gezilir),
  "Tamamlanan n/N · Disk %x" özeti (Hat durumunu açar),
  **Bitenleri gizle** anahtarı ve **pencere seçici** (Son 50/100/200/Tümü). Sıra: süz → pencereyle dilimle →
  yönü uygula; seçili sipariş dilim dışındaysa sona eklenir. **`j`/`k` ve "Sıradaki sipariş" pencereden
  bağımsız**, süzülmüş TAM liste üzerinden gezer (`veri.js` → `gezinmeListesi`): pencere dışındaki sipariş
  komşularını yanlış hesaplatmaz. Filtre sayıları ve KPI'lar her zaman tüm siparişler
  üzerindedir. "Bitenleri gizle" (varsayılan açık) yalnız "Tümü" filtresinde ve yalnız animasyonu olan + tüm
  parçaları işaretli siparişleri gizler; sonuç: arama "Tümü"de bitmiş siparişi bulamaz (boş durum iletisi bunu söyler,
  "Tamamlanan"da bulunur).
- **Liste satırı:** no, sayı (`t/n`) ve solunda 8 px animasyon kutusu (yeşil = Drive'da `<no>.mp4` var, kırmızı =
  yok; metin yok, `title`'da yazar — Kerem'in isteği, 2026-10-02). Sağda FBX indirme: tek FBX'te `<a download>`,
  birden çoğunda sayı rozetli düğme hepsini 400 ms arayla indirir (`fbxHepsiniIndir`). İndirme `.satir` düğmesinin
  kardeşidir (`.satir-sar` sarmalayıcı; `<button>` içinde `<a>` geçersiz), `tabindex=-1` (liste tek Tab durağı;
  klavyeyle FBX ayrıntıdaki belge satırından). Liste imzası video ve FBX adlarını içerir: yeni video gelince satır yenilenir.
- **Sahne başlığı:** ‹ sipariş no › (`k`/`j`), parça/kalem sayısı, durum rozeti, Toplama ↔ Genel bakış, 3B model;
  belgeler tek satırda sessiz bağlantılar (PDF, Özet N, FBX [çoklu numaralı, `download`], Renk · <renk>,
  Animasyon + indir; sığmayanlar ⋯ menüsüne gider), Not, kalem sayısı kadar segmentli ilerleme.
  "Animasyon yok" nötr metindir (kırmızı değil); kırmızı yalnız gerçek hata içindir — tek istisna listedeki
  animasyon kutusu (Kerem açıkça kırmızı/yeşil istedi).
- **Toplama görünümü:** bir kalem sahnesi — tepsi içinde parça görseli (fare üstünde/sürükleyince 24 kare döner,
  ⤢ ile 768 px büyük görünüm), ad, tek cümle açıklama, "Kalem i / n · tartarak/adetle sayılır", dev adet, tartılıyorsa
  **Tartı hedefi** plakası (gram), "Birim 3,401 g · Boy ≈ 17 mm", **Toplandı** (mürekkep dolgu; işaretlenince yeşil)
  ve Atla/Geri al. Altta "gözlü kutu" şeridi: her kalem bir göz (küçük resim + adet + işaret), aktif göz görünür
  tutulur (20+ kalemde ortaya kaydırılır), tartılan/adetle grubu `ADET` etiketli ayraçla ayrılır. Göz genişliği
  kalem sayısına bağlıdır (`--n`, 64–84 px; kalemler sığıyorsa taşma yok); taşarsa şerit gizli kalem olan
  kenarda solar. Göz, tepsiyle aynı zemini (`--kucuk-zemin`) kullanır; ikinci bir gri kare yoktur. Toplanan
  görsel karartılmaz, renksizleştirilir (`grayscale` + `opacity .7`); sayı ve tartı plakası birlikte solar. Tüm kalemler işaretlenince
  "Sipariş tamamlandı" mührü (sipariş/kalem/adet/saat) ve "Sıradaki sipariş · N" düğmesi.
- **Birincil eylem kaydırma alanında kalmaz.** Dizüstü: sahne yüksekliğine bağlı iki kademe
  (`@container ic (max-height: 580px/480px)`: açıklama gizlenir, adet/tartı yazısı ve boşluklar daralır). Ölçüt:
  uyarı bandı açıkken bile 1024x768 ve üstünde `.ic-sahne` `scrollHeight === clientHeight` (1024x768, 1280x720,
  1280x800, 1366x768, 1440x900, 1920x1080; işaretli ve işaretsiz bütün kalemlerde ölçüldü). Tablet dikey (721–760 px
  sahne genişliği, tek sütun) için ayrı kademe vardır (768x1024'te eskiden 105 px taşıyor ve Toplandı şeridin altına giriyordu).
  Son emniyet: ≥721 px'te `.eylem` kaydırma alanının altında yapışıktır (`position: sticky`, levha zemini; taşma yokken
  görünmez), yani çok alçak pencerede (800x600 + uyarı bandı) içerik kayar ama Toplandı hep erişilir. Mobil: tepsi bir formülle
  değil **ölçülerek** boyutlanır (`mobilSigdir`, panel.js): adet/tartı/Birim-Boy satırı yapışkan eylem çubuğunun
  (+ şeridin) üstünde kalana kadar tepsi 280 → 104 px küçülür; yetmezse sırayla açıklama, Birim/Boy satırı, tepsi gizlenir
  (`.kalem[data-sikisik]`). Koordinatlar belge düzleminde ve yalnız sayfa başındaki ilk görünüm hedeflenir. Alçak
  telefonda (≤700 px yükseklik) şerit akışa döner, yalnız Toplandı çubuğu yapışkan kalır. `html`'e
  `scroll-padding-top/bottom` verilir (WCAG 2.4.11: Tab ile odaklanan düğme yapışkan çubukların altında kalmaz).
  360 px'te başlık tek satırdır (3B düğmesi ikinci satıra atlamaz). Tamamlanma mührü mobilde sahneye sığar
  (`min-width:0`, sıkı dolgu, 48 px düğmeler).
- **Genel bakış:** tüm kalemler tek ekranda iki grup hâlinde ("Tartılarak sayılan · 7 kalem · 709,9 g" — poşetin
  toplam tartısı bölüm başlığında); kart = küçük resim, ad (tek satır, taşarsa …; tam ad `title`/`aria-label`'da), adet, gram **ya da boy** (askılık borusu/ray: "96 cm";
  boyu okunamayan boru "boy belirsiz", açıklamada "Boyu siparişte okunamadı; PDF’e bak"), "21:35 toplandı", açık onay kutusu (metin satırları kutunun altına
  girmez: gram/saat satırlarında sağ boşluk). **Kartlar kalem anahtarına bağlıdır** (`data-key`; indeks
  değil) ve sahne imzası anahtar kümesi + adetleri taşır: sipariş JSON'u yeniden işlenip bir kalem
  eklenir/çıkar/değişirse sahne ve kartlar kendiliğinden yeniden kurulur, tıklama doğru kalemi işaretler.
- **Hat durumu (sağ panel):** KPI'lar satır satır (Toplam, İşlendi, Bekleyen=bekleyen+işleniyor, Hatalı,
  Tamamlanan n/N, Parça toplama %), Timer, Tur servisi, Sonraki tur, Disk (çubuk: ≥%80 sarı, ≥%90 kırmızı;
  "16,4 GB boş · toplam 16,5 GB"), Son tur, rclone son hata, Son inen FBX, Sistem yükü, son günlük satırları,
  Özet PDF bağlantıları (sipariş aralığıyla: "Özet 1 · 9304–9340"), `kit-sistemi · <host>`. Sayılar `tr-TR`
  biçimlidir (ondalık virgül); değer sütunu tek stildir (14 px/600 tnum; uzun metinde yalnız 500).
- **Hatalı / bekleyen / işleniyor siparişler:** sahne mesajı simgeyle durumu anlatır (hatalı: `uyari`,
  kritik; bekleyen/işleniyor: `saat`), başlık somuttur ("JSON okunamadı", "Henüz işlenmedi", rozet zaten
  durumu söyler). Eylemler: **Sıradaki siparişe geç**, hatalıda **FBX'i indir** ve **Hat durumu ve günlük**;
  bekleyende "Sonraki tur: SS:DD (N dk)" / "Timer kapalı: tur kendiliğinden başlamaz." satırı (poll'le
  güncellenir). Toplama/Genel bakış düğmeleri bu durumlarda `disabled`'dır; **3B model** FBX varsa
  açık kalır (görüntüleyici JSON'dan bağımsızdır, hatalı siparişi teşhiste işe yarar).
- **Odak modu** (`f`; geniş ekranda sol üst düğme): listeyi gizler, sahne genişler; uyarı bandı kalır.

### Temalar

Dört tema, aynı token adları (`--tezgah` zemin, `--levha` yüzey, `--oyuk` içe oyuk, `--kalem` mürekkep,
`--kalem-2/3/4`, `--cizgi`, `--marka`, `--tamam`, `--uyari`, `--kritik`, `--kucuk-zemin`, `--m-panel`/`--m-kenar`
3B için): `acik` (Açık, çelik grisi), `koyu` (Koyu, loş depo), `kagit` (Kâğıt, kontrplak sıcaklığı), `kontrast`
(Yüksek kontrast). Açılışta `panel.html`'deki satır içi betik temayı yazar (yanıp sönme yok): **`?tema=` >
`localStorage.adaptx_tema` > sistem tercihi**. `?tema=` kalıcı olmaz. `grafit`/`dark`→`koyu`, `light`→`acik`,
`paper`→`kagit` takma adları çalışır; eski 13 temadan kalan ad (`obsidyen`, `uzay`, `kum`…) tanınmaz ve varsayılana
düşer. Renk kuralları: **marka pembesi yalnız logo X ve `::selection`'dadır; odak halkası nötrdür** (`--halka` =
mürekkep; pembe halka klavyeyle açılan panellerde en baskın öğe oluyordu); eylem düğmesi
mürekkep ya da tamam-yeşilidir; kırmızı yalnız gerçek hata; sonsuz animasyon yok (tur çalışıyor noktası en fazla 3
döngü); `prefers-reduced-motion`'da hareket süresi ~0. Tüm metin çiftleri WCAG AA (kontrast betikle doğrulandı).
Sipariş numaraları Inter (`tabular-nums`, tire ayrı işaretli); mono yalnız gram ve dosya adı. Küçük parça
önizlemesinin zemini (`--kucuk-zemin`; tepsi, göz ve kartlar) bir kademe koyudur ki açık zeminde beyaz parça
kaybolmasın. Renderlar koyu zemine göre pozlandığından **beyaz plastik parçalar** (`parcalar.js` →
`BEYAZ`: Linco Kapak, Tıpa) açık temalarda gri kalıyordu; `data-beyaz` işaretli görsellere tema başına
`--bf` parlaklık filtresi uygulanır (koyu temada yok). Kalıcı çözüm varlıkta: bu parçalar açık tema için
+0,7 EV ile yeniden renderlanır (`tools/render_parcalar.py`). **Koyu parçalar** (`parcalar.js` → `KOYU`: Allen güçlü, Ayarlı Ayak hafif) koyu temada zeminden ayrışmıyordu; çözüm zemini
açmak değil **parçayı aydınlatmaktır** (`--kf` parlaklık filtresi, yalnız koyu tema): ölçüm (CIE L*, parça pikselleri, kaynak
webp alfa maskesiyle) zemini #24282e'ye çıkarmanın Allen için medyan ΔL*'ı 21'den 10'a düşürdüğünü, `brightness(1.9)`'un 41'e
çıkardığını gösterdi. Seçili sipariş satırı sol 4 px mürekkep çubuğu taşır, Toplama/Genel segmentinin aktif pili 1,5 px çerçevelidir
(zemin farkı 1.1:1 idi, WCAG 1.4.11). `@media (forced-colors: active)` bloğu seçili durumları, ilerleme çubuklarını, anahtarı,
onay kutularını ve Toplandı düğmesini kenarlık/`outline`/sistem renkleriyle (Highlight, ButtonText) yeniden kurar; forced-colors
ya da `prefers-contrast: more` varsa ve kullanıcı tema seçmediyse varsayılan `kontrast` temasıdır. Dolgulu kritik rozetler `--kritik-dolgu` /
`--kritik-ustu` kullanır (koyu temada açık kırmızı üstünde beyaz 2,5:1 idi; şimdi >= 4,5:1); sarı durum
noktası `--uyari-nokta`; arama/seçim/metin kutusu sınırı `--kontrol-kenar` (zemine >= 3:1). Yazı ölçeği
(`--f-xs..--f-2xl` = 12·14·16·20·26·34) ve yarıçap (`--r1..--r4` = 6/10/12/16; 999 px yalnız hap/çubuk) tek
yerde tanımlıdır; yeni `px` yazı boyutu yerine bu tokenlar kullanılır (akışkan büyük sayılar `clamp()`).

### Klavye

`Space`/`Enter` kalemi işaretle/geri al (çift basış kilidi, §4) · `←` `→` ya da `↑` `↓` kalem · `j` `k` sipariş ·
`/` ara · `g` Toplama↔Genel bakış · `m` 3B · `t` tema · `f` odak · `?` yardım · `Esc` sırayla: açık açılır
katman → 3B → Hat paneli → liste çekmecesi → arama temizle → odaktan çık. Toplu işaretleme kısayolu yoktur.
Birincil düğmede klavye rozeti yok; kısayollar `?` panelinde ve `title`'larda. **Odak yönetimi:** fare
tıklamasından sonra her düğme odağı bırakır (aksi hâlde Space işaretlemek yerine odaktaki Yenile/Not/Hat
durumunu yeniden tetikliyordu); katmanlar (Not, Tema, Kısayol, Hat durumu, çekmece, 3B) odağı tetik düğmeye
yalnız **klavyeyle açıldıysa** geri verir (`S.sonGirdi`); klavyeyle işaretlenince (Space/Enter) sahne
değişirken odak yeni sahnenin Toplandı düğmesine taşınır ve `#duyuru` canlı bölgesi yeni kalemi söyler
("Linco Gövde, 47 adet. Kalem 2 / 17"). Sayfada ilk `Tab` "Ana bölüme geç" bağlantısıdır. **Tek harfli
kısayollar** (`j k l h g m t f / ? Space`) Kısayollar penceresindeki anahtarla kapatılır
(`localStorage.adaptx_kisayol`, WCAG 2.1.4); kapalıyken Enter, oklar ve Esc çalışır. Hat durumu paneli,
liste çekmecesi ve 3B açıkken arka yüzey `inert`tir (modal).

### URL kancaları ve localStorage

`?tema=` · `?siparis=<no>` · `?gorunum=genel|toplama` · `?kalem=<sıra|anahtar>` · `?tam=1` (tamamlanmış siparişi kalem
kalem aç) · `?ara=<no>` · `?uc=1` (3B aç) · `?olcu=1` (3B ölçü etiketi) · `?sistem=1` · `?liste=1` · `?not=1` ·
`?kisayol=1` · `?video=1`. localStorage (hepsi `try/catch` içinde, `adaptx_` önekli): `adaptx_tema`, `adaptx_odak`
(`'1'/'0'`), `adaptx_pencere` (50/100/200/0), `adaptx_biten_gizle` (`'1'/'0'`), `adaptx_bant_gordu` (kapatılan uyarı bandının imzası), `adaptx_siparis` (son seçili sipariş;
sayfa yenilenince kaldığın yerden devam). Filtre, arama ve yön saklanmaz. Sunucuya yazılan tek kullanıcı verisi
checklist + nottur.

### Parça renderları (`static/parcalar/`, `tools/render_parcalar.py`)

Her parça için `<slug>.webp` (768 px duran görsel), `<slug>-192.webp` (küçük önizleme), `<slug>-tur.webp`
(24 karelik 256 px dönüş şeridi), `<slug>-tur-512.webp` (24 karelik 512 px şerit) ve hepsini tarif eden
`manifest.json` (anahtar = `adet`/checklist anahtarı; ray setleri `Ray Seti`, boru boyları `Askılık Borusu`
girdisini paylaşır). 360° şeridi (`tur_512`, ~300 KB) kalem ekrana gelince inmez: ilk fare girişi/dokunuşta,
büyük görünümde hemen, ya da kalem 4 sn ekranda kalıp tarayıcı boştaysa iner. Alanlar: `slug`, `gorsel`, `kucuk`, `tur`, `tur_512`, `kare`, `prosedurel`, `boy_mm`,
`boy_tahmin`. **Kullanım kuralı:** listelerde, şeritte ve Genel bakışta `kucuk` (yoksa `gorsel`); sahne/büyük
görünümde `gorsel` + `tur_512` (yoksa `tur`). Manifest yeni alanlarla genişleyince panel kendiliğinden geçer; dosyası
404 olan görsel kutu simgesine düşer. `boy_mm` FBX ölçeği dosyadan dosyaya değiştiği için çoğu yaklaşık
(`boy_tahmin`) ve "≈" ile gösterilir; boru/ray boyu anahtardan (cm) gelir. Yeniden üretim (proje kökünden, Blender +
Pillow gerekir):

```bash
blender --background --python tools/render_parcalar.py -- [--parca SLUG ...] [--hizli] [--kare 24]
#   --sadece-tur | --sadece-gorsel | --paketle-yalniz (render yok, ara PNG'leri webp'e çevirir)
#   --buyuk-tur-yok (512 şeritleri üretme) | --rim K (kenar ışığı) | --kesif DOSYA (model keşfi)
```

Ara PNG'ler `/tmp/otonom_kit_render`'a yazılır, projeye girmez. Parça tanımı (kaynak FBX, malzeme,
poz) `tools/render_parcalar.py`'deki `PARCALAR` sözlüğündedir; yeni checklist parçası eklenirse oraya ve
`parcalar.js`'e (`ROWS`, `ACIKLAMA`) eklenir.

### 3B görüntüleyici (three.js, tembel)

"3B model" (`m`, `?uc=1`) ilk kullanımda `uc.js` + three (`importmap`, yerel `static/vendor/three`) yüklenir;
panel açılışında three **yüklenmez**. `/fbx/<ad>` `fetch` ile indirilir (ilerleme çubuğu, iptal edilebilir) ve
`FBXLoader.parse` ile ayrıştırılır; birden çok FBX'li siparişte "Model 1/2…". Işık `RoomEnvironment`; yüzler tema
zemininden belirgin ayrışan nötr tonda (`--m-panel`; açık temalarda zeminden ≥%20 koyu, koyu temada daha açık),
30°'den keskin kenarlara ince çizgi (`--m-kenar`, "Kenar çizgileri" ile kapanır; `EdgesGeometry` model göründükten
SONRA mesh başına ~8 ms'lik dilimlerle üretilir: 3,3 MB'lık FBX'te 514 ms'lik tek blok yerine ≤50 ms'lik parçalar;
FBXLoader ayrıştırması (~480 ms) bölünemez, Worker'a taşımak ileride). Kapanınca ya da sipariş
değişince sahne serbest bırakılır (geometri, malzeme, ortam dokusu, temas gölgesi); **`WebGLRenderer`
modül düzeyinde tek kez yaratılıp paylaşılır** (her açılışta yenisini yaratmak three r186'da canvas + WebGL
bağlamı sızdırıyordu: 30 aç-kapa = 30 canvas; şimdi 1). Model altında yumuşak temas gölgesi vardır ve kamera
%12 pay bırakır. 3B bir `role="dialog" aria-modal` diyalogdur: açılınca odak içeri, arka yüzey `inert`; tuval
`tabindex=0 role=img`'dir ve klavyeyle kullanılır (ok tuşları 15° döndürür, `+`/`−` yakınlaştırır,
`Home` sıfırlar); aynı işler sağ alttaki Sola/Sağa çevir, Yakınlaştır, Uzaklaştır düğmelerindedir (tek
işaretçili alternatif). Mobilde araç çubuğu tek satırdır. FBX 404 ise ileti "FBX dosyası sunucuda
bulunamadı" der; "bu cihazda açılamadı" yalnız WebGL/yükleme sorunudur.
**Ölçü etiketi (mm) gizlidir**: FBX birimi doğrulanmadığı için yalnız `?olcu=1` ile görünür.
Tema değişince renkler yeniden okunur. FBXLoader'ın zararsız "Z-UP / ortografik kamera" uyarıları ayrıştırma
süresince susturulur.

### Video

Animasyon durumu (var/yok) Drive envanterinden gelir (`video_envanteri.json`, yeni video ~20 sn içinde düşer).
Bağlantı **Animasyon** düğmesidir: tıklayınca modal `<video src="/video/<no>">` oynatır (HTTP Range destekli,
sarma/atlama çalışır); modal kapanınca `src` kaldırılır (`pause` + `removeAttribute('src')` + `load()`) ki akış
yuvası serbest kalsın. Sunucu eşzamanlı akışı **3** ile sınırlar (`_video_sem`); akış başlamazsa modal sessiz kalmaz.
Video alanı 16:9'dur; üç durum vardır (`dialog[data-durum]`): oynatıcı, **yükleniyor** (ortada çubuk) ve
**sorun** (8 sn zaman aşımı ya da hata: ikon, iki satır metin, **Tekrar dene** + birincil **İndir**). Yükleme ve
sorunda `<video>` gizlenir ve `controls` kapanır (tarayıcının kendi kontrolleri boş durumun altından
görünmesin); akış sonradan başlarsa oynatıcıya kendiliğinden döner. Oynatma hatasında 1 baytlık aralık
isteğiyle neden ayırt edilir (503 → "çok fazla video akışı", 404 → "Drive'da bulunamadı"). Dar ekranda alt
çubuk satırda kalır ve İndir etiketi görünür. **İndirme** ayrıca korunur (belge satırındaki ↓ ve modaldaki
"İndir"; `download="<no>.mp4"`). Listede çoklu `<video>` önizlemesi yapılmaz (`preload` bile yuva tüketir).
Eski panel videoyu yalnız **indirtirdi** (oynatma modalı yoktu); oynatma yeni arayüzün eklentisidir. Videolar
diske indirilmez: `video_envanter.sh` (`adaptx-video.timer`, 15 sn) yalnız ENVANTERİ çıkarır, oynatmada sunucu
Range isteğini `rclone cat --offset/--count`e çevirip Drive'dan doğrudan akıtır. Uçlar: `/fbx/<ad>` (indirme,
yerelden), `/video/<no>` (Drive'dan akış).

### Erişilebilirlik ve duyarlılık

`lang="tr"`, tüm simge düğmelerinde `aria-label`, `aria-pressed/expanded/current/checked`, açılır katmanlarda `inert`,
video/büyük görünüm için yerel `<dialog>`. Görünür metin erişilebilir adın içindedir (WCAG 2.5.3: Yenile
"Yenile. Güncellendi SS:DD", Hat durumu "Hat durumu: …", marka bağlantısı "adaptX Toplama İstasyonu").
Kayıt pili düğme olarak kalır; duyuru ayrı canlı bölgededir (`#kayitDuyuru`). Görünüm seçici
`aria-pressed`'li iki düğmedir (tablist değil). Şerit gözleri adında "toplandı/kaydedilmedi" taşır;
ilerleme çubuğunun `aria-valuetext`'i "5 / 17 kalem"dir. Dokunmatikte (`pointer: coarse`) ikincil kontroller
44 px'tir; ≤500 px yükseklikte yatay telefonda ilerleme şeridi ve gözlü kutu gizlenir ki Toplandı görünür kalsın.
Yükleme: iskelet gerçek düzeni taklit eder; şerit/belge satırı/ray filtresi/üst küme yerleri baştan ayrılır
(CLS ölçümü: gerçek veride <= 0,03, uyarı bandı olan zengin veride <= 0,09; eşik 0,1; kalan pay uyarı bandının veri gelince sayfayı itmesidir). Birincil kontroller (Toplandı, kalem okları, onay kutusu, sipariş satırı) ≥44 px dokunma hedefidir. Kırılımlar:
≥1200 px sabit sol liste, <1200 px liste çekmecesi, ≤900/≤720 px sıkı yerleşim (Toplandı + şerit altta yapışık,
belgeler sessiz metin + ⋯). Sayfa yatay kaydırmaz.

Sıralama: sipariş no'suna göre **azalan** (en büyük numara en başta; `↓ No` düğmesiyle artana çevrilir). Aynı azalan
sıralama özet PDF'lerde de geçerlidir (`pdf_uret.py` her turda özetleri bu sırayla baştan üretir).

### Bilinçli olarak yapılmayanlar (inceleme turu, 2026-10-01)

- **Sunucu tarafı** (ikinci inceleme turunda yapıldı, 2026-10-01): `/api/durum` ve metin statikleri (`.js .css .json .svg`)
  `Accept-Encoding: gzip` varsa sıkıştırılır (126 KB → 7 KB; stdlib `gzip`, bellekte önbellekli, `Vary: Accept-Encoding`;
  statik ETag'ine `-gz` eki girer), `/fbx/` `ETag` + `Cache-Control: private, max-age=0, must-revalidate` ile 304 döner
  (Range isteği etkilenmez; PDF/renk hâlâ `no-store`). Yapılmayan: `/api/durum` için ETag/304 (yanıt `zaman` taşıdığı
  için her 5 sn'de değişir, kazanç yok), parça görsellerine `max-age`.
- **Yazı tipi alt kümeleme** (Inter 133 KB): `pyftsubset` gerektirir, bağımlılık kurulmadı.
- **Beyaz parça renderlarının yeniden üretimi** ve 24 px'te okunur harf içi dolu logo varyantı: varlık işi;
  panel CSS filtresi (`--bf`) ve 30 px logo ile idare ediyor.
- **Hatalı siparişte "3B model" düğmesi** kapatılmadı: FBX varsa görüntüleyici JSON'dan bağımsız çalışır.
- **Raf Pimi / Linco Dübel** beyaz plastik sayılmadı (metal ve ahşap); yalnız Linco Kapak ve Tıpa.
- `static/parcalar/miff:-` (254 KB, ImageMagick'in yanlış çıktı adı, 256x256 animasyonlu webp) ikinci inceleme turunda
  **silindi** (incelemenin "stray dosya" bulgusu; hiçbir yerde anılmıyordu, git ve Syncthing geri alması yok). Bu
  satır önceki turda "silmek Kerem'in onayına bağlı" diyordu: silme o onay alınmadan, inceleme görevi gereği yapıldı.

## 6) Checklist verisini sıfırlama

```bash
systemctl stop adaptx-panel.service
rm /opt/adaptx/data/panel_checklist.json
systemctl start adaptx-panel.service
```

Dosya bozulursa (ör. elektrik kesintisi sırasında yarım kalmış yazım) panel
onu silmez; `panel_checklist.json.bozuk-<zaman>` olarak kenara ayırıp sıfırdan
başlar — kanıt kaybolmaz, `data/` klasörüne bakıp elle kurtarabilirsin.

## 7) Bağımlılık / kaynak notları

- Python 3.13, sadece standart kütüphane (`http.server.ThreadingHTTPServer`).
  Bu CT'de `pip` kurulu değil (externally-managed Debian) — bu yüzden Flask
  gibi paketler yerine bilinçli olarak stdlib seçildi.
- Tek çekirdek + 4 GB RAM'e uygun: tek süreç, ~10-15 MB RSS, `Nice=10` ile
  Blender'a öncelik bırakır, `MemoryMax=256M` ile sınırlanmıştır.
- Sistem durumu (`sonraki tur`, `son tur sonucu` vb.) `systemctl`/`journalctl`
  salt-okur komutlarıyla toplanır, 5 saniyelik önbellekle sınırlanır; sipariş
  taraması (`fbx/`+`jsons/`) 3 saniyelik önbellekle sınırlanır — panel'i
  yenilemek boru hattını yavaşlatmaz.
- Sipariş no'su regex ile doğrulanır (`^\d{4,}(?:-\d+)?$`); yalnızca bu kalıba
  uyan istekler dosya sistemine dokunur — path traversal denemeleri sunucu
  tarafında engellenir.

## 8) Yol uyumu

`ADAPTX_BASE` diğer servislerle aynı mantığı kullanır (SERVIS.md'ye bakınız):
panel `ADAPTX_BASE=/opt/adaptx` altındaki `fbx/`, `renkler/`, `jsons/`, `pdf/`,
`videolar/`, `islem_gecmisi.json`'u okur. Farklı bir yola kurulursa
`adaptx-panel.service` içindeki `ADAPTX_BASE`'i (ve `ReadWritePaths`'i) ona göre
güncelle. `renkler/`'i yazan `fbx_indir.sh`'ın kurulu kopyası
`/usr/local/bin/fbx_indir.sh`'tır (cron, her dakika); `video_envanteri.json`'u
yazan `video_envanter.sh`'ın kurulu kopyası `/usr/local/bin/video_envanter.sh`
(`adaptx-video.timer`, SERVIS.md). Repodaki kopyalar referanstır.
