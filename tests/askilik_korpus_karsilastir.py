"""Korpus karşılaştırması: hesaplanan askılık borusu boyu ↔ FBX'teki boru mesh'i.

Çalıştırma (sistem Python, Blender gerekmez):
  python3 tests/askilik_korpus_karsilastir.py <askilik_korpus.py çıktı dizini>

A = boru hattı: FBX → count_order → askilik_borulari (flanş çiftinden kural).
G = referans: aynı FBX'teki boru mesh'inin en uzun kenarı (varsa). Referans,
    kuraldan bağımsızdır; Kerem'in kuralı (iç yüz mesafesi − 1 cm) ile modelcinin
    çizdiği boru boyu aynı şey olmak zorunda değildir — fark raporlanır, kural
    değiştirilmez.
Eşleme: aynı eksen; mesh merkezinin diğer iki koordinatı flanş çiftinin orta
noktasına ESLEME_TOL_MM içinde; mesh, iki flanş arasında.

Çıkış kodu: koşulmamış (FBX'i olup hata veren) sipariş ya da kaynak FBX'i değişen
koşu varsa 1. Boy uyuşmazlıkları bilgi amaçlıdır (çıkış kodunu etkilemez).
"""
import glob
import json
import os
import sys
from collections import Counter

sys.dont_write_bytecode = True
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "module_ayirici"))
import askilik  # noqa: E402

ESLEME_TOL_MM = 30.0      # mesh ekseni ↔ flanş orta noktası (diğer iki koordinat)
OKLID_FARK_MM = 5.0       # yüz-merkez mesafesi eksen boşluğundan bu kadar uzunsa listele


def yukle(dizin):
    out = {}
    for yol in sorted(glob.glob(os.path.join(dizin, "sonuc-*.jsonl"))):
        with open(yol, encoding="utf-8") as f:
            for satir in f:
                if satir.strip():
                    r = json.loads(satir)
                    out[r["siparis"]] = r
    return out


def mesh_esle(boru, meshler):
    k = "xyz".index(boru["eksen"])
    fa, fb = boru["flanslar"]
    orta = [(fa[i] + fb[i]) / 2 for i in range(3)]
    alt, ust = sorted([fa[k], fb[k]])
    for m in meshler:
        if m["eksen"] != boru["eksen"]:
            continue
        mc = [(m["lo"][i] + m["hi"][i]) / 2 for i in range(3)]
        if any(abs(mc[i] - orta[i]) > ESLEME_TOL_MM for i in range(3) if i != k):
            continue
        if m["lo"][k] < alt - ESLEME_TOL_MM or m["hi"][k] > ust + ESLEME_TOL_MM:
            continue
        return m
    return None


def main(dizin):
    R = yukle(dizin)
    ok = {o: r for o, r in R.items() if r.get("ok")}
    fbx_yok = sorted(o for o, r in R.items() if r.get("hata") == "FBX yok")
    hatali = sorted(o for o, r in R.items() if not r.get("ok") and r.get("hata") != "FBX yok")
    print("== Korpus askılık karşılaştırması")
    print(f"sipariş: {len(R)}  koşulan: {len(ok)}  FBX yok: {len(fbx_yok)}  hata: {len(hatali)} {hatali}")
    print(f"kaynak FBX değişmedi: {sum(bool(r['kaynak_degismedi']) for r in ok.values())}/{len(ok)}")
    print(f"modül kaynağı geometri: {sum(r['modul_kaynak'] == 'geometri' for r in ok.values())}/{len(ok)}")

    flansli = {o: r for o, r in ok.items() if r["flans"]}
    meshli = {o: r for o, r in ok.items() if r["boru_meshleri"]}
    toplam_flans = sum(r["flans"] for r in ok.values())
    borular = [(o, b) for o, r in ok.items() for b in r["askilik_borulari"]]
    eslesmeyen = [(o, e) for o, r in ok.items() for e in r["askilik_eslesme"]["eslesmeyen_flanslar"]]
    print(f"\nflanşlı sipariş: {len(flansli)}  toplam flanş: {toplam_flans}  "
          f"adet (flanş//2 toplamı): {sum(r['boru_adet'] for r in ok.values())}")
    print(f"eşleşen çift (boyu bulunan boru): {len(borular)}  eşsiz flanş: {len(eslesmeyen)} "
          f"{dict(Counter(e['neden'] for _, e in eslesmeyen))}")
    tut = [o for o, r in flansli.items() if r["askilik_eslesme"]["tutarli"]]
    print(f"tutarlı (tüm flanşlar eşleşti): {len(tut)}/{len(flansli)} flanşlı sipariş")
    print("boy dağılımı (cm):", sorted(Counter(b["uzunluk_cm"] for _, b in borular).items()))
    print("eksen:", dict(Counter(b["eksen"] for _, b in borular)))

    # ── referans mesh ile karşılaştırma ──
    print(f"\nboru mesh'i olan sipariş: {len(meshli)}  toplam boru mesh'i: "
          f"{sum(len(r['boru_meshleri']) for r in meshli.values())}")
    farklar, eslesmeyen_boru = Counter(), []
    satir = []
    kullanilan = set()
    for o, b in borular:
        m = mesh_esle(b, ok[o]["boru_meshleri"])
        if m is None:
            eslesmeyen_boru.append((o, b))
            continue
        kullanilan.add((o, m["ad"]))
        g_cm = askilik.yarim_yukari(m["uzunluk_mm"] / 10.0)
        d = b["uzunluk_cm"] - g_cm
        farklar[d] += 1
        satir.append(dict(siparis=o, modul=b["modul"], A_cm=b["uzunluk_cm"], G_cm=g_cm, fark_cm=d,
                          ham_mm=b["ham_mm"], bosluk_mm=b["eksen_boslugu_mm"], mesh_mm=m["uzunluk_mm"],
                          ic_bosluk_eksi_mesh_mm=round(b["eksen_boslugu_mm"] - m["uzunluk_mm"], 1)))
    print(f"mesh'le eşlenen boru: {len(satir)}  fark dağılımı (A−G cm): {sorted(farklar.items())}")
    print(f"±1 cm içinde: {sum(v for k, v in farklar.items() if abs(k) <= 1)}/{len(satir)}  "
          f"tam eşit: {farklar.get(0, 0)}/{len(satir)}")
    print("iç boşluk − mesh boyu (mm) dağılımı:",
          sorted(Counter(s["ic_bosluk_eksi_mesh_mm"] for s in satir).items()))
    for s in satir:
        if abs(s["fark_cm"]) > 1:
            print("  AYKIRI", json.dumps(s, ensure_ascii=False))
    print(f"mesh'i bulunmayan hesaplanan boru: {len(eslesmeyen_boru)}")
    for o, b in eslesmeyen_boru:
        print("   ", o, b["modul"], b["uzunluk_cm"], "mesh sayısı:", len(ok[o]["boru_meshleri"]))
    kalan = [(o, m) for o, r in meshli.items() for m in r["boru_meshleri"] if (o, m["ad"]) not in kullanilan]
    print(f"hesaplanan borusu olmayan mesh: {len(kalan)}")
    for o, m in kalan:
        r = ok[o]
        print(f"    {o} {m['ad']} {m['eksen']} {m['uzunluk_mm']} mm  | flanş={r['flans']} adet={r['boru_adet']} "
              f"eşleşen={len(r['askilik_borulari'])} eşsiz="
              f"{[(e['pano'], e['modul'], e['neden']) for e in r['askilik_eslesme']['eslesmeyen_flanslar']]}")

    # ── adet: flanş//2 ↔ mesh sayısı ──
    print("\nadet (flanş//2) ↔ boru mesh sayısı (mesh'i ya da flanşı olan siparişler):")
    adet_fark = Counter()
    for o in sorted(set(flansli) | set(meshli)):
        r = ok[o]
        adet_fark[(r["boru_adet"] - len(r["boru_meshleri"]))] += 1
        if r["boru_adet"] != len(r["boru_meshleri"]) or not r["askilik_eslesme"]["tutarli"]:
            print(f"    {o}: flanş={r['flans']} adet={r['boru_adet']} eşleşen={len(r['askilik_borulari'])} "
                  f"mesh={len(r['boru_meshleri'])} boylar={[b['uzunluk_cm'] for b in r['askilik_borulari']]}")
    print("  adet − mesh dağılımı:", sorted(adet_fark.items()))

    # ── Öklid ↔ eksen boşluğu ──
    uzak = [(o, b) for o, b in borular if b["ham_mm"] - b["eksen_boslugu_mm"] > OKLID_FARK_MM]
    print(f"\nyüz-merkez mesafesi eksen boşluğundan > {OKLID_FARK_MM} mm uzun: {len(uzak)}")
    for o, b in uzak:
        print(f"    {o} {b['modul']} {b['eksen']} ham={b['ham_mm']} boşluk={b['eksen_boslugu_mm']} "
              f"→ {b['uzunluk_cm']} cm (boşluktan: {askilik.boru_boyu_cm(b['eksen_boslugu_mm'])} cm) "
              f"panolar={b['panolar']}")
    return 1 if hatali or any(not r["kaynak_degismedi"] for r in ok.values()) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
