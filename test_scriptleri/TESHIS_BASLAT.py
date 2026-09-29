"""
TESHIS_BASLAT.py — "script çalışmıyor / empty gelmiyor" durumunu KANITA bağlar.

NEDEN VAR: agac_vidasi_empty.py çalıştırıldığında rapor dosyası yenilenmiyor ve
sahneye empty gelmiyor. Bu, aracın kendisinden mi yoksa çalıştırma biçiminden mi
(blend içinde donmuş yapıştırılmış kopya, yanlış sekme, hatanın konsolda
görülmemesi) kaynaklanıyor belli değil. Bu dosya HER İHTİMALDE diske bir rapor
yazar — araç hata verse bile. Rapora bakılarak sebep kesin bulunur.

KULLANIM:
    1) Text Editor > Open ile BU DOSYAYI diskten aç (yapıştırma DEĞİL).
    2) İncelemek istediğin parçaları seç (istersen hiç seçme).
    3) Alt+P.
    4) Ne olursa olsun şu dosya oluşur/güncellenir:
         test_scriptleri/ciktilar/TESHIS_RAPORU.txt

Rapor: Blender sürümü, blend yolu, AÇIK METİN DATABLOCK'LARI (donmuş yapıştırılmış
kopyalar burada görünür), seçili/sahnedeki mesh'ler, diskteki agac_vidasi_empty.py'nin
yolu/boyutu/tarihi, sonra aracı çalıştırıp tam traceback'i dosyaya döker.
"""

import bpy
import os
import sys
import traceback
import datetime

SABIT_CIKTI_DIZINI = "/home/rocket/Jupiter/Projects/otonom_kit/test_scriptleri/ciktilar"
ARAC = "agac_vidasi_empty"


def _bul_test_scriptleri():
    adaylar = []
    try:
        adaylar.append(os.path.dirname(os.path.abspath(__file__)))
    except NameError:
        pass
    if bpy.data.filepath:
        b = os.path.dirname(bpy.data.filepath)
        adaylar += [os.path.join(b, "test_scriptleri"), b]
    adaylar.append(SABIT_CIKTI_DIZINI.rsplit("/ciktilar", 1)[0])
    for a in adaylar:
        if a and os.path.isfile(os.path.join(a, "BLENDER_CALISTIR.py")):
            return a
    return None


def main():
    R = []

    def y(s=""):
        R.append(str(s))
        print(s)

    y("=" * 70)
    y(f"TESHIS RAPORU — {datetime.datetime.now():%Y-%m-%d %H:%M:%S}")
    y("=" * 70)
    y(f"Blender    : {bpy.app.version_string}")
    y(f"Python     : {sys.version.split()[0]}")
    y(f"blend yolu : {bpy.data.filepath or '(KAYDEDİLMEMİŞ)'}")
    try:
        y(f"__file__   : {os.path.abspath(__file__)}")
    except NameError:
        y("__file__   : YOK  <-- bu dosya YAPISTIRILMIS, diskten acilmamis!")
    y(f"mod        : {bpy.context.mode}")

    y("")
    y("-- Blender icindeki METIN datablock'lari --")
    if not bpy.data.texts:
        y("  (yok)")
    for t in bpy.data.texts:
        kaynak = t.filepath if t.filepath else "YAPISTIRILMIS (diske bagli DEGIL)"
        try:
            satir = len(t.lines)
        except Exception:
            satir = "?"
        y(f"  '{t.name}'  satir={satir}  kaynak={kaynak}  degismis={t.is_dirty}")

    secili = [o for o in bpy.context.selected_objects if o.type == 'MESH']
    tum = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    y("")
    y(f"-- Sahne -- mesh: {len(tum)}, secili mesh: {len(secili)}")
    for o in tum[:40]:
        isaret = "*" if o in secili else " "
        y(f" {isaret} {o.name:<32} scale=({o.scale.x:.4f},{o.scale.y:.4f},{o.scale.z:.4f}) "
          f"vertex={len(o.data.vertices) if o.data else '?'}")
    if len(tum) > 40:
        y(f"   ... ve {len(tum)-40} mesh daha")

    dizin = _bul_test_scriptleri()
    y("")
    y(f"-- test_scriptleri dizini: {dizin} --")
    arac_yolu = os.path.join(dizin, ARAC + ".py") if dizin else None
    if arac_yolu and os.path.isfile(arac_yolu):
        st = os.stat(arac_yolu)
        y(f"  {ARAC}.py bulundu: {st.st_size} bayt, "
          f"degisim={datetime.datetime.fromtimestamp(st.st_mtime):%Y-%m-%d %H:%M:%S}")
    else:
        y("  !! Arac dosyasi BULUNAMADI — dizin cozumlenemedi.")

    y("")
    y("-- Arac calistiriliyor --")
    if arac_yolu and os.path.isfile(arac_yolu):
        try:
            g = {"__name__": "__main__", "__file__": arac_yolu}
            with open(arac_yolu, encoding="utf-8") as f:
                kaynak = f.read()
            exec(compile(kaynak, arac_yolu, "exec"), g)
            y("  >> Arac HATASIZ tamamlandi.")
            y(f"  >> Sahnedeki toplam EMPTY: {len([o for o in bpy.data.objects if o.type=='EMPTY'])}")
            kol = bpy.data.collections.get("AGAC_VIDASI_TESHIS")
            y(f"  >> AGAC_VIDASI_TESHIS koleksiyonu: {len(kol.objects) if kol else 'YOK'} obje")
        except Exception:
            y("  !! ARAC HATA VERDI — tam traceback:")
            y(traceback.format_exc())
    else:
        y("  (arac bulunamadigi icin calistirilamadi)")

    hedefler = []
    if dizin:
        hedefler.append(os.path.join(dizin, "ciktilar"))
    hedefler += [SABIT_CIKTI_DIZINI, os.path.expanduser("~")]
    yazildi = None
    for h in hedefler:
        try:
            os.makedirs(h, exist_ok=True)
            yol = os.path.join(h, "TESHIS_RAPORU.txt")
            with open(yol, "w", encoding="utf-8") as f:
                f.write("\n".join(R) + "\n")
            yazildi = yol
            break
        except OSError:
            continue
    print("=" * 70)
    print(f">> TESHIS RAPORU YAZILDI: {yazildi}")
    print("=" * 70)


main()   # __main__ korumasi YOK — nasil calistirilirsa calistirilsin kossun
