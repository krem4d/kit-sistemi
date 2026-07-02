"""
kulp_mesafe_bul.py — Seçili parçadaki rafpimi hacimleri deliklerin
                     birbirlerine olan uzaklıklarını listeler.

KULLANIM: Blender'da Script moduna geç, seçili objeni hazırla,
          bu scripti çalıştır. Konsol/Info panelinden çıktıyı oku.

Amaç: Kulp delikleri rafpimi ile aynı hacimde olduğu için bu scriptle
      kulp çiftleri arasındaki sabit mesafeyi öğreniyoruz.
"""

import bpy
import bmesh
import mathutils

MODUL_VOL = 351.35
TOLERANCE = 0.05        # %5 tolerans

OUT_PATH = "/home/rocket/Belgeler/adaptx-2/otonom_kit/kulp_mesafe_raporu.txt"


# ── Yardımcılar (parca_sayim.py ile aynı) ───────────────────────────────────

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


# ── Ana logic ────────────────────────────────────────────────────────────────

def main():
    obj = bpy.context.active_object
    if obj is None or obj.type != 'MESH':
        print("!! Lütfen bir MESH objesi seç.")
        return

    print(f"\n=== kulp_mesafe_bul: {obj.name} ===")
    print("Delikler hesaplanıyor...")

    holes = execute_double_boolean(obj)
    print(f"Toplam {len(holes)} delik bulundu.")

    lo = MODUL_VOL * (1 - TOLERANCE)
    hi = MODUL_VOL * (1 + TOLERANCE)
    modul_holes = []
    for h in holes:
        v = h["volume"]
        if lo <= v <= hi:
            wc = world_center(h["object"])
            modul_holes.append((v, wc))
        bpy.data.objects.remove(h["object"], do_unlink=True)

    lines = []
    lines.append(f"=== kulp_mesafe_bul: {obj.name} ===")
    lines.append(f"ModülBağlantı hacim aralığı: {lo:.2f} – {hi:.2f} mm³  (tol=%{int(TOLERANCE*100)})")
    lines.append(f"Eşleşen delik sayısı: {len(modul_holes)}\n")

    if len(modul_holes) == 0:
        lines.append("Bu parçada modül bağlantı hacimiyle eşleşen delik yok.")
    else:
        lines.append("Delik merkezleri (world-space, mm):")
        for i, (v, c) in enumerate(modul_holes):
            lines.append(f"  [{i}]  hacim={v:.3f}  konum=({c.x:.2f}, {c.y:.2f}, {c.z:.2f})")

        lines.append("\nİkili uzaklıklar (mm):")
        n = len(modul_holes)
        for i in range(n):
            for j in range(i + 1, n):
                d = (modul_holes[i][1] - modul_holes[j][1]).length
                lines.append(f"  [{i}]↔[{j}]  dist = {d:.3f} mm")

    report = "\n".join(lines)
    print(report)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(report + "\n")
    print(f"\n>> Rapor kaydedildi: {OUT_PATH}")


main()
