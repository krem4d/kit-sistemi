"""
ray_delik_empty.py — SEÇİLİ parçadaki ray'e özgü deliklere (RAY_DELIK_HACIM
bandı, ahşap vidasından FARKLI) Empty koyar.

AMAÇ: hacim_bul.py raporuyla ray'e özgü deliklerin ahşap vidasıyla AYNI hacimde
OLMADIĞI bulundu (ör. Object_23'te 3 delik ~84.92, [BİLİNMİYOR] — CATEGORIES'teki
hiçbir hacimle eşleşmiyordu). parca_sayim.py bu bilgiyle RAY_DELIK_HACIM sabitini
kullanacak şekilde düzeltildi (ray artık bu bandın delikleri arasından aranıyor,
ahsapcivisi havuzuna dokunmuyor). Bu geçici araç, o düzeltmeyi/RAY_GAPS örüntüsünü
daha ileri debug edebilmen için: seçtiğin parçadaki ray-bandı deliklerinin
merkezine bir Empty koyar; böylece bu delikleri viewport'ta görüp
iki_obje_mesafe.py (artık TÜM ikili kombinasyonları ölçüyor) ile aralarındaki
mesafeleri ölçebilirsin.

KULLANIM (GUI):
    1) Viewport'ta parçayı SEÇ (bir veya birden çok mesh seçebilirsin).
    2) Scripting sekmesinde bu dosyayı çalıştır.
    3) Her ray-bandı deliğinin merkezine bir Empty gelir; konsolda hacim listesi.

ÇIKTI:
    - Her delik için Empty (küre):  "raydelik_<Parca>#<i>_<hacim>"
    - Konsolda: parça başına delik sayısı + HER deliğin hacmi.

NOT: RAY_DELIK_HACIM = 84.92, RAY_DELIK_TOL = %2 (parca_sayim.py ile AYNI sabit,
     buraya birebir kopyalanmıştır — parca_sayim.py'ye dokunulmadı).
"""

import bpy
import bmesh
import mathutils

# ── Ray deliği hacim bandı (parca_sayim.py ile AYNI) ─────────────────────────
RAY_DELIK_HACIM = 84.92
RAY_DELIK_TOL = 0.02
VOL_LO = RAY_DELIK_HACIM * (1 - RAY_DELIK_TOL)
VOL_HI = RAY_DELIK_HACIM * (1 + RAY_DELIK_TOL)

EMPTY_BOYUT = 0.012        # Empty görünüm boyutu (metre; sahne 1 birim = 1000 mm)


# ── Yardımcılar (parca_sayim.py ile aynı) ────────────────────────────────────
def get_perfect_local_bounds(obj):
    verts = obj.data.vertices
    if not verts:
        return None, None
    min_x = min(v.co.x for v in verts); max_x = max(v.co.x for v in verts)
    min_y = min(v.co.y for v in verts); max_y = max(v.co.y for v in verts)
    min_z = min(v.co.z for v in verts); max_z = max(v.co.z for v in verts)
    dim = mathutils.Vector((max_x - min_x, max_y - min_y, max_z - min_z))
    center_local = mathutils.Vector(((min_x + max_x) / 2.0,
                                     (min_y + max_y) / 2.0,
                                     (min_z + max_z) / 2.0))
    return dim, center_local


def create_prism(name, dim, center_local, matrix_world, scale_factor):
    bpy.ops.mesh.primitive_cube_add(size=1)
    prism = bpy.context.active_object
    prism.name = name
    prism.scale = (dim.x * scale_factor, dim.y * scale_factor, dim.z * scale_factor)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bm = bmesh.new(); bm.from_mesh(prism.data)
    bmesh.ops.translate(bm, verts=bm.verts, vec=center_local)
    bm.to_mesh(prism.data); bm.free()
    prism.matrix_world = matrix_world.copy()
    return prism


def execute_double_boolean(original_obj):
    """original_obj içindeki delikleri {'object','volume'} listesi döndürür."""
    dim, center_local = get_perfect_local_bounds(original_obj)
    if not dim:
        return []
    bpy.ops.object.select_all(action='DESELECT')
    outer_prism = create_prism("Temp_Outer", dim, center_local,
                               original_obj.matrix_world, 1.002)
    inner_prism = create_prism("Temp_Inner", dim, center_local,
                               original_obj.matrix_world, 0.998)

    bool_diff = outer_prism.modifiers.new(name="Diff", type='BOOLEAN')
    bool_diff.operation = 'DIFFERENCE'; bool_diff.object = original_obj
    bool_diff.solver = 'EXACT'
    bpy.context.view_layer.objects.active = outer_prism
    bpy.ops.object.modifier_apply(modifier=bool_diff.name)

    bool_int = outer_prism.modifiers.new(name="Int", type='BOOLEAN')
    bool_int.operation = 'INTERSECT'; bool_int.object = inner_prism
    bool_int.solver = 'EXACT'
    bpy.ops.object.modifier_apply(modifier=bool_int.name)
    bpy.data.objects.remove(inner_prism, do_unlink=True)

    bpy.ops.object.select_all(action='DESELECT')
    outer_prism.select_set(True)
    bpy.context.view_layer.objects.active = outer_prism
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.separate(type='LOOSE')
    bpy.ops.object.mode_set(mode='OBJECT')

    holes = []
    for part in bpy.context.selected_objects:
        bm = bmesh.new(); bm.from_mesh(part.data)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        vol = abs(bm.calc_volume()); bm.free()
        if vol > 0.01:
            holes.append({"object": part, "volume": vol})
        else:
            bpy.data.objects.remove(part, do_unlink=True)
    return holes


def world_center(obj):
    wb = [obj.matrix_world @ mathutils.Vector(v) for v in obj.bound_box]
    return sum(wb, mathutils.Vector()) / 8.0


def add_empty(name, loc_m, size=EMPTY_BOYUT):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = 'SPHERE'
    e.empty_display_size = size
    e.location = loc_m
    bpy.context.collection.objects.link(e)
    return e


def _safe(name):
    return name.replace(" ", "_")[:20]


# ── Ana logic ────────────────────────────────────────────────────────────────
def main():
    secili = [o for o in bpy.context.selected_objects if o.type == 'MESH']
    if not secili:
        print("!! Seçili MESH yok. Önce viewport'ta parçayı seç, sonra çalıştır.")
        return

    print(f"\n=== ray_delik_empty: {len(secili)} seçili parça taranıyor ===")
    print(f"    ray deliği bandı: [{VOL_LO:.2f}, {VOL_HI:.2f}]  (RAY_DELIK_HACIM={RAY_DELIK_HACIM}, tol=%{RAY_DELIK_TOL*100:.0f})\n")

    toplam_ray_delik = 0
    for o in secili:
        try:
            holes = execute_double_boolean(o)
        except Exception as e:
            print(f"  [UYARI] {o.name}: delik taraması başarısız ({e})")
            continue

        vols = sorted(h["volume"] for h in holes)
        idx = 0
        for h in holes:
            v = h["volume"]
            if VOL_LO <= v <= VOL_HI:
                c = world_center(h["object"])
                add_empty(f"raydelik_{_safe(o.name)}#{idx}_{v:.2f}", c)
                idx += 1
            bpy.data.objects.remove(h["object"], do_unlink=True)

        toplam_ray_delik += idx
        print(f"  {o.name}: {idx} ray-bandı deliği (toplam {len(holes)} delik). "
              f"Tüm hacimler: {[round(v, 1) for v in vols]}")

    print(f"\n>> Toplam {toplam_ray_delik} ray-bandı deliği Empty'si kondu "
          f"(viewport'ta 'raydelik_' önekiyle filtrele).")
    print("   Sonra hepsini seçip iki_obje_mesafe.py ile TÜM ikili mesafeleri ölç.")


if __name__ == "__main__":
    main()
