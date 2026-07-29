# 03 — Menteşe Tabanı, Frenli ve Frensiz Menteşe

|                       |                                                   |
| --------------------- | ------------------------------------------------- |
| **Kod**               | `count_order()` satır 926-927, 953-954, 968-970   |
| **Girdi**             | `menteseTabani` hacim havuzu (11454.0131 mm³, %5) |
| **Ürettiği parçalar** | Menteşe Tabanı, Frenli Menteşe, Frensiz Menteşe   |
| **Doğruluk**          | ✅ 10 siparişte 10/10 **tam tutuyor**              |

---

## Problem

Bir dolapta iki tip menteşe kullanılır:

- **Frenli menteşe** — yavaş kapanan, pahalı. Her kapağa **bir tane** yeter.
- **Frensiz menteşe** — normal, ucuz. Kapağın kalan menteşe noktalarına takılır.

FBX'te ikisi de **aynı yuvayı** açar — geometrik olarak ayırt edilemezler. Tek bilgi:
bir kapakta kaç yuva olduğu.

---

## Algoritma

Kural şu iş bilgisine dayanır: **her kapağa 1 frenli menteşe konur, gerisi frensizdir.**
Panel = kapak olduğuna göre:

```
1. Delik sınıflandırma sırasında:                          :926-927
     cat == "menteseTabani"  →  counts["menteseTabani"]++
                                part_mentese++            (bu paneldeki sayaç)

2. Panel bitince:                                          :953-954
     part_mentese > 0  →  parts_with_mentese++            (panel sayacı)

3. Türetme:                                                :968-970
     mentese_tabani = counts["menteseTabani"]      # toplam yuva
     frenli         = parts_with_mentese           # menteşeli PANEL sayısı
     frensiz        = mentese_tabani - frenli      # kalan
```

Yani:

| Kalem | Formül | Anlamı |
|---|---|---|
| Menteşe Tabanı | toplam yuva sayısı | Her yuvaya 1 taban |
| Frenli Menteşe | **menteşe yuvası olan panel sayısı** | Kapak başına 1 |
| Frensiz Menteşe | toplam − frenli | Geri kalan |

### Örnek

3 kapaklı bir dolap, kapak başına 2 menteşe:

```
Panel A: 2 yuva  ┐
Panel B: 2 yuva  ├─ toplam 6 yuva, 3 panel
Panel C: 2 yuva  ┘

Menteşe Tabanı = 6
Frenli         = 3      (3 panelde de en az 1 yuva var)
Frensiz        = 6 − 3 = 3
```

Gerçek veriden doğrulama (9359): `menteseTabani` ham = 10, frenli = 4, frensiz = 6 —
yani 4 kapak, biri 4 yuvalı. Referans BoM da 4/6 diyor. ✅

---

## Neden bu kadar iyi çalışıyor

Bu, sistemdeki **en sağlam** algoritma çünkü:

1. Menteşe yuvası hacmi çok büyük (11454 mm³) ve benzersiz — başka hiçbir deliğe
   yakın değil, hacim çakışması riski yok.
2. Türetme **saf sayma** — geometrik desen eşleştirmesi, tolerans penceresi, greedy
   eşleştirme yok. Bu üçü sistemdeki diğer hataların ana kaynağı.
3. `frenli + frensiz == mentese_tabani` özdeşliği yapısal olarak garanti — sayım
   hatası olsa bile toplam tutarlı kalır.

---

## Bilinen zayıflıklar

**1. "Panel = kapak" varsayımı denetlenmiyor.**
Menteşe yuvası açılmış bir panel otomatik olarak kapak sayılıyor. Gövdeye açılan bir
menteşe yuvası (varsa) yanlışlıkla bir frenli menteşe daha üretir. Şu ana kadar gerçek
veride böyle bir durum çıkmadı.

**2. Bölünmüş siparişlerde panel sayısı doğru ama sipariş toplamı şişebilir.**
9360 gibi iki FBX'e bölünmüş siparişlerde her FBX ayrı işlendiği için her ikisi de
kendi frenli menteşesini üretir. Menteşede bu doğrudur (gerçekten iki ayrı modül),
ama aynı mantık **Allen**'da hataya yol açıyor — bkz.
[09-ayarli-ayak.md](09-ayarli-ayak.md) → "Bilinen zayıflıklar".

**3. Tek yuvalı kapak → 1 frenli, 0 frensiz.**
Formül gereği doğru, ama gerçekte tek menteşeyle kapak takılmaz. Böyle bir sonuç
çıkarsa tespitte eksik yuva var demektir — bir uyarı eşiği faydalı olurdu.
