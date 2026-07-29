"""
collider_kutusu_goster.py — Seçili objenin "collider box"unu görselleştirme aracı
====================================================================================

AMAÇ
----
`parca_sayim.py` (ve `delikbulma.py`) içindeki delik tespiti, her parça için önce bir
"collider box" (yerel eksene hizalı sınırlayıcı kutu) çıkarır ve delikleri bu kutu ile
parçanın kendisi arasındaki boolean farkla bulur (`execute_double_boolean`). Bu araç,
boru hattındaki kutu-bulma algoritmasının **birebir aynısını** SEÇİLİ obje(ler) için
çalıştırır ve sonucu sahneye gerçek bir mesh (dikdörtgen prizma) olarak yerleştirir —
böylece kutunun doğru hizada/boyutta olup olmadığını gözle doğrulayabilirsin.

Algoritma `parca_sayim.py::get_perfect_local_bounds` ile BİREBİR AYNI:
  1) Objenin mesh verteksleri yerel (object-space) uzayda gezilir.
  2) min/max x, y, z bulunur -> eksene hizalı kutunun boyutu (dim) ve merkezi
     (center_local) elde edilir. (Blender'ın kendi `obj.bound_box`'ı DEĞİL — o da
     eksene hizalı olsa da farklı bir yol izler; pipeline özellikle bu elle hesaplanan
     min/max'i kullanır, bu yüzden burada da aynısı kullanılıyor.)
  3) `create_prism` ile 1x1x1 küpten başlanıp dim'e göre ölçeklenir, merkez lokal
     uzayda öteleme ile ayarlanır, sonra objenin `matrix_world`'ü uygulanır — yani kutu
     objenin DÖNÜŞ/KONUM/ÖLÇEĞİYLE aynı uzayda oluşur (tıpkı pipeline'daki gibi).

Pipeline'da bu kutu delik tespiti için iki kopya halinde kullanılır (dış: ×1.002,
iç: ×0.998); bu araç ise gözle denetim için TEK kutuyu, TAM ÖLÇEKTE (×1.0, yani
gerçek collider box) oluşturur.

KULLANIM
--------
1) Blender'da denetlemek istediğin MESH obje(leri) SEÇ (birden fazla seçilebilir).
2) Scripting sekmesinde bu dosyayı aç ve "Run Script" (Alt+P).
3) Her seçili obje için sahneye "ColliderBox_<obje adı>" isimli, tel kafes (wireframe)
   görünümlü bir dikdörtgen prizma eklenir; obje ile birebir aynı konum/dönüşte durur.
   Boyutlar System Console'a ve "collider_kutusu_raporu.txt" dosyasına yazılır.

NOT
---
- Oluşturulan kutular sahnede KALIR (silinmez) — amaç görsel denetim; bitirince elle
  seçip silebilirsin (isimleri "ColliderBox_" ile başlar, "Select Pattern" ile toplu
  seçilebilir).
- Bu araç sahneyi/asıl parçaları değiştirmez, sadece yeni kutu objeleri ekler.
- Obje ölçeği (scale) 1 değilse pipeline'daki gibi burada da uyarı basılır.
"""

import bpy
import bmesh
import mathutils
import os


# ── delikbulma.py / parca_sayim.py'den BİREBİR kopyalanan yardımcılar ────────
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


# ── Ana akış ─────────────────────────────────────────────────────────────────
def run():
    selected = [o for o in bpy.context.selected_objects if o.type == 'MESH']
    lines = []

    def out(s=""):
        print(s)
        lines.append(s)

    out("--- SEÇİLİ PARÇA COLLIDER BOX RAPORU (collider_kutusu_goster.py) ---")
    out("Kutu = get_perfect_local_bounds() ile pipeline'daki AYNI hesap; ölçek ×1.0")
    out("")

    if not selected:
        out("!! Seçili MESH obje yok. Önce collider box'ını görmek istediğin obje(leri) seç.")
        _write_report(lines)
        return

    created_boxes = []

    try:
        for obj in selected:
            out("=" * 60)
            out(f"OBJE: {obj.name}")

            sc = obj.scale
            if abs(sc.x - 1) > 1e-4 or abs(sc.y - 1) > 1e-4 or abs(sc.z - 1) > 1e-4:
                out(f"  [UYARI] Obje ölçeği ({sc.x:.4f}, {sc.y:.4f}, {sc.z:.4f}) != 1. "
                    f"Pipeline bu ölçekle çalışır ama kutu da aynı şekilde çarpık görünür.")

            dim, center_local = get_perfect_local_bounds(obj)
            if not dim:
                out("  !! Mesh verteksi yok, collider box hesaplanamadı.")
                out("")
                continue

            out(f"  Yerel boyut (dim):     x={dim.x:.6f}  y={dim.y:.6f}  z={dim.z:.6f}")
            out(f"  Yerel merkez:          x={center_local.x:.6f}  y={center_local.y:.6f}  z={center_local.z:.6f}")

            box_name = f"ColliderBox_{obj.name}"
            # Aynı isimde eski bir kutu varsa (script tekrar çalıştırıldıysa) önce sil
            old = bpy.data.objects.get(box_name)
            if old:
                bpy.data.objects.remove(old, do_unlink=True)

            bpy.ops.object.select_all(action='DESELECT')
            box = create_prism(box_name, dim, center_local, obj.matrix_world, 1.0)
            box.display_type = 'WIRE'      # içini görebilmek için tel kafes
            box.show_in_front = True       # parçanın içinden de görünsün
            created_boxes.append(box)

            world_dim = mathutils.Vector((dim.x * obj.scale.x, dim.y * obj.scale.y, dim.z * obj.scale.z))
            out(f"  Dünya boyutu (~model birimi): x={world_dim.x:.6f}  y={world_dim.y:.6f}  z={world_dim.z:.6f}")
            out(f"  Sahneye eklendi: '{box_name}' (WIRE görünüm)")
            out("")

        # Seçimi: orijinal objeler + yeni kutular olacak şekilde bırak (kıyaslama kolay olsun)
        bpy.ops.object.select_all(action='DESELECT')
        for obj in selected:
            try:
                obj.select_set(True)
            except Exception:
                pass
        for box in created_boxes:
            try:
                box.select_set(True)
            except Exception:
                pass

        out("İpucu: Kutu parçanın gerçek dış hatlarıyla örtüşmüyorsa (kaymışsa/yanlış "
            "boyuttaysa) delik tespiti de yanlış çalışır — sorun muhtemelen bu objenin "
            "mesh verisinde (ör. uygulanmamış transform, taşan/gizli vertex) aranmalı.")
    except Exception as e:
        out("")
        out(f"!! Beklenmedik hata: {e}")
        import traceback
        out(traceback.format_exc())
    finally:
        _write_report(lines)


# Rapor scriptin bulunduğu dizine yazılır (diğer diagnostic araçlarla aynı
# konvansiyon). Öncelik: scriptin klasörü -> blend klasörü -> cwd.
# ═══════════════════════════════════════════════════════════════════════════
# SABİT ÇIKTI DİZİNİ — raporlar buraya düşer
# ═══════════════════════════════════════════════════════════════════════════
# Bu script Blender'ın Text Editor'üne YAPIŞTIRILIP kaydedilmemiş bir blend'de
# çalıştırıldığında Blender __file__'ı "/Text" yapar ve bpy.data.filepath boş
# olur — yani scriptin kendi yerini bulmasının HİÇBİR yolu kalmaz. Kaydetmeden
# test etmek normal bir çalışma biçimi olduğu için, yol burada SABİT yazılıdır.
#
# Projeyi başka bir yere taşırsan SADECE bu satırı güncelle.
# (Boru hattı scriptleri — parca_sayim.py, pdf_uret.py, panel.py — hâlâ tamamen
#  taşınabilir; sabit yol yalnızca bu teşhis araçlarında var.)
SABIT_CIKTI_DIZINI = "/home/rocket/Jupiter/Projects/otonom_kit/test_scriptleri/ciktilar"
# ═══════════════════════════════════════════════════════════════════════════


def _proje_dizini_mi(d):
    """d gercekten test_scriptleri klasoru mu? Isaret dosyasi: BLENDER_CALISTIR.py.

    Sadece os.path.isdir() BAKMAK YETMEZ: script blend'e yapistirilmissa Blender
    __file__'i "/Text" yapar, dirname "/" olur ve "/" bir dizindir -> kod kok
    dizine yazmaya calisir (PermissionError: '/ciktilar'). Isaret dosyasi bu
    sahte yollari eler.
    """
    try:
        return bool(d) and os.path.isfile(os.path.join(d, "BLENDER_CALISTIR.py"))
    except OSError:
        return False


def _yazilabilir(p):
    """p'yi olustur ve gercekten yazilabildigini test et; olmazsa None."""
    try:
        os.makedirs(p, exist_ok=True)
        t = os.path.join(p, ".yazma_testi")
        with open(t, "w") as f:
            f.write("")
        os.remove(t)
        return p
    except OSError:
        return None


def _resolve_output_dir():
    """Rapor cikti dizini — normalde test_scriptleri/ciktilar/.

    Oncelik:
      1) ADAPTX_TEST_CIKTI ortam degiskeni
      2) Bu dosyanin klasoru + /ciktilar   (yalnizca isaret dosyasi varsa)
      3) .blend klasorundeki test_scriptleri/ciktilar
      4) SABIT_CIKTI_DIZINI                <- yapistirilmis + kaydedilmemis blend
      5) ~/adaptx_test_ciktilari           <- son care

    1-3 dinamik: proje tasinirsa kendiliginden dogru yeri bulur.
    4 sabit: dinamik cozumun MUMKUN OLMADIGI tek senaryoyu (yapistirilmis script
    + kaydedilmemis blend) kurtarir. Hicbir adim istisna firlatmaz.
    """
    env = os.environ.get("ADAPTX_TEST_CIKTI")
    if env:
        r = _yazilabilir(env)
        if r:
            return r

    # 2) Script diskten calistirildiysa __file__ gercek yoldur.
    try:
        d = os.path.dirname(os.path.abspath(__file__))
        if _proje_dizini_mi(d):
            r = _yazilabilir(os.path.join(d, "ciktilar"))
            if r:
                return r
    except NameError:
        pass

    # 3) Blend kaydedilmisse onun klasorunden test_scriptleri'ni bul.
    if bpy.data.filepath:
        b = os.path.dirname(bpy.data.filepath)
        for aday in (os.path.join(b, "test_scriptleri"), b):
            if _proje_dizini_mi(aday):
                r = _yazilabilir(os.path.join(aday, "ciktilar"))
                if r:
                    return r

    # 4) Sabit yol — yapistirilmis script + kaydedilmemis blend senaryosu.
    if SABIT_CIKTI_DIZINI:
        r = _yazilabilir(SABIT_CIKTI_DIZINI)
        if r:
            return r
        print("!! SABIT_CIKTI_DIZINI yazilamadi: " + SABIT_CIKTI_DIZINI)
        print("!! Proje tasindiysa scriptin basindaki bu satiri guncelle.")

    # 5) Son care — ev dizini.
    son_care = os.path.join(os.path.expanduser("~"), "adaptx_test_ciktilari")
    r = _yazilabilir(son_care)
    print("!" * 70)
    print("!! Ne dinamik cozum ne de SABIT_CIKTI_DIZINI islemedi.")
    print("!! Rapor su klasore yaziliyor: " + str(r or os.path.expanduser("~")))
    print("!" * 70)
    return r or os.path.expanduser("~")


def _write_report(lines):
    path = os.path.join(_resolve_output_dir(), "collider_kutusu_raporu.txt")
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"\n>> Rapor yazıldı: {path}")
    except Exception as e:
        print(f"\n!! Rapor yazılamadı: {e}")


if __name__ == "__main__":
    run()
