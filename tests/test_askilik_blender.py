"""Gerçek siparişlerle uçtan uca askılık borusu boyu testi (Blender, boru hattı yolu).

Çalıştırma (ayrı arka plan süreci; sahneyi sıfırlar):
  ALSOFT_DRIVERS=null blender -b --factory-startup -noaudio --python-exit-code 1 \
      --python tests/test_askilik_blender.py

parca_sayim.prep_import + count_order — yani boru hattının kendisi — gerçek FBX'lerle
koşar. FBX'ler korpus çözücüsünden (kit.fbx_path_for_order; KORPUS_DIZINI ile
değiştirilebilir) bulunur; bulunamazsa test ATLANDI yazar ve 0 döner (FBX'ler git'te
değil). Beklenen değerler FBX ölçüsünden elle hesaplandı:

  1111  M01: sol duvar x 0–18, sağ duvar x 682–700 (yükseklik/derinlik aynı) →
        iç yüz merkezleri arası 664 mm → 654 → 65.4 → 65 cm. Tek boru, tutarlı.
        (FBX'teki boru mesh'i 660 mm = 66 cm; kural bilerek iç boşluk − 1 cm.)
  9259-2 M01: flanş delikleri YALNIZ sol duvarda (Object_19) var, sağ duvarda
        (Object_18) yok — FBX eksiği. 2 flanş → adet 1, çift 0, tutarlı değil.
"""
import os
import sys
import traceback

sys.dont_write_bytecode = True
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
KORPUS_DIZINI = os.environ.get(
    "KORPUS_DIZINI",
    "/home/rocket/Jupiter/Efforts/otonom_kit/2026-09-09-son-50-modul-incelemesi/2026-09-27-parca-testleri")

import parca_sayim  # noqa: E402


def fbx(order):
    try:
        sys.path.insert(0, KORPUS_DIZINI)
        import kit
        return kit.fbx_path_for_order(order)
    except Exception:
        return None


def kontrol(ad, kosul, hatalar):
    print(("OK  " if kosul else "HATA") + " " + ad, flush=True)
    if not kosul:
        hatalar.append(ad)


def main():
    hatalar = []
    atlanan = 0
    # 1111: tam eşleşen tek boru
    yol = fbx("1111")
    if not yol or not os.path.exists(yol):
        print("ATLANDI 1111 (FBX yok)", flush=True)
        atlanan += 1
    else:
        parca_sayim.prep_import(yol)
        r = parca_sayim.count_order("1111")
        b, e = r["askilik_borulari"], r["askilik_eslesme"]
        print("1111", b, {k: v for k, v in e.items() if k != "eslesmeyen_flanslar"}, flush=True)
        kontrol("1111 adet flanş=2 boru=1", (r["adet"]["Askılık Flanşı"], r["adet"]["Askılık Borusu"]) == (2, 1), hatalar)
        kontrol("1111 tek boru 65 cm", [x["uzunluk_cm"] for x in b] == [65], hatalar)
        kontrol("1111 modül M01 ekseni x", b and (b[0]["modul"], b[0]["eksen"]) == ("M01", "x"), hatalar)
        kontrol("1111 ham 664 mm = eksen boşluğu", b and b[0]["ham_mm"] == 664.0 == b[0]["eksen_boslugu_mm"], hatalar)
        kontrol("1111 tutarlı", e["tutarli"] and e["eslesmeyen_flanslar"] == [], hatalar)
    # 9259-2: tek taraflı flanş delikleri → boy yok, adet korunur, uyuşmazlık kayıtlı
    yol = fbx("9259-2")
    if not yol or not os.path.exists(yol):
        print("ATLANDI 9259-2 (FBX yok)", flush=True)
        atlanan += 1
    else:
        parca_sayim.prep_import(yol)
        r = parca_sayim.count_order("9259-2")
        e = r["askilik_eslesme"]
        kontrol("9259-2 adet korunur (flanş 2 → boru 1)",
                (r["adet"]["Askılık Flanşı"], r["adet"]["Askılık Borusu"]) == (2, 1), hatalar)
        kontrol("9259-2 boy yok, tutarsız", r["askilik_borulari"] == [] and not e["tutarli"]
                and (e["eslesen_boru"], e["beklenen_boru"]) == (0, 1), hatalar)
        kontrol("9259-2 iki eşsiz flanş aynı panoda, karşı flanş yok",
                len(e["eslesmeyen_flanslar"]) == 2
                and {(x["modul"], x["neden"]) for x in e["eslesmeyen_flanslar"]} == {("M01", "karsi_flans_yok")}
                and len({x["pano"] for x in e["eslesmeyen_flanslar"]}) == 1, hatalar)
    print("SONUC", "GECTI" if not hatalar else f"KALDI {len(hatalar)}",
          f"(atlanan {atlanan})" if atlanan else "", flush=True)
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
