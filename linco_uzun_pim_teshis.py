"""
linco_uzun_pim_teshis.py — Uzun linco pimi adaylarını GÖRSEL olarak işaretler.

AMAÇ: detect_long_linco_pins() her siparişte neredeyse hep "2" buluyor —
      bu şüpheli bir örüntü olabilir (eşik rastgele/simetrik bir mesafeyi
      yakalıyor olabilir, gerçek "birbirine dayalı" linco çiftini değil).
      Bu script, sahnedeki TÜM parçaları tarar, farklı parça çiftleri
      arasındaki linco-linco mesafelerini hesaplar ve GENİŞ bir pencere
      içindeki (varsayılan 20-90 mm) her adayın TAM ORTA NOKTASINA, mesafe +
      parça isimlerini içeren bir isimle EMPTY koyar. Böylece viewport'ta
      gezip hangi adayların gerçekten "birbirine dayalı" (bitişik yüzeyler
      arasında) olduğunu, hangilerinin tesadüfi/simetrik eşleşme olduğunu
      gözle görebilirsin.

KULLANIM: Bir siparişin TÜM parçalarını Blender'da içe aktar (ör. FBX'i aç /
          prep_import mantığıyla import et — Default un-parent dahil), hiçbir
          şey seçili olmasa da olur (sahnedeki tüm mesh'ler taranır).
          Script modunda bu dosyayı çalıştır.

ÇIKTI: Her aday için bir Empty (plain axes), adı:
          "LINCO_CAND_<mesafe_mm>_<PartA>#<i>_<PartB>#<j>"
       Ayrıca konsola ve linco_uzun_pim_teshis_raporu.txt'ye tam liste (mesafeye
       göre sıralı) yazılır — hangi empty'nin hangi eşik penceresinde
       (MEVCUT eşik [32,54mm] içinde mi, dışında mı) olduğu işaretlenir.
"""

import bpy
import bmesh
import mathutils

LINCO_VOL = 9680.0
TOLERANCE = 0.05

# Mevcut sistemdeki eşik (parca_sayim.py ile aynı) — rapor bunu MATCH olarak işaretler.
CUR_LO = 0.043 * (1 - 0.25)
CUR_HI = 0.043 * (1 + 0.25)
CUR_ALIGN_MIN = 0.9     # delme yönünün bağlantı doğrusuyla hizası (facing)
CUR_AXIS_MIN = 0.985    # bağlantı doğrusunun eksene hizası (90° katı)

# Empty koyulacak GENİŞ tarama penceresi (mm). Yalnızca aynı-parça-içi DEĞİL,
# FARKLI parçalar arası mesafeler taranır.
SCAN_LO_MM = 15.0
SCAN_HI_MM = 90.0

OUT_PATH = "/home/rocket/Belgeler/adaptx-2/otonom_kit/linco_uzun_pim_teshis_raporu.txt"


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


def hole_direction(hole_obj):
    """Delik parçasının kendi en-uzun lokal ekseni = delme ekseni (işaretsiz, dünya)."""
    dim, _ = get_perfect_local_bounds(hole_obj)
    if dim is None:
        return None
    axes = [(dim.x, mathutils.Vector((1.0, 0.0, 0.0))),
            (dim.y, mathutils.Vector((0.0, 1.0, 0.0))),
            (dim.z, mathutils.Vector((0.0, 0.0, 1.0)))]
    axes.sort(key=lambda t: t[0], reverse=True)
    rot = hole_obj.matrix_world.to_3x3()
    world_dir = (rot @ axes[0][1])
    if world_dir.length < 1e-9:
        return None
    return world_dir.normalized()


def hole_signed_direction(panel_obj, hole_obj):
    """Deliğin AÇILDIĞI (işaretli) yön — panele çarpmayan eksen (ray_cast)."""
    axis = hole_direction(hole_obj)
    if axis is None:
        return None
    center_w = world_center(hole_obj)
    origin_local = panel_obj.matrix_world.inverted() @ center_w
    rot = panel_obj.matrix_world.to_3x3()
    dirs_local = [mathutils.Vector((1.0, 0.0, 0.0)), mathutils.Vector((-1.0, 0.0, 0.0)),
                  mathutils.Vector((0.0, 1.0, 0.0)), mathutils.Vector((0.0, -1.0, 0.0)),
                  mathutils.Vector((0.0, 0.0, 1.0)), mathutils.Vector((0.0, 0.0, -1.0))]
    best = None
    best_align = -1.0
    for dl in dirs_local:
        if panel_obj.ray_cast(origin_local, dl)[0]:
            continue
        dw = (rot @ dl).normalized()
        al = abs(dw.dot(axis))
        if al > best_align:
            best_align = al
            best = dw
    return best if best is not None else axis


def linco_centers(obj):
    """(center, signed_direction) çiftleri döndürür."""
    lo = LINCO_VOL * (1 - TOLERANCE)
    hi = LINCO_VOL * (1 + TOLERANCE)
    holes = execute_double_boolean(obj)
    centers = []
    for h in holes:
        if lo <= h["volume"] <= hi:
            centers.append((world_center(h["object"]), hole_signed_direction(obj, h["object"])))
        bpy.data.objects.remove(h["object"], do_unlink=True)
    return centers


def add_empty(name, loc_m, size=0.02):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = 'PLAIN_AXES'
    e.empty_display_size = size
    e.location = loc_m
    bpy.context.collection.objects.link(e)
    return e


# ── Ana logic ────────────────────────────────────────────────────────────────

def main():
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    print(f"\n=== linco_uzun_pim_teshis: {len(meshes)} parça taranıyor ===")

    parts = []   # (name, [(center, direction), ...])
    for o in meshes:
        c = linco_centers(o)
        if c:
            parts.append((o.name, c))
            print(f"  {o.name}: {len(c)} linco deliği")

    lines = []
    lines.append("=== linco_uzun_pim_teshis ===")
    lines.append(f"Taranan parça sayısı (linco delikli): {len(parts)}")
    lines.append(f"Mevcut sistem eşiği: [{CUR_LO*1000:.1f}, {CUR_HI*1000:.1f}] mm, "
                 f"facing >= {CUR_ALIGN_MIN}, eksen hizası >= {CUR_AXIS_MIN}")
    lines.append(f"Tarama penceresi (empty konulan): [{SCAN_LO_MM}, {SCAN_HI_MM}] mm\n")

    candidates = []   # (dist_mm, name_a, i, a, da, name_b, j, b, db)
    P = len(parts)
    for pi in range(P):
        name_a, ca = parts[pi]
        for pj in range(pi + 1, P):
            name_b, cb = parts[pj]
            for i, (a, da) in enumerate(ca):
                for j, (b, db) in enumerate(cb):
                    d_mm = (a - b).length * 1000.0
                    if SCAN_LO_MM <= d_mm <= SCAN_HI_MM:
                        candidates.append((d_mm, name_a, i, a, da, name_b, j, b, db))

    candidates.sort(key=lambda t: t[0])
    lines.append(f"Toplam aday (pencere içinde): {len(candidates)}\n")

    count = 0
    for d_mm, na, i, a, da, nb, j, b, db in candidates:
        mid = (a + b) / 2.0
        conn = b - a
        clen = conn.length
        ch = conn / clen if clen > 1e-9 else conn
        axis_h = max(abs(ch.x), abs(ch.y), abs(ch.z))
        dot_a = da.dot(ch) if da is not None else 0.0    # A, B'ye bakıyor mu? (+1 iyi)
        dot_b = db.dot(ch) if db is not None else 0.0    # B, A'ya bakıyor mu? (-1 iyi)

        dist_ok = CUR_LO * 1000 <= d_mm <= CUR_HI * 1000
        axis_ok = axis_h >= CUR_AXIS_MIN
        face_ok = (dot_a >= CUR_ALIGN_MIN) and (dot_b <= -CUR_ALIGN_MIN)
        match = dist_ok and axis_ok and face_ok

        if match:
            tag = "MATCH"
        elif not dist_ok:
            tag = "near"
        elif not axis_ok:
            tag = "axis_bad"      # bağlantı doğrusu eksene hizasız (diagonal)
        else:
            tag = "face_bad"      # aynı yöne bakıyor / karşılıklı değil
        ename = f"LINCO_{tag}_{d_mm:.1f}mm_{na}#{i}_{nb}#{j}"
        add_empty(ename, mid)
        count += 1
        lines.append(f"  [{tag}] {d_mm:6.1f} mm  eksen={axis_h:.3f} dotA={dot_a:+.2f} dotB={dot_b:+.2f}   "
                     f"{na}[{i}] ({a.x:.3f},{a.y:.3f},{a.z:.3f})  ↔  {nb}[{j}] ({b.x:.3f},{b.y:.3f},{b.z:.3f})"
                     f"   -> empty: {ename}")

    lines.append(f"\nToplam {count} empty oluşturuldu (isim önekine göre viewport'ta filtrele).")

    report = "\n".join(lines)
    print(report)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(report + "\n")
    print(f"\n>> Rapor kaydedildi: {OUT_PATH}")


main()
