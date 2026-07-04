# Hacim Kayıt Tablosu — Adaptx Otonom Kit

Bu dosya, sayım sistemi için gereken tüm parçaların **referans hacimlerini** tek yerde
tutar. Sayım motoru (Faz 1+) bir deliğin/parçanın hangi parça olduğunu bu hacimlere
`%tolerans` içinde bakarak belirler.

- **Birim:** yerel object-space hacmi (delikbulma.py / hacim_bul.py ile aynı ölçek).
- **Tespit yöntemi:** `delik` = tahtadaki oyuk hacminden; `dummy` = parçanın kendi
  hacminden; `türetme` = başka bir parçadan hesap.
- Eksik değerleri **`hacim_bul.py`** ile ölç ve `⏳ ÖLÇÜLECEK` satırlarını doldur.

---

## 1) Bilinen hacimler (delikbulma.py'de zaten tanımlı)

| Parça | Kategori kodu | Tespit | Hacim (mm³) | Tolerans | Durum |
|-------|---------------|--------|-------------|----------|-------|
| Linco (Gövde/Kapak/Dübel/Minifix kaynağı) | `linco` | delik | 9680.0 | %1 | ✅ |
| Linco Dübel | `pim` | delik | 936.0 | %1 | ✅ (linco'dan türetilir; çapraz kontrol) |
| Ağaç vidası | `ahsapcivisi` | delik | 14.57 | %5 | ✅ (gerçek FBX ölçümü) |
| Raf pimi | `rafpimi` | delik | 234.0 | %1 | ✅ |
| Modül bağlantı aparatı | `modulbaglanti` | delik (A–B çift) | 351.35 | %1 | ✅ |

> Gözlem: linco delikleri raporlarda **9646–9776 mm³** aralığında (üst uç ≈ +%1 sınırda).
> Faz 1'de kategori-bazlı tolerans gerekebilir.

---

## 2) Ölçülen hacimler (yeni_hacimler.md — tamamlandı ✅)

| Parça | Kategori kodu | Tespit | Hacim (mm³) | Tolerans | Durum |
|-------|---------------|--------|-------------|----------|-------|
| **Menteşe tabanı** | `menteseTabani` | delik | 11454.0131 | %1 | ✅ (gerçek FBX'te doğrulandı) |
| **Kulp** | `modulbaglanti` (delik çifti) | delik çifti (~192 mm arayla) | 351.35 × 2 | %5 + %5 mesafe | ✅ (detect_kulp_pairs) |

Bu iki değer `parca_sayim.py` içindeki `CATEGORIES`/`KULP_VOL`'a işlendi.

> ✅ **Ağaç vidası (ahsapcivisi):** delik hacmi `parca_sayim.py`'de **14.57**, `%5` tolerans.
> Ayak tespiti artık delik SAYISINA değil, 4 vidanın oluşturduğu **~32×40 mm dikdörtgene**
> dayanır (bkz. parca_kurallari.md → Ayarlı ayak; `count_ayak_feet`).
> Not: Ağaç vidası KİT ADEDİ ise türetmeyle hesaplanır (bkz. parca_kurallari.md), delik
> sayısıyla değil.

---

## 3) Ertelenen parçalar (Eksikler.md — Mert / ileri faz)

Bu parçaların hacimleri ileride, ilgili karar/entegrasyon netleşince ölçülecek.

| Parça | Tespit (öngörülen) | Hacim (mm³) | Durum |
|-------|--------------------|-------------|-------|
| Askılık flanşı | delik | — | ⛔ ertelendi |
| Askılık borusu | delik/dummy | — | ⛔ ertelendi |
| Ray (Set) | kendine özgü delik deseni (kalibrasyon 1 birim=1000 mm) | `RAY_DELIK_HACIM` ≈ 84.92 (ahsapcivisi=14.57'den FARKLI — bkz. hacim_bul_raporu.txt) | ✅ entegre (detect_rays) |
| L Bağlantı seti / vidası / dübeli | Mert ile karar | — | ⛔ ertelendi |
| L Modül Uzun Linco Pimi | iki parçadaki birbirine dayalı linco çifti (~43 mm) | `linco` = 9680 | ✅ entegre (detect_long_linco_pins) |
