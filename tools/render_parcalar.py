"""Panel parca gorselleri: tek studyo kurulumuyla urun renderlari + donus seridi.

Kullanim (proje kokunden):
    blender --background --python tools/render_parcalar.py -- [secenekler]

Secenekler:
    --parca SLUG [SLUG ...]   yalniz bu parcalar (varsayilan: hepsi)
    --ara DIR                 ara PNG klasoru (varsayilan: /tmp/otonom_kit_render)
    --cikti DIR               webp + manifest klasoru (varsayilan: static/parcalar)
    --kare N                  donus seridi kare sayisi (varsayilan 24)
    --hizli                   dusuk ornekleme (onizleme)
    --sadece-tur / --sadece-gorsel
    --paketle-yalniz          render yok; ara PNG'leri webp'e cevirip manifest yazar
    --buyuk-tur / --buyuk-tur-yok   512 px seritler (<slug>-tur-512.webp) varsayilan acik; ikincisi kapatir
    --rim K                   kenar (rim) isigi carpani (varsayilan 1.0); parca tanimindaki "rim" once gelir
    --kesif DOSYA             tek bir modeli nesne-nesne renkli basar (model kesfi)

Ara PNG'ler projeye girmez (proje .gitignore'u *.png'yi dislar); cikti .webp'dir.
Bu dosya iki modda calisir: Blender icinde render, sistem Python'unda paketleme
(Blender'in Python'unda Pillow yok; render bitince kendini `python3` ile cagirir).
"""
import os
import sys
import json
import math
import subprocess
import unicodedata

try:
    import bpy  # noqa: F401
    BLENDER_ICINDE = True
except ImportError:
    BLENDER_ICINDE = False

PROJE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BELGELER = "/home/rocket/Belgeler"
ESKI = BELGELER + "/adaptx/adaptx old/montaj/parçalar/"
KULLANILAN = BELGELER + "/adaptx/animasyon/montage/.most used/"
MONTAJ2 = BELGELER + "/adaptx-2/Montage System/"
MODULBAG = BELGELER + "/adaptx-2/modulbag/"

# --------------------------------------------------------------------------
# Parca tanimlari. Anahtar = panelde ve jsons/*.json "adet" sozlugunde gecen ad.
#   slug        : dosya adi (ASCII kucuk harf-tire)
#   kaynak      : [(fbx yolu, {nesne_adi_oneki: malzeme | [slot malzemeleri]})]
#                 '*' = kalan tum nesneler; eslesmeyen nesne silinir.
#   prosedurel  : True ise kaynak yok, insa fonksiyonu (INSA[slug]) kurar
#   poz         : (x, y, z) derece, parcayi sahneye koymadan once dondurur
#   yaw         : duran gorselin yatay donus acisi (derece)
#   el          : kamera yuksekligi (derece), varsayilan 26
#   tur_poz     : (istege bagli) donus seridi icin ayri poz; yoksa poz. Doner-simetrik
#                 parcalar duz durunca 24 kare birebir ayni olur; egik poz donusu gorunur kilar
#   tur_el      : (istege bagli) donus seridi icin kamera yuksekligi; yoksa el
#   boy_mm      : FBX parcalar icin gercek boyut (en uzun kenar, mm) — FBX'lerin olcegi
#                 dosyadan dosyaya degistigi icin mesh'ten turetilemez (katalog degeri,
#                 boy_tahmin=True ile isaretlenir); None = boy siparise gore degisir.
#                 Prosedurel parcalarda boy mesh'ten (mm) olculur.
#   pah_oran    : (istege bagli) FBX parcaya en uzun kenarin bu orani kadar kenar pahi ekler
#   boru        : (istege bagli) dict(ic=, oval=(eksen, olcek)): boruyu ici bos yapar
#   malz        : (istege bagli) bu parcaya ozel malzeme ezmesi {malzeme: {alan: deger}}
#   golge_pay   : (istege bagli) tur kamerasi sigdirmasina golgenin zemindeki izini de katar;
#                 deger = golge uzunluguna uygulanan carpan (1.0 = tam). Golge kare disina tasmasin diye
#   tur_doluluk : (istege bagli) tur karelerinde nesnenin kareyi doldurma orani (varsayilan DOLULUK)
#   rim         : (istege bagli) kenar isigi carpani
# --------------------------------------------------------------------------
PARCALAR = {
    "Frenli Menteşe": dict(slug="frenli-mentese", prosedurel=False, boy_mm=100, boy_tahmin=True,
        kaynak=[(ESKI + "frenli menteşe.fbx", {"Body 02": "nikel", "Body 05": "celik", "Body 05.001": "celik"})]),
    "Frensiz Menteşe": dict(slug="frensiz-mentese", prosedurel=False, boy_mm=95, boy_tahmin=True,
        kaynak=[(ESKI + "frensiz menteşe.fbx", {"Body 06 (2)": "nikel", "Body 05.001": "celik", "Body 05.002": "celik"})]),
    "Menteşe Tabanı": dict(slug="mentese-tabani", prosedurel=False, boy_mm=46, boy_tahmin=True,
        kaynak=[(ESKI + "frensiz menteşe.fbx", {"Body 05": "nikel"})]),
    "Modülleri Birbirine Bağlama": dict(slug="modul-baglama", prosedurel=False, boy_mm=42, boy_tahmin=True,
        kaynak=[(ESKI + "modul baglanti.fbx", {"*": "nikel"})]),
    "Raf Pimi": dict(slug="raf-pimi", prosedurel=False, boy_mm=20, boy_tahmin=True,
        kaynak=[(ESKI + "Raf Pimi.fbx", {"*": "nikel"})]),
    "Linco Gövde": dict(slug="linco-govde", prosedurel=False, boy_mm=53, boy_tahmin=True,
        golge_pay=0.85, tur_doluluk=0.72,
        kaynak=[(KULLANILAN + "mesan linco optimized.fbx", {"Mesan_Linco_Gövde": "zamak"})]),
    "Linco Kapak": dict(slug="linco-kapak", prosedurel=False, el=22, poz=(120, 0, 0), yaw=-90, pah_oran=0.017,
        tur_poz=(155, 0, 0), tur_el=50,
        boy_mm=18, boy_tahmin=True,
        kaynak=[(KULLANILAN + "mesan linco optimized.fbx", {"Minifix_Kapak": "beyaz_plastik"})]),
    "Linco Dübel": dict(slug="linco-dubel", prosedurel=True, tur_poz=(70, 0, 0), tur_el=30),
    "Minifix": dict(slug="minifix", prosedurel=False, boy_mm=17, boy_tahmin=True,
        kaynak=[(KULLANILAN + "mesan linco optimized.fbx", {"Minifix.001": "zamak"})]),
    "Uzun Linco Pimi": dict(slug="uzun-linco-pimi", prosedurel=False, el=30, yaw=-55, boy_mm=60, boy_tahmin=True,
        kaynak=[(KULLANILAN + "uzun pim.fbx", {"*": "nikel"})]),
    "Ayarlı Ayak": dict(slug="ayarli-ayak", prosedurel=False, boy_mm=50, boy_tahmin=True,
        kaynak=[(KULLANILAN + "ayak optimized.fbx", {"ayak gövdesi": "beyaz_plastik", "ayak vidası": "siyah_plastik"})]),
    "Allen": dict(slug="allen", prosedurel=False, poz=(0, 90, 0), yaw=0, el=38, boy_mm=80, boy_tahmin=True,
        kaynak=[(ESKI + "alyan.fbx", {"*": "siyah_celik"})]),
    "Tıpa": dict(slug="tipa", prosedurel=True, tur_poz=(35, 0, 0)),
    "Kulp": dict(slug="kulp", prosedurel=False, poz=(90, 0, 0), el=30, boy_mm=210, boy_tahmin=True,
        kaynak=[(KULLANILAN + "Kulp.fbx", {"*": ["celik", "nikel"]})]),
    "Kulp Vidası": dict(slug="kulp-vidasi", prosedurel=True, poz=(90, 0, 0), el=30),
    "L Bağlantı Seti": dict(slug="l-baglanti-seti", prosedurel=True),
    "Askılık Flanşı": dict(slug="askilik-flansi", prosedurel=False, poz=(180, 0, 0), el=34, tur_poz=(200, 0, 0),
        yuva=dict(ic=0.90, derin=0.85),
        boy_mm=50, boy_tahmin=True,
        kaynak=[(KULLANILAN + "askılık.fbx", {"Ask_l_k_Borusu.001": "nikel"})]),
    "Askılık Borusu": dict(slug="askilik-borusu", prosedurel=False, poz=(90, 0, 0), el=30, boy_mm=None,
        boru=dict(ic=0.88, oval=(1, 0.8)),
        kaynak=[(KULLANILAN + "askılık.fbx", {"Ayarl__Ayak_(3).001": "nikel"})],
        boy_kisalt={"Ayarl__Ayak_(3).001": 0.45}),
    "Ağaç Vidası": dict(slug="agac-vidasi", prosedurel=True, poz=(90, 0, 0), el=30),
    "Arkalık Çivisi": dict(slug="arkalik-civisi", prosedurel=True, poz=(90, 0, 0), el=30),
    "Ray Seti": dict(slug="ray-seti", prosedurel=True, el=34, tur_el=48, yaw=0),
}

# --------------------------------------------------------------------------
# Malzemeler (Principled BSDF). Gercek yuzey: metal=1 ise renk = yansima rengi.
# --------------------------------------------------------------------------
MALZEMELER = {
    "celik":          dict(renk=(0.46, 0.47, 0.49), metal=1.0, pur=0.30),
    "nikel":          dict(renk=(0.64, 0.63, 0.61), metal=1.0, pur=0.24),
    "zamak":          dict(renk=(0.45, 0.46, 0.48), metal=1.0, pur=0.30),
    "cinko":          dict(renk=(0.62, 0.64, 0.68), metal=1.0, pur=0.26),
    "siyah_celik":    dict(renk=(0.10, 0.104, 0.112), metal=0.85, pur=0.24),
    "beyaz_plastik":  dict(renk=(0.52, 0.52, 0.51), metal=0.0, pur=0.36),
    "gri_plastik":    dict(renk=(0.40, 0.41, 0.43), metal=0.0, pur=0.40),
    "siyah_plastik":  dict(renk=(0.028, 0.028, 0.030), metal=0.0, pur=0.42),
    "ahsap":          dict(renk=(0.74, 0.55, 0.33), metal=0.0, pur=0.55),
    "pirinc":         dict(renk=(0.78, 0.60, 0.30), metal=1.0, pur=0.22),
}

GORSEL_BOYUT = 768
TUR_BOYUT = 256
TUR_BUYUK = 512        # buyuk gorunum seridi (<slug>-tur-512.webp): gercek 512 render, buyutme yok
KUCUK_BOYUT = 192      # liste/serit kucuk resmi (<slug>-192.webp)
TUR_RENDER = 512       # sprite karelerini 2x cozunurlukte basip kucultur (kenar yumusatma)
BUYUK_HEDEF_KB = 900   # 512 serit dosya basi hedef; asarsa kalite dusurulur
DOLULUK = 0.76         # nesne kareyi %76 doldurur; _kenar_sonuk bandi (%10) ile 0.02 pay kalir
POZLAMA = -0.5         # EV; -0.3 ile acik zeminde 8 parcanin ortalama parlakligi hala >180 cikti
KAMERA_AZ = 35.0       # derece, kameranin -Y ekseninden saga sapmasi
KAMERA_EL = 26.0


# ==========================================================================
#  PAKETLEME (sistem Python'u)
# ==========================================================================
def paketle(ara, cikti, kare, parcalar, tam=True, buyuk=True):
    from PIL import Image
    os.makedirs(cikti, exist_ok=True)
    manifest_yol = os.path.join(cikti, "manifest.json")
    manifest = {}
    if os.path.exists(manifest_yol):
        try:
            manifest = json.load(open(manifest_yol, encoding="utf-8"))
        except Exception:
            manifest = {}
    for anahtar, t in PARCALAR.items():
        slug = t["slug"]
        if parcalar and slug not in parcalar:
            continue
        durak = os.path.join(ara, slug, "durak.png")
        if not os.path.exists(durak):
            continue
        im = Image.open(durak).convert("RGBA")
        if im.size != (GORSEL_BOYUT, GORSEL_BOYUT):
            im = im.resize((GORSEL_BOYUT, GORSEL_BOYUT), Image.LANCZOS)
        im = _kenar_sonuk(im)
        im.save(os.path.join(cikti, slug + ".webp"), "WEBP", quality=88, method=6, alpha_quality=100)
        # kucuk resim: kaydedilmis ana webp'den (kayiplı sikistirma dahil, panelde gorunen bu) Lanczos
        _premul_kucult(Image.open(os.path.join(cikti, slug + ".webp")).convert("RGBA"), KUCUK_BOYUT).save(
            os.path.join(cikti, slug + "-192.webp"), "WEBP", quality=85, method=6, alpha_quality=100)
        girdi = dict(slug=slug, gorsel="parcalar/%s.webp" % slug, tur=None, kare=kare,
                     prosedurel=bool(t["prosedurel"]))
        girdi.update(_boy_oku(ara, slug, t, manifest.get(anahtar, {})))
        kareler = [os.path.join(ara, slug, "tur", "%02d.png" % i) for i in range(kare)]
        if all(os.path.exists(k) for k in kareler):
            serit = Image.new("RGBA", (TUR_BOYUT * kare, TUR_BOYUT), (0, 0, 0, 0))
            for i, k in enumerate(kareler):
                f = Image.open(k).convert("RGBA")
                if f.size != (TUR_BOYUT, TUR_BOYUT):
                    # kucultmeden once on-carpim: seffaf piksellerin siyahi kenara sizmasin
                    f = _premul_kucult(f, TUR_BOYUT)
                f = _kenar_sonuk(f)
                serit.paste(f, (i * TUR_BOYUT, 0))
            serit.save(os.path.join(cikti, slug + "-tur.webp"), "WEBP", quality=86, method=6,
                       alpha_quality=100)
            girdi["tur"] = "parcalar/%s-tur.webp" % slug
            if buyuk:
                _buyuk_serit(kareler, os.path.join(cikti, slug + "-tur-512.webp"))
        else:
            eski = manifest.get(anahtar, {})
            girdi["tur"] = eski.get("tur")
        # alanlar yalniz dosya gercekten varsa yazilir (panel yoklugu tolere eder)
        if buyuk and os.path.exists(os.path.join(cikti, slug + "-tur-512.webp")):
            girdi["tur_512"] = "parcalar/%s-tur-512.webp" % slug
        girdi["kucuk"] = "parcalar/%s-192.webp" % slug
        manifest[anahtar] = girdi
    # sira: PARCALAR sirasi
    sirali = {k: manifest[k] for k in PARCALAR if k in manifest}
    with open(manifest_yol, "w", encoding="utf-8") as f:
        json.dump(sirali, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("paketlendi:", len(sirali), "parca ->", cikti)


def _buyuk_serit(kareler, yol):
    """512 px seridi: kareler zaten 512 render; yeniden boyutlandirma yok (yalniz kenar sonuk).
    Dosya BUYUK_HEDEF_KB'yi asarsa kalite 82'den basamak basamak dusurulur."""
    from PIL import Image
    n = len(kareler)
    serit = Image.new("RGBA", (TUR_BUYUK * n, TUR_BUYUK), (0, 0, 0, 0))
    for i, k in enumerate(kareler):
        f = Image.open(k).convert("RGBA")
        if f.size != (TUR_BUYUK, TUR_BUYUK):
            raise SystemExit("%s: %s 512x512 degil; buyutme yasak, yeniden render gerekir" % (k, f.size))
        serit.paste(_kenar_sonuk(f), (i * TUR_BUYUK, 0))
    for kalite in (82, 78, 74, 70, 66, 62, 58, 54, 50):
        serit.save(yol, "WEBP", quality=kalite, method=6, alpha_quality=100)
        if os.path.getsize(yol) <= BUYUK_HEDEF_KB * 1024:
            break
    print("  %s: q=%d, %d KB" % (os.path.basename(yol), kalite, os.path.getsize(yol) // 1024))


def _boy_oku(ara, slug, t, eski):
    """boy_mm: Blender asamasinin yazdigi olcu.json (prosedurel: mesh'ten olculen; FBX: tanimdaki
    katalog degeri). Yoksa tanima, o da yoksa eski manifeste duser. boy_tahmin=True: katalog tahmini."""
    yol = os.path.join(ara, slug, "olcu.json")
    if os.path.exists(yol):
        try:
            o = json.load(open(yol, encoding="utf-8"))
            return dict(boy_mm=o.get("boy_mm"), boy_tahmin=bool(o.get("boy_tahmin")))
        except Exception:
            pass
    if "boy_mm" in t:
        return dict(boy_mm=t["boy_mm"], boy_tahmin=bool(t.get("boy_tahmin")))
    return {k: eski[k] for k in ("boy_mm", "boy_tahmin") if k in eski}


def _kenar_sonuk(im, bant=0.10):
    """Golgenin kare siniriyla sert kesilmesini onler: kenardan %bant icinde alfa yumusakca sifirlanir.
    Nesne %76 doluluga gore ortalandigi icin (kenardan %12) kenar bandinda yalniz golge vardir."""
    import numpy as np
    a = np.asarray(im).astype("float32")
    h, w = a.shape[:2]
    y = np.minimum(np.arange(h), h - 1 - np.arange(h)) / (h * bant)
    x = np.minimum(np.arange(w), w - 1 - np.arange(w)) / (w * bant)
    t = np.clip(np.minimum(y[:, None], x[None, :]), 0, 1)
    m = t * t * (3 - 2 * t)
    a[..., 3] *= m
    from PIL import Image
    return Image.fromarray(a.clip(0, 255).astype("uint8"), "RGBA")


def _premul_kucult(im, boyut):
    from PIL import Image
    import numpy as np
    a = np.asarray(im).astype("float32") / 255.0
    rgb = a[..., :3] * a[..., 3:4]
    pm = np.concatenate([rgb, a[..., 3:4]], axis=2)
    pim = Image.fromarray((pm * 255 + 0.5).astype("uint8"), "RGBA").resize((boyut, boyut), Image.LANCZOS)
    p = np.asarray(pim).astype("float32") / 255.0
    al = p[..., 3:4]
    rgb = np.where(al > 1e-4, p[..., :3] / np.maximum(al, 1e-4), 0.0)
    out = np.concatenate([np.clip(rgb, 0, 1), al], axis=2)
    return Image.fromarray((out * 255 + 0.5).astype("uint8"), "RGBA")


# ==========================================================================
#  BLENDER TARAFI
# ==========================================================================
if BLENDER_ICINDE:
    import bpy
    import bmesh
    import numpy as np
    from mathutils import Vector, Matrix, Euler

    # ---------------------------------------------------------------- malzeme
    AKTIF_MALZ = {}     # parca_render doldurur: tanim["malz"] ezmeleri (yalniz o parca icin)

    def malzeme_yap(ad):
        if ad.startswith("renk"):       # kesif modu: renk0, renk1 ...
            i = int(ad[4:])
            import colorsys
            r, g, b = colorsys.hsv_to_rgb((i * 0.17) % 1.0, 0.65, 0.9)
            spec = dict(renk=(r, g, b), metal=0.0, pur=0.5)
        else:
            spec = dict(MALZEMELER[ad])
            spec.update(AKTIF_MALZ.get(ad, {}))
        m = bpy.data.materials.get(ad)
        if m:
            return m
        m = bpy.data.materials.new(ad)
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (*spec["renk"], 1.0)
        b.inputs["Metallic"].default_value = spec["metal"]
        b.inputs["Roughness"].default_value = spec["pur"]
        if spec["metal"] < 0.5:
            b.inputs["Specular IOR Level"].default_value = 0.45
        return m

    # ----------------------------------------------------------------- sahne
    def sahne_sifirla():
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def motor_kur(sc, ornek, boyut):
        sc.render.engine = "CYCLES"
        cy = sc.cycles
        cy.samples = ornek
        cy.use_adaptive_sampling = True
        cy.adaptive_threshold = 0.01
        cy.use_denoising = True
        cy.denoiser = "OPENIMAGEDENOISE"
        try:
            cy.denoising_use_gpu = True
        except Exception:
            pass
        cy.max_bounces = 8
        cy.glossy_bounces = 6
        cy.transmission_bounces = 4
        cy.sample_clamp_indirect = 8.0
        cy.film_exposure = 1.0
        cy.device = "CPU"
        try:
            prefs = bpy.context.preferences.addons["cycles"].preferences
            for tur in ("OPTIX", "CUDA"):
                try:
                    prefs.compute_device_type = tur
                    prefs.get_devices()
                    gpuler = [d for d in prefs.devices if d.type != "CPU"]
                    if gpuler:
                        for d in prefs.devices:
                            d.use = d.type != "CPU"
                        cy.device = "GPU"
                        break
                except Exception:
                    continue
        except Exception:
            pass
        r = sc.render
        r.resolution_x = r.resolution_y = boyut
        r.resolution_percentage = 100
        r.film_transparent = True
        r.image_settings.file_format = "PNG"
        r.image_settings.color_mode = "RGBA"
        r.image_settings.color_depth = "8"
        r.filter_size = 1.3
        vs = sc.view_settings
        vs.view_transform = "AgX"
        try:
            vs.look = "AgX - Medium High Contrast"
        except Exception:
            pass
        vs.exposure = POZLAMA
        sc.display_settings.display_device = "sRGB"

    def dunya_kur(sc):
        """Yumusak gradyan studyo ortami: metallerin yansitacak bir seyi olsun."""
        w = bpy.data.worlds.new("studyo")
        sc.world = w
        w.use_nodes = True
        nt = w.node_tree
        nt.nodes.clear()
        tc = nt.nodes.new("ShaderNodeTexCoord")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        mr = nt.nodes.new("ShaderNodeMapRange")
        cr = nt.nodes.new("ShaderNodeValToRGB")
        bg = nt.nodes.new("ShaderNodeBackground")
        out = nt.nodes.new("ShaderNodeOutputWorld")
        mr.inputs["From Min"].default_value = -1.0
        mr.inputs["From Max"].default_value = 1.0
        el = cr.color_ramp.elements
        el[0].position = 0.0
        el[0].color = (0.03, 0.03, 0.035, 1)
        el[1].position = 1.0
        # ust uc 0.60: yukari bakan duz metal yuzeyler saf beyaza patlamasin
        el[1].color = (0.60, 0.60, 0.60, 1)
        # 0.70'te dar koyu bant (v=0.06): metallerde okunacak bir kontrast cizgisi birakir
        for pos, v in ((0.42, 0.10), (0.56, 0.34), (0.70, 0.06), (0.80, 0.58)):
            e = cr.color_ramp.elements.new(pos)
            e.color = (v, v, v * 1.03, 1)
        bg.inputs["Strength"].default_value = 0.42
        nt.links.new(tc.outputs["Generated"], sep.inputs[0])
        nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
        nt.links.new(mr.outputs["Result"], cr.inputs[0])
        nt.links.new(cr.outputs[0], bg.inputs["Color"])
        nt.links.new(bg.outputs[0], out.inputs[0])

    ANAHTAR_ISIK = dict(rel_az=-50, el=58, mesafe=7.0)   # golge izdusumu icin (isik_kur ile ayni)

    def isik_kur(sc, az, rim=1.0):
        """3 nokta + ust yumusak kutu. Kameraya gore yerlesir (kamera sabit, nesne doner).
        rim: kenar (arka) isigi carpani."""
        def alan(ad, rel_az, el, mesafe, boyut, guc, renk=(1, 1, 1), golge=False):
            a = math.radians(az + rel_az)
            e = math.radians(el)
            konum = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))) * mesafe
            konum.z += 0.4
            ld = bpy.data.lights.new(ad, "AREA")
            ld.shape = "SQUARE"
            ld.size = boyut
            ld.energy = guc
            ld.color = renk
            ld.use_shadow = golge
            o = bpy.data.objects.new(ad, ld)
            sc.collection.objects.link(o)
            o.location = konum
            yon = Vector((0, 0, 0.4)) - konum
            o.rotation_euler = yon.to_track_quat("-Z", "Y").to_euler()
            o.visible_camera = False
            return o
        alan("anahtar", -50, 58, 7.0, 1.8, 620, (1.0, 0.98, 0.95), golge=True)
        alan("dolgu", 70, 20, 7.5, 6.0, 140, (0.93, 0.96, 1.0))
        alan("kenar", 165, 35, 7.0, 3.5, 330 * rim)
        alan("ust", 0, 88, 6.5, 5.0, 40)

    def zemin_kur(sc):
        bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0))
        z = bpy.context.object
        z.name = "zemin"
        z.is_shadow_catcher = True
        return z

    def kamera_olustur(sc):
        cd = bpy.data.cameras.new("kamera")
        cd.sensor_width = 36.0
        cd.sensor_fit = "HORIZONTAL"
        co = bpy.data.objects.new("kamera", cd)
        sc.collection.objects.link(co)
        sc.camera = co
        return co

    # ------------------------------------------------------------------ geometri
    def mesh_nesneleri(kok):
        return [o for o in kok.children_recursive if o.type == "MESH"]

    def dunya_vertler(kok):
        parcalar = []
        bpy.context.view_layer.update()
        for o in mesh_nesneleri(kok):
            n = len(o.data.vertices)
            if not n:
                continue
            co = np.empty(n * 3, dtype=np.float64)
            o.data.vertices.foreach_get("co", co)
            co = co.reshape(n, 3)
            M = np.array(o.matrix_world, dtype=np.float64)
            parcalar.append(co @ M[:3, :3].T + M[:3, 3])
        return np.concatenate(parcalar, axis=0)

    def kok_olustur(nesneler):
        kok = bpy.data.objects.new("kok", None)
        bpy.context.scene.collection.objects.link(kok)
        for o in nesneler:
            if o.parent is None or o.parent not in nesneler:
                mw = o.matrix_world.copy()
                o.parent = kok
                o.matrix_world = mw
        return kok

    def pürüzsüz(nesne, aci=38):
        if nesne.type != "MESH":
            return
        bpy.ops.object.select_all(action="DESELECT")
        nesne.select_set(True)
        bpy.context.view_layer.objects.active = nesne
        try:
            bpy.ops.object.shade_smooth_by_angle(angle=math.radians(aci))
        except Exception:
            bpy.ops.object.shade_smooth()

    def boy_kisalt(o, oran):
        """Dunya donusumunu mesh'e isler, en uzun eksen boyunca oran kadar kisaltir (merkezden)."""
        o.parent = None
        o.data.transform(o.matrix_world)
        o.matrix_world = Matrix.Identity(4)
        n = len(o.data.vertices)
        co = np.empty(n * 3)
        o.data.vertices.foreach_get("co", co)
        co = co.reshape(n, 3)
        eks = int(np.argmax(co.max(0) - co.min(0)))
        orta = (co[:, eks].max() + co[:, eks].min()) / 2
        co[:, eks] = orta + (co[:, eks] - orta) * oran
        o.data.vertices.foreach_set("co", co.ravel())
        o.data.update()

    def dunyaya_isle(o):
        """Dunya donusumunu mesh'e isler (parent'siz, birim matris): bevel/boolean genislikleri dunya olcusunde olur."""
        bpy.context.view_layer.update()
        mw = o.matrix_world.copy()
        o.parent = None
        o.data.transform(mw)
        o.matrix_world = Matrix.Identity(4)
        o.data.update()

    def mesh_vertler(o):
        n = len(o.data.vertices)
        co = np.empty(n * 3)
        o.data.vertices.foreach_get("co", co)
        return co.reshape(n, 3)

    def pah_ekle(o, oran, aci):
        """FBX parcaya kenar pahi: genislik = en uzun kenar * oran (kapak icin ~0.3 mm / 18 mm)."""
        dunyaya_isle(o)
        V = mesh_vertler(o)
        bevel(o, float((V.max(0) - V.min(0)).max()) * oran, 2, 35)
        pürüzsüz(o, aci)

    def boru_bosalt(o, cfg, aci):
        """Dolu silindiri boru yapar: boydan boya ic silindiri boolean ile cikarir (ic = ic/dis yaricap
        orani), sonra kesiti oval yapar (cfg['oval'] = (eksen, olcek)); delik de birlikte ovallesir."""
        dunyaya_isle(o)
        V = mesh_vertler(o)
        mn, mx = V.min(0), V.max(0)
        ext = mx - mn
        merk = (mn + mx) / 2
        eks = int(np.argmax(ext))
        diger = [i for i in range(3) if i != eks]
        r = float(max(ext[diger])) / 2
        boy = float(ext[eks])
        k = bm_silindir(r * cfg["ic"], boy * 1.5, z0=-boy * 0.75, seg=64)
        if eks == 0:
            bmesh.ops.rotate(k, verts=k.verts[:], cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(90), 3, "Y"))
        elif eks == 1:
            bmesh.ops.rotate(k, verts=k.verts[:], cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(90), 3, "X"))
        bmesh.ops.translate(k, verts=k.verts[:], vec=tuple(float(x) for x in merk))
        kes(o, k)
        if cfg.get("oval"):
            ax, olc = cfg["oval"]
            V = mesh_vertler(o)
            V[:, ax] = merk[ax] + (V[:, ax] - merk[ax]) * olc
            o.data.vertices.foreach_set("co", V.ravel())
            o.data.update()
        pürüzsüz(o, aci)

    def yuva_ac(o, cfg, aci):
        """Dolu govdeli kovan (kulah) parcaya kor boru yuvasi acar. FBX'te kovan z ekseninde, serbest
        ucu en alttadir (z_min) ve ust uctaki plakaya kapali; ic = yuva/kovan yaricap orani,
        derin = kovan boyunun kacinin oyulacagi."""
        dunyaya_isle(o)
        V = mesh_vertler(o)
        zmin, zmax = float(V[:, 2].min()), float(V[:, 2].max())
        govde = V[V[:, 2] < zmin + 0.9 * (zmax - zmin)]       # plakanin altindaki kovan
        cx, cy = (govde[:, 0].max() + govde[:, 0].min()) / 2, (govde[:, 1].max() + govde[:, 1].min()) / 2
        r = float(np.hypot(govde[:, 0] - cx, govde[:, 1] - cy).max())
        # kovanin plakaya bitistigi z: plaka kalinligi disinda kalan yukseklik
        plaka_z = float(V[np.hypot(V[:, 0] - cx, V[:, 1] - cy) > r * 1.3][:, 2].min())
        h = (plaka_z - zmin) * cfg["derin"]
        k = bm_silindir(r * cfg["ic"], h + 0.02 * r, z0=zmin - 0.02 * r, seg=64, x=cx, y=cy)
        kes(o, k)
        pürüzsüz(o, aci)

    def boy_olc(kok):
        """En uzun kenar: eksene hizali kutu ile ana-eksen (PCA) kutusunun kucugu. Yalniz prosedurel
        parcalarda anlamli (mm); FBX olcekleri dosyadan dosyaya degisir."""
        V = dunya_vertler(kok)
        aabb = float((V.max(0) - V.min(0)).max())
        Vc = V - V.mean(0)
        _, _, vt = np.linalg.svd(Vc[:: max(1, len(Vc) // 20000)], full_matrices=False)
        P = Vc @ vt.T
        return min(aabb, float((P.max(0) - P.min(0)).max()))

    def boy_yuvarla(v):
        return None if v is None else (int(round(v)) if v >= 10 else round(float(v), 1))

    # ---------------------------------------------------------------- iceri aktar
    def ice_aktar(yol):
        once = set(bpy.data.objects.keys())
        ext = os.path.splitext(yol)[1].lower()
        if ext == ".fbx":
            bpy.ops.import_scene.fbx(filepath=yol)
        elif ext == ".obj":
            bpy.ops.wm.obj_import(filepath=yol)
        else:
            raise RuntimeError("desteklenmeyen: " + yol)
        return [bpy.data.objects[k] for k in bpy.data.objects.keys() if k not in once]

    def kaynaklari_kur(tanim):
        """FBX'lerden secilen nesneleri yukler, malzemeyi atar, kok nesneyi dondurur."""
        tutulan = []
        for yol, harita in tanim["kaynak"]:
            yeni = ice_aktar(yol)
            for o in yeni:
                if o.type != "MESH":
                    continue
                malz = None
                # once tam ad, yoksa '*'. Blender adin sonuna .001 ekleyebilir; FBX adini oldugu gibi kullan.
                nfc = {unicodedata.normalize("NFC", k): v for k, v in harita.items()}
                malz = nfc.get(unicodedata.normalize("NFC", o.name))
                if malz is None:
                    malz = harita.get("*")
                if malz is None:
                    continue
                tutulan.append((o, malz))
            # tutulmayanlari sil (bos/ebeveyn nesneleri sonra temizlenir)
            tut_ad = {o.name for o, _ in tutulan}
            for o in list(yeni):
                if o.name not in tut_ad and o.type == "MESH":
                    bpy.data.objects.remove(o, do_unlink=True)
        nesneler = []
        for o, malz in tutulan:
            slotlar = malz if isinstance(malz, list) else [malz]
            o.data.materials.clear()
            for s in slotlar:
                o.data.materials.append(malzeme_yap(s))
            # poligon slot indeksleri fazlaysa son slota sikistir
            n = len(slotlar)
            if n:
                for p in o.data.polygons:
                    if p.material_index >= n:
                        p.material_index = n - 1
            pürüzsüz(o, tanim.get("duzgun_aci", 38))
            nesneler.append(o)
            if o.name in tanim.get("boy_kisalt", {}):
                boy_kisalt(o, tanim["boy_kisalt"][o.name])
            if tanim.get("pah_oran"):
                pah_ekle(o, tanim["pah_oran"], tanim.get("duzgun_aci", 38))
            if tanim.get("boru"):
                boru_bosalt(o, tanim["boru"], tanim.get("duzgun_aci", 38))
            if tanim.get("yuva"):
                yuva_ac(o, tanim["yuva"], tanim.get("duzgun_aci", 38))
        # ebeveyn zincirini sadelestir: dunya donusumunu koruyarak kokle
        kok = kok_olustur(nesneler)
        # kalan bos nesneleri sil
        for o in list(bpy.data.objects):
            if o.type == "EMPTY" and o is not kok:
                bpy.data.objects.remove(o, do_unlink=True)
        return kok

    # --------------------------------------------------------------- yerlestirme
    def yerlestir(kok, poz):
        """Pozu uygular, nesneyi birim yaricapa olcekler, xy merkezler, zemine oturtur.
        Dondurur: (A matrisi, taban vertler [N,3] A uygulanmis)."""
        R = Euler([math.radians(a) for a in poz], "XYZ").to_matrix().to_4x4()
        kok.matrix_world = R
        V = dunya_vertler(kok)
        mn, mx = V.min(0), V.max(0)
        c = (mn + mx) / 2
        s = 1.0 / np.max(np.linalg.norm(V - c, axis=1))
        T1 = Matrix.Translation(Vector((-c[0], -c[1], -c[2])))
        S = Matrix.Scale(s, 4)
        zmin = s * (mn[2] - c[2])
        T2 = Matrix.Translation(Vector((0, 0, -zmin)))
        A = T2 @ S @ T1 @ R
        kok.matrix_world = A
        Vt = dunya_vertler(kok)
        return A, Vt

    def yaw_uygula(kok, A, derece):
        Rz = Matrix.Rotation(math.radians(derece), 4, "Z")
        kok.matrix_world = Rz @ A

    def yaw_vertler(Vt, derece):
        a = math.radians(derece)
        c, s = math.cos(a), math.sin(a)
        R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
        return Vt @ R.T

    def golge_izi(V, az, pay=1.0):
        """Anahtar isigin nesneden zemine dusurdugu golgenin yaklasik noktalari ([N,3], z=0).
        Kamera sigdirmasina katilir ki golge kare siniriyla kesilmesin. pay: golge uzunluk carpani."""
        a = math.radians(az + ANAHTAR_ISIK["rel_az"])
        e = math.radians(ANAHTAR_ISIK["el"])
        L = np.array([math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)]) * ANAHTAR_ISIK["mesafe"]
        L[2] += 0.4
        t = L[2] / np.maximum(L[2] - V[:, 2], 1e-6)
        G = L + (V - L) * t[:, None]
        G[:, 2] = 0.0
        taban = V.copy()
        taban[:, 2] = 0.0
        G = taban + (G - taban) * pay          # golge uzunlugunu pay ile olcekle
        return G

    def kamera_hizala(kam, Vler, el, doluluk=DOLULUK):
        """Vler: [N,3] (ya da birlesik). Sabit dar-FOV kamera; odak+shift ile sigdirir."""
        V = np.concatenate(Vler, axis=0) if isinstance(Vler, list) else Vler
        mn, mx = V.min(0), V.max(0)
        merkez = (mn + mx) / 2
        a = math.radians(KAMERA_AZ)
        e = math.radians(el)
        yon = np.array([math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)])
        D = 14.0
        P = merkez + yon * D
        f = -yon
        sag = np.cross(f, [0, 0, 1.0])
        sag /= np.linalg.norm(sag)
        yuk = np.cross(sag, f)
        rel = V - P
        z = rel @ f
        nx = (rel @ sag) / z
        ny = (rel @ yuk) / z
        xmn, xmx, ymn, ymx = nx.min(), nx.max(), ny.min(), ny.max()
        hx, hy = (xmx - xmn) / 2, (ymx - ymn) / 2
        lens = doluluk * 18.0 / max(hx, hy)
        kam.location = Vector(P)
        kam.rotation_euler = Vector(f).to_track_quat("-Z", "Y").to_euler()
        cd = kam.data
        cd.lens = lens
        cd.shift_x = lens * ((xmx + xmn) / 2) / 36.0
        cd.shift_y = lens * ((ymx + ymn) / 2) / 36.0
        cd.clip_start = 1.0
        cd.clip_end = 60.0

    # ------------------------------------------------------------------- render
    def bas(sc, yol):
        sc.render.filepath = yol
        bpy.ops.render.render(write_still=True)

    def parca_render(anahtar, tanim, ara, kare, hizli, gorsel=True, tur=True, insa=None, rim=1.0):
        slug = tanim["slug"]
        print("=== %s (%s)" % (anahtar, slug), flush=True)
        sahne_sifirla()
        sc = bpy.context.scene
        AKTIF_MALZ.clear()
        AKTIF_MALZ.update(tanim.get("malz", {}))
        if tanim["prosedurel"]:
            kok = insa(sc)
        else:
            kok = kaynaklari_kur(tanim)
        klasor = os.path.join(ara, slug)
        os.makedirs(os.path.join(klasor, "tur"), exist_ok=True)
        if "boy_mm" in tanim:       # FBX: katalog degeri (None = boy siparise gore degisir)
            boy = tanim["boy_mm"]
        else:                       # prosedurel: mesh mm cinsinden
            boy = boy_olc(kok)
        with open(os.path.join(klasor, "olcu.json"), "w", encoding="utf-8") as f:
            json.dump(dict(boy_mm=boy_yuvarla(boy), boy_tahmin=bool(tanim.get("boy_tahmin", False))), f)
        A, Vt = yerlestir(kok, tanim.get("poz", (0, 0, 0)))
        el = tanim.get("el", KAMERA_EL)
        yaw = tanim.get("yaw", 0.0)
        kam = kamera_olustur(sc)
        dunya_kur(sc)
        isik_kur(sc, KAMERA_AZ, tanim.get("rim", rim))
        zemin_kur(sc)

        if gorsel:
            motor_kur(sc, 48 if hizli else 192, GORSEL_BOYUT)
            yaw_uygula(kok, A, yaw)
            kamera_hizala(kam, yaw_vertler(Vt, yaw), el)
            bas(sc, os.path.join(klasor, "durak.png"))
        if tur:
            motor_kur(sc, 24 if hizli else 64, TUR_RENDER)
            acilar = [yaw + 360.0 * i / kare for i in range(kare)]
            # doner-simetrik parca duz durunca 24 kare ayni olur: tur_poz egik/yatik poz verir
            At, Vtt = yerlestir(kok, tanim["tur_poz"]) if tanim.get("tur_poz") else (A, Vt)
            tel = tanim.get("tur_el", el)
            # tum acilarin birlesik kutusu (+ istege bagli golge izi); tek sabit kamera
            vler = [yaw_vertler(Vtt, a) for a in acilar]
            if tanim.get("golge_pay"):
                vler += [golge_izi(v, KAMERA_AZ, tanim["golge_pay"]) for v in vler]
            kamera_hizala(kam, vler, tel, tanim.get("tur_doluluk", DOLULUK))
            for i, a in enumerate(acilar):
                yaw_uygula(kok, At, a)
                bas(sc, os.path.join(klasor, "tur", "%02d.png" % i))

    def kesif(dosya, ara):
        """Bir modeli nesne nesne farkli renkle basar; hangi nesne ne anlasin."""
        sahne_sifirla()
        sc = bpy.context.scene
        yeni = ice_aktar(dosya)
        nes = [o for o in yeni if o.type == "MESH"]
        for i, o in enumerate(nes):
            o.data.materials.clear()
            o.data.materials.append(malzeme_yap("renk%d" % i))
            pürüzsüz(o)
            print("  renk%d = %s  verts=%d" % (i, o.name, len(o.data.vertices)))
        kok = kok_olustur(nes)
        for o in list(bpy.data.objects):
            if o.type == "EMPTY" and o is not kok:
                bpy.data.objects.remove(o, do_unlink=True)
        A, Vt = yerlestir(kok, (0, 0, 0))
        kam = kamera_olustur(sc)
        dunya_kur(sc)
        isik_kur(sc, KAMERA_AZ)
        zemin_kur(sc)
        motor_kur(sc, 32, 640)
        kamera_hizala(kam, Vt, KAMERA_EL)
        ad = os.path.splitext(os.path.basename(dosya))[0].replace(" ", "_")
        os.makedirs(os.path.join(ara, "kesif"), exist_ok=True)
        bas(sc, os.path.join(ara, "kesif", ad + ".png"))

    # ======================================================================
    #  PROSEDUREL MODELLER  (olculer mm; sahneye yerlestirirken birim yaricapa olceklenir)
    # ======================================================================
    INSA = {}

    def bm_nesne(ad, bm, malz, duz=False):
        """bmesh -> sahne nesnesi (malzemeli)."""
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        me = bpy.data.meshes.new(ad)
        bm.to_mesh(me)
        bm.free()
        o = bpy.data.objects.new(ad, me)
        bpy.context.scene.collection.objects.link(o)
        me.materials.append(malzeme_yap(malz))
        return o

    def bm_silindir(r, h, z0=0.0, seg=72, r2=None, x=0.0, y=0.0):
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg,
                              radius1=r, radius2=(r if r2 is None else r2), depth=h)
        bmesh.ops.translate(bm, verts=bm.verts[:], vec=(x, y, z0 + h / 2))
        return bm

    def bm_kutu(bx, by, bz, konum=(0, 0, 0)):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, verts=bm.verts[:], vec=(bx, by, bz))
        bmesh.ops.translate(bm, verts=bm.verts[:], vec=konum)
        return bm

    def bm_donel(noktalar, seg=72):
        """(r, z) profilini Z ekseninde 360 derece dondurur."""
        bm = bmesh.new()
        vs = [bm.verts.new((r, 0.0, z)) for r, z in noktalar]
        es = [bm.edges.new((vs[i], vs[i + 1])) for i in range(len(vs) - 1)]
        bmesh.ops.spin(bm, geom=vs + es, cent=(0, 0, 0), axis=(0, 0, 1),
                       angle=2 * math.pi, steps=seg, use_merge=False, use_duplicate=False)
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
        return bm

    def bm_cokgen_ekstrude(noktalar, uzunluk, y0=0.0):
        """XZ duzleminde kapali cokgen, +Y yonunde ekstrude (y0..y0+uzunluk)."""
        bm = bmesh.new()
        vs = [bm.verts.new((x, y0, z)) for x, z in noktalar]
        f = bm.faces.new(vs)
        r = bmesh.ops.extrude_face_region(bm, geom=[f])
        yeni = [e for e in r["geom"] if isinstance(e, bmesh.types.BMVert)]
        bmesh.ops.translate(bm, verts=yeni, vec=(0, uzunluk, 0))
        return bm

    def uygula_mod(o):
        bpy.context.view_layer.objects.active = o
        for m in list(o.modifiers):
            bpy.ops.object.select_all(action="DESELECT")
            o.select_set(True)
            bpy.ops.object.modifier_apply(modifier=m.name)

    def bevel(o, w, seg=3, aci=32):
        m = o.modifiers.new("bevel", "BEVEL")
        m.width = w
        m.segments = seg
        m.limit_method = "ANGLE"
        m.angle_limit = math.radians(aci)
        uygula_mod(o)

    def kes(o, kesici_bm, islem="DIFFERENCE"):
        """o'dan kesici geometriyi cikarir (boolean fark) ya da kesisimini alir."""
        me = bpy.data.meshes.new("kesici")
        kesici_bm.to_mesh(me)
        kesici_bm.free()
        k = bpy.data.objects.new("kesici", me)
        bpy.context.scene.collection.objects.link(k)
        m = o.modifiers.new("kes", "BOOLEAN")
        m.operation = islem
        m.solver = "EXACT"
        m.object = k
        uygula_mod(o)
        bpy.data.objects.remove(k, do_unlink=True)

    def kok_yap(nesneler):
        for o in nesneler:
            pürüzsüz(o)
        return kok_olustur(nesneler)

    def yerle(o, konum=(0, 0, 0), donus=(0, 0, 0)):
        o.location = Vector(konum)
        o.rotation_euler = Euler([math.radians(a) for a in donus], "XYZ")
        bpy.context.view_layer.update()
        return o

    # ---- vida govdesi: gercek sarmal disli (z = 0 uc, z = L bas altina) ----
    def bm_disli(r, L, adim, derinlik, seg=56, uc=None, adim_kare=10):
        uc = uc if uc is not None else adim * 2.2
        nz = int(L / adim * adim_kare)
        bm = bmesh.new()
        halkalar = []
        for i in range(nz + 1):
            z = L * i / nz
            halka = []
            for j in range(seg):
                th = 2 * math.pi * j / seg
                u = (z / adim - th / (2 * math.pi)) % 1.0
                f = abs(2 * u - 1.0)
                p = min(1.0, max(0.0, (f - 0.12) / 0.76))
                rr = r - derinlik * p
                if z < uc:
                    t = z / uc
                    rr *= 0.22 + 0.78 * (t * t * (3 - 2 * t))
                halka.append(bm.verts.new((rr * math.cos(th), rr * math.sin(th), z)))
            halkalar.append(halka)
        for i in range(nz):
            for j in range(seg):
                a, b = halkalar[i][j], halkalar[i][(j + 1) % seg]
                c, d = halkalar[i + 1][(j + 1) % seg], halkalar[i + 1][j]
                bm.faces.new((a, b, c, d))
        bm.faces.new(halkalar[0][::-1])
        bm.faces.new(halkalar[-1])
        return bm

    def faz_yarigi(o, z_ust, boy=1.0, en=0.55, derin=1.3, acilar=(0, 90)):
        """Phillips (arti) yuva: iki kutu kesilir (acilar ile pozidriv'in capraz kollari da eklenebilir)."""
        for ac in acilar:
            k = bm_kutu(boy, en, derin * 2)
            bmesh.ops.rotate(k, verts=k.verts[:], cent=(0, 0, 0),
                             matrix=Matrix.Rotation(math.radians(ac), 3, "Z"))
            bmesh.ops.translate(k, verts=k.verts[:], vec=(0, 0, z_ust))
            kes(o, k)

    def vida_yap(ad, r=2.0, L=25.0, adim=0.7, bas="tava", bas_r=3.9, bas_h=2.6, malz="cinko", yuva="arti",
                 derinlik=None):
        """Makine vidasi: dislisi + kafa (+ yuva). Tabani z=0, kafa ustu z=L+bas_h."""
        govde = bm_nesne(ad + "-govde", bm_disli(r, L, adim, derinlik if derinlik is not None else adim * 0.62), malz)
        if bas == "tava":  # yuvarlak (pan) kafa
            prof = [(0, L + bas_h), (bas_r * 0.45, L + bas_h * 0.98), (bas_r * 0.86, L + bas_h * 0.78),
                    (bas_r, L + bas_h * 0.42), (bas_r, L + 0.05), (0, L + 0.05)]
        elif bas == "silindirik":
            prof = [(0, L + bas_h), (bas_r - 0.25, L + bas_h), (bas_r, L + bas_h - 0.25),
                    (bas_r, L + 0.05), (0, L + 0.05)]
        else:  # havsa
            prof = [(0, L + bas_h), (bas_r - 0.2, L + bas_h), (bas_r, L + bas_h - 0.2),
                    (bas_r, L + bas_h * 0.55), (r * 1.05, L), (0, L)]
        kafa = bm_nesne(ad + "-kafa", bm_donel(prof), malz)
        if yuva in ("arti", "pozidriv"):
            faz_yarigi(kafa, L + bas_h, boy=bas_r * 1.05, en=bas_r * 0.2, derin=bas_h * 0.75)
        if yuva == "pozidriv":   # pozidriv: artinin arasinda ince capraz kollar
            faz_yarigi(kafa, L + bas_h, boy=bas_r * 0.66, en=bas_r * 0.07, derin=bas_h * 0.6, acilar=(45, 135))
        return [govde, kafa]

    # ------------------------------------------------------------------ Tipa
    def insa_tipa(sc):
        # kucuk plastik kapak: yassi bombeli bas + nervurlu govde (z yukari, bas zeminde)
        prof = [(0, 0.0), (10.6, 0.0), (11.0, 0.5), (11.0, 2.2), (10.2, 3.0), (7.2, 3.35), (0, 3.45)]
        bas = bm_nesne("tipa-bas", bm_donel(prof), "beyaz_plastik")
        bevel(bas, 0.25, 3)
        govde_prof = [(0, 3.3), (5.6, 3.3), (5.6, 5.0), (6.2, 5.6), (6.2, 7.6), (5.7, 8.2), (5.7, 10.0),
                      (6.3, 10.6), (6.3, 12.6), (5.4, 13.6), (3.6, 13.9), (0, 13.9)]
        govde = bm_nesne("tipa-govde", bm_donel(govde_prof), "beyaz_plastik")
        # ic bosluk (alttan cukur) ve dort dikey yarik: esnek tip gorunumu
        kes(govde, bm_silindir(3.0, 9.0, z0=3.3 + 0.0, seg=48))
        for ac in (0, 90):
            k = bm_kutu(14.0, 0.9, 7.6, konum=(0, 0, 9.4))
            bmesh.ops.rotate(k, verts=k.verts[:], cent=(0, 0, 0),
                             matrix=Matrix.Rotation(math.radians(ac), 3, "Z"))
            kes(govde, k)
        bevel(govde, 0.12, 2)
        return kok_yap([bas, govde])
    INSA["tipa"] = insa_tipa

    # -------------------------------------------------------------- Kulp Vidasi
    def insa_kulp_vidasi(sc):
        o = vida_yap("kv", r=2.0, L=28.0, adim=0.7, bas="tava", bas_r=3.9, bas_h=2.7, malz="cinko")
        return kok_yap(o)
    INSA["kulp-vidasi"] = insa_kulp_vidasi

    # ---------------------------------------------------------- L Baglanti Seti
    def bm_yuvarlak_uclu_prizma(x0, x1, yy, r, z0, z1):
        """Ayak izi: x0..x1 x (-yy..yy), x1 tarafi r yaricapli yuvarlak kose; Z ekseninde z0..z1."""
        nok = [(x0, -yy), (x1 - r, -yy)]
        for i in range(1, 8):
            a = -math.pi / 2 + (math.pi / 2) * i / 8
            nok.append((x1 - r + r * math.cos(a), -yy + r + r * math.sin(a)))
        nok += [(x1, -yy + r), (x1, yy - r)]
        for i in range(1, 8):
            a = (math.pi / 2) * i / 8
            nok.append((x1 - r + r * math.cos(a), yy - r + r * math.sin(a)))
        nok += [(x1 - r, yy), (x0, yy)]
        bm = bmesh.new()
        vs = [bm.verts.new((x, y, z0)) for x, y in nok]
        f = bm.faces.new(vs)
        rr = bmesh.ops.extrude_face_region(bm, geom=[f])
        yeni = [e for e in rr["geom"] if isinstance(e, bmesh.types.BMVert)]
        bmesh.ops.translate(bm, verts=yeni, vec=(0, 0, z1 - z0))
        return bm

    def delik_ekle(o, merkez, eksen, r=2.2, r_havsa=4.3, t=2.2, ic_yon=1):
        """eksen 'Z' (yatay kolda) ya da 'X' (dikey kolda); havsa ic yuzde."""
        k = bm_silindir(r, t * 4, z0=-t * 2, seg=40)
        h = bm_silindir(r, t * 0.75, z0=t - t * 0.75 + 0.001, seg=40, r2=r_havsa)
        for b in (k, h):
            if eksen == "X":
                bmesh.ops.rotate(b, verts=b.verts[:], cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(90), 3, "Y"))
        return k, h

    def insa_l_baglanti(sc):
        t, gen, kol, r_ic = 2.2, 24.0, 38.0, 2.6
        r_dis = r_ic + t
        nok = [(kol, 0.0)]
        seg = 12
        for i in range(seg + 1):                    # dis yay: merkez (r_dis, r_dis), yaricap r_dis
            a = math.pi * 1.5 - (math.pi / 2) * i / seg
            nok.append((r_dis + r_dis * math.cos(a), r_dis + r_dis * math.sin(a)))
        nok += [(0.0, kol), (t, kol)]
        for i in range(seg + 1):                    # ic yay: yaricap r_ic
            a = math.pi + (math.pi / 2) * i / seg
            nok.append((r_dis + r_ic * math.cos(a), r_dis + r_ic * math.sin(a)))
        nok += [(kol, t)]
        br = bm_nesne("braket", bm_cokgen_ekstrude(nok, gen, y0=-gen / 2), "cinko")
        # kol uclarini yuvarla: yatay kol icin Z prizma, dikey kol icin X prizma ile kesisim
        kes(br, bm_yuvarlak_uclu_prizma(-60.0, kol, gen / 2, 4.5, -60.0, 60.0), "INTERSECT")
        pz = bm_yuvarlak_uclu_prizma(-60.0, kol, gen / 2, 4.5, -60.0, 60.0)
        bmesh.ops.rotate(pz, verts=pz.verts[:], cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(-90), 3, "Y"))
        # prizma uzunlugu artik +Z -> x ekseni ters; dikey kol (z yonunde) icin x'i z'ye cevirdik: kalinlik yonu -x..+x
        kes(br, pz, "INTERSECT")
        # delikler: her kolda yan yana 2 adet havsali delik
        for yy in (-6.0, 6.0):
            k, h = delik_ekle(br, None, "Z")
            for b in (k, h):
                bmesh.ops.translate(b, verts=b.verts[:], vec=(kol * 0.68, yy, 0))
            kes(br, k)
            kes(br, h)
            k, h = delik_ekle(br, None, "X")
            for b in (k, h):
                # dikey kol: x ekseninde delik, z konumu kol*0.68; ic yuz x=t -> havsa x=t tarafinda
                bmesh.ops.translate(b, verts=b.verts[:], vec=(0, yy, kol * 0.68))
            kes(br, k)
            kes(br, h)
        bevel(br, 0.16, 2)
        nesneler = [br]
        # takimdaki iki vida: onde, yatay yatmis
        for i, yy in enumerate((-gen / 2 - 8.0, -gen / 2 - 19.0)):
            for o in vida_yap("lv%d" % i, r=2.0, L=16.0, adim=1.3, bas="havsa", bas_r=4.1, bas_h=2.2, malz="cinko"):
                o.rotation_euler = Euler((0, math.radians(90), 0), "XYZ")
                o.location = Vector((8.0 + (i * 3.0), yy, 4.1))
                bpy.context.view_layer.update()
                nesneler.append(o)
        return kok_yap(nesneler)
    INSA["l-baglanti-seti"] = insa_l_baglanti

    # ------------------------------------------------------------------ Ray Seti
    def c_profil(h, w, t, lip, yon=1, dx=0.0):
        p = [(0, -h / 2), (w, -h / 2), (w, -h / 2 + lip), (w - t, -h / 2 + lip), (w - t, -h / 2 + t),
             (t, -h / 2 + t), (t, h / 2 - t), (w - t, h / 2 - t), (w - t, h / 2 - lip), (w, h / 2 - lip),
             (w, h / 2), (0, h / 2)]
        return [(yon * (x + dx), z) for x, z in p]

    def insa_ray(sc):
        t = 1.3
        nesneler = []
        uzak = 30.0            # iki rayin gövde (web) arasi yari uzaklik
        uyeler = [  # (yukseklik, web x-kayma, genislik, y baslangic, uzunluk, dilim)
            (45.0, 0.0, 12.5, 0.0, 200.0),
            (34.0, 2.6, 11.0, -90.0, 200.0),
            (24.0, 5.2, 9.6, -180.0, 200.0),
        ]
        for yon in (-1, 1):
            for k, (h, dx, w, y0, L) in enumerate(uyeler):
                nok = c_profil(h, w, t, 4.2 if k < 2 else 3.6, yon=yon, dx=dx)
                nok = [(x + (-yon) * (-uzak) * 0 + (yon * uzak), z) for x, z in nok]
                o = bm_nesne("ray%d-%d" % (yon, k), bm_cokgen_ekstrude(nok, L, y0=y0), "cinko" if k != 1 else "celik")
                # web uzerinde yuvarlak montaj delikleri (x yonunde)
                for j in range(4):
                    kes_b = bm_silindir(2.6, 6.0, z0=-3.0, seg=32)
                    bmesh.ops.rotate(kes_b, verts=kes_b.verts[:], cent=(0, 0, 0),
                                     matrix=Matrix.Rotation(math.radians(90), 3, "Y"))
                    bmesh.ops.translate(kes_b, verts=kes_b.verts[:],
                                        vec=(yon * (uzak + dx + t / 2), y0 + L * (0.14 + 0.24 * j), 0))
                    kes(o, kes_b)
                bevel(o, 0.12, 2)
                nesneler.append(o)
            # on tampon (siyah plastik) ve arka dayama
            on = bm_nesne("tampon%d" % yon, bm_kutu(9.0, 6.0, 15.0, konum=(yon * (uzak + 7.0), -183.0, 0)), "siyah_plastik")
            bevel(on, 0.6, 3)
            nesneler.append(on)
        return kok_yap(nesneler)
    INSA["ray-seti"] = insa_ray

    # -------------------------------------------------------------- Agac Vidasi
    def insa_agac_vidasi(sc):
        # sarmal diskli govde (r=2, L=26, adim 1.8, derinlik 0.6) + havsa baslik O8x3.2 + pozidriv yuva
        o = vida_yap("av", r=2.0, L=26.0, adim=1.8, derinlik=0.6, bas="havsa", bas_r=4.0, bas_h=3.2,
                     malz="cinko", yuva="pozidriv")
        return kok_yap(o)
    INSA["agac-vidasi"] = insa_agac_vidasi

    # ----------------------------------------------------------- Arkalik Civisi
    def insa_arkalik_civisi(sc):
        # z=0 sivri uc; govde O1.6x20 + 2 mm konik uc; hafif kubbeli yuvarlak baslik O4.5x0.6
        zg = 22.0
        prof = [(0.0, 0.0), (0.4, 0.9), (0.8, 2.0), (0.8, zg), (2.25, zg), (2.25, zg + 0.2),
                (2.05, zg + 0.4), (1.5, zg + 0.54), (0.7, zg + 0.6), (0.0, zg + 0.62)]
        c = bm_nesne("civi", bm_donel(prof, seg=48), "celik")
        return kok_yap([c])
    INSA["arkalik-civisi"] = insa_arkalik_civisi

    # -------------------------------------------------------------- Linco Dubel
    def insa_linco_dubel(sc):
        # O10.5x15 ahsap dubel: alt yaka, 9 testere dislisi kaburga, boydan boya O4 delik (seg=72)
        r_ic, r_yaka, r_kok, r_tepe, H = 2.0, 4.3, 4.3, 5.25, 15.0
        z0, z1, n = 2.4, 13.6, 9
        p = (z1 - z0) / n
        prof = [(r_ic, 0.0), (r_yaka, 0.0), (r_yaka, z0)]
        for i in range(n):
            z = z0 + i * p
            prof += [(r_kok, z), (r_tepe, z + 0.80 * p), (r_tepe, z + 0.90 * p)]
        prof += [(r_kok, z1), (r_kok, H - 0.4), (r_kok - 0.4, H), (r_ic, H), (r_ic, 0.0)]
        d = bm_nesne("dubel", bm_donel(prof, seg=72), "ahsap")
        return kok_yap([d])
    INSA["linco-dubel"] = insa_linco_dubel


def _argumanlar():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--parca", nargs="*", default=[])
    p.add_argument("--ara", default="/tmp/otonom_kit_render")
    p.add_argument("--cikti", default=os.path.join(PROJE, "static", "parcalar"))
    p.add_argument("--kare", type=int, default=24)
    p.add_argument("--hizli", action="store_true")
    p.add_argument("--sadece-tur", action="store_true")
    p.add_argument("--sadece-gorsel", action="store_true")
    p.add_argument("--paketle-yalniz", action="store_true")
    p.add_argument("--kesif", default=None)
    p.add_argument("--buyuk-tur-yok", action="store_true")
    p.add_argument("--rim", type=float, default=1.0)
    return p.parse_args(argv)


def main():
    a = _argumanlar()
    if a.paketle_yalniz:
        paketle(a.ara, a.cikti, a.kare, a.parca, buyuk=not a.buyuk_tur_yok)
        return
    if not BLENDER_ICINDE:
        sys.exit("Bu dosya 'blender --background --python' ile calistirilir.")
    if a.kesif:
        kesif(a.kesif, a.ara)
        return
    secilen = [(k, t) for k, t in PARCALAR.items() if not a.parca or t["slug"] in a.parca]
    for k, t in secilen:
        try:
            parca_render(k, t, a.ara, a.kare, a.hizli,
                         gorsel=not a.sadece_tur, tur=not a.sadece_gorsel,
                         insa=INSA.get(t["slug"]), rim=a.rim)
        except Exception as e:  # tek parca dusse digerleri surer
            import traceback
            traceback.print_exc()
            print("!!! HATA:", k, e, flush=True)
    sonuc = subprocess.run([sys.executable if not BLENDER_ICINDE else "python3", os.path.abspath(__file__),
                            "--paketle-yalniz", "--ara", a.ara, "--cikti", a.cikti, "--kare", str(a.kare)]
                           + (["--buyuk-tur-yok"] if a.buyuk_tur_yok else [])
                           + (["--parca"] + a.parca if a.parca else []))
    print("paketleme cikis kodu:", sonuc.returncode)


if __name__ == "__main__":
    main()
