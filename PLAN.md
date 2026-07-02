# Adaptx Otonom Kit — Proje Yol Haritası

## Amaç
Tahtalarla gönderilen **küçük parça kiti**nin adetlerini, 3D modeldeki delik/parça
hacimlerinden **otonom** belirleyen bir sistem kurmak; sonunda fotoğraftaki çeklist
tablosuna benzer bir **PDF** üretmek.

## Temel kararlar
1. Sayım mantığı `delikbulma.py`'ye dokunmadan **ayrı yeni modülde** kurulur
   (`delikbulma.py` montaj animasyonu için kullanılıyor, korunacak).
2. Siparişler ileride **toplu / headless** işlenir
   (`blender --background --python`, her FBX bir sipariş → tek tabloda birleşen sütunlar).
3. Sayım sisteminde parça **yerleştirmeye gerek yok** — sadece **adet**.

## Referans dosyalar
- `hacimler.md` — parça referans hacimleri (eşik değerleri).
- `parca_kurallari.md` — her parçanın adet formülü.
- `Eksikler.md` — Mert'i bekleyen / ileri faz kalemleri.
- `PROGRESS.md` — güncel durum.

## Fazlar

### Faz 0 — Veri + Ölçüm aracı  ← ŞU AN
- `hacim_bul.py`: seçili parçanın kendi hacmini + delik hacimlerini raporlar.
- `hacimler.md`, `parca_kurallari.md`, `PLAN.md`, `PROGRESS.md`.
- **Çıkış koşulu:** menteşe tabanı + kulp hacimleri ölçülüp `hacimler.md`'ye girildi.

### Faz 1 — Sayım motoru
- `parca_sayim.py` (yeni). `delikbulma.py`'nin tespit mantığını al; **Empty
  yerleştirmeyi çıkar**, yerine **parça-başına + sipariş-başına adet sayacı** koy.
- `menteseTabani` kategorisini ekle.
- Çıktı: sipariş başına parça→adet sözlüğü.

### Faz 2 — Türetilen parçalar
- Frenli/frensiz split, Allen, Tıpa, Kulp vidası, Linco×4, modül A–B çiftleri
  (`parca_kurallari.md`'ye göre).

### Faz 3 — Kulp tespiti
- Kulp dummy'sini kendi hacminden (ve/veya isim kuralından) sayma.

### Faz 4 — Ertelenenler (Mert)
- Askılık, Ray, L bağlantı, ağaç vidası toplamı, renk ayrımı, kontrol bayrakları.

### Faz 5 — Toplu işleme + PDF
- Klasördeki tüm sipariş FBX'lerini headless işle; fotoğraftaki tablo formatında PDF.
- (Bu faza kullanıcı onayı olmadan başlanmayacak.)
