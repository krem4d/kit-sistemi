"""
kalinlik_bul.py — Seçili parça MDF kalınlığı (en kısa kenar) ölçüm aracı
========================================================================

AMAÇ
----
Arkalık tespit algoritmasını kurmak için: seçili parça(lar)ın collider-box
(yerel bounding-box) boyutlarını hesaplar ve **en kısa kenarı = MDF kalınlığı**
olarak raporlar. Arkalık paneli diğer parçalardan daha incedir; bu araçla
arkalık vs normal parça kalınlık eşiğini bulabilirsin.

Bu araç SAYIM akışının parçası değildir (parca_sayim.py'den bağımsız).

KULLANIM
--------
1) Blender'da ölçmek istediğin parça(ları) SEÇ.
2) Scripting sekmesinde bu dosyayı çalıştır (Alt+P).
3) Sonuç konsola basılır ve proje dizinine "kalinlik_raporu.txt" yazılır.

NOT: Kalınlık, delik hacmi ile aynı yerel (object-space) birimdedir.
     Obje ölçeği 1 değilse uyarı basılır.
"""

import bpy
import mathutils
import os

PROJE_DIZINI = "/home/rocket/Belgeler/adaptx-2/otonom_kit"


def _resolve_output_dir():
    if os.path.isdir(PROJE_DIZINI):
        return PROJE_DIZINI
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        pass
    if bpy.data.filepath:
        return os.path.dirname(bpy.data.filepath)
    return os.getcwd()


def get_local_dims(obj):
    """Objenin yerel bounding-box boyutları (collider box) — Vector(x,y,z)."""
    verts = obj.data.vertices
    if not verts:
        return None
    xs = [v.co.x for v in verts]
    ys = [v.co.y for v in verts]
    zs = [v.co.z for v in verts]
    return mathutils.Vector((max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)))


def run():
    selected = [o for o in bpy.context.selected_objects if o.type == 'MESH']
    lines = []

    def out(s=""):
        print(s)
        lines.append(s)

    out("--- SEÇİLİ PARÇA KALINLIK (en kısa kenar) RAPORU ---")
    out("Birim: yerel object-space (delik hacmi ile aynı ölçek)")
    out("")

    if not selected:
        out("!! Seçili MESH obje yok. Önce parça(ları) seç.")
    else:
        for obj in selected:
            dims = get_local_dims(obj)
            if dims is None:
                out(f"{obj.name}: geometri yok, atlandı")
                continue
            sorted_dims = sorted([dims.x, dims.y, dims.z])
            kalinlik = sorted_dims[0]

            sc = obj.scale
            uyari = ""
            if abs(sc.x - 1) > 1e-4 or abs(sc.y - 1) > 1e-4 or abs(sc.z - 1) > 1e-4:
                uyari = f"  [UYARI ölçek {sc.x:.3f},{sc.y:.3f},{sc.z:.3f}]"

            out(f"{obj.name}")
            out(f"   Boyutlar (x,y,z): {dims.x:.3f} × {dims.y:.3f} × {dims.z:.3f}")
            out(f"   >> KALINLIK (en kısa kenar): {kalinlik:.4f}{uyari}")
            out("")

    out("İpucu: Arkalık paneli diğer parçalardan daha incedir; "
        "bu kalınlık değerini eşik belirlemek için kullan.")

    path = os.path.join(_resolve_output_dir(), "kalinlik_raporu.txt")
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"\n>> Rapor yazıldı: {path}")
    except Exception as e:
        print(f"\n!! Rapor yazılamadı: {e}")


if __name__ == "__main__":
    run()
