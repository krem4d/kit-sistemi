# 04 — Raf Pimi

| | |
|---|---|
| **Kod** | `count_order()` satır 925 (sayım), 971 (türetme) |
| **Girdi** | `rafpimi` hacim havuzu (234.0 mm³, %5) |
| **Ürettiği parça** | Raf Pimi |
| **Doğruluk** | 🟡 10 siparişte toplam **−2** (134 / 136) |

---

## Problem

Raf pimi, rafın yüksekliğini ayarlamak için gövde yan panellerine açılan delik
sırasına takılır. Kullanıcı rafı yukarı/aşağı alabilsin diye **her pim için birden
fazla delik** açılır — kullanılacak delik montajda seçilir.

Yani delik sayısı ≠ pim sayısı.

---

## Algoritma

En basit algoritma: **say ve böl.**

```
1. Delik sınıflandırma sırasında:                          :925
     cat == "rafpimi"  →  counts["rafpimi"]++

2. Türetme:                                                :971
     raf_pimi = counts["rafpimi"] // 3
```

Sabit bölen **3** — her raf pimi için 3 delik açıldığı varsayımı. Tam bölme
(`//`, integer division) kullanılıyor, yani artan delikler **atılır**.

### Gerçek veriden

| Sipariş | Ham `rafpimi` deliği | `// 3` | Referans |
|---|---|---|---|
| 9355 | 36 | 12 | 12 ✅ |
| 9359 | 84 | 28 | 30 ❌ |
| 9364-2 | 54 | 18 | 18 ✅ |
| 9372 | 12 | 4 | 4 ✅ |

Çoğunlukla tutuyor. 9359'da 2 eksik → 6 delik kaçırılmış (84 yerine 90 olmalıydı).

---

## Neden 3?

Bu, koda gömülü bir **iş kuralı** — geometriden türetilmiyor, ölçülmüyor. Kodda tek
yorum satırı var: `# her raf pimi = 3 delik`. `parca_kurallari.md` de aynı şeyi
tekrarlıyor, kaynak göstermeden.

> ⚠️ Bu sabit **doğrulanmamış**. Rafın yükseklik ayar aralığı modele göre değişiyorsa
> (ör. bazı modüllerde 3, bazılarında 5 delik) bölen sabit kaldığı sürece sapma
> kaçınılmaz. Gerçek bir modülde delik sırası sayılıp teyit edilmeli.

---

## Bilinen zayıflıklar

**1. Tam bölme kalanı sessizce yutuyor.**
`85 // 3 = 28` — 1 delik kaybolur, hiçbir uyarı yok. Ham sayı `_ham` altında JSON'a
yazıldığı için sonradan kontrol edilebilir, ama otomatik denetim yok.

> `counts["rafpimi"] % 3 != 0` durumunda uyarı basmak, delik tespitindeki eksikleri
> anında görünür kılardı — 9359'daki −2 tam olarak böyle yakalanırdı.

**2. Bölen 3 sabit ve doğrulanmamış.**
Yukarıda açıklandı. Modül tipine göre değişiyorsa bu algoritma yapısal olarak yanlış.

**3. Simetri kontrolü yok.**
Raf pimi delikleri gövdenin **iki yan panelinde simetrik** açılır (sol 3 + sağ 3 =
1 raf). Algoritma toplamı 3'e bölüyor, panel eşleştirmesi yapmıyor. Bir panelde
delik kaçırılırsa sonuç sessizce yarım pim eksik çıkar — 9359'daki sapmanın olası
sebebi bu.

**4. Rafın kendisi sayılmıyor.**
Sadece pim sayılıyor; kaç raf olduğu bilgisi üretilmiyor. Şu an BoM'da raf kalemi
olmadığı için sorun değil.
