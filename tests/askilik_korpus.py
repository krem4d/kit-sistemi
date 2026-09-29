"""Gerçek sipariş FBX'lerinde askılık borusu boyu koşusu (Blender, boru hattı yolu).

Her sipariş için parca_sayim'in KENDİ sayımı koşar: prep_import → count_order
(delik boolean'ları dahil). Ek olarak, sayımdan ÖNCE FBX'teki boru mesh'leri
(varsa) ölçülür — gerçek boru boyunun referansı (panel_roles.classify_hardware:
en uzun kenar ≥ 250 mm, kesit ≤ 40 mm). Sonuç sipariş başına bir JSON satırı
olarak ASKILIK_CIKTI dizinine yazılır; karşılaştırma askilik_korpus_karsilastir.py'de.
Kaynak FBX'e yazılmaz (SHA-256 önce/sonra kontrol edilir); jsons/ pdf/ ve
islem_gecmisi.json'a dokunulmaz (count_order dosya yazmaz).

Kullanım:
  ASKILIK_CIKTI=<dizin> [ASKILIK_PARCA=<ad>] ALSOFT_DRIVERS=null blender -b --factory-startup \
      -noaudio --python-exit-code 1 --python tests/askilik_korpus.py -- <sipariş|FBX yolu> ...

Sipariş no'su → FBX çözümü tests/sutun_korpus.py ile aynı (kit.fbx_path_for_order).
"""
import hashlib
import json
import os
import sys
import time
import traceback

sys.dont_write_bytecode = True
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
KORPUS_DIZINI = os.environ.get(
    "KORPUS_DIZINI",
    "/home/rocket/Jupiter/Efforts/otonom_kit/2026-09-09-son-50-modul-incelemesi/2026-09-27-parca-testleri")

import bpy  # noqa: E402
import parca_sayim  # noqa: E402
import panel_roles  # noqa: E402  (parca_sayim module_ayirici'yi sys.path'e ekledi)


def fbx_bul(arg):
    if arg.lower().endswith(".fbx"):
        return arg
    sys.path.insert(0, KORPUS_DIZINI)
    import kit
    return kit.fbx_path_for_order(arg)


def boru_meshleri():
    """Sahnedeki boru mesh'leri: [{eksen, uzunluk_mm, lo, hi, ad}] (mm, kopyasız)."""
    out, gorulen = [], set()
    for o in bpy.context.scene.objects:
        if o.type != 'MESH':
            continue
        lo, hi = parca_sayim._dunya_kutusu_mm(o)
        if lo is None:
            continue
        dims = [hi[i] - lo[i] for i in range(3)]
        if panel_roles.classify_hardware({"dims": dims}) != "askilik_borusu":
            continue
        anahtar = tuple(round(v, 1) for v in lo + hi)
        if anahtar in gorulen:
            continue
        gorulen.add(anahtar)
        k = max(range(3), key=lambda i: dims[i])
        out.append({"ad": o.name, "eksen": "xyz"[k], "uzunluk_mm": round(dims[k], 2),
                    "lo": [round(v, 2) for v in lo], "hi": [round(v, 2) for v in hi]})
    return out


def kos(arg):
    fbx = fbx_bul(arg)
    if not fbx or not os.path.exists(fbx):
        return {"siparis": arg, "ok": False, "hata": "FBX yok"}
    with open(fbx, "rb") as f:
        once = hashlib.sha256(f.read()).hexdigest()
    t0 = time.monotonic()
    order = parca_sayim.prep_import(fbx)
    borular_mesh = boru_meshleri()
    res = parca_sayim.count_order(order)
    with open(fbx, "rb") as f:
        sonra = hashlib.sha256(f.read()).hexdigest()
    return {"siparis": arg, "ok": True, "fbx": os.path.basename(fbx),
            "kaynak_degismedi": once == sonra, "sure_sn": round(time.monotonic() - t0, 2),
            "flans": res["adet"]["Askılık Flanşı"], "boru_adet": res["adet"]["Askılık Borusu"],
            "askilik_borulari": res["askilik_borulari"], "askilik_eslesme": res["askilik_eslesme"],
            "modul_kaynak": res["moduller"]["kaynak"], "modul_sayisi": res["moduller"]["modul_sayisi"],
            "boru_meshleri": borular_mesh}


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    cikti = os.environ["ASKILIK_CIKTI"]
    os.makedirs(cikti, exist_ok=True)
    yol = os.path.join(cikti, "sonuc-%s.jsonl" % os.environ.get("ASKILIK_PARCA", "0"))
    with open(yol, "a", encoding="utf-8") as f:
        for a in args:
            try:
                r = kos(a)
            except Exception as e:
                r = {"siparis": a, "ok": False, "hata": repr(e), "iz": traceback.format_exc()}
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            f.flush()
            print("ASKILIK", a, r.get("ok"), r.get("flans"), r.get("boru_adet"),
                  [b["uzunluk_cm"] for b in r.get("askilik_borulari", [])],
                  len(r.get("boru_meshleri", [])), r.get("sure_sn"), flush=True)


if __name__ == "__main__":
    kod = 0
    try:
        main()
    except Exception:
        traceback.print_exc()
        kod = 1
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(kod)
