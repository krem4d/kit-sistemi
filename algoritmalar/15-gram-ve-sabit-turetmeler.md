# 15 — Sabit Türetmeler ve Gram Hesabı

| | |
|---|---|
| **Kod** | `count_order()` satır 966-1020 |
| **Girdi** | Diğer tüm algoritmaların çıktısı |
| **Ürettiği parçalar** | L Bağlantı Seti + tüm gram değerleri |

---

## Türetme zinciri

Sistemde **hiç delik gerektirmeyen**, tamamen başka bir sayıdan hesaplanan kalemler:

```
ayak ──┬─→ Allen           = 1 if ayak ≥ 1 else 0          :998
       └─→ Tıpa            = ayak                          :999

kulp ────→ Kulp Vidası     = 2 × kulp                      :1001

flanş ───→ Askılık Borusu  = flanş // 2                    :980

linco ─┬─→ Linco Gövde     = linco                         :992
       ├─→ Linco Kapak     = linco                         :993
       ├─→ Minifix         = linco                         :995
       └─→ Linco Dübel     = linco − 2×uzun_pim            :967

mentese ─→ Frensiz         = toplam − frenli               :970

(sabit) ─→ L Bağlantı Seti = 2                             :972
```

Tam bağımlılık haritası:

| Kalem | Kaynak | Formül |
|---|---|---|
| Frensiz Menteşe | Menteşe Tabanı | `toplam − frenli` |
| Linco Gövde/Kapak/Minifix | linco deliği | `= linco` |
| Linco Dübel | linco + uzun pim | `linco − 2×pim` |
| Allen | Ayarlı Ayak | `1 if ayak ≥ 1 else 0` |
| Tıpa | Ayarlı Ayak | `= ayak` |
| Kulp Vidası | Kulp | `2 × kulp` |
| Askılık Borusu | Askılık Flanşı | `flanş // 2` |
| Ağaç Vidası | ahsapcivisi + L + ray | `sayım + 4×L − ray_delik` |
| L Bağlantı Seti | — | sabit `2` |

---

## L Bağlantı Seti — tek gerçek sabit

```python
L_BAGLANTI_ADET = 2          # satır 156
l_baglanti = L_BAGLANTI_ADET # satır 972
```

Her sipariş için **sabit 2** kabul ediliyor. Modelden tespit edilmiyor.

İki yere etki ediyor:
1. Doğrudan `"L Bağlantı Seti": 2` olarak çıktıya
2. Ağaç vidası hesabına `+ 4 × 2 = +8`

### Referansla karşılaştırma

| Sipariş | Bizim | Referans |
|---|---|---|
| Çoğu | 2 | 2 ✅ |
| 9364-2 | 2 | **3** ❌ |
| 9360 (1+2) | **4** | 4 ✅ |

9360'ta doğru çıkması **tesadüf** — sipariş iki FBX'e bölündüğü için her biri 2
üretti, toplam 4 oldu ve referans da 4 diyordu. Bölünmemiş olsaydı 2 çıkardı.

> ⚠️ Aynı sorun `Allen` için **hata üretiyor**: 9360'ta 2 Allen çıktı, referans 1.
> Bkz. [09-ayarli-ayak.md](09-ayarli-ayak.md).
>
> **Kök sorun:** sipariş bazlı sabitler **FBX bazlı** uygulanıyor. Bir sipariş
> birden fazla FBX'e bölündüğünde sabitler çarpılıyor. Şu an bu iki kalemi
> (`L_BAGLANTI_ADET`, `Allen`) etkiliyor.

---

## Gram hesabı

```python
def gr(n, w):                                              # :1009
    return round(n * w, 1)
```

Basit çarpım, 1 ondalığa yuvarlama.

### Birim ağırlıklar (satır 215-223, kaynak `Ağırlıklar.md`)

| Anahtar | Gram | Parça |
|---|---|---|
| `rafpimi` | 2.7 | Raf Pimi |
| `ahsapcivisi` | 1.108 | Ağaç Vidası |
| `minifix` | 3.401 | Minifix |
| `lincodubel` | 4.4 | Linco Dübel |
| `linco` | 4.631 | Linco Gövde |
| `lincokapak` | 0.216 | Linco Kapak |
| `civi` | 0.335 | Arkalık Çivisi |

### Hesaplanan gramlar (satır 1012-1020)

```python
gram = {
    "Raf Pimi":    raf_pimi     × 2.7,
    "Ağaç Vidası": agac_vidasi  × 1.108,
    "Minifix":     linco        × 3.401,
    "Linco Dübel": linco_dubel  × 4.4,      ← uzun pim düşülmüş sayı
    "Linco":       linco        × 4.631,
    "Linco Kapak": linco        × 0.216,
    "Çivi":        arkalik_civi × 0.335,
}
```

### Doğrulama (9355)

```
Raf Pimi    12 × 2.7    = 32.4   ✅ JSON'da 32.4
Ağaç Vidası 48 × 1.108  = 53.18  → 53.2  ✅
Minifix     31 × 3.401  = 105.43 → 105.4 ✅
Linco Dübel 31 × 4.4    = 136.4  ✅
Linco       31 × 4.631  = 143.56 → 143.6 ✅
Linco Kapak 31 × 0.216  = 6.696  → 6.7   ✅
Çivi        46 × 0.335  = 15.41  → 15.4  ✅
```

Referans BoM 9355 için: raf pimi 27.7, ağaç vidası 60.2, minifix 107.7, dübel 143.6,
linco kapak 7.3, linco 155.6, çivi 38.

Farklar tamamen **adet farklarından** geliyor — birim ağırlıklar doğru, çarpma
doğru. Gram hesabı bir hata kaynağı değil.

> Not: referansta "Dübel gram (D) 143.6" ile bizim "Linco 143.6" aynı sayı — ama
> bunlar farklı kalemler. Referansın sütun eşleşmesi (A-F harfleri) bizim JSON
> anahtarlarımızla birebir örtüşmüyor; karşılaştırırken harflere değil isimlere
> bakmak gerekiyor.

---

## Gram hesabı neden sadece 7 kalem için var

BoM'un üst kısmındaki gram tablosu yalnızca **dökme gönderilen** parçalar için:
vida, çivi, pim gibi tartılarak sayılan malzemeler. Menteşe, kulp, ray gibi adet
bazında gönderilen parçaların gramı hesaplanmıyor — gerek yok.

---

## Bilinen zayıflıklar

**1. Sipariş bazlı sabitler FBX bazlı uygulanıyor (yukarıda).**
`L_BAGLANTI_ADET` ve `Allen`. Çözüm: sabitleri sipariş numarasının kök kısmına
(`9360-1` → `9360`) göre bir kez uygulamak; bu, `pdf_uret.py` tarafında birleştirme
gerektirir.

**2. `L Bağlantı Seti = 2` doğrulanmamış.**
Kod yorumu "şimdilik" diyor, `parca_kurallari.md` "🟡 geçici" işaretlemiş. 9364-2'de
3 olması gerekiyordu — yani gerçekten değişken bir kalem.

**3. Gram yuvarlaması her kalemde ayrı.**
`round(n × w, 1)` — toplam alınırken yuvarlama hataları birikir. Şu an toplam
hesaplanmadığı için sorun değil.

**4. `WEIGHTS` sözlüğünde kullanılmayan anahtar yok ama eksik var.**
7 ağırlık tanımlı, 7'si de kullanılıyor. Ancak Menteşe Tabanı, Kulp, Ray gibi
kalemler için ağırlık yok — ileride toplam kit ağırlığı istenirse eklenmesi gerekir.
