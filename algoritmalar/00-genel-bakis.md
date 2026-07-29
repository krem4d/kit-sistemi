# 00 — Genel Bakış: Parça Bulma Algoritmaları

Bu klasör, `parca_sayim.py` içindeki **her parça bulma algoritmasının mantığını** ayrı
ayrı açıklar. Kaynak dosya tek: `parca_sayim.py` (1085 satır). Bu dokümanlar koddan
türetildi, `parca_kurallari.md`'den değil — satır numaraları gerçek koda referanstır.

> `parca_kurallari.md` **ne** sayıldığını listeler. Buradaki dosyalar **nasıl ve neden**
> öyle sayıldığını anlatır.

---

## Temel fikir

Sistem parça **isimlerine bakmaz**. FBX'te parçaların adı `Object_23` gibi anlamsızdır.
Bunun yerine tahtaya **açılmış deliklerin geometrisinden** hangi donanımın takılacağı
çıkarılır:

```
FBX  →  her panel için delikleri çıkar  →  deliği hacmine göre sınıflandır
     →  aynı sınıftaki deliklerin BİRBİRİNE GÖRE KONUMUNDAN parçayı türet
     →  adet  →  gram  →  JSON
```

İki katmanlı bir çıkarım var:

| Katman | Soru | Örnek |
|---|---|---|
| **Hacim** | Bu delik ne tipi? | 9680 mm³ → linco deliği |
| **Desen** | Bu delikler birlikte ne oluşturuyor? | 192 mm arayla 2 delik → kulp |

Bazı parçalar hiç delik gerektirmez; onlar **türetme** ile gelir (Allen, Tıpa, Kulp
Vidası, Askılık Borusu). Bir parça da geometriden değil, panelin **kalınlığından**
bulunur (Arkalık Çivisi).

---

## ⚠️ En kritik tuzak: iki ayrı ölçek

Kodda **iki farklı koordinat uzayı** iç içe kullanılıyor. Bunu bilmeden hiçbir sabit
anlam ifade etmez:

| Uzay | Nasıl elde edilir | Birim | Nerede kullanılır |
|---|---|---|---|
| **Yerel (mesh)** | `obj.data.vertices` (ham) | **mm** | Delik hacimleri (`CATEGORIES`), panel kalınlığı, arkalık W×H |
| **Dünya** | `matrix_world @ ...` | **1 birim = 1000 mm** | Tüm merkez/mesafe hesapları (kulp, ray, ayak, uzun pim) |

Bu yüzden:
- Linco deliği `9680.0` yazar → **9680 mm³** (yerel).
- Kulp mesafesi `0.192` yazar → **192 mm** (dünya).
- `RAY_SCALE_MM = 1000` ve `AYAK_SCALE_MM = 1000` sabitlerinin tek işi dünya
  mesafesini mm'ye çevirmektir.
- `ARKALIK_MAX_KALINLIK = 8.0` → **8 mm** (yerel), çünkü kalınlık yerel uzayda ölçülür.

Yeni bir sabit eklerken önce "bu değer hangi uzaydan geliyor?" sorusunu cevapla.

---

## Boru hattındaki sıra (`count_order`, satır 868-1033)

Sıra **önemlidir** — bazı algoritmalar bir öncekinin havuzundan artakalanı kullanır.

```
1. Tüm mesh'leri kalınlığa göre ikiye ayır          (satır 886-894)
   ├─ ince (≤8 mm) → ARKALIK adayı  ─→ [13] Arkalık Çivisi
   └─ kalın        → delik taraması yapılacak panel

2. Her kalın panel için:
   ├─ [01] Çift-boolean ile delikleri çıkar
   ├─ [01] Her deliği hacmine göre sınıflandır
   │       linco / pim / ahsapcivisi / rafpimi / modulbaglanti / menteseTabani / ray
   ├─ [07] modulbaglanti havuzundan KULP çiftlerini ayır
   │       └─ artakalan → global modül bağlantı havuzuna
   ├─ [09] ahsapcivisi havuzundan AYAK dikdörtgenlerini ayıkla
   ├─ [11] ray havuzunda RAY desenlerini ara
   └─ [12] ahsapcivisi havuzunda EŞKENAR ÜÇGEN (flanş) ara

3. Tüm parçalar bittikten sonra (global):
   ├─ [08] modül bağlantı çiftleri (parçalar arası)
   └─ [06] uzun linco pimi (parçalar arası)

4. [15] Türetmeler + gram hesabı
```

### Havuz izolasyonu

Aynı deliğin iki kez sayılmaması için havuzlar ayrılmıştır:

| Havuz | Kim tüketir | Not |
|---|---|---|
| `modulbaglanti` | önce **kulp**, artakalan **modül bağlantı** | Kulp önce gelir |
| `ahsapcivisi` | **ayak**, **flanş** — ama havuzdan DÜŞMEZ | Ayak vidaları ağaç vidası olarak da sayılır |
| `RAY_DELIK_HACIM` | sadece **ray** | `ahsapcivisi` ile kesişmez (bilerek) |
| `linco` | **linco ailesi** + **uzun pim** | Uzun pim sadece dübeli azaltır |

Ray havuzunun ayrılması tarihsel bir düzeltmedir — bkz. [11-ray-seti.md](11-ray-seti.md).

---

## Dosya haritası

| # | Dosya | Bulduğu parçalar |
|---|---|---|
| 01 | [delik-cikarma-cift-boolean](01-delik-cikarma-cift-boolean.md) | *(altyapı)* tüm deliklerin çıkarılması ve sınıflandırılması |
| 02 | [delik-yonu-tespiti](02-delik-yonu-tespiti.md) | *(altyapı)* deliğin hangi yöne açıldığı |
| 03 | [mentese-tabani](03-mentese-tabani.md) | Menteşe Tabanı, Frenli Menteşe, Frensiz Menteşe |
| 04 | [raf-pimi](04-raf-pimi.md) | Raf Pimi |
| 05 | [linco-ailesi](05-linco-ailesi.md) | Linco Gövde, Linco Kapak, Linco Dübel, Minifix |
| 06 | [uzun-linco-pimi](06-uzun-linco-pimi.md) | Uzun Linco Pimi (L Modül) |
| 07 | [kulp](07-kulp.md) | Kulp, Kulp Vidası |
| 08 | [modul-baglanti](08-modul-baglanti.md) | Modülleri Birbirine Bağlama |
| 09 | [ayarli-ayak](09-ayarli-ayak.md) | Ayarlı Ayak, Allen, Tıpa |
| 10 | [agac-vidasi](10-agac-vidasi.md) | Ağaç Vidası |
| 11 | [ray-seti](11-ray-seti.md) | Ray Seti (boy bazında) |
| 12 | [askilik-flansi](12-askilik-flansi.md) | Askılık Flanşı, Askılık Borusu |
| 13 | [arkalik-civisi](13-arkalik-civisi.md) | Arkalık Çivisi |
| 14 | [renk-tespiti](14-renk-tespiti.md) | Linco/Tıpa rengi |
| 15 | [gram-ve-sabit-turetmeler](15-gram-ve-sabit-turetmeler.md) | L Bağlantı Seti, gram hesapları |

---

## Sistemin şu anki doğruluğu

2026-07-29 tarihli referans BoM karşılaştırmasına göre (bkz.
`Efforts/otonom_kit/Farkların Tablosu.md`) 10 sipariş üzerinden:

| Durum              | Parçalar                                                                      |
| ------------------ | ----------------------------------------------------------------------------- |
| ✅ **Tam tutuyor**  | Menteşe Tabanı, Frenli/Frensiz Menteşe, Modül Bağlantı, Askılık Flanşı/Borusu |
| 🟡 **Küçük sapma** | Linco ailesi (−25/−37), Raf Pimi (−2), Kulp (−1), Ayarlı Ayak (−2), Ray (−1)  |
| 🔴 **Büyük sapma** | Arkalık Çivisi (−502), Ağaç Vidası (−90)                                      |
| ⛔ **Hiç yok**      | Çivili Ayak (−44) — sistemde bu parça için kod yok                            |

Her algoritma dosyasının sonunda o parçanın **"Bilinen zayıflık"** bölümü var.
