"""
parca_sayim.py — Adaptx Otonom Kit sayım motoru (Blender headless / Faz 1-2)
============================================================================

AKIŞ
----
`fbx/` klasöründeki HER .fbx için:
  1) Hazırlık   : import + çöp temizleme + "Default" altındaki parçaları un-parent
  2) Tespit     : parça-parça çift-boolean ile delikleri hacme göre say + kulp (kendi hacmi)
  3) Türetme    : frenli/frensiz, linco×4, ayak/allen/tıpa, kulp vidası, modül çiftleri
  4) Gram       : adet × birim ağırlık (Ağırlıklar.md)
  5) Çıktı      : pdf/<siparis>.json  (PDF'i pdf_uret.py üretir)

ÇALIŞTIRMA
----------
  blender --background --python parca_sayim.py
(veya orkestratör: bash calistir.sh)

NOT
---
- Arkalık çivisi bu sürümde ERTELENDİ (ham FBX'te tab/tav/sag/sol/ark isimleri yok).
  Çıktıda None olarak görünür. Ayrı kalinlik_bul.py aracı arkalık algoritması içindir.
- delikbulma.py'ye dokunmaz; gerekli yardımcıları kopyalar (standalone).
"""

import bpy
import bmesh
import mathutils
import os
import re
import glob
import json
import math
import itertools
from collections import Counter

# ── Yol çözümü (proje dizini) ────────────────────────────────────────────────
PROJE_DIZINI = "/home/rocket/Belgeler/adaptx-2/otonom_kit"


def _base_dir():
    # 1) ADAPTX_BASE ortam değişkeni (Docker/servis): veri klasörü (fbx/jsons/pdf).
    #    Böylece dosya yolları statiktir ve her makineye/CT'ye uyar.
    env = os.environ.get("ADAPTX_BASE")
    if env and os.path.isdir(env):
        return env
    # Blender Text editöründe __file__ = ".../x.blend/Text" olabilir (dizin DEĞİL),
    # bu yüzden önce sabit proje dizinini dene (hacim_bul.py ile aynı sıra).
    if os.path.isdir(PROJE_DIZINI):
        return PROJE_DIZINI
    try:
        d = os.path.dirname(os.path.abspath(__file__))
        if os.path.isdir(d):
            return d
    except NameError:
        pass
    return os.getcwd()


BASE = _base_dir()
FBX_DIR = os.path.join(BASE, "fbx")
OUT_DIR = os.path.join(BASE, "jsons")
# Bellek: daha önce işlenmiş siparişlerin İŞLENME sırası. JSON'u zaten olan sipariş
# tekrar işlenmez (ağır Blender adımı atlanır); yeni siparişler bu listenin SONUNA
# eklenir (pdf_uret.py özeti bu sıraya göre üretir → var olanın sonuna eklenmiş olur).
MANIFEST = os.path.join(BASE, "islem_gecmisi.json")

# ── Hacim eşikleri (delikbulma.py + yeni_hacimler.md) ────────────────────────
CATEGORIES = {
    "linco": 9680.0,
    "pim": 936.0,             # Linco Dübel deliği (linco'ya eşit; çapraz kontrol)
    "ahsapcivisi": 14.57,     # Ağaç vidası (gerçek FBX ölçümü: ~14.57)
    "rafpimi": 234.0,
    "modulbaglanti": 351.35,
    "menteseTabani": 11454.0131,   # yeni_hacimler.md
}
TOLERANCE = 0.05           # %5 (güncel delikbulma.py ile aynı)
KULP_DELIK_MESAFE = 0.192  # m — kulp deliği çifti arasındaki sabit mesafe (192 mm)
KULP_DELIK_TOL = 0.05      # %5 tolerans (±~10 mm)

# ── Uzun linco pimi (iki parçadaki birbirine dayalı linco delikleri) ──────────
# İki AYRI modülün birbirine dayanan linco gövde delikleri arasına normal linco
# dübeli yerine tek bir uzun linco pimi konur. linco_mesafe_bul.py ölçümü: abutting
# çift ~0.043 birim (~43 mm); aynı kümedeki çapraz komşular ~0.068 birim → net ayrım.
# Her abutting çift = 1 uzun pim; o çiftin 2 linco dübeli sayımdan düşülür.
LONG_LINCO_MESAFE = 0.043  # birim — birbirine dayalı linco çifti mesafesi (~43 mm)
LONG_LINCO_TOL = 0.25      # ±%25 → [0.032, 0.054], çapraz komşu (0.068) altında
# Gerçek uzun pim: iki delik AYNI eksende KARŞILIKLI (birbirine BAKAN) ve merkezleri
# arasındaki doğru bir dünya eksenine paralel (90°'nin katı). Yalnızca mesafe + işaretsiz
# yön kontrolü yetersizdi (görsel teşhiste iki gerçek çiftin arasına alakasız bir bağ ve
# AYNI yöne bakan çiftler girdi). Bu yüzden İŞARETLİ delme yönü kullanılır (conn = b - a):
#   - A deliği B'ye bakar:  dir_A · conn_hat >=  LONG_LINCO_ALIGN_MIN
#   - B deliği A'ya bakar:  dir_B · conn_hat <= -LONG_LINCO_ALIGN_MIN
#   - bağlantı doğrusu eksene hizalı: max|conn_hat bileşeni| >= LONG_LINCO_AXIS_MIN
LONG_LINCO_ALIGN_MIN = 0.9    # delme yönünün bağlantı doğrusuyla hizası (cos ~25°)
LONG_LINCO_AXIS_MIN = 0.985   # bağlantı doğrusunun en yakın eksene hizası (cos ~10°, 90° katı)

# ── Arkalık paneli (kalınlıktan tespit) + arkalık çivisi ─────────────────────
# Ölçüm: arkalık paneli 5.0 mm, gövde panelleri 18.0 mm → net ayrım.
ARKALIK_MAX_KALINLIK = 8.0   # en kısa kenar <= bu ise arkalık paneli sayılır
CIVI_ARALIK_MM = 150.0       # arkalık çivisi aralığı (orijinal 0.15 m kuralının mm karşılığı)

# ── Sabit varsayımlar (şimdilik) ─────────────────────────────────────────────
L_BAGLANTI_ADET = 2          # her sipariş için 2 L bağlantı seti (set+vida+dübel dahil)

# ── Askılık flanşı (ağaç vidası üçgeninden tespit) ───────────────────────────
# Bir parçadaki ağaç vidası deliklerinin 3'lü kombinasyonlarından kenarları
# %FLANS_KENAR_TOL içinde eşit (eşkenar, ~60°) üçgen oluşturanlar = 1 askılık flanşı.
FLANS_KENAR_TOL = 0.02       # kenar uzunlukları %2 toleransla eşit
FLANS_ACI_LO = 59.0          # eşkenar üçgen açı alt sınırı (derece)
FLANS_ACI_HI = 61.0          # eşkenar üçgen açı üst sınırı (derece)

# ── Ray seti (ahsapcivisi deliklerinin ray deseninden tespiti) ───────────────
# Kalibrasyon: kulp deliği modelde 0.192 birim ↔ gerçek 192 mm → 1 birim = 1000 mm.
# Ray delikleri de ahşap vidası boyutunda; parçadaki ahsapcivisi delikleri
# arasından doğrusal + aralıkları bir ray desenine uyanlar = 1 ray (kalanlar
# gerçek ağaç vidası). Ölçüler Ray_Seti_Bulma_Planı.md'den (mm).
RAY_SCALE_MM = 1000.0        # model birimi → mm çarpanı (kulp 0.192 ↔ 192 mm)
RAY_TOL_MM = 8.0             # delik-aralığı eşleşme toleransı (mm)
RAY_COLINEAR_TOL_MM = 8.0    # doğrusallık: en uzun kenar ≈ diğer ikisinin toplamı (mm)
# Ray boyu → ardışık delik aralıkları (mm). (delik konumları yorumda)
RAY_GAPS = {
    "55cm": [149.0, 222.0],   # delikler: 63, 212, 434
    "50cm": [150.0, 161.0],   # 64, 214, 375
    "45cm": [152.0, 102.0],   # 64, 216, 318
    "40cm": [129.0, 82.0],    # 64, 193, 275
    "35cm": [77.0, 83.0],     # 64, 141, 224
    "30cm": [109.0],          # 63, 172
    "25cm": [188.0],          # 43, 231
}

# ── Birim ağırlıklar (gram) — Ağırlıklar.md ──────────────────────────────────
WEIGHTS = {
    "rafpimi": 2.7,
    "ahsapcivisi": 1.108,
    "minifix": 3.401,
    "lincodubel": 4.4,
    "linco": 4.631,
    "lincokapak": 0.216,
    "civi": 0.335,
}


# ── delikbulma.py'den kopyalanan yardımcılar ─────────────────────────────────
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


def match_category(vol):
    for cat_name, target in CATEGORIES.items():
        if target * (1 - TOLERANCE) <= vol <= target * (1 + TOLERANCE):
            return cat_name
    return None


def world_center(obj):
    wb = [obj.matrix_world @ mathutils.Vector(v) for v in obj.bound_box]
    return sum(wb, mathutils.Vector()) / 8.0


def hole_direction(hole_obj):
    """Delik parçasının kendi lokal en-uzun ekseni = delme yönü (dünya uzayında,
    birim vektör, işaretsiz eksen). Silindirik/uzun delikler (linco) bir eksende
    belirgin uzun, diğer ikisinde ince olduğu için bu eksen delme yönünü verir."""
    dim, _ = get_perfect_local_bounds(hole_obj)
    if dim is None:
        return None
    axes = [(dim.x, mathutils.Vector((1.0, 0.0, 0.0))),
            (dim.y, mathutils.Vector((0.0, 1.0, 0.0))),
            (dim.z, mathutils.Vector((0.0, 0.0, 1.0)))]
    axes.sort(key=lambda t: t[0], reverse=True)
    local_dir = axes[0][1]
    rot = hole_obj.matrix_world.to_3x3()
    world_dir = (rot @ local_dir)
    if world_dir.length < 1e-9:
        return None
    return world_dir.normalized()


def hole_signed_direction(panel_obj, hole_obj):
    """Deliğin AÇILDIĞI (işaretli) yön — dünya uzayı, birim vektör.

    Delik boşluğunun merkezinden 6 eksen yönünde panele ray_cast atılır; panel
    gövdesine ÇARPMAYAN yön deliğin açık ucudur (delme yönü; karşı yön kör dip).
    Kenar/köşe deliğinde birden çok açık yön olabilir → deliğin en-uzun eksenine en
    hizalı açık yön seçilir. (delikbulma.py open-dir mantığının işaretli sadeleştirmesi.)
    """
    axis = hole_direction(hole_obj)
    if axis is None:
        return None
    center_w = world_center(hole_obj)
    origin_local = panel_obj.matrix_world.inverted() @ center_w
    rot = panel_obj.matrix_world.to_3x3()
    dirs_local = [mathutils.Vector((1.0, 0.0, 0.0)), mathutils.Vector((-1.0, 0.0, 0.0)),
                  mathutils.Vector((0.0, 1.0, 0.0)), mathutils.Vector((0.0, -1.0, 0.0)),
                  mathutils.Vector((0.0, 0.0, 1.0)), mathutils.Vector((0.0, 0.0, -1.0))]
    best = None
    best_align = -1.0
    for dl in dirs_local:
        hit = panel_obj.ray_cast(origin_local, dl)[0]
        if hit:
            continue
        dw = (rot @ dl).normalized()
        al = abs(dw.dot(axis))       # açık yön, en-uzun eksene ne kadar hizalı
        if al > best_align:
            best_align = al
            best = dw
    return best if best is not None else axis


def pair_count(centers, threshold=0.2):
    """Yakınlık (<threshold) ile A-B çift sayısı (delikbulma.py mantığı)."""
    unmatched = list(centers)
    pairs = 0
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
            unmatched.pop(best_idx)
            pairs += 1
    return pairs


def detect_kulp_pairs(centers):
    """Aynı parçadaki modulbaglanti-hacimli delikler arasından kulp çiftlerini ayır.
    Kulp: iki delik KULP_DELIK_MESAFE ±KULP_DELIK_TOL arasında.
    Returns (kulp_adet, kalan_merkezler — gerçek modül bağlantı adayları)."""
    lo = KULP_DELIK_MESAFE * (1 - KULP_DELIK_TOL)
    hi = KULP_DELIK_MESAFE * (1 + KULP_DELIK_TOL)
    used = [False] * len(centers)
    kulp_adet = 0
    for i in range(len(centers)):
        if used[i]:
            continue
        for j in range(i + 1, len(centers)):
            if used[j]:
                continue
            d = (centers[i] - centers[j]).length
            if lo <= d <= hi:
                used[i] = used[j] = True
                kulp_adet += 1
                break
    remaining = [c for i, c in enumerate(centers) if not used[i]]
    return kulp_adet, remaining


def detect_long_linco_pins(parts_holes):
    """Farklı parçalardaki birbirine dayalı (abutting) linco gövde delik çiftlerini bul.

    Uzun linco pimi, iki AYRI modülün birbirine dayanan linco delikleri arasına
    normal linco dübeli yerine tek bir uzun pim olarak konur. Her abutting çift =
    1 uzun pim; o çiftin normalde 2 olan linco dübeli sayımdan düşer.

    Yalnızca FARKLI parçalar arası çiftler değerlendirilir. Mesafe eşiğine EK olarak
    (conn = b - a, conn_hat = birim):
      1) A deliği B'ye bakar:  dir_A · conn_hat >=  LONG_LINCO_ALIGN_MIN
      2) B deliği A'ya bakar:  dir_B · conn_hat <= -LONG_LINCO_ALIGN_MIN
      3) bağlantı doğrusu bir eksene paralel (90° katı): max|conn_hat| >= LONG_LINCO_AXIS_MIN
    En yakın+geçerli çift önce (greedy) eşleşir, her delik en fazla bir kez kullanılır.

    parts_holes: her parça için (center, signed_direction) tuple listesi.
    Returns: uzun linco pimi adedi.
    """
    lo = LONG_LINCO_MESAFE * (1 - LONG_LINCO_TOL)
    hi = LONG_LINCO_MESAFE * (1 + LONG_LINCO_TOL)
    candidates = []   # (dist, (pi, ii), (pj, jj))
    P = len(parts_holes)
    for pi in range(P):
        for pj in range(pi + 1, P):
            for ii, (a, da) in enumerate(parts_holes[pi]):
                for jj, (b, db) in enumerate(parts_holes[pj]):
                    conn = b - a
                    d = conn.length
                    if not (lo <= d <= hi):
                        continue
                    if da is None or db is None:
                        continue
                    conn_hat = conn / d
                    # (3) bağlantı doğrusu eksene hizalı mı? (90° ve katları)
                    if max(abs(conn_hat.x), abs(conn_hat.y), abs(conn_hat.z)) < LONG_LINCO_AXIS_MIN:
                        continue
                    # (1)+(2) delikler birbirine BAKIYOR mu? (aynı yöne bakanlar elenir)
                    if da.dot(conn_hat) < LONG_LINCO_ALIGN_MIN:
                        continue
                    if db.dot(conn_hat) > -LONG_LINCO_ALIGN_MIN:
                        continue
                    candidates.append((d, (pi, ii), (pj, jj)))
    candidates.sort(key=lambda t: t[0])
    used = set()
    pins = 0
    for d, key_a, key_b in candidates:
        if key_a in used or key_b in used:
            continue
        used.add(key_a); used.add(key_b)
        pins += 1
    return pins


def _match_gap_pair(p, q):
    """İki ölçülen aralık (mm) 3-delikli bir ray desenine uyuyor mu? Ray adı ya da None."""
    for name, gaps in RAY_GAPS.items():
        if len(gaps) != 2:
            continue
        g1, g2 = gaps
        if (abs(p - g1) <= RAY_TOL_MM and abs(q - g2) <= RAY_TOL_MM) or \
           (abs(p - g2) <= RAY_TOL_MM and abs(q - g1) <= RAY_TOL_MM):
            return name
    return None


def _match_gap_single(d):
    """Tek ölçülen aralık (mm) 2-delikli bir ray desenine uyuyor mu? Ray adı ya da None."""
    for name, gaps in RAY_GAPS.items():
        if len(gaps) != 1:
            continue
        if abs(d - gaps[0]) <= RAY_TOL_MM:
            return name
    return None


def detect_rays(centers):
    """Parçadaki ahsapcivisi delik merkezlerinden ray desenlerini ayır.
    Önce 3-delikli (doğrusal + aralıkları eşleşen) raylar, sonra kalan deliklerde
    2-delikli raylar. Her ray = 1 çekmece rayı; kalan delikler gerçek ağaç vidası.
    Returns (ray_isimleri:list, kalan_merkezler:list)."""
    n = len(centers)
    used = [False] * n
    rays = []

    # 3-delikli raylar (daha spesifik → önce)
    for i, j, k in itertools.combinations(range(n), 3):
        if used[i] or used[j] or used[k]:
            continue
        dij = (centers[i] - centers[j]).length * RAY_SCALE_MM
        djk = (centers[j] - centers[k]).length * RAY_SCALE_MM
        dik = (centers[i] - centers[k]).length * RAY_SCALE_MM
        p, q, r = sorted([dij, djk, dik])
        # doğrusal mı? (en uzun kenar ≈ diğer ikisinin toplamı)
        if abs(r - (p + q)) > RAY_COLINEAR_TOL_MM:
            continue
        name = _match_gap_pair(p, q)
        if name:
            used[i] = used[j] = used[k] = True
            rays.append(name)

    # 2-delikli raylar (kalan deliklerde)
    for i, j in itertools.combinations(range(n), 2):
        if used[i] or used[j]:
            continue
        d = (centers[i] - centers[j]).length * RAY_SCALE_MM
        name = _match_gap_single(d)
        if name:
            used[i] = used[j] = True
            rays.append(name)

    remaining = [c for i, c in enumerate(centers) if not used[i]]
    return rays, remaining


def _triangle_angles(a, b, c):
    """Kenar uzunlukları (a,b,c) verilen üçgenin 3 açısı (derece). Kosinüs teoremi."""
    def ang(opp, s1, s2):
        cosv = (s1 * s1 + s2 * s2 - opp * opp) / (2.0 * s1 * s2)
        cosv = max(-1.0, min(1.0, cosv))
        return math.degrees(math.acos(cosv))
    return ang(a, b, c), ang(b, c, a), ang(c, a, b)


def count_equilateral_flanges(centers):
    """Ağaç vidası delik merkezlerinden eşkenar (~60°, kenarları %FLANS_KENAR_TOL
    içinde eşit) üçgen oluşturan 3'lüleri say. Her delik en fazla bir üçgende
    kullanılır (greedy). Her üçgen = 1 askılık flanşı."""
    n = len(centers)
    if n < 3:
        return 0
    used = [False] * n
    flanges = 0
    for i, j, k in itertools.combinations(range(n), 3):
        if used[i] or used[j] or used[k]:
            continue
        a = (centers[i] - centers[j]).length
        b = (centers[j] - centers[k]).length
        c = (centers[k] - centers[i]).length
        dmin, dmax = min(a, b, c), max(a, b, c)
        if dmin <= 1e-6:
            continue
        # kenarlar %2 içinde eşit mi?
        if dmax / dmin - 1.0 > FLANS_KENAR_TOL:
            continue
        # açılar 59-61° arasında mı? (eşkenar doğrulaması)
        angs = _triangle_angles(a, b, c)
        if any(ang < FLANS_ACI_LO or ang > FLANS_ACI_HI for ang in angs):
            continue
        used[i] = used[j] = used[k] = True
        flanges += 1
    return flanges


def part_thickness(obj):
    """Parçanın en kısa kenarı (MDF kalınlığı), yerel uzayda."""
    dim, _ = get_perfect_local_bounds(obj)
    if dim is None:
        return None
    return min(dim.x, dim.y, dim.z)


def arkalik_civi_count(obj):
    """Arkalık panelinin çevresine CIVI_ARALIK_MM aralıkla dizilen çivi sayısı
    (delikbulma.py 0.15 m kuralının mm karşılığı: 2*num_x + 2*num_z)."""
    dim, _ = get_perfect_local_bounds(obj)
    dims = sorted([dim.x, dim.y, dim.z])
    W, H = dims[2], dims[1]      # iki büyük kenar (kalınlık hariç)
    nx = max(1, math.ceil(W / CIVI_ARALIK_MM))
    nz = max(1, math.ceil(H / CIVI_ARALIK_MM))
    return 2 * nx + 2 * nz


# ── Bellek (işlem geçmişi) ───────────────────────────────────────────────────
def order_from_name(fbx_path):
    """Dosya adından sipariş no'yu çıkar (import gerektirmez → atlama kontrolü için)."""
    m = re.search(r'(\d{4,}(?:-\d+)?)', os.path.basename(fbx_path))
    return m.group(1) if m else "0000"


def _load_manifest():
    try:
        with open(MANIFEST, encoding="utf-8") as f:
            return list(json.load(f).get("siralama", []))
    except (FileNotFoundError, ValueError):
        return []


def _save_manifest(order_list):
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump({"siralama": order_list}, f, ensure_ascii=False, indent=2)


def _existing_orders():
    return [os.path.splitext(os.path.basename(p))[0]
            for p in glob.glob(os.path.join(OUT_DIR, "*.json"))]


# ── Hazırlık: FBX import + un-parent (hazırlık scriptinin sadece prep kısmı) ──
def prep_import(fbx_path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=fbx_path)

    order = order_from_name(fbx_path)

    for n in ["Front", "Perspective", "Right", "Top"]:
        ob = bpy.data.objects.get(n)
        if ob:
            bpy.data.objects.remove(ob, do_unlink=True)

    default_obj = bpy.data.objects.get("Default")
    if default_obj:
        for child in list(default_obj.children):
            wm = child.matrix_world.copy()
            child.parent = None
            child.matrix_world = wm
        bpy.data.objects.remove(default_obj, do_unlink=True)

    return order


# ── Sayım ────────────────────────────────────────────────────────────────────
def count_order(order):
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']

    counts = Counter()          # ham kategori sayıları
    kulp = 0
    ayak = 0
    parts_with_mentese = 0
    modulbag_centers = []
    linco_holes_by_part = []    # her parçanın linco delikleri: [(center, direction), ...]
    arkalik_civi = 0
    askilik_flansi = 0
    ray_isimleri = []           # tespit edilen ray boyları (ör. "55cm", "30cm")
    part_count = len(meshes)

    for o in meshes:
        # Arkalık paneli mi? (kalınlıktan) → çivi say, delik taramasını atla
        th = part_thickness(o)
        if th is not None and th <= ARKALIK_MAX_KALINLIK:
            arkalik_civi += arkalik_civi_count(o)
            continue

        # Delikler
        try:
            holes = execute_double_boolean(o)
        except Exception as e:
            print(f"  [UYARI] {o.name}: delik taraması başarısız ({e})")
            continue

        part_mentese = 0
        part_ahsap_centers = []
        part_modul_centers = []
        part_linco_holes = []
        for h in holes:
            v = h["volume"]
            obj_part = h["object"]
            cat = match_category(v)
            if cat == "modulbaglanti":
                part_modul_centers.append(world_center(obj_part))
            elif cat == "ahsapcivisi":
                # ray/ağaç vidası ayrımı aşağıda desen taramasıyla yapılır
                part_ahsap_centers.append(world_center(obj_part))
            elif cat == "linco":
                counts["linco"] += 1
                part_linco_holes.append(
                    (world_center(obj_part), hole_signed_direction(o, obj_part)))
            elif cat:
                counts[cat] += 1
                if cat == "menteseTabani":
                    part_mentese += 1
            bpy.data.objects.remove(obj_part, do_unlink=True)

        # Bu parçadaki modulbaglanti deliklerinden kulp çiftlerini ayır
        kulp_from_part, remaining_modul = detect_kulp_pairs(part_modul_centers)
        kulp += kulp_from_part
        modulbag_centers.extend(remaining_modul)

        # Ray desenleri (ahsapcivisi deliklerinden) — bu delikler ağaç vidası
        # sayımından çıkarılır; kalanlar gerçek ağaç vidası deliğidir.
        part_rays, remaining_ahsap = detect_rays(part_ahsap_centers)
        ray_isimleri.extend(part_rays)
        counts["ahsapcivisi"] += len(remaining_ahsap)

        if part_mentese > 0:
            parts_with_mentese += 1
        if len(remaining_ahsap) == 4:   # bir parçada TAM 4 ağaç vidası → 1 ayak
            ayak += 1
        # Askılık flanşı: kalan ağaç vidası deliklerinden eşkenar üçgenler
        askilik_flansi += count_equilateral_flanges(remaining_ahsap)

        # Uzun linco pimi için: bu parçanın linco delik/yön çiftlerini sakla
        if part_linco_holes:
            linco_holes_by_part.append(part_linco_holes)

    pairs = pair_count(modulbag_centers)
    # Farklı parçalardaki birbirine dayalı + yönü hizalı linco çiftleri → uzun linco pimi
    uzun_linco_pim = detect_long_linco_pins(linco_holes_by_part)

    linco = counts["linco"]
    linco_dubel = linco - 2 * uzun_linco_pim   # her uzun pim = 2 linco dübeli yerine 1
    mentese_tabani = counts["menteseTabani"]
    frenli = parts_with_mentese
    frensiz = mentese_tabani - frenli
    raf_pimi = counts["rafpimi"] // 3     # her raf pimi = 3 delik
    l_baglanti = L_BAGLANTI_ADET
    # Ağaç vidası = (ray'lar çıkarılmış) delik sayısı + her L bağlantı seti için 4 adet
    agac_vidasi = counts["ahsapcivisi"] + 4 * l_baglanti
    askilik_borusu = askilik_flansi // 2     # her 2 flanşı için 1 boru
    ray_adet = len(ray_isimleri)             # tespit edilen tekil ray sayısı
    ray_counter = Counter(ray_isimleri)      # boya göre tekil ray sayısı
    # Aynı boydaki 2 ray (sol+sağ) = 1 set. Boy bazında set adedi (ör. {"55cm": 2}).
    ray_setleri = {L: c // 2 for L, c in sorted(ray_counter.items()) if c // 2 >= 1}

    adet = {
        "Frenli Menteşe": frenli,
        "Frensiz Menteşe": frensiz,
        "Menteşe Tabanı": mentese_tabani,
        "Modülleri Birbirine Bağlama": pairs,
        "Raf Pimi": raf_pimi,
        "Linco Gövde": linco,
        "Linco Kapak": linco,
        "Linco Dübel": linco_dubel,
        "Minifix": linco,
        "Uzun Linco Pimi": uzun_linco_pim,
        "Ayarlı Ayak": ayak,
        "Allen": 1 if ayak >= 1 else 0,
        "Tıpa": ayak,
        "Kulp": kulp,
        "Kulp Vidası": 2 * kulp,
        "L Bağlantı Seti": l_baglanti,
        "Askılık Flanşı": askilik_flansi,
        "Askılık Borusu": askilik_borusu,
        "Ağaç Vidası": agac_vidasi,
        "Arkalık Çivisi": arkalik_civi,   # kalınlık-tabanlı arkalık tespiti
    }

    def gr(n, w):
        return round(n * w, 1)

    gram = {
        "Raf Pimi": gr(raf_pimi, WEIGHTS["rafpimi"]),
        "Ağaç Vidası": gr(agac_vidasi, WEIGHTS["ahsapcivisi"]),
        "Minifix": gr(linco, WEIGHTS["minifix"]),
        "Linco Dübel": gr(linco_dubel, WEIGHTS["lincodubel"]),
        "Linco": gr(linco, WEIGHTS["linco"]),
        "Linco Kapak": gr(linco, WEIGHTS["lincokapak"]),
        "Çivi": gr(arkalik_civi, WEIGHTS["civi"]),
    }

    return {
        "siparis": order,
        "parca_sayisi": part_count,
        "adet": adet,
        "gram": gram,
        "ray_setleri": ray_setleri,    # boy bazında ray seti adedi (ör. {"55cm": 2})
        "_ham": dict(counts),          # doğrulama için (linco==pim beklenir)
        "_kulp": kulp,
        "_raylar": ray_isimleri,       # tespit edilen ray boyları (doğrulama için)
        "_uzun_linco": uzun_linco_pim, # birbirine dayalı linco çifti sayısı
    }


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    fbxs = sorted(glob.glob(os.path.join(FBX_DIR, "*.fbx")))
    print(f"== parca_sayim: {len(fbxs)} FBX bulundu ({FBX_DIR})")
    if not fbxs:
        print("!! fbx/ klasörü boş. İşlenecek sipariş yok.")
        return

    # Bellek: önceki çalıştırmalardan kalan JSON'ları sıraya tohumla (sıralı), yeni
    # işlenenler sona eklenecek. JSON'u zaten olan sipariş yeniden işlenmez.
    manifest = _load_manifest()
    for o in sorted(_existing_orders()):
        if o not in manifest:
            manifest.append(o)

    yeni = 0
    atlanan = 0
    for fbx in fbxs:
        order = order_from_name(fbx)
        out_path = os.path.join(OUT_DIR, f"{order}.json")
        if os.path.exists(out_path):
            print(f"--- Atlandı (zaten işlenmiş): {os.path.basename(fbx)}")
            atlanan += 1
            continue

        print(f"\n--- İşleniyor: {os.path.basename(fbx)}")
        try:
            prep_import(fbx)
            res = count_order(order)
        except Exception as e:
            print(f"!! {os.path.basename(fbx)} işlenemedi: {e}")
            import traceback; traceback.print_exc()
            continue

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
        if order not in manifest:
            manifest.append(order)     # yeni sipariş → sıranın sonuna
        _save_manifest(manifest)
        yeni += 1
        print(f"   Sipariş {order}: {res['adet']} ")
        print(f"   [ham] {res['_ham']}  kulp={res['_kulp']}  uzunlinco={res['_uzun_linco']}")
        print(f"   >> {out_path}")

    _save_manifest(manifest)
    print(f"\n== Bitti: {yeni} yeni sipariş işlendi, {atlanan} atlandı (zaten işlenmiş).")


if __name__ == "__main__":
    main()
