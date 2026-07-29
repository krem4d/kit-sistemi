"""
BLENDER_CALISTIR.py — test scriptlerini DİSKTEN çalıştıran launcher
====================================================================

NEDEN VAR
---------
Teşhis scriptlerini Blender'ın Text Editor'üne KOPYALA-YAPIŞTIR yaparsan,
blend dosyasının içinde o kodun donmuş bir kopyası kalır. Diskteki .py'yi
sonradan düzeltsen bile Blender hâlâ eski kopyayı çalıştırır.

`delik bulma.blend` içinde tam olarak bu olmuştu: içeride `parca_sayim.py`'nin
382 satırlık eski bir kopyası duruyordu (diskteki hali 1085 satır). Rapor
yazma düzeltmeleri gerçekte çalışan koda hiç ulaşmadı — raporlar bu yüzden
"kaybolmuş" görünüyordu.

Bu launcher o sorunu kökten bitirir: kodu her çalıştırmada diskten okur.
Bir kez kurarsın, bir daha script yapıştırmazsın.

KURULUM (bir kez)
-----------------
1) Blender > Scripting sekmesi > Text Editor > **Open** (yapıştırma DEĞİL!)
2) Bu dosyayı seç:  test_scriptleri/BLENDER_CALISTIR.py
3) Blend'i kaydet (Ctrl+S) — böylece launcher blend'de kalır.

KULLANIM (her seferinde)
------------------------
1) Viewport'ta ölçmek istediğin objeleri SEÇ.
2) Aşağıdaki ARAC satırını istediğin araca çevir.
3) Run Script (Alt+P).

Rapor her zaman şuraya düşer:  test_scriptleri/ciktilar/
Çıktı yolu her çalıştırmada konsola basılır — bir daha "nereye yazdı?" olmaz.
"""

# ─────────────────────────────────────────────────────────────────────────────
# ÇALIŞTIRILACAK ARAÇ — sadece bu satırı değiştir
# ─────────────────────────────────────────────────────────────────────────────
ARAC = "hacim_bul"

# Kullanılabilir araçlar:
#
#   ÖLÇÜM (rapor .txt üretir → ciktilar/)
#     "hacim_bul"              seçili objenin kendi hacmi + içindeki delik hacimleri
#     "iki_obje_mesafe"        seçili TÜM objelerin ikili mesafeleri (rapora EKLER)
#     "kalinlik_bul"           seçili parçanın MDF kalınlığı (en kısa kenar)
#     "kulp_mesafe_bul"        seçili parçadaki delik mesafeleri
#     "linco_mesafe_bul"       İKİ seçili parça arasındaki linco delik mesafeleri
#     "linco_uzun_pim_teshis"  uzun linco pimi adayları + görsel Empty işaretleri
#     "collider_kutusu_goster" seçili objenin collider box boyutları
#
#   GÖRSEL (sahneye Empty koyar, rapor üretmez)
#     "arkalik_civi_empty"     arkalık paneli + çivi yerleşimi
#     "ray_delik_empty"        ray'e özgü delikler
#     "ray_seti_empty"         tespit edilen ray desenleri
#     "moduller_baglama_empty" modül-modül bağlantı delikleri

# Proje dizinini elle sabitlemek istersen buraya yaz (normalde boş bırak):
PROJE_DIZINI = ""

# ─────────────────────────────────────────────────────────────────────────────

import bpy
import os


def _test_scriptleri_dizini():
    """test_scriptleri/ klasörünü bul. Sırayla: elle ayar → ADAPTX_BASE →
    bu dosyanın yeri → açık blend'in yeri."""
    adaylar = []

    if PROJE_DIZINI:
        adaylar.append(PROJE_DIZINI)
        adaylar.append(os.path.join(PROJE_DIZINI, "test_scriptleri"))

    env = os.environ.get("ADAPTX_BASE")
    if env:
        adaylar.append(os.path.join(env, "test_scriptleri"))

    # Bu dosya diskten açıldıysa (Text Editor > Open) __file__ gerçek yoldur.
    try:
        d = os.path.dirname(os.path.abspath(__file__))
        if os.path.isdir(d):
            adaylar.append(d)
            adaylar.append(os.path.join(d, "test_scriptleri"))
    except NameError:
        pass

    if bpy.data.filepath:
        d = os.path.dirname(bpy.data.filepath)
        adaylar.append(os.path.join(d, "test_scriptleri"))
        adaylar.append(d)

    for a in adaylar:
        # Doğru klasör: içinde hacim_bul.py olan klasör.
        if a and os.path.isfile(os.path.join(a, "hacim_bul.py")):
            return a
    return None


def calistir(arac_adi):
    dizin = _test_scriptleri_dizini()
    if dizin is None:
        print("=" * 70)
        print("!! test_scriptleri/ klasörü bulunamadı.")
        print("!! Çözüm: bu dosyayı Text Editor > OPEN ile diskten aç")
        print("!!         (kopyala-yapıştır ile değil), ya da yukarıdaki")
        print("!!         PROJE_DIZINI satırına tam yolu yaz.")
        print("=" * 70)
        return

    yol = os.path.join(dizin, arac_adi + ".py")
    if not os.path.isfile(yol):
        print(f"!! Böyle bir araç yok: {arac_adi}")
        mevcut = sorted(f[:-3] for f in os.listdir(dizin)
                        if f.endswith(".py") and f != "BLENDER_CALISTIR.py")
        print("   Kullanılabilir araçlar: " + ", ".join(mevcut))
        return

    print("=" * 70)
    print(f">> Çalıştırılıyor : {yol}")
    print(f">> Çıktı klasörü  : {os.path.join(dizin, 'ciktilar')}")
    print(f">> Seçili obje    : {len(bpy.context.selected_objects)}")
    print("=" * 70)

    with open(yol, encoding="utf-8") as f:
        kaynak = f.read()

    # __file__ GERÇEK yola ayarlanır → script kendi çıktı dizinini doğru bulur.
    ad_alani = {"__name__": "__main__", "__file__": yol}
    exec(compile(kaynak, yol, "exec"), ad_alani)


if __name__ == "__main__":
    calistir(ARAC)
