# 14 — Renk Tespiti

| | |
|---|---|
| **Kod** | `siparis_rengi_belirle()` — satır 789-823<br>`_renk_json_yolu()` — satır 770-786 |
| **Girdi** | `renkler/<sipariş>.json` (FBX değil — **ayrı bir dosya**) |
| **Ürettiği çıktı** | Linco Gövde, Linco Kapak, Tıpa renkleri |
| **Doğruluk** | ⚪ Test edilemedi — `renkler/` klasörü mevcut değil |

---

## Problem

BoM'da bazı kalemler renge göre ayrı satırda:

```
Linco Gövde (BEYAZ)     ...
Linco Gövde (GRİ)       ...
Beyaz Tıpa              ...
Siyah Tıpa              ...
Kahverengi Tıpa         ...
```

Renk bilgisi **geometride yok** — bir deliğe bakarak takılacak parçanın rengi
anlaşılamaz. Bu yüzden bu, diğerlerinden farklı bir algoritma: **geometri değil,
veri eşleştirme**.

---

## Veri kaynağı

Mert, FBX'in yanında parça başına renk kodu içeren ayrı bir JSON yüklüyor:

```json
{
  "parcalar": [
    { "user_data": { "renk": "0" }, ... },
    { "user_data": { "renk": "0" }, ... },
    { "user_data": { "renk": "2" }, ... }
  ]
}
```

| Kod | Renk |
|---|---|
| `"0"` | Beyaz |
| `"1"` | Meşe |
| `"2"` | Gri |

---

## Adım 1 — Dosyayı bul (`_renk_json_yolu`)

```
1. Tam eşleşme dene:   renkler/<sipariş>.json                :771-773
2. Bulamazsan klasörü tara:                                  :776-785
     her .json dosyası için:
       ad içindeki ilk 4+ haneli sayıyı çıkar    (order_from_name ile AYNI regex)
       sipariş no ile eşleşiyorsa → o dosya
3. Hiçbiri yoksa → None
```

İkinci adım pratik bir çözüm: Mert'in yüklediği dosya adı
`9307-2-mert c..json` gibi fazladan metin içerebiliyor. Aynı regex
(`\d{4,}(?:-\d+)?`) hem FBX hem renk dosyası için kullanılıyor — tutarlı.

---

## Adım 2 — Baskın rengi bul

```python
kodlar = Counter()                                          :804-808
for parca in ham.get("parcalar") or []:
    kod = (parca.get("user_data") or {}).get("renk")
    if kod is not None:
        kodlar[str(kod)] += 1

baskin_kod, _ = kodlar.most_common(1)[0]                    :812
```

**Siparişin rengi = parçalar arasında en çok geçen kod.** Sipariş bazında tek renk
belirleniyor, parça bazında değil.

> Bu bilinçli bir basitleştirme: bir dolabın gövdesi ve kapakları genelde aynı renk.
> Karma renkli bir sipariş gelirse azınlıkta kalan renk sessizce kaybolur.

---

## Adım 3 — Parça renklerini eşle

```python
PARCA_RENK_KURALI = {                                       # :149-153
    "Beyaz": {"Linco Gövde": "Beyaz",  "Linco Kapak": "Beyaz",  "Tıpa": "Beyaz"},
    "Meşe":  {"Linco Gövde": "Siyah",  "Linco Kapak": "Siyah",  "Tıpa": "Kahverengi"},
    "Gri":   {"Linco Gövde": "Siyah",  "Linco Kapak": "Siyah",  "Tıpa": "Siyah"},
}
```

| Sipariş rengi | Linco (Gövde/Kapak) | Tıpa |
|---|---|---|
| Beyaz | Beyaz | Beyaz |
| Meşe | **Siyah** | Kahverengi |
| Gri | **Siyah** | Siyah |

Dikkat: beyaz olmayan her mobilyada linco **siyah** kullanılıyor — yani linco rengi
mobilya rengiyle birebir değil, bir eşleme tablosuyla belirleniyor.

**Minifix ve Linco Dübel renklendirilmiyor** — montajdan sonra görünmüyorlar.

---

## Çıktı

```python
return {                                                    # :818-823
    "siparis_rengi_kodu": baskin_kod,
    "siparis_rengi": ad,
    "kaynak_dosya": os.path.basename(yol),
    "parca_renkleri": dict(PARCA_RENK_KURALI[ad]),
}
```

JSON'da `"renk"` alanına yazılır. Dosya yoksa **`null`** kalır ve PDF/panel bunu
sessizce atlar — miktar hesabı etkilenmez.

Şu anki durum: işlenmiş tüm siparişlerde `"renk": null` (klasör mevcut değil).

---

## Hata toleransı

Bu, kodun **en savunmacı** bölümü — üç ayrı noktada zarif başarısızlık var:

| Durum | Davranış | Satır |
|---|---|---|
| Dosya yok | `None` dön, sessiz | 795-796 |
| JSON bozuk | `[UYARI]` bas, `None` dön | 800-802 |
| Hiç renk kodu yok | `None` dön, sessiz | 809-810 |
| Tanınmayan kod | `[UYARI]` bas, `None` dön | 814-816 |

Renk verisi henüz yüklenmemiş olması **normal bir durum** olduğu için bu doğru
tasarım — sayım işi renk yüzünden durmuyor.

---

## Bilinen zayıflıklar

**1. Hiç test edilmedi.**
`renkler/` klasörü projede yok. Kod yolu bir kez bile çalışmamış olabilir.

**2. Baskın renk mantığı karma siparişlerde yanlış.**
İki renkli bir sipariş (ör. beyaz gövde + meşe kapak) tek renge indirgeniyor.
Referans BoM ise aynı siparişte hem "Linco Gövde (BEYAZ)" hem "Linco Gövde (GRİ)"
satırları taşıyabiliyor — yani gerçek dünyada karma sipariş **var**.

> 9355'in referans BoM'unda Linco Gövde (BEYAZ) = 0, (GRİ) = 33; 9356'da tersi
> (BEYAZ 21, GRİ 0). Bu siparişlerde tek renk, ama yapı karma siparişi destekliyor.

**3. Sayım ile renk arasında bağ yok.**
Renk, adetleri **bölmüyor**. BoM'da "Linco Gövde (BEYAZ) 21 / (GRİ) 0" gibi iki satır
varken sistem tek bir "Linco Gövde: 21" üretip rengi ayrı alanda veriyor. PDF'in bunu
nasıl ikiye ayırdığı `pdf_uret.py`'de kontrol edilmeli.

**4. `parcalar` anahtarı sabit varsayılıyor.**
Mert'in JSON şeması değişirse (`parcalar` → `parts` gibi) fonksiyon sessizce `None`
döner, hiçbir uyarı basmaz — çünkü `ham.get("parcalar") or []` boş listeye düşer ve
"hiç renk kodu yok" dalına girer.
