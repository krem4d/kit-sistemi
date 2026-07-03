# Adaptx Panel — Web İzleme + Checklist Arayüzü

Sayım hattını (rclone → `fbx/` → Blender → `jsons/` → `pdf/`) tarayıcıdan izlemek
ve her siparişi checklist ile takip etmek için native (Docker'sız, pip'siz)
bir web paneli. Sadece Python standart kütüphanesi kullanır — ek paket
kurulumu gerekmez.

Panel boru hattına karşı **salt okurdur**: `fbx/`, `jsons/`, `pdf/`,
`islem_gecmisi.json` yalnızca okunur. Yazdığı tek dosya `data/panel_checklist.json`'dur.
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

Checklist artık sabit adımlar değil — her siparişin **kendi içindeki küçük
parçalarına** göre otomatik oluşur: o siparişte miktarı sıfırdan büyük olan
her `adet` kalemi (Linco Gövde, Kulp, Menteşe Tabanı, …) ve her aktif ray
seti için ayrı bir checkbox gösterilir. Değiştirilecek bir konfig listesi
yok — kaynak `jsons/<no>.json` değiştikçe checkbox listesi otomatik
güncellenir (`panel.py`'deki `parca_anahtarlari()` fonksiyonu).

Sipariş "tamamlandı" sayılması = o siparişteki tüm parçaların işaretlenmiş
olması (`tamam == toplam`, `toplam > 0`). Ayrı bir "teslim edildi" adımı
yok; istenirse ileride eklenebilir.

Eski kayıtlar (`data/panel_checklist.json`) parça anahtarına göre saklanır;
bir parça sonradan siparişten kalkarsa (miktar 0'a düşerse) o parçaya ait
eski işaret sessizce yok sayılır, dosyadan silinmez.

## 5) Görünüm — Obsidian tarzı yığılmış sekmeler + temalar

Siparişler, Obsidian'ın **kayan yığılmış sekmeleri** (sliding panes) gibi
yatay bir yığında durur: her sipariş her zaman tam bir checklist panelidir;
yatay kaydırdıkça paneller kenarlarda üst üste binerek yalnızca sipariş
numarasının **dikey yazıldığı** şeritleri kalır ve kaydırmaya devam edince
kendiliğinden açılırlar — elle aç/kapat yoktur (`position:sticky` +
JS'te hesaplanan left/right ofsetleri; `SERIT_W` sabiti CSS'teki şerit
genişliğiyle eşleşmelidir). Şeride veya üstteki hızlı-git piline tıklamak
o siparişi görünüme kaydırır; şeritlerin üzerinde fare tekerleği yatay
kaydırır. `/` tuşu aramaya odaklanır; arama tek sonuca inince o sekmeye
kendiliğinden kaydırılır. Üst bölüm (KPI/uyarı/araç çubuğu) bilinçli olarak
kompakt tutulur — ana odak checklist yığınıdır; yığın yüksekliği görünür
pencereye göre büyür (`calc(100vh - …)`).

Sıralama: sipariş no'suna göre **azalan** — en büyük numara en başta (araç
çubuğundaki ↑/↓ butonuyla yön değiştirilebilir). Aynı azalan sıralama özet
PDF'lerde de geçerlidir (`pdf_uret.py` her turda özetleri bu sırayla baştan
üretir; araya sonradan eklenen sipariş doğru yere oturur ve kayan sayfalar
kendiliğinden yenilenir).

13 tema vardır; başlıktaki isimli tema menüsünden seçilir: **Uzay**
(varsayılan), **Obsidyen** (kullanıcının Obsidian ekran görüntüsünden piksel
örneklemeyle alındı: Catppuccin Frappé zemin/metin + parlak turkuaz vurgu +
monospace yazı tipi), **Nord**, **Karbon**, **Okyanus**, **Gece**, **Gül
Kurusu**, **Kahve**, **Orman**, **Gün Batımı**, **Matris** (monospace),
**Açık**, **Kum**. Obsidyen ve Matris minimalisttir: köşe yarıçapları 0
(`--radius*` değişkenleri) ve kart başlığındaki degrade/vurgu şeridi kapalı.
Seçim `localStorage`'da saklanır, sunucuya yazılmaz.

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
panel `ADAPTX_BASE=/opt/adaptx` altındaki `fbx/`, `jsons/`, `pdf/`,
`islem_gecmisi.json`'u okur. Farklı bir yola kurulursa `adaptx-panel.service`
içindeki `ADAPTX_BASE`'i (ve `ReadWritePaths`'i) ona göre güncelle.
