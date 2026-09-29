"""Gerçek sipariş FBX'lerinde sütun/braket koşusu (Blender, boru hattı yolu).

Her sipariş için parca_sayim'in KENDİ adımları koşar: prep_import →
prepare_unique_parts → modul_sutun_bilgisi. Sonuç sipariş başına bir JSON satırı
olarak SUTUN_CIKTI dizinine yazılır; karşılaştırma sutun_korpus_karsilastir.py'de.
Kaynak FBX'e yazılmaz (SHA-256 önce/sonra kontrol edilir).

Kullanım:
  SUTUN_CIKTI=<dizin> [SUTUN_PARCA=<ad>] ALSOFT_DRIVERS=null blender -b --factory-startup \
      -noaudio --python-exit-code 1 --python tests/sutun_korpus.py -- <sipariş|FBX yolu> ...

Sipariş no'su verilirse FBX, parça-testleri toolkit'inin çözücüsüyle bulunur
(kit.fbx_path_for_order; KORPUS_DIZINI ile değiştirilebilir). `.fbx` ile biten
argüman doğrudan yol sayılır.
"""
import hashlib
import json
import os
import sys
import time
import traceback

sys.dont_write_bytecode = True   # Efforts/ altındaki kit.py'nin yanına __pycache__ yazma
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
KORPUS_DIZINI = os.environ.get(
    "KORPUS_DIZINI",
    "/home/rocket/Jupiter/Efforts/otonom_kit/2026-09-09-son-50-modul-incelemesi/2026-09-27-parca-testleri")

import bpy  # noqa: E402,F401
import parca_sayim  # noqa: E402


def fbx_bul(arg):
    if arg.lower().endswith(".fbx"):
        return arg
    sys.path.insert(0, KORPUS_DIZINI)
    import kit
    return kit.fbx_path_for_order(arg)


def kos(arg):
    fbx = fbx_bul(arg)
    if not fbx or not os.path.exists(fbx):
        return {"siparis": arg, "ok": False, "hata": "FBX yok"}
    with open(fbx, "rb") as f:
        once = hashlib.sha256(f.read()).hexdigest()
    t0 = time.monotonic()
    parca_sayim.prep_import(fbx)
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    ham = len(meshes)
    meshes, kopyalar = parca_sayim.prepare_unique_parts(meshes)
    bilgi = parca_sayim.modul_sutun_bilgisi(meshes)
    with open(fbx, "rb") as f:
        sonra = hashlib.sha256(f.read()).hexdigest()
    return {"siparis": arg, "ok": True, "fbx": os.path.basename(fbx), "ham_parca": ham,
            "tekil_parca": len(meshes), "kopya": len(kopyalar),
            "kaynak_degismedi": once == sonra, "sure_sn": round(time.monotonic() - t0, 2),
            "ornek_adlar": sorted(o.name for o in meshes)[:5], **bilgi}


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    cikti = os.environ["SUTUN_CIKTI"]
    os.makedirs(cikti, exist_ok=True)
    yol = os.path.join(cikti, "sonuc-%s.jsonl" % os.environ.get("SUTUN_PARCA", "0"))
    with open(yol, "a", encoding="utf-8") as f:
        for a in args:
            try:
                r = kos(a)
            except Exception as e:
                r = {"siparis": a, "ok": False, "hata": repr(e), "iz": traceback.format_exc()}
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            f.flush()
            print("SUTUN", a, r.get("ok"), r.get("modul_sayisi"), r.get("sutun_sayisi"),
                  r.get("braket"), r.get("kaynak"), r.get("sure_sn"), flush=True)


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
