"""
linco_empty.py — Seçili parçalardaki (veya tüm sahnedeki) Linco deliklerine Empty atar.

KULLANIM (Blender GUI):
    1) Viewport'ta incelemek istediğin parçaları SEÇ (Hiçbir şey seçmezsen TÜM sahneyi tarar).
    2) Scripting sekmesinde bu dosyayı çalıştır.
    3) Her linco deliğinin merkezine 'linco1', 'linco2' şeklinde Empty (Küre) konur
       ve ilgili parça objesine parent edilir (dünya konumu korunarak).
    4) Konsolda kaç linco deliği bulunduğu listelenir.
"""

import bpy
import bmesh
import mathutils

# ── Linco Hacim Tanımı (parca_sayim.py ile birebir aynı) ──────────────────────
LINCO_HACIM = 9680.0
TOLERANCE = 0.05  # %5 tolerans -> [9196.0, 10164.0] mm³

LINCO_MIN = LINCO_HACIM * (1 - TOLERANCE)
LINCO_MAX = LINCO_HACIM * (1 + TOLERANCE)

EMPTY_BOYUT = 0.015  # Empty görünüm boyutu (metre)


def is_linco(v):
    return LINCO_MIN <= v <= LINCO_MAX


# ── Çift Boolean Yardımcıları ────────────────────────────────────────────────
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
    bpy.context.view_layer.objects.active = outer_prism
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


def add_empty_parented(name, loc_m, parent_obj, size=EMPTY_BOYUT):
    """Empty oluşturur, dünya konumunu koruyarak parent_obj'ye bağlar."""
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = 'SPHERE'
    e.empty_display_size = size
    e.location = loc_m
    bpy.context.collection.objects.link(e)

    # Dünya koordinatını koruyarak parent yap
    e.parent = parent_obj
    e.matrix_parent_inverse = parent_obj.matrix_world.inverted()
    return e


def main():
    secili = [o for o in bpy.context.selected_objects if o.type == 'MESH']
    if not secili:
        # Seçili parça yoksa sahnedeki tüm MESH objelerini tara
        secili = [o for o in bpy.context.scene.objects if o.type == 'MESH' and not o.name.startswith("Temp_")]
        print(f"\n[BİLGİ] Seçili obje olmadığı için tüm sahnedeki {len(secili)} MESH taranıyor.")
    else:
        print(f"\n[BİLGİ] {len(secili)} seçili MESH taranıyor.")

    print(f"Linco hacim aralığı: [{LINCO_MIN:.1f}, {LINCO_MAX:.1f}] mm³ (Hedef: {LINCO_HACIM}, Tol: %{TOLERANCE*100:.0f})\n")

    toplam_linco = 0
    for o in secili:
        try:
            holes = execute_double_boolean(o)
        except Exception as e:
            print(f"  [UYARI] {o.name}: Delik taraması başarısız ({e})")
            continue

        linco_bu_parca = 0
        for h in holes:
            v = h["volume"]
            if is_linco(v):
                c = world_center(h["object"])
                toplam_linco += 1
                add_empty_parented(f"linco{toplam_linco}", c, parent_obj=o)
                linco_bu_parca += 1
            bpy.data.objects.remove(h["object"], do_unlink=True)

        if linco_bu_parca > 0:
            print(f"  {o.name}: {linco_bu_parca} adet linco deliği bulundu.")

    print(f"\n>> Toplam {toplam_linco} Linco deliğine Empty eklendi (linco1..linco{toplam_linco}).")
    print("   Empty'ler ilgili parçalara parent edildi.")


if __name__ == "__main__":
    main()
