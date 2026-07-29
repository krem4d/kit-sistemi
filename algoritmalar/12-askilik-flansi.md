# 12 — Askılık Flanşı ve Askılık Borusu

| | |
|---|---|
| **Kod** | `count_equilateral_flanges()` — satır 552-579<br>`_triangle_angles()` — satır 543-549 |
| **Girdi** | Parça bazında **tüm** `ahsapcivisi` merkezleri (ayak vidaları dahil) |
| **Ürettiği parçalar** | Askılık Flanşı, Askılık Borusu |
| **Doğruluk** | ✅ 10 siparişte **tam tutuyor** (Flanş 2/2, Boru 1/1) |

---

## Problem

Askılık borusu, dolabın içine iki flanşla monte edilir. Flanş yuvarlak bir plakadır
ve **3 vidayla** tutturulur — bu 3 vida **eşkenar üçgen** oluşturur (~120° aralıklarla
yerleştirilmiş delikler).

Vida delikleri ağaç vidasıyla aynı hacimde, yani ayrım yine geometriden: paneldeki
vidalar arasında **eşkenar üçgen** arıyoruz.

---

## Algoritma

```
Girdi: bir paneldeki tüm ahsapcivisi merkezleri

n < 3  →  0 dön                                            :556-557

Her (i,j,k) üçlüsü için (hiçbiri kullanılmamışsa):         :561-578

  a = |merkez_i − merkez_j|
  b = |merkez_j − merkez_k|
  c = |merkez_k − merkez_i|

  ┌ TEST 1 — kenarlar eşit mi?                             :567-572
  │   dmin, dmax = min(a,b,c), max(a,b,c)
  │   dmin ≤ 1e-6  →  ele (çakışık nokta)
  │   dmax/dmin − 1 > %2  →  ele
  └

  ┌ TEST 2 — açılar 60° civarında mı?                      :574-576
  │   açılar = _triangle_angles(a, b, c)      (kosinüs teoremi)
  │   herhangi bir açı < 59° veya > 61°  →  ele
  └

  → GEÇTİ: üç deliği KULLANILDI işaretle, flanges++
```

### Neden iki test?

Matematiksel olarak kenarları eşit olan üçgenin açıları zaten 60°'dir — Test 2
gereksiz görünür. Ama:

- Test 1 **bağıl** (%2 oran), Test 2 **mutlak** (±1°).
- Küçük bir üçgende %2'lik kenar sapması, açıda 1°'den fazla oynayabilir.
- İkisi birlikte, hem küçük hem büyük üçgenlerde tutarlı bir sıkılık sağlıyor.

Ucuz bir çifte doğrulama; yanlış pozitifi düşürüyor.

### Kosinüs teoremi (`_triangle_angles`)

```python
def ang(opp, s1, s2):
    cosv = (s1² + s2² − opp²) / (2·s1·s2)
    cosv = clamp(cosv, −1, 1)               # sayısal taşmaya karşı
    return degrees(acos(cosv))
```

`clamp` şart: kayan nokta hatası `cosv`'yi 1.0000000002 yapabilir, `acos` o zaman
`ValueError` fırlatır.

---

## Türetme: Askılık Borusu

```python
askilik_borusu = askilik_flansi // 2                       # :980
```

Bir borunun iki ucunda birer flanş var → **2 flanş = 1 boru**.

Gerçek veri (9364-1): flanş 2 → boru 1. Referans BoM aynı. ✅

---

## Sabitler (satır 161-163)

| Sabit | Değer | Anlamı |
|---|---|---|
| `FLANS_KENAR_TOL` | 0.02 | Kenarlar %2 içinde eşit |
| `FLANS_ACI_LO` | 59.0 | Açı alt sınırı (derece) |
| `FLANS_ACI_HI` | 61.0 | Açı üst sınırı (derece) |

> Dikkat: flanşın **kenar uzunluğu** hiçbir yerde tanımlı değil. Algoritma sadece
> "eşkenar" arıyor, "şu boyutta eşkenar" değil. Herhangi bir boyutta eşkenar üçgen
> flanş sayılır.

---

## Havuz etkileşimi

Flanş araması `remaining_ahsap` üzerinde çalışıyor (satır 956) — bu,
[09 — Ayarlı Ayak](09-ayarli-ayak.md)'ta ayrılıp geri birleştirilen **tam liste**:

```python
remaining_ahsap = ayak_noktalari + ayak_disi               # :950
askilik_flansi += count_equilateral_flanges(remaining_ahsap)   # :956
```

Yani **ayak vidaları da flanş aramasına giriyor**. Pratikte sorun değil: ayağın 4
vidası 32×40 dikdörtgen oluşturur, dikdörtgenin hiçbir üçlüsü eşkenar olamaz
(32-40-51.22 üçgeni eşkenar değil). Ama bu bir tesadüf, kasıtlı bir koruma değil.

Flanş delikleri de ağaç vidası havuzundan **düşmüyor** — kitte gönderilen ağaç
vidası sayısına dahil kalıyorlar.

---

## Bilinen zayıflıklar

**1. Boyut kontrolü yok.**
Herhangi bir ölçekte eşkenar üçgen flanş sayılır. Panelde tesadüfen eşkenar dizilmiş
3 yapısal vida varsa yanlış flanş üretir. Şu ana kadar görülmedi (10 siparişte tam
tutuyor), ama flanşın gerçek kenar uzunluğu ölçülüp bir aralık eklenirse algoritma
belirgin şekilde sağlamlaşır.

**2. Karmaşıklık O(n³).**
Bir panelde 12 vida varsa 220 üçlü, 50 vida varsa 19600 üçlü. Panel başına vida
sayısı artarsa yavaşlar.

**3. Greedy — ilk bulunan üçlü kilitleniyor.**
FBX'teki delik sırasına bağlı. En iyi uyanı seçmiyor (karşılaştır:
[09 — Ayarlı Ayak](09-ayarli-ayak.md) sapmaya göre sıralıyor).

**4. Tek sayıda flanşta kalan yutulur.**
`3 // 2 = 1` — 3 flanş bulunursa 1 boru üretilir, artan flanş sessizce kaybolur.
Uyarı basılmıyor.

**5. Test verisi çok az.**
10 siparişten sadece 1'inde (9364-1) flanş var. "Tam tutuyor" değerlendirmesi tek bir
gözleme dayanıyor — güvenilir bir doğrulama değil.
