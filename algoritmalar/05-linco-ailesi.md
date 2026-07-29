# 05 — Linco Ailesi (Gövde, Kapak, Dübel, Minifix)

| | |
|---|---|
| **Kod** | `count_order()` satır 920-923 (sayım), 966-967, 992-995 (türetme) |
| **Girdi** | `linco` hacim havuzu (9680.0 mm³, %5) |
| **Ürettiği parçalar** | Linco Gövde, Linco Kapak, Linco Dübel, Minifix |
| **Doğruluk** | 🟡 10 siparişte Gövde/Kapak/Minifix **−25**, Dübel **−37** |

---

## Problem

"Linco" bir eksantrik bağlantı sistemidir — iki paneli birbirine kilitler. Tek bir
bağlantı noktası için **dört ayrı parça** gerekir:

| Parça | Nereye gider |
|---|---|
| Linco Gövde | Panel A'daki büyük yuvaya oturur (eksantrik göbek) |
| Linco Kapak | Gövdenin üstünü kapatan görünür plastik kapak |
| Linco Dübel | Panel B'ye çakılan, gövdeye giren pim |
| Minifix | Vidalı bağlantı elemanı |

Hepsi **1:1 oranında** — bir linco yuvası = her birinden bir tane.

---

## Algoritma

```
1. Delik sınıflandırma sırasında:                          :920-923
     cat == "linco"  →  counts["linco"]++
                        part_linco_holes.append(
                            (world_center(delik),
                             hole_signed_direction(panel, delik))   # [06] için
                        )

2. Türetme:                                                :966-967, 992-995
     linco       = counts["linco"]
     linco_dubel = linco - 2 * uzun_linco_pim

     Linco Gövde = linco
     Linco Kapak = linco
     Minifix     = linco
     Linco Dübel = linco_dubel
```

Yani **Gövde = Kapak = Minifix = ham delik sayısı**, hiçbir düzeltme yok. Tek istisna
Dübel'dir.

### Dübel neden farklı?

İki modül yan yana geldiğinde, birbirine dayanan panellerdeki linco delikleri arasına
normal dübel yerine **tek bir uzun linco pimi** konur. O pim iki deliğe birden hizmet
eder, dolayısıyla **2 dübel eksilir**:

```
linco_dubel = linco − 2 × uzun_linco_pim
```

Uzun pimin nasıl bulunduğu ayrı bir algoritma:
[06-uzun-linco-pimi.md](06-uzun-linco-pimi.md).

### Gerçek veriden (9364-2)

```
ham linco delik    = 55
uzun linco pim     = 15
→ Gövde/Kapak/Minifix = 55
→ Dübel               = 55 − 2×15 = 25
```

Referans BoM: Gövde/Kapak/Minifix 60, Dübel 42, uzun pim 20.
Yani hem ham sayım 5 eksik, hem de uzun pim 5 eksik → dübel farkı büyüyor (−17).

---

## Çapraz kontrol: `pim` kategorisi

`CATEGORIES` içinde `pim: 936.0` diye ikinci bir kategori var — bu **linco dübelinin
kendi deliği**. Teorik olarak `counts["pim"] ≈ counts["linco"]` olmalı.

Kod bu eşitliği **kontrol etmiyor**, sadece `_ham` altında JSON'a yazıyor:

```json
"_ham": { "linco": 31, "pim": 27, ... }
```

9355'te linco=31 ama pim=27 → **4 delik uyuşmazlığı**, hiçbir uyarı basılmıyor.

> ⚠️ Bu, sistemdeki en kolay kazanç. `linco` ile `pim` arasındaki fark, linco
> sayımındaki eksiğin doğrudan göstergesi. Neredeyse her siparişte `pim < linco`
> ve referansla farkımız da tam bu yönde. Bir uyarı satırı, Linco ailesindeki
> −25/−37 sapmasını anında teşhis edilebilir yapardı.

Gerçek verideki durum:

| Sipariş | `linco` | `pim` | Fark | Referans linco |
|---|---|---|---|---|
| 9355 | 31 | 27 | −4 | 33 |
| 9356 | 19 | 17 | −2 | 21 |
| 9359 | 23 | 23 | 0 | 25 |
| 9363 | 65 | 53 | −12 | 68 |
| 9364-2 | 55 | 23 | −32 | 60 |

---

## Bilinen zayıflıklar

**1. `pim` çapraz kontrolü hesaplanıyor ama kullanılmıyor.**
Yukarıda açıklandı. Ölçülüyor, JSON'a yazılıyor, hiç okunmuyor.

**2. Ham linco sayımı sistematik olarak 1-5 eksik.**
10 siparişin 9'unda referanstan az. Sebebi delik tespitinde olmalı (hacim toleransı,
boolean başarısızlığı veya kenar deliklerinin ayrık mesh olmaması). `linco` hacmi
9680 ama `hacimler.md` gözlemi **9646–9776** aralığı diyor — %5 tolerans bandı
[9196, 10164] olduğu için bu aralık kapsanıyor, yani sebep tolerans değil.

**3. Renk ayrımı burada yapılmıyor.**
Referans BoM "Linco Gövde (BEYAZ)" ve "Linco Gövde (GRİ)" diye iki satır tutuyor.
Sistem tek sayı üretip rengi ayrı bir alandan (`renk`) veriyor — bkz.
[14-renk-tespiti.md](14-renk-tespiti.md).

**4. Minifix'in ayrı deliği aranmıyor.**
Minifix, linco sayısına eşit varsayılıyor. Kendi deliği varsa ve o delik
sayılmıyorsa bu varsayım sessizce yanlış olabilir.
