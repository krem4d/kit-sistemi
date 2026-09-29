"""Korpus karşılaştırması: boru hattının sütun sayısı ↔ modules.jsonl'den bağımsız sayım.

Çalıştırma (sistem Python, Blender gerekmez):
  python3 tests/sutun_korpus_karsilastir.py <sutun_korpus.py çıktı dizini>

A  = boru hattı: FBX → prepare_unique_parts → module_segmenter → sutunlar.py
     (tests/sutun_korpus.py'nin yazdığı sonuc-*.jsonl).
B  = bağımsız referans, yalnız modules.jsonl bbox'larından ve FARKLI bir
     tanımla: "sütun sayısı = modül sayısı − başka bir modülün ÜSTÜNE oturan
     modül sayısı". Oturma: alt modülün tavanı ile üst modülün tabanı arasında
     ≤ OTURMA_Z_MM fark ve plan izdüşümünde (x ve y) > OTURMA_PLAN_MM örtüşme.
     Örtüşme oranı / birleşim-bul kullanılmaz; sutunlar.py'ye dokunmaz.
C  = sutunlar.py modules.jsonl kutularına uygulanır — A↔B farkı ayırıcıdan mı
     (modül kutuları farklı) yoksa sütun kuralından mı geliyor, onu ayırır.

Çıkış kodu: sütun kuralından doğan bir uyuşmazlık (A≠B iken kutular aynı, ya da A≠B_A)
veya koşulmamış sipariş varsa 1. Modül kutuları modules.jsonl ile farklıysa (FBX
revizyonu) A≠B raporlanır ama tek başına hata sayılmaz; o siparişte kural B_A ile sınanır.
"""
import glob
import json
import os
import sys
from collections import Counter, defaultdict

sys.dont_write_bytecode = True
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "module_ayirici"))
import sutunlar  # noqa: E402

KORPUS_DIZINI = os.environ.get(
    "KORPUS_DIZINI",
    "/home/rocket/Jupiter/Efforts/otonom_kit/2026-09-09-son-50-modul-incelemesi/2026-09-27-parca-testleri")

OTURMA_Z_MM = 1.0      # alt tavan ↔ üst taban: korpusta fark ≤ 0.0004 mm
OTURMA_PLAN_MM = 1.0   # yalnız kenar teması (≈0 mm) oturma sayılmasın
KUTU_TOL_MM = 1.0      # A ve modules.jsonl kutuları "aynı modül" eşiği

# Önceden bilinen, testin kurgusunu değiştirmeyen istisnalar (görev tanımı,
# 2026-09-29): iki dolap tek modül sayılmış. Sütun sayısına etkisi ayrıca raporlanır.
BILINEN_ISTISNA = {"9020", "9155"}


def modules_jsonl():
    by = defaultdict(list)
    with open(os.path.join(KORPUS_DIZINI, "modules.jsonl"), encoding="utf-8") as f:
        for satir in f:
            if satir.strip():
                m = json.loads(satir)
                by[m["order"]].append(m)
    return by


def ortusme(a, b, k):
    return min(a["hi"][k], b["hi"][k]) - max(a["lo"][k], b["lo"][k])


def bagimsiz_sutun(moduller):
    """B: modül − (başka modülün üstüne oturan modül)."""
    ustte = 0
    for m in moduller:
        if any(n is not m and abs(n["hi"][2] - m["lo"][2]) <= OTURMA_Z_MM
               and ortusme(m, n, 0) > OTURMA_PLAN_MM and ortusme(m, n, 1) > OTURMA_PLAN_MM
               for n in moduller):
            ustte += 1
    return len(moduller) - ustte


def kutular_ayni(a_kutular, ref):
    """A'nın modül kutuları ile modules.jsonl kutuları birebir eşleşiyor mu?"""
    kalan = [dict(lo=m["lo"], hi=m["hi"]) for m in ref]
    for k in a_kutular.values():
        for i, r in enumerate(kalan):
            if all(abs(k[s][j] - r[s][j]) <= KUTU_TOL_MM for s in ("lo", "hi") for j in range(3)):
                del kalan[i]
                break
        else:
            return False
    return not kalan


def main(dizin):
    ref = modules_jsonl()
    a = {}
    for yol in glob.glob(os.path.join(dizin, "sonuc-*.jsonl")):
        with open(yol, encoding="utf-8") as f:
            for satir in f:
                r = json.loads(satir)
                a[r["siparis"]] = r
    satirlar = []
    for o in sorted(ref):
        B = bagimsiz_sutun(ref[o])
        C = len(sutunlar.sutunlari_bul(ref[o]))
        r = a.get(o)
        if r is None or not r.get("ok"):
            satirlar.append(dict(siparis=o, durum="FBX_YOK" if r and r.get("hata") == "FBX yok" else "KOSULMADI",
                                 B=B, C=C, ref_modul=len(ref[o])))
            continue
        A = r["sutun_sayisi"]
        # B_A: aynı bağımsız tanım, bu kez A'nın KENDİ modül kutularına uygulanır —
        # modules.jsonl ile FBX farklı revizyonsa sütun kuralını yine sınar.
        B_A = bagimsiz_sutun([dict(lo=k["lo"], hi=k["hi"]) for k in r["kutular"].values()])
        ayni_kutu = kutular_ayni(r["kutular"], ref[o])
        if A == B:
            durum = "UYUSTU"
        elif o in BILINEN_ISTISNA:
            durum = "BILINEN_ISTISNA"
        elif not ayni_kutu:
            durum = "UYUSMADI_MODUL_KUTULARI_FARKLI"
        else:
            durum = "UYUSMADI_SUTUN_KURALI"
        satirlar.append(dict(siparis=o, durum=durum, A=A, B=B, B_A=B_A, C=C, A_modul=r["modul_sayisi"],
                             ref_modul=len(ref[o]), kutu_ayni=ayni_kutu, kaynak=r["kaynak"],
                             braket=r["braket"], kaynak_degismedi=r.get("kaynak_degismedi")))
    say = Counter(s["durum"] for s in satirlar)
    kosulan = [s for s in satirlar if "A" in s]
    print("== Korpus sütun karşılaştırması")
    print(f"sipariş (modules.jsonl): {len(satirlar)}  koşulan: {len(kosulan)}")
    for k, v in sorted(say.items()):
        print(f"  {k:34s} {v}")
    print(f"C (sutunlar.py, modules.jsonl kutuları) == B: "
          f"{sum(s['C'] == s['B'] for s in satirlar)}/{len(satirlar)}")
    print(f"A == B_A (bağımsız tanım, A'nın kendi kutuları): "
          f"{sum(s['A'] == s['B_A'] for s in kosulan)}/{len(kosulan)}")
    print(f"A modül kutuları == modules.jsonl: {sum(s['kutu_ayni'] for s in kosulan)}/{len(kosulan)}")
    print(f"kaynak=geometri: {sum(s['kaynak'] == 'geometri' for s in kosulan)}/{len(kosulan)}; "
          f"kaynak FBX değişmedi: {sum(bool(s['kaynak_degismedi']) for s in kosulan)}/{len(kosulan)}")
    print("sütun dağılımı (A):", sorted(Counter(s["A"] for s in kosulan).items()))
    print("braket dağılımı (A):", sorted(Counter(s["braket"] for s in kosulan).items()))
    print("-- uyuşmazlıklar / koşulamayanlar")
    for s in satirlar:
        if s["durum"] != "UYUSTU":
            print("  ", json.dumps(s, ensure_ascii=False))
    for o in sorted(BILINEN_ISTISNA):
        s = next((x for x in satirlar if x["siparis"] == o), None)
        print(f"-- bilinen istisna {o}:", json.dumps(s, ensure_ascii=False))
    for s in kosulan:
        if not s["kutu_ayni"]:
            print("-- kutular modules.jsonl'den farklı (FBX revizyonu?):", s["siparis"],
                  f"A={s['A']} B={s['B']} B_A={s['B_A']} A_modul={s['A_modul']} ref_modul={s['ref_modul']}")
    kotu = [s for s in satirlar if s["durum"] == "UYUSMADI_SUTUN_KURALI" or s["durum"] == "KOSULMADI"
            or ("A" in s and s["A"] != s["B_A"])]
    return 1 if kotu else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
