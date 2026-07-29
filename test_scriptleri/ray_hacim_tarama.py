"""
ray_hacim_tarama.py — GEÇİCİ teşhis aracı (2026-07-29)
=======================================================

AMAÇ
----
Ray deliklerinin hacimleri modellerde stabil çıkmıyor: bazı parçalarda ~84.92,
bazılarında ~80.83 ölçülüyor. `parca_sayim.py`'deki `RAY_DELIK_HACIM = 84.9181`
±%1 bandı [84.07, 85.77] olduğu için 80.83 kümesi hiç yakalanmıyor.

Bu araç, elimizdeki TÜM fbx'lerde ray deliklerinin hangi hacimlerde çıktığını
tablolar. Çıktı Mert'e "şu modelleri revize et" demek için kullanılacak.

NASIL BULUYOR
-------------
Çekmece yan duvarları (ray'in vidalandığı parçalar) şu imzaya sahip:
  - TAM 2 adet linco deliği
  - 2 veya 3 adet, BİRBİRİYLE AYNI hacimde, linco olmayan delik  ← ray delikleri

Algoritma yalnızca "tam 2 linco deliği olan" parçalara bakar; oradaki linco
olmayan delikleri hacme göre kümeler ve 2-3'lü eşit-hacim kümelerini ray adayı
olarak raporlar.

ÇALIŞTIRMA (headless, tüm fbx'ler)
----------------------------------
  blender --background --python test_scriptleri/ray_hacim_tarama.py

Çıktı: test_scriptleri/ciktilar/ray_hacim_tarama.txt  (+ konsol)

GEÇİCİ: iş bitince silinebilir. Boru hattının parçası değildir.
"""

import bpy
import bmesh
import mathutils
import os
import glob
import re
from collections import defaultdict

LINCO_HACIM = 9680.0
LINCO_TOL = 0.05          # %5 — parca_sayim.py ile aynı
KUME_TOL = 0.005          # %0.5 — "aynı hacim" sayılma eşiği
MIN_HACIM = 1.0           # bundan küçük delikler gürültü sayılır
MAX_RAY_HACIM = 5000.0    # ray deliği linco/menteşe boyutunda olamaz

SABIT_CIKTI = "/home/rocket/Jupiter/Projects/otonom_kit/test_scriptleri/ciktilar"


# ── delikbulma.py yardımcıları (standalone) ─────────────────────────────────
def get_perfect_local_bounds(obj):
    verts = obj.data.vertices
    if not verts:
        return None, None
    xs = [v.co.x for v in verts]; ys = [v.co.y for v in verts]; zs = [v.co.z for v in verts]
    dim = mathutils.Vector((max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)))
    merkez = mathutils.Vector(((min(xs) + max(xs)) / 2.0,
                               (min(ys) + max(ys)) / 2.0,
                               (min(zs) + max(zs)) / 2.0))
    return dim, merkez


def create_prism(name, dim, merkez, matrix_world, olcek):
    bpy.ops.mesh.primitive_cube_add(size=1)
    p = bpy.context.active_object
    p.name = name
    p.scale = (dim.x * olcek, dim.y * olcek, dim.z * olcek)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bm = bmesh.new(); bm.from_mesh(p.data)
    bmesh.ops.translate(bm, verts=bm.verts, vec=merkez)
    bm.to_mesh(p.data); bm.free()
    p.matrix_world = matrix_world.copy()
    return p


def delik_hacimleri(obj):
    """obj içindeki deliklerin hacim listesi (yerel uzay, mm³)."""
    dim, merkez = get_perfect_local_bounds(obj)
    if not dim:
        return []
    bpy.ops.object.select_all(action='DESELECT')
    dis = create_prism("T_Dis", dim, merkez, obj.matrix_world, 1.002)
    ic = create_prism("T_Ic", dim, merkez, obj.matrix_world, 0.998)

    m = dis.modifiers.new(name="D", type='BOOLEAN')
    m.operation = 'DIFFERENCE'; m.object = obj; m.solver = 'EXACT'
    bpy.context.view_layer.objects.active = dis
    bpy.ops.object.modifier_apply(modifier=m.name)

    m = dis.modifiers.new(name="I", type='BOOLEAN')
    m.operation = 'INTERSECT'; m.object = ic; m.solver = 'EXACT'
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(ic, do_unlink=True)

    bpy.ops.object.select_all(action='DESELECT')
    dis.select_set(True)
    bpy.context.view_layer.objects.active = dis
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.separate(type='LOOSE')
    bpy.ops.object.mode_set(mode='OBJECT')

    hacimler = []
    for parca in list(bpy.context.selected_objects):
        bm = bmesh.new(); bm.from_mesh(parca.data)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        v = abs(bm.calc_volume()); bm.free()
        if v > 0.01:
            hacimler.append(v)
        bpy.data.objects.remove(parca, do_unlink=True)
    return hacimler


def linco_mu(v):
    return LINCO_HACIM * (1 - LINCO_TOL) <= v <= LINCO_HACIM * (1 + LINCO_TOL)


def kumele(hacimler):
    """Birbirine %KUME_TOL içinde eşit olan hacimleri gruplar.
    Returns: [(ortalama_hacim, adet, [hacimler]), ...]"""
    kalan = sorted(hacimler)
    kumeler = []
    while kalan:
        oncu = kalan.pop(0)
        grup = [oncu]
        digerleri = []
        for v in kalan:
            if abs(v - oncu) <= oncu * KUME_TOL:
                grup.append(v)
            else:
                digerleri.append(v)
        kalan = digerleri
        kumeler.append((sum(grup) / len(grup), len(grup), grup))
    return kumeler


def siparis_adi(yol):
    m = re.search(r'(\d{4,}(?:-\d+)?)', os.path.basename(yol))
    return m.group(1) if m else "????"


def main():
    base = "/home/rocket/Jupiter/Projects/otonom_kit"
    fbxler = sorted(glob.glob(os.path.join(base, "fbx", "*.fbx")))
    satirlar = []
    tum_adaylar = defaultdict(list)   # yuvarlanmış hacim -> [(sipariş, parça, adet)]

    def yaz(s=""):
        print(s)
        satirlar.append(s)

    yaz("=" * 78)
    yaz("RAY DELİĞİ HACİM TARAMASI — çekmece yan duvarları")
    yaz("=" * 78)
    yaz("Ölçüt: parçada TAM 2 linco deliği + 2-3 adet eşit hacimli linco-olmayan delik")
    yaz(f"Kümeleme toleransı: %{KUME_TOL*100:g}   |   Birim: yerel mm³")
    yaz("")
    yaz(f"{'Sipariş':<9} {'Parça':<14} {'Delik':>6} {'RAY ADAYI HACİM':>18} {'Adet':>5}")
    yaz("-" * 78)

    for fbx in fbxler:
        sip = siparis_adi(fbx)
        bpy.ops.wm.read_factory_settings(use_empty=True)
        try:
            bpy.ops.import_scene.fbx(filepath=fbx)
        except Exception as e:
            yaz(f"{sip:<9} !! import edilemedi: {e}")
            continue

        # "Default" altındaki parçaları un-parent (parca_sayim.py ile aynı hazırlık)
        for n in ["Front", "Perspective", "Right", "Top"]:
            o = bpy.data.objects.get(n)
            if o:
                bpy.data.objects.remove(o, do_unlink=True)
        d = bpy.data.objects.get("Default")
        if d:
            for c in list(d.children):
                wm = c.matrix_world.copy(); c.parent = None; c.matrix_world = wm
            bpy.data.objects.remove(d, do_unlink=True)

        bulundu = 0
        for obj in [o for o in bpy.context.scene.objects if o.type == 'MESH']:
            try:
                hacimler = delik_hacimleri(obj)
            except Exception:
                continue
            lincolar = [v for v in hacimler if linco_mu(v)]
            if len(lincolar) != 2:
                continue          # çekmece yan duvarı imzası değil

            digerleri = [v for v in hacimler
                         if not linco_mu(v) and MIN_HACIM < v < MAX_RAY_HACIM]
            for ort, adet, grup in kumele(digerleri):
                if adet not in (2, 3):
                    continue
                yaz(f"{sip:<9} {obj.name:<14} {len(hacimler):>6} {ort:>18.4f} {adet:>5}")
                tum_adaylar[round(ort, 1)].append((sip, obj.name, adet))
                bulundu += 1
        if bulundu == 0:
            yaz(f"{sip:<9} {'—':<14} {'':>6} {'(uygun parça yok)':>18}")

    # ── Özet ────────────────────────────────────────────────────────────────
    yaz("")
    yaz("=" * 78)
    yaz("ÖZET — bulunan farklı hacim kümeleri")
    yaz("=" * 78)
    yaz(f"{'Hacim':>12} {'Kaç parçada':>12}  {'Mevcut band [84.07, 85.77]':<28} Siparişler")
    yaz("-" * 78)
    for hacim in sorted(tum_adaylar):
        kayitlar = tum_adaylar[hacim]
        sipler = sorted({s for s, _p, _a in kayitlar})
        icinde = "✓ yakalanıyor" if 84.0718 <= hacim <= 85.7644 else "✗ KAÇIRILIYOR"
        yaz(f"{hacim:>12.1f} {len(kayitlar):>12}  {icinde:<28} {', '.join(sipler)}")

    yol = os.path.join(SABIT_CIKTI, "ray_hacim_tarama.txt")
    os.makedirs(SABIT_CIKTI, exist_ok=True)
    with open(yol, "w", encoding="utf-8") as f:
        f.write("\n".join(satirlar) + "\n")
    print(f"\n>> Rapor: {yol}")


if __name__ == "__main__":
    main()
