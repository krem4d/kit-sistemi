"""
arkalik_civi_empty.py — Arkalık paneli + arkalık çivisi tespitini GÖRSEL
olarak test etmek için Empty koyan araç.

AMAÇ: parca_sayim.py'deki GERÇEK algoritmayı (kalınlık eşiği → hacim+yüzey-
teması ile ikiye-kesilmiş çift birleştirme → çevre çivisi formülü) BİREBİR
aynı mantıkla ama SAHNEYİ BOZMADAN (bpy.ops.object.join YOK — gerçek
algoritma bunu kalıcı yapar, bu araç sadece SİMÜLE eder) çalıştırır ve:
    1) Her tespit edilen arkalık paneline (birleşmiş çift veya tekil) bir
       KÜP Empty koyar — adında TEKIL/BIRLESIK, boy (W×H mm) ve hesaplanan
       çivi adedi yazar.
    2) O panelin çevresine, gerçek formülle (CIVI_ARALIK_MM aralıklı,
       2·nx + 2·nz) hesaplanan HER çivi konumuna küçük bir KÜRE Empty koyar.
Böylece hem "hangi parçalar arkalık sayıldı", hem "hangi çiftler ikiye-
kesilmiş sayılıp birleştirildi", hem de "çiviler nereye ve kaç tane
geliyor" viewport'ta gözle doğrulanabilir.

KULLANIM (GUI):
    1) Test etmek istediğin FBX'i normal şekilde içe aktar
       (File > Import > FBX). Sahnede TÜM parçalar olsun yeterli — Default
       parent'ını temizlemene gerek yok (bu script parent'tan bağımsız,
       world-uzayında çalışır).
    2) Scripting sekmesinde bu dosyayı çalıştır (Alt+P).
    3) Konsolda özet + viewport'ta Empty'ler oluşur:
         - "arkalik_TEKIL_<obj>_WxHmm_civi=N"
         - "arkalik_BIRLESIK_<objA>+<objB>_WxHmm_civi=N"
         - "civi_<panelId>#<i>"

NOT: Gerçek algoritma (parca_sayim.py) birleştirmeyi bpy.ops.object.join ile
     KALICI yapar (iki obje tek mesh'e döner). Bu araç sahneni bozmasın diye
     birleştirmeyi SADECE world-AABB üzerinden matematiksel olarak simüle
     eder — objeler sahnede değişmeden kalır, tekrar tekrar çalıştırabilirsin.
NOT: Sabitler (ARKALIK_MAX_KALINLIK, ARKALIK_ESLESME_TOL, ARKALIK_TEMAS_TOL_MM,
     CIVI_ARALIK_MM) parca_sayim.py ile AYNI değerde, buraya birebir
     kopyalanmıştır — parca_sayim.py'ye dokunulmadı.
"""

import bpy
import bmesh
import mathutils
import math

# ── Sabitler (parca_sayim.py ile AYNI) ────────────────────────────────────────
ARKALIK_MAX_KALINLIK = 8.0     # en kısa kenar (mm, local) <= bu ise arkalık paneli
CIVI_ARALIK_MM = 150.0         # çivi aralığı (mm)
ARKALIK_ESLESME_TOL = 0.03     # %3 — iki yarının hacmi bu tolerans içinde eşit olmalı
ARKALIK_TEMAS_TOL_MM = 2.0     # mm — temas/örtüşme toleransı (world uzayında)
SCALE_MM = 1000.0              # world birim -> mm (sahne 1 birim = 1000 mm)

PANEL_EMPTY_BOYUT = 0.03
CIVI_EMPTY_BOYUT = 0.01


# ── Yardımcılar (parca_sayim.py ile aynı mantık) ─────────────────────────────
def get_perfect_local_bounds(obj):
    verts = obj.data.vertices
    if not verts:
        return None
    min_x = min(v.co.x for v in verts); max_x = max(v.co.x for v in verts)
    min_y = min(v.co.y for v in verts); max_y = max(v.co.y for v in verts)
    min_z = min(v.co.z for v in verts); max_z = max(v.co.z for v in verts)
    return mathutils.Vector((max_x - min_x, max_y - min_y, max_z - min_z))


def part_thickness(obj):
    dim = get_perfect_local_bounds(obj)
    if dim is None:
        return None
    return min(dim.x, dim.y, dim.z)


def mesh_volume(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.transform(obj.matrix_world)
    vol = abs(bm.calc_volume())
    bm.free()
    return vol


def world_aabb(obj):
    wb = [obj.matrix_world @ mathutils.Vector(v) for v in obj.bound_box]
    xs = [c.x for c in wb]; ys = [c.y for c in wb]; zs = [c.z for c in wb]
    return (mathutils.Vector((min(xs), min(ys), min(zs))),
            mathutils.Vector((max(xs), max(ys), max(zs))))


def tam_yuzey_temasi(a, b):
    amin, amax = world_aabb(a)
    bmin, bmax = world_aabb(b)
    tol = ARKALIK_TEMAS_TOL_MM / SCALE_MM
    for eksen in range(3):
        digerleri = [e for e in range(3) if e != eksen]
        bitisik = (abs(amax[eksen] - bmin[eksen]) <= tol or
                   abs(bmax[eksen] - amin[eksen]) <= tol)
        if not bitisik:
            continue
        if all(abs(amin[e] - bmin[e]) <= tol and abs(amax[e] - bmax[e]) <= tol
               for e in digerleri):
            return True
    return False


def pair_split_arkalik_sanal(parts):
    """pair_split_arkalik ile AYNI eşleştirme mantığı, ama bpy.ops.object.join
    YOK — sadece (çift, tekil) listelerini döndürür, sahneyi değiştirmez."""
    kalan = list(parts)
    ciftler = []
    tekiller = []
    while kalan:
        o = kalan.pop(0)
        vo = mesh_volume(o)
        eslesen = None
        for i, o2 in enumerate(kalan):
            if (abs(mesh_volume(o2) - vo) <= vo * ARKALIK_ESLESME_TOL
                    and tam_yuzey_temasi(o, o2)):
                eslesen = i
                break
        if eslesen is not None:
            o2 = kalan.pop(eslesen)
            ciftler.append((o, o2))
        else:
            tekiller.append(o)
    return ciftler, tekiller


def _linspace(a, b, n):
    if n <= 1:
        return [(a + b) / 2.0]
    return [a + (b - a) * i / (n - 1) for i in range(n)]


def civi_pozisyonlari_ve_adet(aabb_min, aabb_max):
    """Verilen world-AABB için (nail_pozisyonlari[Vector], adet) döndürür.
    Adet formülü arkalik_civi_count ile AYNI: 2·ceil(W/150) + 2·ceil(H/150)."""
    dims = [aabb_max[i] - aabb_min[i] for i in range(3)]
    kalinlik_ekseni = dims.index(min(dims))
    a0, a1 = [i for i in range(3) if i != kalinlik_ekseni]
    min0, max0 = aabb_min[a0], aabb_max[a0]
    min1, max1 = aabb_min[a1], aabb_max[a1]
    kalinlik_orta = (aabb_min[kalinlik_ekseni] + aabb_max[kalinlik_ekseni]) / 2.0

    n0 = max(1, math.ceil((max0 - min0) * SCALE_MM / CIVI_ARALIK_MM))
    n1 = max(1, math.ceil((max1 - min1) * SCALE_MM / CIVI_ARALIK_MM))

    pozisyonlar = []

    def nokta(v0, v1):
        p = [0.0, 0.0, 0.0]
        p[a0] = v0; p[a1] = v1; p[kalinlik_ekseni] = kalinlik_orta
        return mathutils.Vector(p)

    for v0 in _linspace(min0, max0, n0):     # üst + alt kenar
        pozisyonlar.append(nokta(v0, max1))
        pozisyonlar.append(nokta(v0, min1))
    for v1 in _linspace(min1, max1, n1):     # sağ + sol kenar
        pozisyonlar.append(nokta(max0, v1))
        pozisyonlar.append(nokta(min0, v1))

    return pozisyonlar, 2 * n0 + 2 * n1


def add_empty(name, loc, size, disp='PLAIN_AXES'):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = disp
    e.empty_display_size = size
    e.location = loc
    bpy.context.collection.objects.link(e)
    return e


def _safe(name):
    return name.replace(" ", "_")[:24]


def _panel_wh_mm(aabb_min, aabb_max):
    dims = sorted([(aabb_max[i] - aabb_min[i]) * SCALE_MM for i in range(3)])
    return dims[2], dims[1]   # iki büyük kenar (kalınlık hariç), mm


# ── Ana logic ──────────────────────────────────────────────────────────────
def main():
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    adaylar = [o for o in meshes if (part_thickness(o) or 999) <= ARKALIK_MAX_KALINLIK]

    print(f"\n=== arkalik_civi_empty: {len(meshes)} mesh tarandı, "
          f"{len(adaylar)} arkalık adayı bulundu ===")

    if not adaylar:
        print("!! Arkalık adayı yok (kalınlık <= {ARKALIK_MAX_KALINLIK} mm hiç bulunamadı).")
        return

    ciftler, tekiller = pair_split_arkalik_sanal(adaylar)

    toplam_civi = 0
    panel_no = 0

    for a, b in ciftler:
        panel_no += 1
        amin, amax = world_aabb(a)
        bmin, bmax = world_aabb(b)
        birlesik_min = mathutils.Vector((min(amin.x, bmin.x), min(amin.y, bmin.y), min(amin.z, bmin.z)))
        birlesik_max = mathutils.Vector((max(amax.x, bmax.x), max(amax.y, bmax.y), max(amax.z, bmax.z)))
        W, H = _panel_wh_mm(birlesik_min, birlesik_max)
        merkez = (birlesik_min + birlesik_max) / 2.0
        pozisyonlar, adet = civi_pozisyonlari_ve_adet(birlesik_min, birlesik_max)
        toplam_civi += adet

        isim = f"arkalik_BIRLESIK_{_safe(a.name)}+{_safe(b.name)}_{W:.0f}x{H:.0f}mm_civi={adet}"
        add_empty(isim, merkez, PANEL_EMPTY_BOYUT, disp='CUBE')
        for i, p in enumerate(pozisyonlar):
            add_empty(f"civi_p{panel_no}#{i}", p, CIVI_EMPTY_BOYUT, disp='SPHERE')

        print(f"  [BİRLEŞİK] {a.name} + {b.name}  ->  {W:.1f}×{H:.1f} mm  ->  {adet} çivi")

    for o in tekiller:
        panel_no += 1
        omin, omax = world_aabb(o)
        W, H = _panel_wh_mm(omin, omax)
        merkez = (omin + omax) / 2.0
        pozisyonlar, adet = civi_pozisyonlari_ve_adet(omin, omax)
        toplam_civi += adet

        isim = f"arkalik_TEKIL_{_safe(o.name)}_{W:.0f}x{H:.0f}mm_civi={adet}"
        add_empty(isim, merkez, PANEL_EMPTY_BOYUT, disp='CUBE')
        for i, p in enumerate(pozisyonlar):
            add_empty(f"civi_p{panel_no}#{i}", p, CIVI_EMPTY_BOYUT, disp='SPHERE')

        print(f"  [TEKİL]    {o.name}  ->  {W:.1f}×{H:.1f} mm  ->  {adet} çivi")

    print(f"\n>> {len(ciftler)} birleşmiş çift + {len(tekiller)} tekil panel "
          f"= {panel_no} arkalık paneli.")
    print(f">> Toplam Arkalık Çivisi: {toplam_civi}")
    print("   Viewport'ta 'arkalik_' ve 'civi_' önekleriyle filtrele.")


if __name__ == "__main__":
    main()
