"""
moduller_baglama_empty.py — "Modülleri Birbirine Bağlama" tespitini GÖRSEL
olarak test etmek için Empty koyan araç.

AMAÇ: parca_sayim.py'deki GERÇEK algoritmayı (çift-boolean ile delik bulma →
modulbaglanti hacim kategorisi → aynı parçadaki kulp (tutamak) çiftlerini
ayıkla → kalan modül-bağlantı deliklerini TÜM parçalar arasında en-yakın
komşuya göre eşleştir) BİREBİR aynı mantıkla çalıştırır ve:
    1) Her parçadaki HAM modulbaglanti deliği merkezine küçük bir KÜRE Empty
       koyar ("moduladay_...").
    2) Aynı parçada kulp (tutamak, 192mm ±%5 mesafeli çift) olarak ayıklanan
       delik çiftlerinin ortasına bir KÜP Empty koyar ("kulp_ÇİFT#i").
    3) Kalan (kulp OLMAYAN) modül-bağlantı delikleri arasında, gerçek
       algoritmanın (pair_count, eşik=0.2) ürettiği eşleşmiş ÇİFTlerin
       ortasına bir KÜP Empty koyar ("moduller_baglama_ÇİFT#i").
    4) Eşiğin içinde eşi bulunamayan (tek kalan) modül-bağlantı deliğine ayrı
       bir KÜP Empty koyar ("moduller_baglama_ESLESMEMIS#i").
Konsola "Modülleri Birbirine Bağlama" adedi (gerçek pipeline'daki "adet"
sözlüğündeki değerle AYNI olmalı) ve kulp adedi basılır.

KULLANIM (GUI):
    1) Test etmek istediğin FBX'i normal şekilde içe aktar (File > Import > FBX).
       Sahnede tüm parçalar olsun yeterli.
    2) Scripting sekmesinde bu dosyayı çalıştır (Alt+P).
    3) Konsolda özet + viewport'ta Empty'ler oluşur; 'moduller_' / 'kulp_' /
       'moduladay_' önekleriyle filtrele.

NOT: Gerçek algoritma gibi bu araç da her parça için GEÇİCİ boolean
     prizmaları (Temp_Outer/Temp_Inner) oluşturup deliklere ayırır, hacme
     göre kategorize eder ve delik/prizma parçalarını hemen SİLER — orijinal
     mesh'lere DOKUNULMAZ, sahne kalıcı olarak bozulmaz (production'daki
     `bpy.data.objects.remove` ile aynı temizlik burada da yapılır).
NOT: Sabitler (CATEGORIES["modulbaglanti"], TOLERANCE, KULP_DELIK_MESAFE,
     KULP_DELIK_TOL, ARKALIK_MAX_KALINLIK, pair_count eşiği) parca_sayim.py
     ile AYNI değerde, buraya birebir kopyalanmıştır — parca_sayim.py'ye
     dokunulmadı.
"""

import bpy
import bmesh
import mathutils

# ── Sabitler (parca_sayim.py ile AYNI) ────────────────────────────────────────
MODULBAGLANTI_HACIM = 351.35
TOLERANCE = 0.05
KULP_DELIK_MESAFE = 0.192   # m — kulp deliği çifti arasındaki sabit mesafe
KULP_DELIK_TOL = 0.05       # %5 tolerans
ARKALIK_MAX_KALINLIK = 8.0  # arkalık panelleri (kalınlıktan) sayıma hiç girmez
PAIR_THRESHOLD = 0.2        # pair_count eşleştirme mesafe eşiği (dünya birimi)

ADAY_EMPTY_BOYUT = 0.008
CIFT_EMPTY_BOYUT = 0.02


# ── Yardımcılar (parca_sayim.py ile aynı mantık) ─────────────────────────────
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


def part_thickness(obj):
    dim, _ = get_perfect_local_bounds(obj)
    if dim is None:
        return None
    return min(dim.x, dim.y, dim.z)


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
    """original_obj içindeki delikleri {'object','volume'} listesi döndürür.
    Döndürülen delik objeleri sahnede kalır; çağıran silmelidir."""
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

    valid_holes = []
    for part in bpy.context.selected_objects:
        bm = bmesh.new(); bm.from_mesh(part.data)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        vol = abs(bm.calc_volume()); bm.free()
        if vol > 0.01:
            valid_holes.append({"object": part, "volume": vol})
        else:
            bpy.data.objects.remove(part, do_unlink=True)
    return valid_holes


def is_modulbaglanti(vol):
    lo = MODULBAGLANTI_HACIM * (1 - TOLERANCE)
    hi = MODULBAGLANTI_HACIM * (1 + TOLERANCE)
    return lo <= vol <= hi


def world_center(obj):
    wb = [obj.matrix_world @ mathutils.Vector(v) for v in obj.bound_box]
    return sum(wb, mathutils.Vector()) / 8.0


def detect_kulp_pairs(centers):
    """Aynı parçadaki modulbaglanti-hacimli delikler arasından kulp çiftlerini
    ayır. Returns (kulp_ciftleri [(c1,c2), ...], kalan_merkezler)."""
    lo = KULP_DELIK_MESAFE * (1 - KULP_DELIK_TOL)
    hi = KULP_DELIK_MESAFE * (1 + KULP_DELIK_TOL)
    used = [False] * len(centers)
    kulp_ciftleri = []
    for i in range(len(centers)):
        if used[i]:
            continue
        for j in range(i + 1, len(centers)):
            if used[j]:
                continue
            d = (centers[i] - centers[j]).length
            if lo <= d <= hi:
                used[i] = used[j] = True
                kulp_ciftleri.append((centers[i], centers[j]))
                break
    remaining = [c for i, c in enumerate(centers) if not used[i]]
    return kulp_ciftleri, remaining


def pair_count_detailed(centers, threshold=PAIR_THRESHOLD):
    """pair_count ile AYNI greedy mantık, ama gerçek Vector çiftlerini de
    döndürür: (ciftler [(c1,c2),...], eslesmemis [c,...])."""
    unmatched = list(centers)
    ciftler = []
    eslesmemis = []
    while len(unmatched) >= 2:
        h1 = unmatched.pop(0)
        best_idx = None
        min_dist = 9999.0
        for i, h2 in enumerate(unmatched):
            d = (h1 - h2).length
            if d < min_dist:
                min_dist = d
                best_idx = i
        if best_idx is not None and min_dist < threshold:
            h2 = unmatched.pop(best_idx)
            ciftler.append((h1, h2))
        else:
            eslesmemis.append(h1)
    eslesmemis.extend(unmatched)
    return ciftler, eslesmemis


def add_empty(name, loc, size, disp='PLAIN_AXES'):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = disp
    e.empty_display_size = size
    e.location = loc
    bpy.context.collection.objects.link(e)
    return e


def _safe(name):
    return name.replace(" ", "_")[:24]


# ── Ana logic ──────────────────────────────────────────────────────────────
def main():
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    # Arkalık panelleri (kalınlıktan) gerçek algoritmadaki gibi delik
    # taramasına hiç sokulmaz.
    diger_parcalar = [o for o in meshes
                       if (part_thickness(o) or 999) > ARKALIK_MAX_KALINLIK]

    print(f"\n=== moduller_baglama_empty: {len(meshes)} mesh, "
          f"{len(diger_parcalar)} parça delik taramasına giriyor ===")

    modulbag_centers_all = []   # ham (kulptan önce) — sadece görsel/rapor için
    remaining_all = []          # kulp ayıklandıktan sonra havuz (global eşleştirme)
    kulp_ciftleri_all = []

    for o in diger_parcalar:
        try:
            holes = execute_double_boolean(o)
        except Exception as e:
            print(f"  [UYARI] {o.name}: delik taraması başarısız ({e})")
            continue

        part_modul_centers = []
        for h in holes:
            v = h["volume"]
            obj_part = h["object"]
            if is_modulbaglanti(v):
                part_modul_centers.append(world_center(obj_part))
            bpy.data.objects.remove(obj_part, do_unlink=True)

        if not part_modul_centers:
            continue

        modulbag_centers_all.extend(part_modul_centers)
        kulp_ciftleri, remaining = detect_kulp_pairs(part_modul_centers)
        kulp_ciftleri_all.extend(kulp_ciftleri)
        remaining_all.extend(remaining)

    # Ham adaylar (görsel referans)
    for i, c in enumerate(modulbag_centers_all):
        add_empty(f"moduladay_{i}", c, ADAY_EMPTY_BOYUT, disp='SPHERE')

    # Kulp (tutamak) çiftleri
    for i, (c1, c2) in enumerate(kulp_ciftleri_all):
        mid = (c1 + c2) / 2.0
        add_empty(f"kulp_CIFT#{i}", mid, CIFT_EMPTY_BOYUT, disp='CUBE')

    # Kalan modül-bağlantı deliklerini TÜM parçalar arasında eşleştir
    ciftler, eslesmemis = pair_count_detailed(remaining_all)

    for i, (c1, c2) in enumerate(ciftler):
        mid = (c1 + c2) / 2.0
        d_mm = (c1 - c2).length * 1000.0
        isim = f"moduller_baglama_CIFT#{i}_uzaklik={d_mm:.0f}mm"
        add_empty(isim, mid, CIFT_EMPTY_BOYUT, disp='CUBE')

    for i, c in enumerate(eslesmemis):
        add_empty(f"moduller_baglama_ESLESMEMIS#{i}", c, CIFT_EMPTY_BOYUT, disp='CUBE')

    print(f"  Ham modulbaglanti deliği: {len(modulbag_centers_all)}")
    print(f"  Kulp (tutamak) çifti: {len(kulp_ciftleri_all)}")
    print(f"  Kulp'tan arta kalan modül-bağlantı deliği: {len(remaining_all)}")
    print(f"\n>> Modülleri Birbirine Bağlama (eşleşmiş çift): {len(ciftler)}")
    if eslesmemis:
        print(f"!! Eşi bulunamayan {len(eslesmemis)} modül-bağlantı deliği var "
              f"(bkz. 'moduller_baglama_ESLESMEMIS#' Empty'leri).")
    print("   Viewport'ta 'moduller_', 'kulp_', 'moduladay_' önekleriyle filtrele.")


if __name__ == "__main__":
    main()
