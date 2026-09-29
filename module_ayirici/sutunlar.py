"""sutunlar.py — modül sütunları ve duvar bağlantı braketi sayısı (saf Python, bpy yok)
====================================================================================

Sütun: önden bakınca aynı yatay aralıkta üst üste duran modüller (1–3 modül).
Kural (Kerem, 2026-09-29): duvar bağlantı braketi = 2 × sütun — her sütunun en üst
modülüne bir sol + bir sağ braket (delikbulma.py'deki solduvarbag/sagduvarbag).
Siparişte bu braket "L Bağlantı Seti" kalemi olarak çıkar (parca_sayim.py).

Girdi yalnız modül kutularıdır: her modülde `lo`/`hi` (mm, dünya ekseni; 0=x, 1=y,
2=z yukarı). module_segmenter.segment() çıktısındaki `modules` listesi de,
modules.jsonl satırları da doğrudan verilebilir. Parça adı hiç kullanılmaz; bu
yüzden `Object_N` adlı siparişlerde de, adlı siparişlerde de aynı çalışır.

Yöntem: iki modülün plan izdüşümleri (x ve y) her iki eksende de dar olanın
genişliğinin en az SUTUN_ORTUSME_ORANI kadarı örtüşüyorsa aynı sütundadır. Bu
ilişkinin geçişli kapanışı (birleşim-bul) sütunları verir. Düz bir dizide y
örtüşmesi hep tamdır ve kural "x aralığı örtüşüyor mu" sorusuna iner; y şartı
köşe (L) dizilimde diğer koldaki modülün x'te örtüşüp yine de ayrı sütun olmasını
korur.
"""

# ── Eşikler ──────────────────────────────────────────────────────────────────
# Aynı sütun sayılmak için plan örtüşmesinin, iki modülden DAR olanın o eksendeki
# boyuna oranı. Ölçüm (2026-09-29, 2026-09-27-parca-testleri/modules.jsonl, 281
# sipariş / 471 modül, sipariş içi bütün modül çiftleri): x oranı ya ≤ 1.5e-7
# (yan yana, yalnız yüzey teması) ya da tam 1.0 (üst üste) — arada hiçbir değer
# yok. 0.5 bu boşluğun ortası: iki yana da 0.5'lik pay bırakır, üst modül alttakinden
# biraz dar/kaydırılmış olsa da (oran < 1) ya da komşu yan duvarlar birkaç mm
# bindirilmiş olsa da (oran > 0) karar değişmez.
SUTUN_ORTUSME_ORANI = 0.5

# Kerem, 2026-09-29: her sütunun en üst modülüne sol + sağ = 2 braket.
BRAKET_PER_SUTUN = 2


def _kutu(m):
    return m["lo"], m["hi"]


def _ortusme_orani(a, b, k):
    """k ekseninde örtüşme / dar olanın boyu. Temas ya da boşluk → ≤ 0."""
    (alo, ahi), (blo, bhi) = _kutu(a), _kutu(b)
    dar = min(ahi[k] - alo[k], bhi[k] - blo[k])
    if dar <= 0:
        return 0.0
    return (min(ahi[k], bhi[k]) - max(alo[k], blo[k])) / dar


def ayni_sutun(a, b, oran=SUTUN_ORTUSME_ORANI):
    """İki modül aynı sütunda mı? (plan x ve y örtüşmesi ikisi de ≥ oran)"""
    return _ortusme_orani(a, b, 0) >= oran and _ortusme_orani(a, b, 1) >= oran


def sutunlari_bul(moduller, oran=SUTUN_ORTUSME_ORANI):
    """Modül listesini sütunlara ayır.

    Dönüş: sütun listesi; her sütun modül İNDEKSLERİNİN listesi, alttan üste
    (lo z) sıralı. Sütunlar soldan sağa (en küçük lo x, sonra lo y) sıralı.
    """
    n = len(moduller)
    ata = list(range(n))

    def bul(i):
        while ata[i] != i:
            ata[i] = ata[ata[i]]
            i = ata[i]
        return i

    for i in range(n):
        for j in range(i + 1, n):
            if ayni_sutun(moduller[i], moduller[j], oran):
                ata[bul(i)] = bul(j)
    gruplar = {}
    for i in range(n):
        gruplar.setdefault(bul(i), []).append(i)
    sutun = [sorted(g, key=lambda i: moduller[i]["lo"][2]) for g in gruplar.values()]
    sutun.sort(key=lambda g: (min(moduller[i]["lo"][0] for i in g),
                              min(moduller[i]["lo"][1] for i in g)))
    return sutun


def duvar_braketi_sayisi(sutun_sayisi):
    """Duvar bağlantı braketi = BRAKET_PER_SUTUN × sütun."""
    return BRAKET_PER_SUTUN * sutun_sayisi
