"""Sentetik gövdelerle uçtan uca sütun/braket testi (Blender, geometri yolu).

Çalıştırma (ayrı arka plan süreci; sahneyi sıfırlar):
  ALSOFT_DRIVERS=null blender -b --factory-startup -noaudio --python-exit-code 1 \
      --python tests/test_sutun_blender.py

parca_sayim.modul_sutun_bilgisi() — yani boru hattının kullandığı yolun
kendisi — gerçek 18 mm panellerden kurulmuş gövdelerle beslenir: sol/sağ yan
duvar, taban, tavan, 5 mm arkalık. Parça adları ya `Object_N` (Adaptx'in yeni
FBX'leri) ya da isim önekli (`1sol`, `1tab`...) verilir; sonuç adlardan
bağımsız olmalı. Beklenen braket = 2 × sütun, düzenin tanımından gelir.
"""
import os
import random
import sys
import traceback

import bpy

sys.dont_write_bytecode = True
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
import parca_sayim  # noqa: E402

T = 18.0
GENISLIKLER = [450.0, 600.0, 1000.0, 700.0]
YUKSEKLIKLER = [1800.0, 400.0, 720.0]


def kutu(ad, lo, hi):
    bpy.ops.mesh.primitive_cube_add(size=1, location=[(a + b) / 2000 for a, b in zip(lo, hi)])
    o = bpy.context.object
    o.name = ad
    o.dimensions = [(b - a) / 1000 for a, b in zip(lo, hi)]
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return o


def govde(x, z, w, d, h, onek):
    """18 mm gövde + 5 mm arkalık. y=0 ön, y=d arka."""
    return [
        (onek + "sol", (x, 0, z), (x + T, d, z + h)),
        (onek + "sag", (x + w - T, 0, z), (x + w, d, z + h)),
        (onek + "tab", (x + T, 0, z), (x + w - T, d, z + T)),
        (onek + "tav", (x + T, 0, z + h - T), (x + w - T, d, z + h)),
        (onek + "ark", (x + T, d - 5, z + T), (x + w - T, d, z + h - T)),
    ]


def duzen_kur(yukseklikler, adlandirma):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    parcalar = []
    x = 0.0
    for c, n in enumerate(yukseklikler):
        w = GENISLIKLER[c % len(GENISLIKLER)]
        z = 0.0
        for r in range(n):
            h = YUKSEKLIKLER[(r + c) % len(YUKSEKLIKLER)]
            d = 580.0 if r == 0 else 350.0
            parcalar += govde(x, z, w, d, h, f"{c + 1}.{r + 1}")
            z += h
        x += w
    random.Random(len(parcalar)).shuffle(parcalar)
    objeler = []
    for i, (ad, lo, hi) in enumerate(parcalar, 1):
        objeler.append(kutu(ad if adlandirma == "onek" else f"Object_{i}", lo, hi))
    return objeler


DURUMLAR = [
    ("L2-33", [3, 3], 4),
    ("L4-1111", [1, 1, 1, 1], 8),
    ("L1-1 tek modül", [1], 2),
    ("L3-132 farklı yükseklik", [1, 3, 2], 6),
    ("L2-12 alçak yanında yüksek", [1, 2], 4),
]


def main():
    hatalar = []
    for ad, hs, beklenen in DURUMLAR:
        for adlandirma in ("Object_N", "onek"):
            objeler = duzen_kur(hs, adlandirma)
            objeler, _ = parca_sayim.prepare_unique_parts(objeler)
            b = parca_sayim.modul_sutun_bilgisi(objeler)
            durum = "OK" if (b["kaynak"] == "geometri" and b["braket"] == beklenen
                             and b["modul_sayisi"] == sum(hs)
                             and sorted(len(s) for s in b["sutunlar"]) == sorted(hs)) else "HATA"
            print(f"{durum} {ad:28s} {adlandirma:9s} modül={b['modul_sayisi']} "
                  f"sütun={b['sutun_sayisi']} braket={b['braket']} beklenen={beklenen} "
                  f"kaynak={b['kaynak']} sütunlar={b['sutunlar']}", flush=True)
            if durum != "OK":
                hatalar.append((ad, adlandirma, b))
    print("SONUC", "GECTI" if not hatalar else f"KALDI {len(hatalar)}", flush=True)
    return 1 if hatalar else 0


if __name__ == "__main__":
    kod = 1
    try:
        kod = main()
    except Exception:
        traceback.print_exc()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(kod)
