# 13 — Arkalık Çivisi

| | |
|---|---|
| **Kod** | `part_thickness()` — satır 664-669<br>`pair_split_arkalik()` — satır 727-760<br>`_tam_yuzey_temasi()` — satır 704-724<br>`arkalik_civi_count()` — satır 672-680 |
| **Girdi** | Panel mesh'leri (delik değil — **kalınlıktan** tespit) |
| **Ürettiği parça** | Arkalık Çivisi |
| **Doğruluk** | 🔴 10 siparişte **−502** (498 / 1000) — **sistemdeki en büyük hata** |

---

## Problem

Arkalık paneli (dolabın arka kapağı) ince MDF'tir ve gövdeye çivilerle çakılır.
Çivinin deliği yoktur — dolayısıyla delik sayarak bulunamaz.

İki alt problem:
1. Hangi panelin arkalık olduğunu anlamak
2. Kaç çivi gerektiğini hesaplamak

---

## Adım 1 — Arkalığı kalınlıktan bul

```python
def part_thickness(obj):                                   # :664
    dim, _ = get_perfect_local_bounds(obj)
    return min(dim.x, dim.y, dim.z)        # en kısa kenar = MDF kalınlığı
```

```python
for o in meshes:                                           # :888-894
    th = part_thickness(o)
    if th is not None and th <= ARKALIK_MAX_KALINLIK:      # 8 mm
        arkalik_adaylari.append(o)
    else:
        diger_parcalar.append(o)
```

Ölçüm: **arkalık 5 mm, gövde panelleri 18 mm** → net ayrım, eşik 8 mm ortada.

> ⚠️ Bu ayrım aynı zamanda **arkalık panellerini delik taramasından tamamen
> çıkarıyor**. `diger_parcalar` döngüsüne girmiyorlar, yani arkalıktaki hiçbir delik
> hiçbir yerde sayılmıyor.

---

## Adım 2 — İkiye kesilmiş arkalıkları birleştir

Bazı arkalıklar paketleme kolaylığı için üretimde **ikiye kesilip bantlanır**.
FBX'te bu, aynı arkalığın **iki ayrı mesh parçası** olarak görünür.

Birleştirilmezse: her yarı ayrı sayılır, W×H yarım okunur, çivi sayısı yanlış çıkar.

### Neden hacim eşleşmesi tek başına yetmiyor

Müşteri **aynı boyda 2 ayrı modül** sipariş edebilir — bu da aynı hacimde 2 arkalık
demektir, ama bunlar gerçekten ayrı panellerdir, birleştirilmemeli.

Ek şart: adaylar **tam bir yüzeyde temas** etmeli.

```python
def _tam_yuzey_temasi(a, b):                               # :704
    amin, amax = _world_aabb(a)
    bmin, bmax = _world_aabb(b)
    tol = 2.0 / 1000        # 2 mm, dünya birimine çevrilmiş

    for eksen in (0, 1, 2):
        digerleri = diğer iki eksen

        # Bu eksende SIFIR boşlukla bitişik mi?
        bitisik = |amax[eksen] − bmin[eksen]| ≤ tol
               or |bmax[eksen] − amin[eksen]| ≤ tol
        if not bitisik: continue

        # Diğer İKİ eksende TAM örtüşüyor mu?
        if her iki eksende de (amin ≈ bmin and amax ≈ bmax):
            return True
    return False
```

Gerçek ikiye-kesilmiş yarılar kesim hattı boyunca **sıfır boşlukla bitişik ve tam
örtüşen** durur. Ayrı modüllerin arkalıkları bunu sağlamaz.

### Birleştirme

```python
def pair_split_arkalik(parts):                             # :727
    while kalan:
        o = kalan.pop(0)
        vo = mesh_volume(o)                    # dünya uzayı hacmi
        for o2 in kalan:
            if |mesh_volume(o2) − vo| ≤ vo × %3    and   _tam_yuzey_temasi(o, o2):
                → bpy.ops.object.join()  ile TEK objede birleştir
                break
        sonuc.append(o)
```

Eşleşmeyen adaylar zaten tek parça arkalıktır, oldukları gibi kalır.

---

## Adım 3 — Çivi sayısı

```python
def arkalik_civi_count(obj):                               # :672
    dim, _ = get_perfect_local_bounds(obj)
    dims = sorted([dim.x, dim.y, dim.z])
    W, H = dims[2], dims[1]              # iki büyük kenar (kalınlık hariç)

    nx = max(1, ceil(W / 150))
    nz = max(1, ceil(H / 150))
    return 2 * nx + 2 * nz
```

Model: panelin **çevresine 150 mm aralıklarla** çivi çakılır. Genişlik boyunca `nx`,
yükseklik boyunca `nz` çivi; her biri **iki kenarda** (üst-alt, sol-sağ) → `2nx + 2nz`.

### Örnek

600 × 800 mm bir arkalık:
```
nx = ceil(600/150) = 4
nz = ceil(800/150) = 6
çivi = 2×4 + 2×6 = 20
```

---

## Sabitler (satır 123-124, 138-139)

| Sabit | Değer | Anlamı |
|---|---|---|
| `ARKALIK_MAX_KALINLIK` | 8.0 | mm — bu kalınlığın altı arkalık (yerel uzay) |
| `CIVI_ARALIK_MM` | 150.0 | mm — çivi aralığı |
| `ARKALIK_ESLESME_TOL` | 0.03 | %3 — iki yarının hacim eşleşmesi |
| `ARKALIK_TEMAS_TOL_MM` | 2.0 | mm — temas/örtüşme toleransı |

---

## 🔴 Neden bu kadar yanlış — kök sebep analizi

Referansla karşılaştırma çarpıcı bir örüntü gösteriyor:

| Sipariş | Bizim | Referans |
|---|---|---|
| 9355 | 46 | **100** |
| 9356 | 34 | **100** |
| 9359 | 56 | **100** |
| 9361 | 58 | **100** |
| 9362 | 38 | **100** |
| 9363 | 58 | **100** |
| 9364-1 | 64 | **100** |
| 9364-2 | 62 | **100** |
| 9372 | 14 | **50** |
| 9360 | 68 | **150** (=100+50) |

**Referans tarafı hep 100 (veya 50'nin katı).** Bizim tarafımız 14 ile 68 arasında
değişiyor.

Bu, referansın çiviyi **hiç hesaplamadığını** gösteriyor — 100, "modül başına bir
paket/avuç çivi" gibi **sabit bir değer** görünüyor. 9372 tek küçük modül olduğu için
50, 9360 iki modül olduğu için 150.

> **Yani bu bir algoritma hatası olmayabilir.** Bizim `2·ceil(W/150) + 2·ceil(H/150)`
> formülümüz "gerçekte kaç çivi çakılır" sorusunu cevaplıyor; referans BoM ise
> "depodan kaç çivi çıkışı yapılır" sorusunu. İkisi farklı sorular.
>
> Bunu Kerem'in netleştirmesi gerekiyor: BoM'daki 100 gerçek bir sayım mı, yoksa
> yuvarlanmış bir tedarik miktarı mı? Cevaba göre ya formül düzeltilir ya da
> referansla karşılaştırma bu kalem için anlamsız kabul edilir.

---

## Bilinen zayıflıklar

**1. Referansla karşılaştırma temeli şüpheli (yukarıda).**
Düzeltmeye başlamadan önce cevaplanması gereken soru bu.

**2. 150 mm aralık doğrulanmamış.**
Kod yorumu "orijinal 0.15 m kuralının mm karşılığı" diyor — yani bir varsayımdan
geliyor, ölçümden değil.

**3. Sadece çevre sayılıyor, ortadan geçen çiviler yok.**
Büyük arkalıklarda genelde ortadan da (raf hizasından) çivi çakılır. Formül bunu
hiç modellemiyor — büyük panellerde sistematik eksik sayım.

**4. Köşeler iki kez sayılıyor olabilir.**
`2nx + 2nz` formülünde köşe çivileri hem yatay hem dikey kenarda sayılıyor olabilir.
Gerçek bir çevre dizilimi `2(nx + nz) − 4` olurdu. Yön hangisiyse, formül tutarlı
şekilde 4 fazla sayıyor.

**5. `mesh_volume` her karşılaştırmada yeniden hesaplanıyor (satır 743-746).**
`pair_split_arkalik` iç döngüde `mesh_volume(o2)` çağırıyor — O(n²) mesh
triangülasyonu. Çok arkalıklı siparişlerde yavaş.

**6. `bpy.ops.object.join()` sahne durumunu değiştiriyor.**
Birleştirme sonrası `o2` objesi yok oluyor ama `kalan` listesinden zaten çıkarılmış
durumda — güvenli. Yine de `bpy.ops` çağrıları bağlam (context) bağımlıdır; headless
çalışmada seçim durumu beklenmedik şekilde bozulursa sessizce yanlış obje birleşebilir.
