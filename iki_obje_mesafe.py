"""
iki_obje_mesafe.py — SEÇİLİ (2 veya daha fazla) objenin TÜM ikili kombinasyonları
arasındaki uzaklıkları bir texte yazar.

AMAÇ (Algoritmaların_testi.md #15 / ray debug): Ayarlı ayağı ve ray desenlerini
"birbirine hep AYNI mesafelerde olan delik grupları" ile bulacağız. Bu geçici
araç, seçtiğin TÜM objeler (ör. ahsap_civi_empty.py / ray_delik_empty.py'nin
koyduğu Empty'ler) arasındaki HER ikili mesafeyi ölçer ve bir metin dosyasına
EKLER. Böylece 3-4-5+ deliği tek seferde seçip aralarındaki TÜM mesafeleri
görebilir, sabit örüntüyü (kenar uzunlukları, köşegen, ray aralıkları) tek
çalıştırmada çıkarabilirsin.

KULLANIM (GUI):
    1) Viewport'ta 2 veya daha fazla obje seç (Empty ya da mesh farketmez).
    2) Scripting sekmesinde bu dosyayı çalıştır.
    3) N obje seçiliyse C(N,2) ikili mesafe konsola yazılır VE
       iki_obje_mesafe_raporu.txt'ye eklenir (küçükten büyüğe sıralı).
    (Her çalıştırma dosyanın SONUNA bir ölçüm bloğu ekler → çok sayıda ölçüm birikir.)

ÇIKTI (her ikili için):
    - A ve B obje adları
    - origin↔origin uzaklık (m ve mm)          ← Empty'ler için asıl ölçü
    - eksen bileşenleri |dx| |dy| |dz| (mm)
    - (mesh'ler için) bbox-merkez↔bbox-merkez uzaklık (mm)

NOT: Sahne ölçeği 1 birim = 1000 mm (kulp deliği 0.192 birim ↔ 192 mm kalibrasyonu),
     bu yüzden mm = birim × 1000.
"""

import bpy
import mathutils
import time
import itertools

SCALE_MM = 1000.0
OUT_PATH = "/home/rocket/Belgeler/adaptx-2/otonom_kit/iki_obje_mesafe_raporu.txt"


def obj_origin(o):
    """Objenin dünya-uzayı origin'i (Empty için = konumu)."""
    return o.matrix_world.translation.copy()


def obj_bbox_center(o):
    """Objenin dünya-uzayı bbox merkezi (Empty'de bbox sıfır → origin'e eşit)."""
    wb = [o.matrix_world @ mathutils.Vector(v) for v in o.bound_box]
    return sum(wb, mathutils.Vector()) / 8.0


def _blok(a, b):
    oa, ob = obj_origin(a), obj_origin(b)
    d = ob - oa
    dist = d.length
    ca, cb = obj_bbox_center(a), obj_bbox_center(b)
    dist_bbox = (cb - ca).length

    lines = []
    lines.append(f"A = {a.name}   ({a.type})")
    lines.append(f"B = {b.name}   ({b.type})")
    lines.append(f"origin↔origin :  {dist:.5f} birim   =  {dist * SCALE_MM:.2f} mm")
    lines.append(f"  |dx|={abs(d.x) * SCALE_MM:8.2f} mm   "
                 f"|dy|={abs(d.y) * SCALE_MM:8.2f} mm   "
                 f"|dz|={abs(d.z) * SCALE_MM:8.2f} mm")
    if a.type == 'MESH' or b.type == 'MESH':
        lines.append(f"bbox↔bbox    :  {dist_bbox:.5f} birim   =  {dist_bbox * SCALE_MM:.2f} mm")
    return dist * SCALE_MM, "\n".join(lines)


def main():
    sec = list(bpy.context.selected_objects)
    if len(sec) < 2:
        print(f"!! En az 2 obje seçmelisin (şu an {len(sec)} seçili). "
              f"Delik/Empty seç ve tekrar çalıştır.")
        return

    ciftler = list(itertools.combinations(sec, 2))
    sonuclar = [(_blok(a, b)) for a, b in ciftler]
    sonuclar.sort(key=lambda t: t[0])   # küçükten büyüğe mesafeye göre sırala

    baslik = "=" * 60 + "\n" + time.strftime("[%Y-%m-%d %H:%M:%S]") + \
        f"\n{len(sec)} obje seçili -> {len(ciftler)} ikili kombinasyon\n" + "=" * 60

    bloklar = [baslik] + [b for _mm, b in sonuclar]
    block = "\n\n".join(bloklar)
    print("\n" + block)

    try:
        with open(OUT_PATH, "a", encoding="utf-8") as f:
            f.write(block + "\n")
        print(f"\n>> Eklendi: {OUT_PATH}")
    except OSError as e:
        print(f"\n[UYARI] Dosyaya yazılamadı ({e}); yukarıdaki konsol çıktısı geçerli.")


if __name__ == "__main__":
    main()
