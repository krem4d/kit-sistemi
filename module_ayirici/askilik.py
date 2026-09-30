"""askilik.py — askılık borusu boyu: karşılıklı flanş eşleştirme (saf Python, bpy yok)
================================================================================

Kural (Kerem, 2026-09-29):
  Aynı modülde, X ya da Y ekseni boyunca birbirine BAKAN iki askılık flanşı = 1 boru.
  Boru boyu = iki panelin İÇ yüzeylerinin (birbirine bakan yüzlerinin) ORTA
  noktaları arasındaki Öklid mesafesi − ASKILIK_KESINTI_MM (1 cm), sonra tam cm'ye
  yarım-yukarı yuvarlanır (math.floor(x + 0.5); Python round() çifte yuvarlar,
  kullanılmaz).

İki flanş birbirine bakar ⇔
  1) farklı panellerde ve aynı modüldeler (modül bilinmiyorsa eşleşmez),
  2) iki panelin de normali (bbox'un ince ekseni) aynı eksen k ∈ {x, y},
  3) flanş merkezleri (üçgen ağırlık merkezi) diğer iki koordinatta
     ASKILIK_HIZA_TOL_MM içinde hizalı,
  4) paneller k ekseninde ayrık (arada boşluk var) ve her flanş kendi panelinin
     öbür panele bakan yüzünde (dış yüzde değil).
Adaylar iç yüzeyler arası k-boşluğu küçükten büyüğe greedy eşlenir; her flanş en
fazla bir boruda kullanılır (panel-bölme-panel dizisinde doğru komşu seçilir).

Girdi bpy'siz sade veridir; Blender tarafı (parca_sayim.py) flanşları üretir.
Birimler: mm, dünya ekseni (0=x, 1=y, 2=z yukarı).
"""
import math

# ── Sabitler ─────────────────────────────────────────────────────────────────
ASKILIK_KESINTI_MM = 10.0   # Kerem: yüzey-merkez mesafesinden 1 cm düşülür
MM_PER_CM = 10.0
# Karşılıklı iki flanşın merkezleri diğer iki eksende bu kadar içinde olmalı.
# Aynı modülde iki boru arası dikey mesafe yüzlerce mm; aynı borunun iki flanşı
# korpusta birebir aynı y/z'de (sapma 0). 15 mm hem model kaymalarına pay bırakır
# hem flanşın kendi yarı genişliğinin (25 mm) altında kalır.
ASKILIK_HIZA_TOL_MM = 15.0
# Flanş "iç yüzde" sayılır: merkezi iç yüze, dış yüze olduğundan en fazla bu kadar
# uzak olabilir (karşıya çıkan delikte merkez panel ortasında → eşit uzaklık).
ASKILIK_YUZ_PAYI_MM = 1.0
BORU_EKSENLERI = (0, 1)     # yalnız X ve Y (boru yatay)
EKSEN_ADI = "xyz"


def yarim_yukari(x):
    """Yarım-yukarı yuvarlama (x.5 → yukarı). round() banker yuvarlaması yapar."""
    return int(math.floor(x + 0.5))


def boru_boyu_cm(ham_mm):
    """Yüzey-merkez mesafesi (mm) → kesilecek boru boyu (tam cm)."""
    return yarim_yukari((ham_mm - ASKILIK_KESINTI_MM) / MM_PER_CM)


def ucgen_merkezi(p1, p2, p3):
    """Üç noktanın ağırlık merkezi."""
    return [(p1[i] + p2[i] + p3[i]) / 3.0 for i in range(3)]


def normal_ekseni(lo, hi):
    """Panel bbox'unun ince ekseni (panelin normali)."""
    d = [hi[i] - lo[i] for i in range(3)]
    return min(range(3), key=lambda i: d[i])


def ic_yuz_merkezi(lo, hi, k, isaret):
    """Panelin k-normalli yüzünün orta noktası. isaret=+1 → hi yüzü, −1 → lo yüzü."""
    p = [(lo[i] + hi[i]) / 2.0 for i in range(3)]
    p[k] = hi[k] if isaret > 0 else lo[k]
    return p


def _mesafe(a, b):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def _aday(fa, fb, k, hiza_tol):
    """fa ile fb, k ekseninde birbirine bakıyor mu? Evet ise aday çifti döndür."""
    if fa["pano"] == fb["pano"]:
        return None
    if fa.get("modul") is None or fa.get("modul") != fb.get("modul"):
        return None
    if normal_ekseni(fa["pano_lo"], fa["pano_hi"]) != k:
        return None
    if normal_ekseni(fb["pano_lo"], fb["pano_hi"]) != k:
        return None
    ca, cb = fa["merkez"], fb["merkez"]
    if any(abs(ca[i] - cb[i]) > hiza_tol for i in range(3) if i != k):
        return None
    # a k ekseninde b'nin "altında" olsun (gerekirse yer değiştir)
    if ca[k] > cb[k]:
        fa, fb, ca, cb = fb, fa, cb, ca
    alo, ahi, blo, bhi = fa["pano_lo"], fa["pano_hi"], fb["pano_lo"], fb["pano_hi"]
    bosluk = blo[k] - ahi[k]          # a'nın +k (iç) yüzü ↔ b'nin −k (iç) yüzü
    if bosluk <= 0:
        return None                   # paneller ayrık değil (iç içe/üst üste)
    # her flanş kendi panelinin iç yüzünde mi? (dış yüzdeki flanş başka boruya ait)
    if abs(ca[k] - ahi[k]) > abs(ca[k] - alo[k]) + ASKILIK_YUZ_PAYI_MM:
        return None
    if abs(cb[k] - blo[k]) > abs(cb[k] - bhi[k]) + ASKILIK_YUZ_PAYI_MM:
        return None
    pa = ic_yuz_merkezi(alo, ahi, k, +1)
    pb = ic_yuz_merkezi(blo, bhi, k, -1)
    return dict(a=fa, b=fb, k=k, bosluk=bosluk, pa=pa, pb=pb, ham=_mesafe(pa, pb))


def eslestir(flanslar, hiza_tol=ASKILIK_HIZA_TOL_MM):
    """Flanş listesini borulara eşle.

    flanslar: [{"merkez": [x,y,z], "pano": ad, "modul": "M01"|None,
                "pano_lo": [..], "pano_hi": [..]}, ...]  (mm)
    Dönüş: (borular, eslesmeyenler)
      borular      [{"uzunluk_cm", "modul", "eksen", "ham_mm", "eksen_boslugu_mm",
                     "flanslar", "panolar"}]  uzunluk büyükten küçüğe
      eslesmeyenler [{"merkez", "pano", "modul", "neden"}]
    """
    adaylar = []
    for i in range(len(flanslar)):
        for j in range(i + 1, len(flanslar)):
            for k in BORU_EKSENLERI:
                c = _aday(flanslar[i], flanslar[j], k, hiza_tol)
                if c:
                    c["ij"] = (i, j)
                    adaylar.append(c)
    adaylar.sort(key=lambda c: (c["bosluk"], c["ham"]))
    kullanildi = set()
    borular = []
    for c in adaylar:
        i, j = c["ij"]
        if i in kullanildi or j in kullanildi:
            continue
        kullanildi.update((i, j))
        borular.append(dict(
            uzunluk_cm=boru_boyu_cm(c["ham"]),
            modul=c["a"]["modul"],
            eksen=EKSEN_ADI[c["k"]],
            ham_mm=round(c["ham"], 1),
            eksen_boslugu_mm=round(c["bosluk"], 1),
            flanslar=[[round(v, 1) for v in c["a"]["merkez"]],
                      [round(v, 1) for v in c["b"]["merkez"]]],
            panolar=[c["a"]["pano"], c["b"]["pano"]],
        ))
    borular.sort(key=lambda b: (-b["uzunluk_cm"], b["modul"] or "", b["flanslar"][0][2]))
    eslesmeyenler = []
    for i, f in enumerate(flanslar):
        if i in kullanildi:
            continue
        eslesmeyenler.append(dict(
            merkez=[round(v, 1) for v in f["merkez"]],
            pano=f["pano"],
            modul=f.get("modul"),
            neden="modul_yok" if f.get("modul") is None else "karsi_flans_yok",
        ))
    return borular, eslesmeyenler


def ozet(borular, eslesmeyenler, flans_adedi):
    """JSON'a yazılacak eşleşme özeti; adet anlamı değişmez (flanş // 2)."""
    beklenen = flans_adedi // 2
    return dict(
        flans=flans_adedi,
        eslesen_boru=len(borular),
        beklenen_boru=beklenen,
        tutarli=len(borular) == beklenen and not eslesmeyenler,
        eslesmeyen_flanslar=eslesmeyenler,
    )


BILINMEYEN_BOY = "?"   # boyu bulunamayan boruların satır etiketi


def boy_satirlari(adet, borular):
    """Askılık Borusu'nu boy başına satırlara böler (PDF + panel):
    [("96", 2), ("66", 1), ("?", 1)] → "Askılık Borusu 96 cm — 2 adet" vb.
    Büyükten küçüğe; boyu bulunamayan borular (adet − eşleşen boru) en sonda
    BILINMEYEN_BOY satırında. Satır toplamı her zaman `adet`tir (JSON
    adet["Askılık Borusu"]); her çift 2 flanş kullandığından eşleşen boru adedi
    flanş // 2'yi aşamaz. adet 0/None → [] (satır yok)."""
    if not adet:
        return []
    boylar = [b["uzunluk_cm"] for b in (borular or [])]
    satirlar = [(str(L), boylar.count(L)) for L in sorted(set(boylar), reverse=True)]
    eksik = adet - len(boylar)
    if eksik > 0:
        satirlar.append((BILINMEYEN_BOY, eksik))
    return satirlar
