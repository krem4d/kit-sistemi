"""hacim_dok.py — 9441 siparişindeki TÜM delik hacimlerini kümeler halinde döker.
parca_sayim.py'nin yardımcılarını kullanır (headless Blender). Geçici teşhis aracı.
"""
import bpy, bmesh, mathutils, glob, os, sys
# parca_sayim.py proje kökünde; betik test_scriptleri/ klasöründe → kökü ekle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import parca_sayim as ps

fbxs = sorted(glob.glob(os.path.join(ps.FBX_DIR, "9441*.fbx")))
if not fbxs:
    print("!! 9441.fbx bulunamadı"); sys.exit(1)

ps.prep_import(fbxs[0])
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
print(f"Parça sayısı: {len(meshes)}")

all_vols = []
for o in meshes:
    try:
        holes = ps.execute_double_boolean(o)
    except Exception as e:
        print(f"  [UYARI] {o.name}: {e}")
        continue
    vols = sorted(round(h["volume"], 1) for h in holes)
    if vols:
        print(f"  {o.name}: {len(vols)} delik -> {vols}")
    all_vols.extend(vols)
    for h in holes:
        bpy.data.objects.remove(h["object"], do_unlink=True)

import collections
print("\n=== HACİM KÜMELERİ (9441) ===")
d = collections.Counter(round(v, 1) for v in all_vols)
for k in sorted(d):
    print(f"  {k:9.1f} mm³ -> {d[k]} adet")

# linco (9680) ve pim (936) bandlarında kaç delik var, 1% ve 5% ile:
for tol in (0.01, 0.05):
    llo, lhi = 9680*(1-tol), 9680*(1+tol)
    plo, phi = 936*(1-tol), 936*(1+tol)
    nlinco = sum(1 for v in all_vols if llo <= v <= lhi)
    npim = sum(1 for v in all_vols if plo <= v <= phi)
    print(f"\ntol %{tol*100:.0f}: linco[9680]={nlinco}, pim[936]={npim}")
