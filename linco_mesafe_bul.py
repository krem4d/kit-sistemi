"""
linco_mesafe_bul.py — İKİ seçili parçadaki linco (gövde) deliklerinin
                      birbirlerine olan uzaklıklarını listeler.

KULLANIM: Blender'da TAM 2 mesh parçası seç (uzun linco pimiyle birbirine
          bağlanan iki modül gövdesi), Script moduna geç, bu scripti çalıştır.
          Konsol/Info panelinden ve linco_mesafe_raporu.txt'den çıktıyı oku.

AMAÇ: Uzun linco pimi, iki AYRI parçadaki birbirine dayalı linco gövde
      delikleri arasına konur. Bu scriptle iki parçadaki linco delikleri
      arasındaki (parçalar-arası) mesafeleri ölçüp "birbirine dayalı" çift
      eşiğini (uzun linco pimi mesafesi) öğreniyoruz.
"""

import bpy
import bmesh
import mathutils

LINCO_VOL = 9680.0
TOLERANCE = 0.05        # %5 tolerans

OUT_PATH = "/home/rocket/Belgeler/adaptx-2/otonom_kit/linco_mesafe_raporu.txt"


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


def linco_centers(obj):
    """obj içindeki linco-hacimli deliklerin world merkezlerini döndürür."""
    lo = LINCO_VOL * (1 - TOLERANCE)
    hi = LINCO_VOL * (1 + TOLERANCE)
    holes = execute_double_boolean(obj)
    centers = []
    for h in holes:
        if lo <= h["volume"] <= hi:
            centers.append((h["volume"], world_center(h["object"])))
        bpy.data.objects.remove(h["object"], do_unlink=True)
    return centers


# ── Ana logic ────────────────────────────────────────────────────────────────

def main():
    sel = [o for o in bpy.context.selected_objects if o.type == 'MESH']
    if len(sel) != 2:
        print(f"!! Lütfen TAM 2 mesh parçası seç. (şu an {len(sel)} seçili)")
        return

    a, b = sel[0], sel[1]
    print(f"\n=== linco_mesafe_bul: [{a.name}] ↔ [{b.name}] ===")
    print("Linco delikleri hesaplanıyor...")

    ca = linco_centers(a)
    cb = linco_centers(b)

    lo = LINCO_VOL * (1 - TOLERANCE)
    hi = LINCO_VOL * (1 + TOLERANCE)

    lines = []
    lines.append("=== linco_mesafe_bul ===")
    lines.append(f"Parça A: {a.name}   (linco delik: {len(ca)})")
    lines.append(f"Parça B: {b.name}   (linco delik: {len(cb)})")
    lines.append(f"Linco hacim aralığı: {lo:.1f} – {hi:.1f} mm³  (tol=%{int(TOLERANCE*100)})\n")

    lines.append("Parça A linco delik merkezleri (world, mm):")
    for i, (v, c) in enumerate(ca):
        lines.append(f"  A[{i}] hacim={v:.1f} konum=({c.x:.2f}, {c.y:.2f}, {c.z:.2f})")
    lines.append("\nParça B linco delik merkezleri (world, mm):")
    for j, (v, c) in enumerate(cb):
        lines.append(f"  B[{j}] hacim={v:.1f} konum=({c.x:.2f}, {c.y:.2f}, {c.z:.2f})")

    if ca and cb:
        lines.append("\nParçalar-arası uzaklıklar A[i] ↔ B[j] (mm):")
        rows = []
        for i, (_, pa) in enumerate(ca):
            for j, (_, pb) in enumerate(cb):
                d = (pa - pb).length
                rows.append((d, i, j))
        rows.sort()   # en yakın çiftler üstte → "birbirine dayalı" delikleri gör
        for d, i, j in rows:
            lines.append(f"  A[{i}] ↔ B[{j}]  dist = {d:.3f} mm")

        best = rows[0]
        lines.append(f"\nEn yakın parçalar-arası çift: A[{best[1]}] ↔ B[{best[2]}]"
                     f"  = {best[0]:.3f} mm")
    else:
        lines.append("\n!! Parçalardan birinde hiç linco deliği bulunamadı.")

    report = "\n".join(lines)
    print(report)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(report + "\n")
    print(f"\n>> Rapor kaydedildi: {OUT_PATH}")


main()
