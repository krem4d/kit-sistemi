# Arkalık Paneli Tespiti + Arkalık Çivisi Sayımı

Bu doküman `parca_sayim.py` içindeki iki iç içe geçmiş mekanizmayı anlatır:
1. Bir parçanın **arkalık paneli** olup olmadığını anlayıp onu (delik taraması
   yapmadan) **tek parça** olarak bırakan tespit adımı.
2. O tek parça arkalık panelinin çevresine kaç **çivi** dizildiğini geometriden
   hesaplayan formül.

İlgili kod: `parca_sayim.py` satır 109-112 (sabitler), 609-625 (fonksiyonlar),
691-696 (count_order içindeki kullanım yeri).

---

## 1) Arkalığı "tek parça" bırakan tespit algoritması

Normal şartlarda `count_order()` sahnedeki her mesh parçasını çift-boolean
(`execute_double_boolean`) ile içindeki **deliklere** ayırıp, her deliğin
hacmine bakarak kategori (ahşap vidası, linco, modül bağlantı, kulp vidası...)
belirler. Yani normal bir parça "delik deliğine" parçalanıp incelenir.

Arkalık paneli (dolabın arka MDF'i) bu işlemden **muaf tutulur** — hiç
delik taramasına sokulmadan, geometrisi bozulmadan **tek bir bütün parça**
olarak ele alınır ve doğrudan bir formülle çivi sayısına çevrilir. Bunun
nedeni: arkalık panelinde delik yerine çevresine dizilmiş çiviler var; onu
diğer parçalar gibi delik-hacmi mantığıyla incelemenin bir anlamı yok.

### Nasıl ayırt ediliyor: kalınlık eşiği

```python
ARKALIK_MAX_KALINLIK = 8.0   # en kısa kenar <= bu ise arkalık paneli sayılır
```

Bu eşik `kalinlik_bul.py` adlı ayrı bir ölçüm aracıyla ampirik olarak
bulundu: gerçek modellerde **arkalık paneli ~5.0 mm**, **gövde panelleri
~18.0 mm** kalınlığında çıktı — aralarında net bir boşluk var, `8.0` bu
boşluğun ortasında güvenli bir sınır.

`part_thickness(obj)`:
```python
def part_thickness(obj):
    """Parçanın en kısa kenarı (MDF kalınlığı), yerel uzayda."""
    dim, _ = get_perfect_local_bounds(obj)
    if dim is None:
        return None
    return min(dim.x, dim.y, dim.z)
```
`get_perfect_local_bounds` parçanın **yerel (object-space) vertex
bounding-box**'ını hesaplar (x/y/z aralıkları). Bir MDF panel için üç
kenardan en kısası her zaman panelin kalınlığıdır (diğer ikisi panelin
genişlik/yükseklik gibi büyük kenarlarıdır) — bu yüzden `min(dim.x,dim.y,dim.z)`
doğrudan "MDF kalınlığı" anlamına gelir.

### count_order() içindeki karar noktası

```python
for o in meshes:
    # Arkalık paneli mi? (kalınlıktan) → çivi say, delik taramasını atla
    th = part_thickness(o)
    if th is not None and th <= ARKALIK_MAX_KALINLIK:
        arkalik_civi += arkalik_civi_count(o)
        continue          # <-- bu parça için delik taraması hiç yapılmaz

    # buradan sonrası SADECE arkalık olmayan parçalar için çalışır
    holes = execute_double_boolean(o)
    ...
```

`continue` satırı kritik: kalınlığı eşiğin altında bulunan parça, döngünün
geri kalanına (delik ayıklama / hacim-kategori eşleme) hiç girmeden bir
sonraki parçaya geçilir. Yani "tek parça yapma" aslında bir **bypass**'tır —
parça bölünüp incelenmez, olduğu gibi (tek obje) `arkalik_civi_count()`'a
verilir.

---

## 2) Arkalık çivisi sayma formülü

```python
CIVI_ARALIK_MM = 150.0   # arkalık çivisi aralığı (orijinal 0.15 m kuralının mm karşılığı)

def arkalik_civi_count(obj):
    """Arkalık panelinin çevresine CIVI_ARALIK_MM aralıkla dizilen çivi sayısı
    (delikbulma.py 0.15 m kuralının mm karşılığı: 2*num_x + 2*num_z)."""
    dim, _ = get_perfect_local_bounds(obj)
    dims = sorted([dim.x, dim.y, dim.z])
    W, H = dims[2], dims[1]      # iki büyük kenar (kalınlık hariç)
    nx = max(1, math.ceil(W / CIVI_ARALIK_MM))
    nz = max(1, math.ceil(H / CIVI_ARALIK_MM))
    return 2 * nx + 2 * nz
```

Adım adım:

1. `get_perfect_local_bounds(obj)` ile panelin 3 boyutu alınır ve küçükten
   büyüğe sıralanır: `dims = sorted([x, y, z])`.
   - `dims[0]` = kalınlık (zaten `part_thickness` ile eşiğin altında olduğu
     doğrulanmış, burada artık kullanılmıyor).
   - `dims[1]` ve `dims[2]` = panelin **genişlik** ve **yükseklik**i (`W`, `H`).
2. Her büyük kenar, `CIVI_ARALIK_MM = 150.0` mm aralıkla bölünüyor:
   - `nx = ceil(W / 150)` → o kenar boyunca kaç aralık/çivi hizası düştüğü.
   - `nz = ceil(H / 150)` → diğer kenar için aynısı.
   - `max(1, ...)` ile en küçük panelde bile en az 1 çivi hizası garanti
     edilir (kenar 150 mm'den kısa olsa bile sıfıra düşmesin diye).
3. Toplam çivi = **iki paralel kenarın her biri için `nx` çivi + diğer iki
   paralel kenarın her biri için `nz` çivi** → `2*nx + 2*nz`. Yani panelin
   dört kenarına da (üst-alt, sağ-sol) aynı aralık kuralı ayrı ayrı
   uygulanıp toplanıyor; gerçek çivi delikleri taranmıyor, tamamen
   **geometriden türetilen bir tahmin** (perimetre / 150mm mantığı).

### Örnek

Bir arkalık paneli 640 mm × 320 mm ise:
- `nx = ceil(640/150) = 5`
- `nz = ceil(320/150) = 3`
- çivi = `2*5 + 2*3 = 16`

### count_order() içinde toplanması

Sahnedeki her arkalık paneli için `arkalik_civi_count()` çağrılıp
`arkalik_civi` değişkenine eklenir (birden fazla arkalık paneli olabilir —
ör. bölmeli dolaplarda); sipariş sonunda tek bir `"Arkalık Çivisi"` alanı
olarak çıktıya yazılır (satır ~804), ve ağırlık hesabına da `"Çivi"` adı
altında katılır (satır ~817).

---

## Özet — neden bu iki şeyin birlikte anlatılması gerekiyor

Arkalık çivisi sayısı, arkalık panelinin **delik hacimlerinden değil**,
panelin **dış boyutlarından** (genişlik × yükseklik) türetiliyor. Bunun
çalışabilmesi için önce o panelin delik-tarama işlemine hiç sokulmadan
**bütün/tek parça** halinde kalması gerekiyor — çünkü `execute_double_boolean`
parçayı iç deliklerine ayırıp orijinal dış boyutunu kaybettirir. Kalınlık
eşiği (`ARKALIK_MAX_KALINLIK`) bu ayrımı yapan anahtar, `continue` bunu
uygulayan mekanizma, `arkalik_civi_count` da sonucu üreten formüldür.
