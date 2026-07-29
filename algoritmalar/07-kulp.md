# 07 — Kulp ve Kulp Vidası

| | |
|---|---|
| **Kod** | `detect_kulp_pairs()` — satır 403-423 |
| **Girdi** | Parça bazında `modulbaglanti` hacimli delik merkezleri (351.35 mm³, %5) |
| **Ürettiği parçalar** | Kulp, Kulp Vidası |
| **Doğruluk** | 🟡 10 siparişte **−1** (27 / 28) — sadece 9364-2'de kayıp |

---

## Problem

Kulp (tutamak) ile modül bağlantı aparatı **aynı hacimde delik açar** (351.35 mm³).
Hacim ikisini ayırt edemez. Ayrım tek yerden gelir: **delikler arası mesafe**.

| Parça | Delik çifti mesafesi |
|---|---|
| **Kulp** | 192 mm (standart kulp delik aralığı) |
| **Modül bağlantı** | 18 mm |

Bu yüzden `modulbaglanti` havuzu iki tüketiciye sırayla veriliyor: **önce kulp**,
artakalan **modül bağlantıya**.

---

## Algoritma

```
Girdi: bir PANELDEKİ modulbaglanti delik merkezleri

1. Pencere hesapla:                                        :407-408
     lo = 192 mm × 0.95 = 182.4 mm
     hi = 192 mm × 1.05 = 201.6 mm

2. Greedy eşleştirme:                                      :411-421
     her i için (kullanılmamışsa):
       her j > i için (kullanılmamışsa):
         d = |merkez_i − merkez_j|
         lo ≤ d ≤ hi  →  ikisini KULLANILDI işaretle
                          kulp_adet++
                          break        ← ilk uyanla eşleş, devam etme

3. Dön: (kulp_adet, eşleşmeyen merkezler)                  :422-423
```

Eşleşmeyen merkezler `modulbag_centers` global havuzuna gider ve
[08 — Modül Bağlantı](08-modul-baglanti.md) tarafından değerlendirilir.

### Neden panel bazında?

Kulp tek bir kapağa takılır — iki deliği de **aynı panelde**dir. Bu yüzden
`detect_kulp_pairs` her panel için ayrı çağrılır (satır 935). Modül bağlantı ise
**iki ayrı paneli** birleştirir, o yüzden global havuzda aranır.

Bu ayrım hem doğru hem hızlı: panel içi arama, tüm sahneyi taramaktan çok daha ucuz.

---

## Türetme: Kulp Vidası

```python
"Kulp Vidası": 2 * kulp,                                   # :1001
```

Her kulpun 2 vidası var — sabit, doğrulanmamış ama referans BoM ile tutarlı
(9355: kulp 4 → vida 8 ✅).

---

## Sabitler (satır 80-81)

| Sabit | Değer | Anlamı |
|---|---|---|
| `KULP_DELIK_MESAFE` | 0.192 | 192 mm (dünya uzayı) |
| `KULP_DELIK_TOL` | 0.05 | ±%5 → [182.4, 201.6] mm |

> **Kalibrasyon çıpası:** Bu değer sistemdeki ölçek dönüşümünün de kaynağı.
> Kulp deliği modelde `0.192` birim, gerçekte `192 mm` → **1 birim = 1000 mm**.
> `RAY_SCALE_MM` ve `AYAK_SCALE_MM` sabitleri bu gözlemden geliyor.

---

## Bilinen zayıflıklar

**1. `break` ilk uyanla eşleştiriyor, en yakınla değil (satır 421).**
Üç delik 192 mm civarında sıralanmışsa, `i` en yakın olanla değil **indeks sırasında
ilk gelen** ile eşleşir. Delik sırası FBX'ten geldiği için bu keyfi. Pratikte kulp
delikleri ikişerli net gruplandığından sorun çıkmadı.

**2. Tek bir mesafe standardı var.**
192 mm dışında bir kulp aralığı (128 mm, 160 mm yaygın standartlar) kullanılan bir
modül gelirse hiç tespit edilmez ve o delikler **modül bağlantı havuzuna düşer** —
yani sadece kulp kaybolmaz, modül bağlantı da yanlış artabilir.

**3. 9364-2'de kulp 0 çıktı, referans 1.**
Bu siparişte Ayarlı Ayak, Allen, Tıpa, Kulp, Kulp Vidası'nın **hepsi** sıfır. Tek
kalemin değil, bir grubun birden düşmesi, o modülün geometrisinin tanınmadığını
gösteriyor — muhtemelen delik tespiti aşamasında (`execute_double_boolean`) bir
panelde başarısızlık var. Kodda o durumda sadece uyarı basılıp `continue` ediliyor
(satır 903-905), sipariş yine de "başarılı" yazılıyor.

> ⚠️ `[UYARI] ... delik taraması başarısız` satırı JSON'a yazılmıyor. Bir panelin
> tamamen atlandığı, çıktıya bakınca anlaşılamıyor.
