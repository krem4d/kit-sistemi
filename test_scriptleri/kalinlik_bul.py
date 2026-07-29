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
