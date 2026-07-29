# 06 — Uzun Linco Pimi (L Modül)

| | |
|---|---|
| **Kod** | `detect_long_linco_pins()` — satır 426-475 |
| **Girdi** | Parça bazında `[(merkez, işaretli_yön), ...]` linco delikleri |
| **Ürettiği parça** | Uzun Linco Pimi + Linco Dübel'i azaltır |
| **Doğruluk** | 🟡 10 siparişte **−5** (15 / 20) — sadece 9364-2'de görünüyor |

---

## Problem

İki modül **L şeklinde** birleştiğinde, birbirine dayanan panellerdeki linco delikleri
karşı karşıya gelir. Bu iki deliğe iki ayrı dübel yerine **tek bir uzun pim** takılır —
pim her iki panele birden girer.

Tespit edilmesi gereken: hangi linco delikleri **karşılıklı ve bitişik**.

---

## Neden mesafe tek başına yetmiyor

İlk sürüm sadece "iki delik ~43 mm arayla" diye baktı. Görsel teşhiste
(`linco_uzun_pim_teshis.py`) iki hata çıktı:

1. **Aynı yöne bakan çiftler** sayıldı — iki delik yan yana ama ikisi de aynı tarafa
   açılıyor, aralarında bağlantı yok.
2. **Çapraz/diagonal bağlar** sayıldı — iki gerçek çiftin arasına, eksenle hizasız
   alakasız bir bağ girdi.

Çözüm: mesafeye ek olarak **işaretli yön** ve **eksen hizası** şartı.

---

## Algoritma

```
Girdi: parts_holes = [ [(merkez, yön), ...],   ← parça 1
                       [(merkez, yön), ...],   ← parça 2
                       ... ]

1. FARKLI iki parçanın her delik ikilisi (a, b) için:      :447-450
     conn = b − a
     d    = |conn|

2. Mesafe filtresi:                                        :451-453
     43 mm ± %25  →  [32.25, 53.75] mm   içinde mi?
     değilse ele

3. Yön bilgisi eksikse ele                                 :454-455

4. conn_hat = conn / d      (birim bağlantı vektörü)

5. ┌ ŞART 3 — bağlantı doğrusu eksene paralel mi?          :458-459
   │   max(|conn_hat.x|, |conn_hat.y|, |conn_hat.z|) ≥ 0.985
   │   → 90°'nin katı; çapraz bağları eler (cos 10°)
   └

6. ┌ ŞART 1 — A deliği B'ye BAKIYOR mu?                    :461-463
   │   dir_A · conn_hat  ≥  +0.9        (cos ~25°)
   ├ ŞART 2 — B deliği A'ya BAKIYOR mu?
   │   dir_B · conn_hat  ≤  −0.9        (ters işaret!)
   └   → aynı yöne bakanlar burada elenir

7. Geçen her ikili aday listesine: (d, (parça_i, delik_i), (parça_j, delik_j))

8. Adayları MESAFEYE GÖRE SIRALA (en yakın önce)           :467
9. Greedy eşleştir: her delik en fazla BİR kez kullanılır  :468-474
     pins++
```

### İşaretin önemi

Şart 1 ve 2'nin **zıt işaretli** olması kritik:

```
GERÇEK ÇİFT (karşılıklı):          YANLIŞ (aynı yöne bakıyor):

  A ──→ ● ────── ● ←── B             A ──→ ● ────── ● ──→ B
        dir_A     dir_B                    dir_A     dir_B

  dir_A · conn = +1  ✓ (≥ +0.9)      dir_A · conn = +1  ✓
  dir_B · conn = −1  ✓ (≤ −0.9)      dir_B · conn = +1  ✗ (≤ −0.9 değil)
```

İşaretsiz yön (`hole_direction`) kullanılsaydı ikisi de geçerdi. Bu yüzden
[02 — Delik Yönü](02-delik-yonu-tespiti.md) içindeki `hole_signed_direction`
(ray_cast tabanlı) gerekli.

---

## Sabitler (satır 109-119)

| Sabit | Değer | Anlamı |
|---|---|---|
| `LONG_LINCO_MESAFE` | 0.043 | 43 mm — bitişik çift mesafesi |
| `LONG_LINCO_TOL` | 0.25 | ±%25 → [32, 54] mm |
| `LONG_LINCO_ALIGN_MIN` | 0.9 | Karşılıklılık eşiği (cos ~25°) |
| `LONG_LINCO_AXIS_MIN` | 0.985 | Eksen hizası eşiği (cos ~10°) |

**Toleransın kaynağı:** `linco_mesafe_bul.py` ölçümü — bitişik çift ~0.043 birim,
aynı kümedeki çapraz komşu ~0.068 birim. %25 tolerans üst sınırı 0.054'te bırakıyor,
yani 0.068'e değmiyor. Net ayrım var.

---

## Dübel etkisi

```python
linco_dubel = linco - 2 * uzun_linco_pim          # :967
```

Her uzun pim, 2 normal dübelin yerini alır. Gövde/Kapak/Minifix **etkilenmez** —
onlar hâlâ delik başına 1 adet.

---

## Bilinen zayıflıklar

**1. Sadece FARKLI parçalar arası bakılıyor (satır 447-448).**
`for pi in range(P): for pj in range(pi+1, P)` — aynı panelin iki deliği asla
eşleşmez. Bu doğru bir kısıt (uzun pim iki *ayrı* paneli birleştirir), ama tek bir
panel FBX'te ikiye bölünmüşse gerçek bir çift kaçırılır.

**2. Karmaşıklık O(P² × H²).**
Her parça çiftinin her delik çiftine bakılıyor. 9363'te 65 linco deliği var; parça
sayısı arttıkça bu kısım kübik davranıyor. Şu an kabul edilebilir ama büyük
siparişlerde yavaşlar.

**3. Greedy eşleştirme optimal değil.**
En yakın çift önce eşleşiyor. Üç delik birbirine yakınsa yanlış ikili kilitlenip
üçüncü delik eşsiz kalabilir. Global optimum (maksimum eşleme) hesaplanmıyor.

**4. 9364-2'de 15 bulundu, referans 20 — %25 eksik.**
Aynı siparişte ham linco sayımı da 5 eksik (55 vs 60). Eksik linco delikleri ⇒ eksik
uzun pim adayı ⇒ hem pim hem dübel yanlış. Yani bu, [05](05-linco-ailesi.md)'teki
eksik sayımın **ikinci dereceden sonucu** olabilir — önce linco tespiti düzeltilmeli.

**5. Yön geri düşüşü sessiz.**
`hole_signed_direction` açık yön bulamazsa işaretsiz ekseni döndürür (satır 367).
O durumda şart 1/2 rastgele sonuç verir ve fark edilmez.
