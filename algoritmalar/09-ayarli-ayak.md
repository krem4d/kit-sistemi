# 09 — Ayarlı Ayak, Allen ve Tıpa

| | |
|---|---|
| **Kod** | `_ayak_dikdortgen_adaylari()` — satır 582-626<br>`extract_ayak_feet()` — satır 629-655<br>`count_ayak_feet()` — satır 658-661 (teşhis kısayolu) |
| **Girdi** | Parça bazında `ahsapcivisi` delik merkezleri (14.57 mm³, %5) |
| **Ürettiği parçalar** | Ayarlı Ayak, Allen, Tıpa |
| **Doğruluk** | 🟡 10 siparişte Ayak **−2**, Tıpa **−2**, Allen **0*** |

---

## Problem

Ayarlı ayak, dolabın altına 4 vidayla monte edilir. Bu 4 vida deliği ağaç vidası
deliğiyle **aynı hacimde** — hacim ayırt edemez.

Ayrım geometriden: ayağın 4 vidası her zaman **~32 × 40 mm'lik bir dikdörtgen**
oluşturur (köşegen ~51.22 mm). Paneldeki diğer yapısal vidalar böyle bir düzen
oluşturmaz.

---

## İki başarısız yaklaşım (tarihçe)

### 1. "Panelde tam 4 vida varsa 1 ayak"

Panele **dağılmış** 4 yapısal vidayı da ayak sayıyordu.
Kanıt: 9262 siparişinde **11 ayak** sayıldı, gerçek ~1. Dağınık dörtlülerin köşegeni
500-850 mm'ydi — yani şekil hiç kontrol edilmiyordu.

### 2. "6 ikili mesafeyi sırala, `[32,32,40,40,51.22,51.22]` ile karşılaştır"

4 noktanın 6 ikili mesafesini sıralayıp beklenen listeyle kıyaslıyordu. Sorun:
**sıralama topolojiyi kaybeder** — hangi mesafenin kenar, hangisinin köşegen olduğu
bilgisi silinir. Bu hem yanlış pozitif hem yanlış negatif üretir.

Kanıt (9304-2 / Object_18): panelin 12 vidasından 3'ü tam 32.00/40.00/51.22'ye
uyuyordu ama 4. köşe **ray tespiti tarafından havuzdan çalınmıştı** → ayak sıfır
bulundu. Tolerans büyütmek bunu düzeltmez, çünkü eksik köşe zaten aday havuzunda yok.

---

## Şimdiki algoritma: köşegen + orta nokta

Kullanılan geometri teoremi:

> Bir paralelkenarın **köşegenleri birbirini ortalar**.
> Bu köşegenler **eşit uzunluktaysa** şekil bir **dikdörtgendir**.

Bu, sıralı-mesafe listesinin aksine topolojiyi doğrudan kullanır.

```
Girdi: bir paneldeki ahsapcivisi delik merkezleri

── 1. ADAY KÖŞEGENLER ────────────────────────────────  :601-607
   Her (i,j) ikilisi için:
     d = |merkez_i − merkez_j| × 1000        (mm'ye çevir)
     51.22 mm × (1 ± %3) içinde mi?
       evet → diagonaller.append( (i, j, d, ortanokta) )

── 2. İKİ KÖŞEGEN ORTAK ORTA NOKTA PAYLAŞIYOR MU? ────  :610-614
   Her (köşegen1, köşegen2) ikilisi için:
     4 delik de AYRI mı?          (len({i,j,k,l}) == 4)
     |m1 − m2| ≤ 1.54 mm ?        (51.22 × %3)
       → EVET: köşegenler birbirini ortalıyor
         ⇒ paralelkenar, ve köşegenler eşit ⇒ DİKDÖRTGEN

── 3. KENAR DOĞRULAMASI ──────────────────────────────  :616-624
   kenar1 = |merkez_i − merkez_k|
   kenar2 = |merkez_i − merkez_l|
   kısa, uzun = sorted([kenar1, kenar2])

   sapma = max(
     |kısa  − 32|    / 32,
     |uzun  − 40|    / 40,
     |d1 − 51.22|    / 51.22,
     |d2 − 51.22|    / 51.22
   )
   sapma ≤ %3  →  ADAY dikdörtgen (sapma ile birlikte kaydet)

── 4. GREEDY SEÇİM ───────────────────────────────────  :645-652
   Adayları sapmaya göre SIRALA (en iyi uyum önce)
   Hiçbir deliği paylaşmayan adayları sırayla kabul et
     feet++
```

### `i-k` ve `i-l` neden bitişik kenarlar?

Köşegenler `(i,j)` ve `(k,l)` ise, `i`'nin karşısı `j`'dir. O halde `i`'ye komşu
köşeler `k` ve `l`'dir — yani `i-k` ve `i-l` iki **bitişik kenardır**, biri 32 diğeri
40 olmalı. Kod `sorted()` ile hangisinin hangisi olduğunu bilmeden eşleştiriyor,
bu doğru: dikdörtgenin yönelimi önemli değil.

---

## Çıktı ve havuz davranışı

```python
return feet, ayak_noktalari, ayak_disi                     # :655
```

Üç değer döner ama `count_order` şunu yapıyor:

```python
ayak_bu_parca, ayak_noktalari, ayak_disi = extract_ayak_feet(part_ahsap_centers)
ayak += ayak_bu_parca
...
remaining_ahsap = ayak_noktalari + ayak_disi               # :950  ← HEPSİ geri birleşiyor
counts["ahsapcivisi"] += len(remaining_ahsap)              # :951
```

Yani **ayak vidaları ağaç vidası havuzundan DÜŞMÜYOR** — ayrılıp hemen geri
birleştiriliyor. Bu bilinçli: ayağın vidaları da kitte gönderilen ağaç vidalarıdır.

Ayrımın tek amacı **ray tespitinden korumaktı** (tarihsel). Ray artık ayrı havuzda
çalıştığı için bu koruma yapısal olarak gereksiz — kod yorumu da bunu kabul ediyor
(satır 636-642), ama ayrım yine de duruyor.

---

## Türetmeler

```python
"Ayarlı Ayak": ayak,                                       # :997
"Allen":       1 if ayak >= 1 else 0,                      # :998
"Tıpa":        ayak,                                       # :999
```

| Parça | Kural | Mantık |
|---|---|---|
| Allen | Ayak varsa **1**, yoksa 0 | Ayakları ayarlamak için tek anahtar yeter |
| Tıpa | Ayak sayısına eşit | Her ayak deliğinin üstüne 1 tıpa |

---

## Sabitler (satır 207-212)

| Sabit | Değer | Anlamı |
|---|---|---|
| `AYAK_KENAR_A_MM` | 32.0 | Kısa kenar |
| `AYAK_KENAR_B_MM` | 40.0 | Uzun kenar |
| `_AYAK_DIAG_MM` | 51.22 | `hypot(32, 40)` — koddan hesaplanır |
| `AYAK_KENAR_TOL_PCT` | 0.03 | %3 bağıl tolerans |
| `AYAK_SCALE_MM` | 1000.0 | Dünya birimi → mm |

Kalibrasyon: `iki_obje_mesafe.py` ile Object_55 üzerinde ölçüldü.

---

## Bilinen zayıflıklar

**1. ⚠️ Allen bölünmüş siparişlerde çift sayılıyor.**
`Allen = 1 if ayak >= 1` her **FBX** için ayrı hesaplanıyor. 9360 siparişi
`9360-1.fbx` + `9360-2.fbx` diye ikiye bölündüğü için **2 Allen** üretti; referans 1.
Toplam tabloda bu, 9364-2'deki −1 ile birbirini götürüp fark 0 gösteriyor — yani
**iki gerçek hata birbirini maskeliyor**.

> Aynı sorun sipariş bazlı olan her sabit için geçerli: `L Bağlantı Seti = 2` de
> bölünmüş siparişlerde 4 oluyor.

**2. Tek ayak modeli destekleniyor.**
32×40 mm dışında bir ayak (farklı marka/model) hiç bulunmaz. `_AYAK_DIAG_MM` tek bir
değer; birden fazla model için liste gerekirdi.

**3. Karmaşıklık O(H²) + O(D²).**
`D` = aday köşegen sayısı. 51.22 mm civarında çok vida varsa aday sayısı patlar ve
ikinci döngü kareleşir. Şu an sorun değil.

**4. 9364-2'de ayak 0, referans 2.**
Kulp/Allen/Tıpa da aynı siparişte sıfır. Bkz. [07-kulp.md](07-kulp.md) →
"Bilinen zayıflıklar" — muhtemelen panel düzeyinde bir delik tarama başarısızlığı,
tek bir algoritmanın hatası değil.

**5. Çivili Ayak diye ayrı bir parça var ve sistemde hiç yok.**
Referans BoM her siparişte "Çivili Ayak" (4 veya 8) listeliyor. Ayarlı Ayak'tan
farklı bir parça. Kodda hiçbir yerde geçmiyor → 10 siparişte toplam **−44**.
Bu bir hata değil, **eksik özellik**.
