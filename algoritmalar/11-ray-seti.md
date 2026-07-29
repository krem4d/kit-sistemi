# 11 — Ray Seti (Çekmece Rayı)

| | |
|---|---|
| **Kod** | `detect_rays()` — satır 499-540<br>`_ray_signature_match()` — satır 478-496<br>`is_ray_hole()` — satır 308-312 |
| **Girdi** | `RAY_DELIK_HACIM` bandındaki delik merkezleri (≈84.92 mm³, %1) |
| **Ürettiği parça** | Ray Seti (boy bazında) |
| **Doğruluk** | 🟡 10 siparişte **−1** (2 / 3) — 9363'te kaçırıldı |

---

## Problem

Çekmece rayı panele 2-3 vidayla monte edilir. Hangi **boyda** ray olduğunu bilmek
gerekiyor (25cm - 55cm arası 7 standart boy), çünkü BoM'da her boy ayrı kalem.

Ray'in kendisi FBX'te yok — sadece vida delikleri var. Boy, **deliklerin arasındaki
mesafelerden** çıkarılmalı.

---

## Kritik keşif: ray deliği ağaç vidası deliği DEĞİL

İlk sürüm ray desenini `ahsapcivisi` havuzunda (14.57 mm³) arıyordu. Bu iki hataya
yol açtı:

1. **Gerçek ağaç vidaları ray sanıldı.** Panele rastgele aralıklarla dağılmış vidalar
   tesadüfen bir ray imzasına uyuyordu → yanlış ray, ve o vidalar ağaç vidası
   sayımından haksız düşülüyordu.
2. **Gerçek raylar yanlış boy bulunuyordu.** Gerçek bir 55cm ray, araya karışan
   alakasız vidalar yüzünden 25cm olarak eşleşiyordu.

`hacim_bul.py` ile Object_23 tarandığında sebep ortaya çıktı: ray'e ait 3 delik
`CATEGORIES`'teki **hiçbir hacimle eşleşmiyordu** — `[BİLİNMİYOR]`, hacimler
84.9189 / 84.9188 / 84.9175 mm³.

Yani ray deliği kendine özgü bir hacme sahip, ağaç vidasıyla (14.57) alakası yok.

**Düzeltme:** ray delikleri `CATEGORIES`'e eklenmedi, ayrı bir kontrol olarak
(`is_ray_hole`) tanımlandı ve kendi havuzuna gönderildi (satır 928-931). Böylece
iki havuz **hiç kesişmiyor** — ray tespiti ağaç vidası sayımını artık etkileyemez.

> Bu düzeltmenin kalıntısı olan bir hata hâlâ duruyor:
> [10-agac-vidasi.md](10-agac-vidasi.md) → "ray çıkarması".

---

## Ray imzası nereden geliyor

Her ray boyu için delikler, rayla aynı doğrultudaki sabit bir **referans noktasına**
göre ölçüldü (kullanıcı ölçümü). Ardışık farklar o boyun **imzasıdır**.

```python
RAY_HOLE_POSITIONS = {                                     # :180-188
    "55cm": [63.0, 212.0, 434.0],
    "50cm": [64.0, 214.0, 375.0],
    "45cm": [64.0, 216.0, 318.0],
    "40cm": [64.0, 193.0, 275.0],
    "35cm": [64.0, 141.0, 224.0],
    "30cm": [63.0, 172.0],
    "25cm": [43.0, 231.0],
}

RAY_GAPS = {ad: [pos[i+1] - pos[i] for i in range(len(pos)-1)]    # :191-192
            for ad, pos in RAY_HOLE_POSITIONS.items()}
```

Türetilen imzalar:

| Boy | Delik | İmza (ardışık aralıklar, mm) |
|---|---|---|
| 55cm | 3 | **[149, 222]** |
| 50cm | 3 | [150, 161] |
| 45cm | 3 | [152, 102] |
| 40cm | 3 | [129, 82] |
| 35cm | 3 | [77, 83] |
| 30cm | 2 | [109] |
| 25cm | 2 | [188] |

> ⚠️ **Boy ile aralık doğru orantılı DEĞİL.** 55cm'nin ikinci aralığı 222, 45cm'nin
> 102. Her imza kendine özgü. (Kod yorumunda bir hata itirafı var: `[152, 102]` bir
> ara yanlışlıkla 55cm sanılmış, aslında 45cm.)
>
> İmzalar `RAY_HOLE_POSITIONS`'tan **otomatik türetiliyor**, elle yazılmıyor — böylece
> konum ile aralık arasında kayma/tutarsızlık olamaz. İyi bir tasarım kararı.

---

## Algoritma

```
Girdi: bir paneldeki RAY_DELIK_HACIM bandındaki merkezler

── AŞAMA 1: 3 delikli raylar (55-35cm) ───────────────  :514-527
   Her (i,j,k) üçlüsü için (hiçbiri kullanılmamışsa):
     dij, djk, dik = üç ikili mesafe × 1000        (mm)
     p, q, r = sorted([dij, djk, dik])
              └─ p,q = iki ardışık aralık, r = toplam açıklık

     DOĞRUSALLIK TESTİ:  |r − (p+q)| ≤ 8 mm ?
       → değilse üçgen oluşturuyor, ray değil, ele

     boy = _ray_signature_match([p, q])
       → eşleşirse üç deliği KULLANILDI işaretle, rays.append(boy)

── AŞAMA 2: 2 delikli raylar (30/25cm) ───────────────  :529-537
   Kalan deliklerde her (i,j) ikilisi için:
     d = mesafe × 1000
     boy = _ray_signature_match([d])
       → eşleşirse iki deliği işaretle, rays.append(boy)

── Dön: (ray_isimleri, kalan_merkezler)                :539-540
```

### Doğrusallık testi neden böyle çalışıyor

Üç nokta aynı doğru üzerindeyse, en uzun mesafe diğer ikisinin toplamına eşittir:

```
●───────●─────────────●
   p          q
└──────────r──────────┘        r = p + q  ⟺  doğrusal
```

Üçgen oluşturuyorsa `r < p + q` (üçgen eşitsizliği). 8 mm tolerans ölçüm gürültüsü
için.

### Neden 3 delikli önce?

3 delikli imza **daha spesifik** — iki aralığın birden uyması gerekir. Önce onlar
kilitlenirse, artakalan deliklerde 2 delikli aramanın yanlış pozitif üretme şansı
azalır. Ters sırada olsa 3 delikli bir ray'in iki deliği 2'lik bir imzaya uyup
çalınabilirdi.

---

## İmza eşleştirme (`_ray_signature_match`)

```python
measured = sorted(gaps_mm)
for ad, gaps in RAY_GAPS.items():
    if len(gaps) != len(measured): continue        # delik sayısı tutmalı
    ref = sorted(gaps)
    if all(|m − r| ≤ 8 mm for m, r in zip(measured, ref)):
        dev = Σ |m − r|
        → EN DÜŞÜK toplam sapmalı boyu seç        # ilk-uyan DEĞİL
```

**"İlk uyan" değil "en iyi uyan"** olmasının sebebi: 55/50/45'in ilk aralıkları
149/150/152 — birbirine 8 mm toleransın içinde. Sadece ilk aralığa bakılsa ayrım
imkânsızdı. Ayrımı ikinci aralık yapıyor (222/161/102), ama garantiye almak için
toplam sapma karşılaştırılıyor.

---

## Set türetmesi

```python
ray_counter = Counter(ray_isimleri)                        # :982
ray_setleri = {L: c // 2 for L, c in sorted(ray_counter.items()) if c // 2 >= 1}
```

Bir çekmecenin **sol + sağ** iki rayı vardır → **aynı boydan 2 ray = 1 set**.

Örnek (9364-1): 2 adet 45cm ray bulundu → `{"45cm": 2}`

> Burada bir isimlendirme karışıklığı var: `ray_setleri` sözlüğünün değeri
> `c // 2` yani **set sayısı**. 9364-1'de 2 yazıyor, bu 2 set (4 ray) demek olmalı.
> Ama loglarda toplam ray sayısı 2 görünüyor. Değerin gerçekten set mi ray mi
> olduğu PDF çıktısıyla teyit edilmeli.

---

## Sabitler (satır 101-102, 171-173)

| Sabit | Değer | Anlamı |
|---|---|---|
| `RAY_DELIK_HACIM` | 84.9181 mm³ | 3 deliğin ortalaması |
| `RAY_DELIK_TOL` | 0.01 | ±%1 (dar — tekil hassas ölçüm) |
| `RAY_SCALE_MM` | 1000.0 | Dünya birimi → mm |
| `RAY_TOL_MM` | 8.0 | İmza eşleşme toleransı |
| `RAY_COLINEAR_TOL_MM` | 8.0 | Doğrusallık toleransı |

---

## Bilinen zayıflıklar

**1. 9363'te ray kaçırıldı (0 bulundu, referans 1).**
Sebebi bilinmiyor. Olasılıklar: ray deliği hacmi %1 bandın dışına çıktı, delikler
doğrusallık testini geçemedi, veya panel delik taramasında düştü.

**2. `RAY_DELIK_TOL = %1` çok dar.**
Diğer tüm kategoriler %5. Ölçüm 84.9172-84.9189 aralığında çok tutarlı çıktığı için
dar seçilmiş, ama farklı bir ray markası/modeli gelirse hiç yakalanmaz.

**3. Karmaşıklık O(n³).**
`itertools.combinations(range(n), 3)` — panelde çok ray deliği varsa kübik. Şu an
panel başına birkaç delik olduğu için sorun değil.

**4. Greedy, optimal değil.**
İlk bulunan geçerli üçlü kilitleniyor. Deliklerin FBX'teki sırası sonucu etkileyebilir.

**5. `_ray_disi` kullanılmıyor (satır 948).**
`detect_rays` kalan merkezleri döndürüyor ama çağıran `_ray_disi` diye alıp hiç
kullanmıyor. Hiçbir ray desenine uymayan ray-hacimli delikler **hiçbir yere
yazılmıyor** — sessizce kayboluyorlar. Bir uyarı, 9363'teki kaybı görünür kılardı.
