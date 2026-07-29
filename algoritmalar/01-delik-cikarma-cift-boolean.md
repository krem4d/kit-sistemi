# 01 — Delik Çıkarma (Çift Boolean) ve Hacim Sınıflandırma

> **Altyapı algoritması.** Diğer bütün parça tespitleri bunun çıktısı üzerine kurulu.

| | |
|---|---|
| **Kod** | `execute_double_boolean()` — satır 254-298<br>`match_category()` — satır 301-305<br>`is_ray_hole()` — satır 308-312 |
| **Girdi** | Bir panel mesh'i (`bpy` objesi) |
| **Çıktı** | `[{"object": <delik mesh'i>, "volume": <mm³>}, ...]` |
| **Ürettiği parça** | Hiçbiri doğrudan — hepsinin ham verisini üretir |

---

## Problem

FBX'te delik diye bir nesne yoktur. Delik, tahtanın **olmayan** kısmıdır — bir boşluk.
Boşluğu sayabilmek için önce onu **katı bir cisme** çevirmek gerekir.

Ayrıca panel isimleri anlamsız (`Object_23`), yani hangi deliğin ne olduğu isimden
anlaşılamaz. Tek ayırt edici özellik **deliğin hacmidir**.

---

## Algoritma: çift boolean numarası

Fikir şu: panelin etrafına iki kutu çiz — biri panelden **azıcık büyük**, biri
**azıcık küçük**. Büyük kutudan paneli çıkar, sonra sonucu küçük kutuyla kes.
Geriye sadece **panelin içindeki boşluklar** kalır.

```
1. Panelin yerel sınır kutusunu ölç              get_perfect_local_bounds() :227
   → dim (x,y,z) + merkez

2. İki prizma üret, panelin matrix_world'ü ile   create_prism() :241
   ├─ Temp_Outer : dim × 1.002   (%0.2 büyük)
   └─ Temp_Inner : dim × 0.998   (%0.2 küçük)

3. Outer − Panel        (BOOLEAN DIFFERENCE, solver=EXACT)   :267-271
   → panelin negatifi: dış kabuk + içerideki boşluklar

4. Sonuç ∩ Inner        (BOOLEAN INTERSECT, solver=EXACT)    :273-276
   → dış kabuk kırpılır, SADECE iç boşluklar kalır

5. Inner prizmayı sil                                        :278

6. Edit mode → separate LOOSE                                :284-287
   → her ayrık boşluk kendi objesi olur = her delik ayrı mesh

7. Her parçanın hacmini ölç (triangulate + calc_volume)      :290-297
   ├─ hacim > 0.01  → geçerli delik, listeye ekle
   └─ hacim ≤ 0.01  → gürültü, sil
```

### Neden iki kutu, neden 1.002 / 0.998?

Tek `DIFFERENCE` yapılsaydı sonuç, panelin **dış yüzeyini saran kabuk + delikler**
olurdu — kabuk da ayrık bir parça olarak sayılırdı. `INTERSECT` adımı, %0.2 küçük
kutuyla keserek bu dış kabuğu kırpar. Geriye topolojik olarak **sadece iç boşluklar**
kalır.

%0.2'lik pay (`1.002` / `0.998`) boolean solver'ın aynı düzlemde çakışan yüzeyler
(coplanar faces) yüzünden bozulmasını engeller. Tam 1.0 kullanılsa EXACT solver
belirsiz sonuç üretirdi.

### Hacim hangi uzayda?

`bm.from_mesh(part.data)` — **transform uygulanmadan**, yani **yerel (mm) uzayda**.
Bu yüzden `CATEGORIES` değerleri mm³'tür. (Bkz. [00-genel-bakis.md](00-genel-bakis.md)
→ "iki ayrı ölçek".)

---

## Sınıflandırma: hacim → parça tipi

```python
def match_category(vol):                                    # :301
    for cat_name, target in CATEGORIES.items():
        if target * (1 - TOLERANCE) <= vol <= target * (1 + TOLERANCE):
            return cat_name
    return None
```

Basit bağıl aralık kontrolü. İlk uyan kategori döner (sözlük sırası).

### Hacim tablosu (satır 71-79)

| Kategori | Hacim (mm³) | Tolerans | Ne demek |
|---|---|---|---|
| `linco` | 9680.0 | %5 | Linco gövde deliği |
| `pim` | 936.0 | %5 | Linco dübel deliği (çapraz kontrol) |
| `ahsapcivisi` | 14.57 | %5 | Ağaç vidası deliği |
| `rafpimi` | 234.0 | %5 | Raf pimi deliği |
| `modulbaglanti` | 351.35 | %5 | Modül bağlantı **veya kulp** deliği |
| `menteseTabani` | 11454.0131 | %5 | Menteşe tabanı yuvası |

`TOLERANCE = 0.05` (%5) — tüm kategoriler için ortak.

### Ayrı bir kategori: ray deliği

```python
def is_ray_hole(vol):                                       # :308
    lo = RAY_DELIK_HACIM * (1 - RAY_DELIK_TOL)   # 84.9181 × 0.99
    hi = RAY_DELIK_HACIM * (1 + RAY_DELIK_TOL)   # 84.9181 × 1.01
    return lo <= vol <= hi
```

Ray deliği (`≈84.92 mm³`, %1 tolerans) bilerek `CATEGORIES`'e **konmamıştır** —
`match_category()` `None` döndürdükten *sonra* ayrıca kontrol edilir (satır 928).
Sebebi izolasyon: ray delikleri ağaç vidası havuzuna sızmasın. Bkz.
[11-ray-seti.md](11-ray-seti.md).

---

## Sınıflandırma akışı (`count_order`, satır 912-932)

```
her delik için:
  cat = match_category(hacim)

  cat == "modulbaglanti"  → part_modul_centers    [07][08]
  cat == "ahsapcivisi"    → part_ahsap_centers    [09][10][12]
  cat == "linco"          → counts["linco"]++ ve part_linco_holes  [05][06]
  cat == başka bir şey    → counts[cat]++         [03][04]
  cat is None + is_ray_hole(hacim) → part_ray_centers  [11]
  cat is None + ray değil → SESSİZCE DÜŞER  ⚠️

  → delik objesi sahneden silinir
```

---

## Bilinen zayıflıklar

**1. Sınıflanamayan delikler sessizce kayboluyor (satır 916-932).**
Hiçbir hacme uymayan ve ray da olmayan bir delik hiçbir sayaca yazılmaz, hiçbir log
üretmez. Yeni bir donanım tipi (ör. çivili ayak) FBX'e girdiğinde sistem bunu
**fark etmez** — sessizce sıfır sayar. Bu, Çivili Ayak'ın hiç bulunmamasının ve
muhtemelen Ağaç Vidası eksiğinin bir kısmının sebebi olabilir.

> Düzeltme fikri: `else` dalında `bilinmeyen_hacimler.append(v)` tutup JSON'a yazmak.
> Tek satırlık değişiklik, teşhis değeri yüksek.

**2. Arkalık panelleri delik taramasına HİÇ girmiyor (satır 886-899).**
Kalınlığı ≤8 mm olan her panel `arkalik_adaylari`'na ayrılır ve `diger_parcalar`
döngüsüne girmez. Arkalıkta delik varsa (ör. arkalığı gövdeye tutturan ağaç vidaları)
o delikler hiç sayılmaz.

**3. %5 tolerans bantları çakışabilir.**
Şu anki değerlerde çakışma yok, ama `match_category` **ilk uyanı** döndürdüğü için
ileride yakın hacimli bir kategori eklenirse sözlük sırası sessizce belirleyici olur.

**4. Hacim eşiği `0.01` sabit.**
Ondan küçük boşluklar gürültü sayılıp atılıyor. Ağaç vidası deliği 14.57 mm³ olduğuna
göre pay geniş, ama daha küçük bir donanım tipi eklenirse bu eşik onu yutar.
