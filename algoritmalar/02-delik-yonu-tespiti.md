# 02 — Delik Yönü Tespiti (İşaretsiz Eksen + İşaretli Delme Yönü)

> **Altyapı algoritması.** Şu an yalnızca [06 — Uzun Linco Pimi](06-uzun-linco-pimi.md)
> kullanıyor, ama genel amaçlı.

| | |
|---|---|
| **Kod** | `hole_direction()` — satır 320-336<br>`hole_signed_direction()` — satır 339-367<br>`world_center()` — satır 315-317 |
| **Girdi** | Delik mesh'i (+ işaretli yön için panel mesh'i) |
| **Çıktı** | Birim vektör (dünya uzayında) |

---

## Problem

İki deliğin **birbirine bakıp bakmadığını** anlamak, sadece aralarındaki mesafeye
bakarak mümkün değil. İki modül yan yana dururken:

- **gerçek bağlantı**: iki delik karşılıklı, ağızları birbirine dönük
- **yanlış pozitif**: iki delik aynı mesafede ama **aynı yöne** bakıyor (paralel),
  aralarında hiçbir bağlantı yok

Ayırt etmek için her deliğin **hangi yöne açıldığını** bilmek gerekir.

---

## Aşama 1 — İşaretsiz eksen (`hole_direction`)

Silindirik bir delik, bir eksende uzun, diğer ikisinde incedir. O halde deliğin
**en uzun yerel ekseni = delme ekseni**.

```python
dim, _ = get_perfect_local_bounds(hole_obj)      # yerel boyutlar
axes = [(dim.x, X), (dim.y, Y), (dim.z, Z)]
axes.sort(reverse=True)                          # en uzun önce
local_dir = axes[0][1]                           # en uzun eksen
world_dir = (hole_obj.matrix_world.to_3x3() @ local_dir).normalized()
```

**Sınırı:** bu bir **eksendir, yön değildir**. `+X` ile `−X` ayırt edilmez. Deliğin
hangi *ucundan* açıldığı bilinmez. Bu yüzden ikinci aşama var.

---

## Aşama 2 — İşaretli delme yönü (`hole_signed_direction`)

Fikir: **deliğin açık ucu, dışarıya bakan uçtur.** Delik boşluğunun merkezinden
6 eksen yönüne ışın (ray) gönder; panel gövdesine **çarpmayan** yön açık uçtur,
çarpan yön kör diptir.

```
1. axis = hole_direction(hole_obj)               # aday eksen (işaretsiz)
2. origin = deliğin dünya merkezi → panelin yerel uzayına çevir
3. 6 yerel eksen yönü için:  ±X, ±Y, ±Z
     hit = panel_obj.ray_cast(origin, yön)
     hit varsa  → kör dip, atla
     hit yoksa  → AÇIK yön, aday
4. Birden çok açık yön varsa (kenar/köşe deliği):
     en uzun eksene EN HİZALI olanı seç       max |dw · axis|
5. Hiç açık yön yoksa → axis'e geri düş (işaretsiz)
```

### Neden "en hizalı açık yön"?

Panelin kenarına yakın bir delikte birden fazla yön ışını boşa çıkabilir (ör. hem
delik ağzı hem panel kenarı). Bunlar arasından **deliğin kendi uzun eksenine en yakın
olanı** gerçek delme yönüdür; kenar kaçağı eksene dik olacağından elenir.

### Ölçek notu

`ray_cast` **panelin yerel uzayında** çalışır, o yüzden merkez önce
`panel_obj.matrix_world.inverted() @ center_w` ile geri çevrilir. Dönen vektör ise
`rot @ dl` ile tekrar dünyaya taşınır — sonuç dünya uzayında birim vektördür.

---

## Yardımcı: `world_center`

```python
def world_center(obj):                                       # :315
    wb = [obj.matrix_world @ Vector(v) for v in obj.bound_box]
    return sum(wb, Vector()) / 8.0
```

Sınır kutusunun 8 köşesini dünyaya taşıyıp ortalamasını alır. **Tüm mesafe tabanlı
algoritmalar** (kulp, ray, ayak, modül bağlantı, uzun pim) delik konumu olarak bunu
kullanır — yani hepsi **dünya uzayında, 1 birim = 1000 mm** ölçeğinde çalışır.

---

## Nerede kullanılıyor

| Kullanan | Nasıl |
|---|---|
| [06 — Uzun Linco Pimi](06-uzun-linco-pimi.md) | İki linco deliğinin **karşılıklı** olduğunu doğrulamak için (`dir_A · conn ≥ 0.9`, `dir_B · conn ≤ −0.9`) |
| `count_order` satır 923 | Her linco deliği için `(merkez, işaretli_yön)` çifti saklanır |

Diğer hiçbir algoritma yön kullanmıyor — hepsi salt mesafe/şekil tabanlı.

---

## Bilinen zayıflıklar

**1. `ray_cast` panelin kendi mesh'ine atılıyor, delik objesine değil.**
Delik objesi zaten sahneden silinmek üzere; panel katı olduğu için ışın testi doğru.
Ancak panel **kapalı bir mesh değilse** (bozuk FBX) `ray_cast` güvenilmez sonuç verir
ve sessizce yanlış yön döner.

**2. Küp benzeri deliklerde eksen belirsiz.**
`hole_direction` en uzun ekseni seçer. Delik neredeyse küpse (x≈y≈z) seçim gürültüye
bağlı olur. Linco deliği belirgin silindirik olduğu için pratikte sorun değil, ama
yeni bir delik tipine bu fonksiyon uygulanırsa önce oranına bakılmalı.

**3. Geri düşüş sessiz.**
Hiç açık yön bulunamazsa fonksiyon işaretsiz `axis`'i döndürür (satır 367). Çağıran
taraf bunun işaretli mi işaretsiz mi olduğunu **anlayamaz**; uzun pim testi o durumda
rastgele yarı yarıya yanlış karar verebilir.
