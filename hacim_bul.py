"""
hacim_bul.py — Seçili parça hacim ölçüm aracı (Adaptx Otonom Kit / Faz 0)
==========================================================================

AMAÇ
----
Blender'da SEÇİLİ obje(ler) için iki şeyi raporlar:
  1) KENDİ HACMİ        -> objenin kendi katı hacmi (ör. KULP dummy modeli için)
  2) DELİK HACİMLERİ     -> objenin içindeki deliklerin hacimleri (ör. MENTEŞE TABANI)

Her delik hacminin yanına, bilinen kategorilerden (CATEGORIES) hangisine uyduğunu
yazar. Hiçbirine uymayan delik "BİLİNMİYOR" olarak işaretlenir -> yeni parça adayı.
(Menteşe tabanının delik hacmini böyle yakalayacaksın.)

KULLANIM
--------
1) Blender'da delik/dummy içeren obje(leri) SEÇ (birden fazla seçebilirsin).
2) Scripting sekmesinde bu dosyayı aç ve "Run Script" (Alt+P).
3) Sonuç: System Console'a basılır ve blend dosyasının yanına
   "hacim_bul_raporu.txt" olarak yazılır.

NOT
---
- Delik tespiti delikbulma.py ile AYNI "çift boolean kabuk" tekniğini kullanır;
  bu yüzden ölçülen hacimler sayım sistemiyle birebir uyumludur.
- Bu araç sahnede geçici objeler (prizma/kabuk) oluşturur ve ölçüm bitince
  hepsini SİLER; sahneyi kirletmez. Yine de ölçümü yedekli bir dosyada yapman
  önerilir.
- Hacimler yerel (object-space) uzayda hesaplanır; obje ölçeği 1 değilse uyarı
  basılır (Ctrl+A > Scale ile ölçeği uygula).
"""

import bpy
import bmesh
import mathutils
import os

# ── Bilinen kategoriler (delikbulma.py ile birebir aynı) ─────────────────────
CATEGORIES = {
    "linco": 9680.0,
    "pim": 936.0,            # Linco Dübel
    "ahsapcivisi": 14.57,    # Ağaç vidası (gerçek FBX ölçümü: ~14.57)
    "rafpimi": 234.0,
    "modulbaglanti": 351.35,
    "menteseTabani": 11454.0131,
}
TOLERANCE = 0.05  # %5


# ── delikbulma.py'den kopyalanan yardımcılar (standalone kalması için) ───────
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
    """original_obj içindeki delikleri {'object', 'volume'} listesi olarak döndürür.
    Döndürülen delik objeleri sahnede kalır; çağıran taraf silmelidir."""
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

    separated_objects = bpy.context.selected_objects
    valid_holes = []
    for part in separated_objects:
        bm = bmesh.new(); bm.from_mesh(part.data)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        vol = abs(bm.calc_volume()); bm.free()
        if vol > 0.01:
            valid_holes.append({"object": part, "volume": vol})
        else:
            bpy.data.objects.remove(part, do_unlink=True)
    return valid_holes


# ── Bu araca özel: objenin kendi hacmi ───────────────────────────────────────
def get_own_volume(obj):
    """Objenin kendi katı hacmi (yerel uzay, modifier'lar uygulanmış hali)."""
    deps = bpy.context.evaluated_depsgraph_get()
    obj_eval = obj.evaluated_get(deps)
    me = obj_eval.to_mesh()
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    vol = abs(bm.calc_volume()); bm.free()
    obj_eval.to_mesh_clear()
    return vol


def match_category(vol):
    """Verilen hacme uyan kategori adını döndürür, yoksa None."""
    for cat_name, target in CATEGORIES.items():
        if target * (1 - TOLERANCE) <= vol <= target * (1 + TOLERANCE):
            return cat_name
    return None


# ── Ana akış ─────────────────────────────────────────────────────────────────
def run():
    selected = [o for o in bpy.context.selected_objects if o.type == 'MESH']
    lines = []

    def out(s=""):
        print(s)
        lines.append(s)

    out("--- SEÇİLİ PARÇA HACİM RAPORU (hacim_bul.py) ---")
    out("Birim: yerel object-space hacmi (delikbulma.py ile aynı ölçek)")
    out("")

    if not selected:
        out("!! Seçili MESH obje yok. Önce ölçmek istediğin obje(leri) seç.")
        _write_report(lines)
        return

    try:
        for obj in selected:
            out("=" * 60)
            out(f"OBJE: {obj.name}")

            # Ölçek uyarısı (hacimler ölçekten etkilenir)
            sc = obj.scale
            if abs(sc.x - 1) > 1e-4 or abs(sc.y - 1) > 1e-4 or abs(sc.z - 1) > 1e-4:
                out(f"  [UYARI] Obje ölçeği ({sc.x:.4f}, {sc.y:.4f}, {sc.z:.4f}) != 1. "
                    f"Doğru hacim için Ctrl+A > Scale uygula.")

            # 1) Kendi hacmi (dummy parçalar için, ör. KULP)
            try:
                own = get_own_volume(obj)
                m = match_category(own)
                etiket = f"[{m}]" if m else "[eşleşme yok]"
                out(f"  KENDİ HACMİ: {own:.4f}  {etiket}")
            except Exception as e:
                out(f"  KENDİ HACMİ: hesaplanamadı ({e})")

            # 2) İçindeki delikler (ör. MENTEŞE TABANI)
            try:
                holes = execute_double_boolean(obj)
            except Exception as e:
                out(f"  DELİK HACİMLERİ: hesaplanamadı ({e})")
                out("")
                continue

            if not holes:
                out("  DELİK HACİMLERİ: (geçerli delik bulunamadı)")
            else:
                out(f"  DELİK HACİMLERİ: {len(holes)} adet (büyükten küçüğe):")
                holes.sort(key=lambda h: h["volume"], reverse=True)
                for i, h in enumerate(holes, 1):
                    m = match_category(h["volume"])
                    etiket = f"[{m}]" if m else "[BİLİNMİYOR]"
                    out(f"    Delik {i:>2}: {h['volume']:>12.4f}  {etiket}")
                # Geçici delik objelerini temizle
                for h in holes:
                    bpy.data.objects.remove(h["object"], do_unlink=True)
            out("")

        # Seçimi geri yükle
        bpy.ops.object.select_all(action='DESELECT')
        for obj in selected:
            try:
                obj.select_set(True)
            except Exception:
                pass

        out("İpucu: [BİLİNMİYOR] etiketli delik = yeni parça adayı (ör. menteşe tabanı).")
        out("Bu değeri hacimler.md dosyasına işle.")
    except Exception as e:
        # Beklenmedik hata olsa bile o ana kadarki sonuçları kaydet
        out("")
        out(f"!! Beklenmedik hata: {e}")
        import traceback
        out(traceback.format_exc())
    finally:
        _write_report(lines)


# Rapor bu proje dizinine yazılır (kullanıcı isteği). Proje taşınırsa
# aşağıdaki fallback'ler devreye girer.
PROJE_DIZINI = "/home/rocket/Belgeler/adaptx-2/otonom_kit"


def _resolve_output_dir():
    """Öncelik: sabit proje dizini -> scriptin klasörü -> blend klasörü -> cwd.
    Böylece Blender Text Editor'den de çalıştırsan rapor hep aynı yere düşer."""
    if os.path.isdir(PROJE_DIZINI):
        return PROJE_DIZINI
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        pass  # Blender text editor'de __file__ tanımsız olabilir
    if bpy.data.filepath:
        return os.path.dirname(bpy.data.filepath)
    return os.getcwd()


def _write_report(lines):
    path = os.path.join(_resolve_output_dir(), "hacim_bul_raporu.txt")
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"\n>> Rapor yazıldı: {path}")
    except Exception as e:
        print(f"\n!! Rapor yazılamadı: {e}")


if __name__ == "__main__":
    run()
