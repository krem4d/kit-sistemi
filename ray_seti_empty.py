"""
ray_seti_empty.py — SEÇİLİ parçadaki ray desenlerini (parca_sayim.detect_rays ile
AYNI mantık) bulur ve HER ray setinin ahşap çivisi deliklerine, ray adı/uzunluğu
yazılı Empty koyar.

AMAÇ (Algoritmaların_testi.md): Ray seti algoritması bazen yanlış uzunluk buluyor
(ör. gerçekte 55cm olması gereken bir ray, 25cm olarak bulunuyor). Bunu debug
etmek için: şu anki ray-bulma algoritmasını AYNEN kullanan bu geçici script,
tespit ettiği her ray setinin ahşap çivisi deliklerine, o ray setinin adını
(dolayısıyla algoritmanın bulduğu cm karşılığını) yazan Empty'ler koyar. Böylece
viewport'ta o delikleri görüp `iki_obje_mesafe.py` ile aralarındaki GERÇEK
mesafeleri ölçüp algoritmanın hangi adımda yanlış eşleştiğini bulabilirsin.

KULLANIM (GUI):
    1) Viewport'ta parçayı SEÇ (bir veya birden çok mesh seçebilirsin).
    2) Scripting sekmesinde bu dosyayı çalıştır.
    3) Ray setine dahil edilen HER deliğe bir Empty gelir (ray adı adında);
       ray dışı kalan ahşap çivilerine de ayrı bir Empty gelir (karşılaştırma için).
       Konsolda: parça başına bulunan ray listesi + her rayın delikleri arası
       ÖLÇÜLEN ham mesafeler (mm).

ÇIKTI:
    - Ray'e dahil delik:     "ray_<Parca>_<RayAdi>#<k>_<i>"   (küre, kırmızımsı boyut)
    - Ray dışı ahşap çivisi: "ahsapdisi_<Parca>#<i>_<hacim>mm3"
    - Konsolda: her ray için kullanılan delik indeksleri ve aralarındaki ham
      mesafeler (mm) — RAY_GAPS tablosundaki beklenen değerlerle kıyaslamak için.

NOT: detect_rays() içindeki 3'lü/2'li eşleştirme mantığı buraya BİREBİR
     kopyalanmıştır (parca_sayim.py'ye dokunulmadı); sadece hangi deliklerin
     hangi ray'e girdiğini (grup indekslerini) de döndürecek şekilde genişletildi.
"""

import bpy
import bmesh
import mathutils
import itertools

# ── Ahşap çivisi "vida sınıfı" hacim bandı (mm^3) ────────────────────────────
VOL_LO = 8.0
VOL_HI = 25.0

EMPTY_BOYUT_RAY = 0.014
EMPTY_BOYUT_DISI = 0.009

RAY_SCALE_MM = 1000.0
RAY_TOL_MM = 8.0
RAY_COLINEAR_TOL_MM = 8.0
RAY_GAPS = {
    "55cm": [149.0, 222.0],
    "50cm": [150.0, 161.0],
    "45cm": [152.0, 102.0],
    "40cm": [129.0, 82.0],
    "35cm": [77.0, 83.0],
    "30cm": [109.0],
    "25cm": [188.0],
}


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


def add_empty(name, loc_m, size):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = 'SPHERE'
    e.empty_display_size = size
    e.location = loc_m
    bpy.context.collection.objects.link(e)
    return e


def _safe(name):
    return name.replace(" ", "_")[:20]


# ── detect_rays'in BİREBİR kopyası — TEK FARK: grup indekslerini de döndürür ─
def _match_gap_pair(p, q):
    for name, gaps in RAY_GAPS.items():
        if len(gaps) != 2:
            continue
        g1, g2 = gaps
        if (abs(p - g1) <= RAY_TOL_MM and abs(q - g2) <= RAY_TOL_MM) or \
           (abs(p - g2) <= RAY_TOL_MM and abs(q - g1) <= RAY_TOL_MM):
            return name
    return None


def _match_gap_single(d):
    for name, gaps in RAY_GAPS.items():
        if len(gaps) != 1:
            continue
        if abs(d - gaps[0]) <= RAY_TOL_MM:
            return name
    return None


def detect_rays_debug(centers):
    """detect_rays ile birebir aynı mantık; ek olarak her ray için (idx grubu,
    o ray'i oluşturan ham mesafeler) de döner.
    Returns: rays = [(ray_adi, [idx...], [mesafe_mm...]), ...], kalan_idx (ray dışı)."""
    n = len(centers)
    used = [False] * n
    rays = []

    for i, j, k in itertools.combinations(range(n), 3):
        if used[i] or used[j] or used[k]:
            continue
        dij = (centers[i] - centers[j]).length * RAY_SCALE_MM
        djk = (centers[j] - centers[k]).length * RAY_SCALE_MM
        dik = (centers[i] - centers[k]).length * RAY_SCALE_MM
        p, q, r = sorted([dij, djk, dik])
        if abs(r - (p + q)) > RAY_COLINEAR_TOL_MM:
            continue
        name = _match_gap_pair(p, q)
        if name:
            used[i] = used[j] = used[k] = True
            rays.append((name, [i, j, k], [dij, djk, dik]))

    for i, j in itertools.combinations(range(n), 2):
        if used[i] or used[j]:
            continue
        d = (centers[i] - centers[j]).length * RAY_SCALE_MM
        name = _match_gap_single(d)
        if name:
            used[i] = used[j] = True
            rays.append((name, [i, j], [d]))

    kalan_idx = [i for i in range(n) if not used[i]]
    return rays, kalan_idx


# ── Ana logic ────────────────────────────────────────────────────────────────
def main():
    secili = [o for o in bpy.context.selected_objects if o.type == 'MESH']
    if not secili:
        print("!! Seçili MESH yok. Önce viewport'ta parçayı seç, sonra çalıştır.")
        return

    print(f"\n=== ray_seti_empty: {len(secili)} seçili parça taranıyor ===")

    toplam_ray = 0
    toplam_disi = 0
    for o in secili:
        try:
            holes = execute_double_boolean(o)
        except Exception as e:
            print(f"  [UYARI] {o.name}: delik taraması başarısız ({e})")
            continue

        centers = []
        for h in holes:
            v = h["volume"]
            if VOL_LO <= v <= VOL_HI:
                centers.append(world_center(h["object"]))
            bpy.data.objects.remove(h["object"], do_unlink=True)

        if not centers:
            print(f"  {o.name}: ahşap çivisi yok, atlandı.")
            continue

        rays, kalan_idx = detect_rays_debug(centers)

        print(f"\n  --- {o.name}: {len(centers)} ahşap çivisi, {len(rays)} ray bulundu ---")
        for k, (name, idxs, dists) in enumerate(rays):
            dist_str = ", ".join(f"{d:.1f}mm" for d in dists)
            print(f"    Ray#{k} -> '{name}'  delikler={idxs}  ham_mesafeler=[{dist_str}]")
            for i in idxs:
                add_empty(f"ray_{_safe(o.name)}_{name}#{k}_{i}", centers[i], EMPTY_BOYUT_RAY)
            toplam_ray += 1

        for i in kalan_idx:
            add_empty(f"ahsapdisi_{_safe(o.name)}#{i}", centers[i], EMPTY_BOYUT_DISI)
            toplam_disi += 1

    print(f"\n>> Toplam {toplam_ray} ray seti Empty grubu ('ray_' önekiyle) ve "
          f"{toplam_disi} ray-dışı ahşap çivisi Empty'si ('ahsapdisi_' önekiyle) kondu.")
    print("   Şüpheli ray'in deliklerini seçip iki_obje_mesafe.py ile gerçek mesafeyi ölç,")
    print("   sonra konsoldaki 'ham_mesafeler' ile RAY_GAPS tablosundaki beklenen değeri kıyasla.")


if __name__ == "__main__":
    main()
