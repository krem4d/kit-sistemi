# 08 — Modülleri Birbirine Bağlama

| | |
|---|---|
| **Kod** | `detect_modul_baglanti_pairs()` — satır 370-400 |
| **Girdi** | Kulptan artakalan `modulbaglanti` merkezleri (**global havuz**) |
| **Ürettiği parça** | Modülleri Birbirine Bağlama |
| **Doğruluk** | ✅ 10 siparişte **tam tutuyor** (12 / 12) |

---

## Problem

İki modül yan yana konduğunda, birbirine dayanan panellere bir bağlantı vidası
takılır. Bu vidanın delikleri **iki ayrı panelde**, karşılıklı ve çok yakındır.

Zorluk: bu delikler kulp delikleriyle **aynı hacimde** (351.35 mm³). Ayrım mesafeden.
Kulp önce ayıklandığı için buraya sadece artakalanlar gelir — ama artakalan her delik
de bağlantı deliği değildir.

---

## Algoritma

```
Girdi: TÜM panellerden artakalan modulbaglanti merkezleri (tek havuz)

1. Pencere hesapla:                                        :385-386
     lo = 18 mm × 0.999 = 17.982 mm
     hi = 18 mm × 1.001 = 18.018 mm      ← ÇOK DAR (±%0.1)

2. Greedy eşleştirme:                                      :389-399
     her i için (kullanılmamışsa):
       her j > i için (kullanılmamışsa):
         d = |merkez_i − merkez_j|
         lo ≤ d ≤ hi  →  ikisini KULLANILDI işaretle
                          pairs++
                          break

3. Dön: pairs                                              :400
```

Yapısı [07 — Kulp](07-kulp.md) ile **birebir aynı** — tek fark hedef mesafe ve
tolerans. Kulp panel içinde, bu global havuzda çalışır.

---

## Neden ±%0.1 gibi absürt dar bir tolerans?

Bu, sistemdeki en dar tolerans (kulp %5, ayak %3, ray ±8 mm). Sebebi ölçüme dayanıyor:

`diag_modul_mesafe.py` ile gerçek FBX'ler tarandığında:

```
gerçek bağlantı çiftleri     :  TAM 18.000 mm
bir sonraki en yakın mesafe  :  101-136 mm+
```

Arada **boşluk var** — 18 ile 101 arasında hiçbir şey yok. Dar tolerans hem güvenli
hem gerekli.

### Eski yöntem neden terk edildi

İlk sürüm (`pair_count`) "en yakın komşuyu bul, 200 mm eşiğin altındaysa eşleştir"
mantığındaydı. Bu, **birbirine hiç bağlı olmayan** ama tesadüfen en yakın düşen
delikleri de çift sayıyordu — ör. farklı modüllerin 136 mm arayla duran köşe
delikleri.

```
ESKİ:  "en yakın komşu + gevşek eşik"   →  136 mm'lik alakasız çift SAYILDI ❌
YENİ:  "tam 18 mm ± %0.1"               →  eşi olmayan delik EŞLEŞMEZ ✅
```

Kritik davranış farkı: yeni yöntemde eşi bulunamayan delik **yanlış bir komşuya
zorla eşlenmez**, eşleşmemiş kalır. Yanlış pozitif üretmemek, eksik saymaktan
yeğdir — çünkü eksik sayım `_ham` üzerinden görünür, yanlış pozitif görünmez.

Bu düzeltmenin kanıtı `Algoritmaların_testi.md`'de.

---

## Sabitler (satır 89-90)

| Sabit | Değer | Anlamı |
|---|---|---|
| `MODUL_BAGLANTI_MESAFE` | 0.018 | 18 mm (dünya uzayı) |
| `MODUL_BAGLANTI_TOL` | 0.001 | ±%0.1 → [17.982, 18.018] mm |

---

## Neden bu algoritma doğru çalışıyor

10 siparişin 10'unda da tam tutuyor. Sebebi:

1. **Ölçülmüş bir imza var** — 18 mm tahmin değil, gerçek FBX'lerden ölçüldü.
2. **Ayrım net** — sonraki en yakın mesafe 5 kat uzakta. Tolerans seçimi kritik değil,
   geniş bir aralık aynı sonucu verirdi.
3. **Yanlış pozitif üretmemeyi tercih ediyor** — şüphede kalınca eşleştirmiyor.

Bu üçü, [11 — Ray](11-ray-seti.md) ve [13 — Arkalık Çivisi](13-arkalik-civisi.md)
gibi sorunlu algoritmalarda **yok**. İyi çalışan algoritmanın deseni bu.

---

## Bilinen zayıflıklar

**1. Global havuz, panel bilgisini kaybediyor.**
`modulbag_centers` tüm panellerden toplanıyor (satır 937), hangi merkezin hangi
panelden geldiği unutuluyor. Teorik olarak **aynı panelin** iki deliği 18 mm arayla
duruyorsa yanlışlıkla çift sayılır. Gerçek veride görülmedi ama yapısal bir açık —
[06 — Uzun Linco Pimi](06-uzun-linco-pimi.md) bu bilgiyi koruyor, burası korumuyor.

**2. `break` ilk uyanla eşleştiriyor.**
[07](07-kulp.md) ile aynı sorun. Tolerans bu kadar darken pratikte etkisiz.

**3. Yön kontrolü yok.**
Uzun linco piminde kullanılan "karşılıklı mı bakıyor" testi burada yapılmıyor.
18 mm'lik dar pencere şu an yeterli, ama başka bir donanım da 18 mm aralık
kullanırsa ayrım kalmaz.
