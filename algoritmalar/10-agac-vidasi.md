# 10 — Ağaç Vidası

| | |
|---|---|
| **Kod** | `count_order()` satır 918-919 (sayım), 950-951, 976-979 (türetme) |
| **Girdi** | `ahsapcivisi` hacim havuzu (14.57 mm³, %5) |
| **Ürettiği parça** | Ağaç Vidası |
| **Doğruluk** | 🔴 10 siparişte **−90** (438 / 528) — ikinci en büyük sapma |

---

## Problem

Ağaç vidası, kitte **dökme** gönderilen genel bağlantı elemanı. Sayısı doğrudan
delik sayısına eşit değil — bazı vidalar delik gerektirmeyen yerlere de gidiyor
(L bağlantı setleri), bazı delikler ise başka bir parçanın kapsamında.

---

## Algoritma

```
1. Delik sınıflandırma:                                    :918-919
     cat == "ahsapcivisi"  →  part_ahsap_centers.append(merkez)

2. Panel bitince — ayak ayıklaması (havuzdan DÜŞMEZ):      :941, 950-951
     ayak, ayak_noktalari, ayak_disi = extract_ayak_feet(part_ahsap_centers)
     remaining_ahsap = ayak_noktalari + ayak_disi     ← hepsi geri birleşiyor
     counts["ahsapcivisi"] += len(remaining_ahsap)

3. Türetme:                                                :976-979
     ray_delik_toplam = Σ len(RAY_HOLE_POSITIONS[boy])  for boy in ray_isimleri

     agac_vidasi = counts["ahsapcivisi"]        # sayılan tüm vida delikleri
                 + 4 * l_baglanti               # L bağlantı başına 4 vida (= +8)
                 − ray_delik_toplam             # ray deliklerini düş   ⚠️
```

| Terim | Değer | Gerekçe |
|---|---|---|
| `counts["ahsapcivisi"]` | ölçülen | Panellerde bulunan vida delikleri (ayak dahil) |
| `+ 4 × 2` | +8 | Her L bağlantı seti 4 vida kullanır, set sayısı sabit 2 |
| `− ray_delik_toplam` | değişken | Ray vidaları ray setiyle birlikte geliyor sayılıyor |

---

## ⚠️ Üçüncü terimde bir tutarsızlık var

Kodun kendi yorumu (satır 973-976) şöyle diyor:

> *"Ray'lerde kullanılan delik sayısı (RAY_DELIK_HACIM havuzundan, **ahsapcivisi
> havuzuna hiç girmedi** — ama ray varsa o rayların delikleri de birer vidayla
> kapatıldığından, genel ağaç vidası adedinden düşülür)."*

Bu yorumun iki yarısı **birbiriyle çelişiyor**:

1. Ray delikleri `ahsapcivisi` havuzuna **hiç girmedi** — doğru. Ray delikleri
   `RAY_DELIK_HACIM` (84.92 mm³) bandında, `match_category()` onları `None`
   döndürüyor, ayrı havuza gidiyorlar (satır 928-931). `counts["ahsapcivisi"]`
   içinde **hiç yoklar**.

2. Ama sonra o sayı `counts["ahsapcivisi"]`'den **çıkarılıyor**.

Havuza hiç girmemiş bir sayıyı havuzdan çıkarmak, **gerçek ağaç vidalarını siler**.

Ayrıca yorumun gerekçesi (*"delikleri de birer vidayla kapatıldığından"*) mantıken
**eklemeyi** savunuyor, çıkarmayı değil.

### Sayısal etkisi

```
9364-1:  ray_setleri = {"45cm": 2}
         ray_isimleri = ["45cm", "45cm"]
         RAY_HOLE_POSITIONS["45cm"] → 3 delik
         ray_delik_toplam = 3 + 3 = 6

         Bizim sonuç : 46      (referans 65)
         Çıkarma olmasaydı: 52
```

Yani bu tek satır 9364-1'de 6 vida siliyor. Ray bulunan siparişlerde (9363, 9364-1)
farkın bir kısmı buradan geliyor. Ray bulunmayan siparişlerde `ray_delik_toplam = 0`
olduğu için etkisiz — bu yüzden fark tutarsız görünüyor.

> **Bu bir varsayım değil, koddan doğrulanabilir bir tutarsızlık.** Ray havuzunun
> `ahsapcivisi`'nden ayrılması sonradan yapılan bir düzeltmeydi (bkz.
> [11-ray-seti.md](11-ray-seti.md)); bu çıkarma satırı **eski durumdan kalmış**
> olmalı — o zaman ray delikleri gerçekten `ahsapcivisi` havuzundaydı ve çıkarma
> doğruydu.

---

## Sabitler

| Sabit | Değer | Nerede |
|---|---|---|
| `ahsapcivisi` hacmi | 14.57 mm³ | satır 74 |
| `TOLERANCE` | %5 | satır 79 |
| `L_BAGLANTI_ADET` | 2 | satır 156 |
| L başına vida | 4 (koda gömülü) | satır 979 |

---

## Bilinen zayıflıklar

**1. Ray çıkarması muhtemelen fazladan (yukarıda detaylı).**
En somut, en kolay düzeltilebilir hata.

**2. Arkalık panellerindeki vidalar hiç sayılmıyor.**
Kalınlığı ≤8 mm olan paneller delik taramasına girmiyor (satır 886-899). Arkalığı
gövdeye tutturan vidalar varsa hepsi kayıp. Ağaç vidası eksiğinin büyük kısmı
buradan geliyor olabilir.

**3. `L_BAGLANTI_ADET = 2` sabit ve bölünmüş siparişlerde çift sayılıyor.**
9360 gibi iki FBX'e bölünen siparişlerde toplam +16 vida ekleniyor, olması gereken +8.

**4. 14.57 mm³ çok küçük bir hacim.**
En küçük kategori. `execute_double_boolean` içindeki gürültü eşiği `vol > 0.01`
(satır 294) uzak ama %5 tolerans bandı [13.84, 15.30] dar. Boolean solver'ın küçük
deliklerde ürettiği sapma bu bandın dışına çıkarsa delik sessizce kaybolur —
[01](01-delik-cikarma-cift-boolean.md) → "sınıflanamayan delikler sessizce
kayboluyor".

**5. Sapma tutarsız: bazı siparişte tam, bazısında %40 eksik.**
9372: 24/24 ✅ — 9364-2: 20/46 ❌. Tek bir sistematik sebep değil, en az iki farklı
hata (ray çıkarması + panel/arkalık kaybı) üst üste biniyor.
