"""
agac_vidasi_empty.py — Ağaç vidası deliklerini boru hattının GÜNCEL 3-yollu
algoritmasıyla sınıflandırır, her deliğe yolunu söyleyen bir Empty atar ve
tam sayısal rapor yazar.

(Adlandırma notu: CATEGORIES anahtarı eskiden yanlışlıkla `ahsapcivisi` idi;
2026-09-01'de `agacvidasi` olarak düzeltildi — ahşap çivisi diye bir parça yok.)

AMAÇ: Ağaç vidası sayısı beklenenden fazla arttığında HANGİ deliklerin hangi
      yoldan "vida" sayıldığını gözle görmek. 2026-09-01'den beri vida deliği
      üç yoldan tanınır (bkz. parca_kurallari.md → Ağaç vidası):
        1) VIDA_ESKI — hacim 14.57 %5 (standart kör delik, eski tek yol)
        2) VIDA_TAM  — hacim 83.2121 %1 (karşıya çıkan delik)
        3) VIDA_DGSK — değişken derinlikli kör delik: iki yanal bbox kenarı ≈
           çap, hacim/derinlik ≈ sabit kesit (agac_vidasi_degisken_mi)
      Sayım eskiye göre arttıysa fark TAM + DGSK gruplarındadır; empty
      önekleri bunu doğrudan gösterir.

DRİFT YOK: Bu araç boru hattı fonksiyonlarını KOPYALAMAZ; parca_sayim.py'yi
      diskten yükleyip (exec) birebir onun match_category / is_ray_hole /
      agac_vidasi_degisken_mi / execute_double_boolean fonksiyonlarını koşar.
      (Bu dosyanın eski sürümü kopya helper'larla bayatlamıştı: yalnızca
      14.57 bandını biliyordu.)

KULLANIM (GUI):
    1) İncelemek istediğin parçaları SEÇ (hiçbiri seçili değilse tüm sahne
       taranır ve boru hattı gibi arkalık kalınlığındaki parçalar ATLANIR).
    2) test_scriptleri/BLENDER_CALISTIR.py üzerinden çalıştır (ARAC =
       "agac_vidasi_empty").

ÇIKTI:
    - Her Empty, işaretlediği parçanın child'ıdır; dünya konumu ve görünür
      boyutu parent ölçeğinden etkilenmez:
        VIDA_ESKI_<Parca>#<i>                  (14.57 bandı)
        VIDA_TAM_<Parca>#<i>                   (83.2121 bandı)
        VIDA_DGSK_<kesit>x<derinlik>_<Parca>#<i>
        RAYBAND_<Parca>#<i>                    (ray bandı — vida DEĞİL, bilgi)
        BILINMEZ_<hacim>_<Parca>#<i>           (hiçbir kategoriye girmeyen)
      Önceki çalıştırmanın empty'leri (aynı önekler) baştan silinir.
    - Rapor: ciktilar/agac_vidasi_empty_raporu.txt — her boşluk için hacim,
      bbox, sınıf; BILINMEZ için eksen bazında kesit denemeleri ve red
      sebepleri; sonda grup/parça özetleri + Ağaç Vidası formül dökümü
      (count_order ile aynı: havuz + 2×L_BAGLANTI − ray delikleri).
"""

import bpy
import os

# ── Empty görünümü ──────────────────────────────────────────────────────────
# Empty'ler işaretledikleri parçanın child'ıdır. Parent inverse ve dünya matrisi
# açıkça korunur; böylece scale'i 0.009 olan FBX parçasında bile küçülmezler.
# Ayrıca topluca açılıp kapanabilmeleri için ayrı koleksiyonda dururlar.
EMPTY_BOYUT = 0.02      # Empty görünüm boyutu (metre) — 20 mm, panelde rahat seçilir
KOLEKSIYON_ADI = "AGAC_VIDASI_TESHIS"   # tüm empty'ler burada; göz ikonuyla aç/kapa
ONEKLER = ("VIDA_ESKI_", "VIDA_TAM_", "VIDA_DGSK_", "RAYBAND_", "BILINMEZ_")

# Sınıfa göre empty görünümü — viewport'ta bakmadan ayırt etmek için
GORUNUM = {
    "VIDA_ESKI": ('SPHERE', 1.0),
    "VIDA_TAM": ('CUBE', 1.2),
    "VIDA_DGSK": ('PLAIN_AXES', 1.6),   # asıl şüpheli: en büyük ve en göze çarpan
    "RAYBAND": ('CIRCLE', 1.0),
    "BILINMEZ": ('CONE', 1.4),
}

# ═══════════════════════════════════════════════════════════════════════════
# SABİT ÇIKTI DİZİNİ — raporlar buraya düşer (diğer teşhis araçlarıyla aynı
# mantık: yapıştırılmış script + kaydedilmemiş blend'de dinamik çözüm imkansız;
# projeyi taşırsan SADECE bu satırı güncelle).
# ═══════════════════════════════════════════════════════════════════════════
SABIT_CIKTI_DIZINI = "/home/rocket/Jupiter/Projects/otonom_kit/test_scriptleri/ciktilar"


def _proje_dizini_mi(d):
    try:
        return bool(d) and os.path.isfile(os.path.join(d, "BLENDER_CALISTIR.py"))
    except OSError:
        return False


def _yazilabilir(p):
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
    env = os.environ.get("ADAPTX_TEST_CIKTI")
    if env:
        r = _yazilabilir(env)
        if r:
            return r
    try:
        d = os.path.dirname(os.path.abspath(__file__))
        if _proje_dizini_mi(d):
            r = _yazilabilir(os.path.join(d, "ciktilar"))
            if r:
                return r
    except NameError:
        pass
    if bpy.data.filepath:
        b = os.path.dirname(bpy.data.filepath)
        for aday in (os.path.join(b, "test_scriptleri"), b):
            if _proje_dizini_mi(aday):
                r = _yazilabilir(os.path.join(aday, "ciktilar"))
                if r:
                    return r
    if SABIT_CIKTI_DIZINI:
        r = _yazilabilir(SABIT_CIKTI_DIZINI)
        if r:
            return r
    return _yazilabilir(os.path.expanduser("~/adaptx_test_ciktilari"))


def _parca_sayim_yukle():
    """parca_sayim.py'yi diskten bul ve exec et → modül sözlüğü döndür.

    Boru hattıyla birebir aynı fonksiyon/sabitleri kullanmanın tek garantili
    yolu (kopyalar bayatlıyor). main() __main__ korumalı, exec güvenli.
    """
    adaylar = []
    try:
        d = os.path.dirname(os.path.abspath(__file__))
        if _proje_dizini_mi(d):
            adaylar.append(os.path.dirname(d))
    except NameError:
        pass
    if bpy.data.filepath:
        b = os.path.dirname(bpy.data.filepath)
        adaylar += [b, os.path.dirname(b)]
    if SABIT_CIKTI_DIZINI:
        adaylar.append(os.path.dirname(os.path.dirname(SABIT_CIKTI_DIZINI)))
    for kok in adaylar:
        yol = os.path.join(kok, "parca_sayim.py")
        if os.path.isfile(yol):
            g = {"__file__": yol, "__name__": "parca_sayim_teshis"}
            exec(compile(open(yol, encoding="utf-8").read(), yol, "exec"), g)
            print(f"[BİLGİ] parca_sayim.py yüklendi: {yol}")
            return g
    raise RuntimeError("parca_sayim.py bulunamadı — blend'i proje içinden aç "
                       "veya SABIT_CIKTI_DIZINI'ni güncelle.")


def _safe(name):
    return name.replace(" ", "_")[:20]


def _teshis_koleksiyonu():
    """Empty'lerin gideceği koleksiyon — yoksa oluşturulur."""
    k = bpy.data.collections.get(KOLEKSIYON_ADI)
    if k is None:
        k = bpy.data.collections.new(KOLEKSIYON_ADI)
        bpy.context.scene.collection.children.link(k)
    return k


def add_empty(name, loc, grup, koleksiyon, parent_obj):
    """Parçanın child'ı olan, dünya dönüşümü parent ölçeğinden etkilenmeyen Empty."""
    tip, carpan = GORUNUM.get(grup, ('SPHERE', 1.0))
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = tip
    e.empty_display_size = EMPTY_BOYUT * carpan
    e.show_name = True          # adı viewport'ta yazsın
    e.show_in_front = True      # panelin içinde kalsa da görünsün
    koleksiyon.objects.link(e)
    e.parent = parent_obj
    e.matrix_parent_inverse = parent_obj.matrix_world.inverted_safe()
    e.location = loc
    return e


def _dgsk_detay(P, hole_obj, vol):
    """RAPOR için: değişken-derinlik kuralının eksen bazında denemeleri.

    Karar bu fonksiyondan ÇIKMAZ (karar = P['agac_vidasi_degisken_mi']); burası
    yalnızca aynı sabitlerle 'neden tuttu / neden tutmadı'yı yazıya döker.
    """
    dim, _ = P["get_perfect_local_bounds"](hole_obj)
    if dim is None:
        return ["bbox yok"]
    kenar = (dim.x, dim.y, dim.z)
    cap_lo = P["AGAC_VIDA_CAP_MM"] * (1 - P["AGAC_VIDA_CAP_TOL"])
    cap_hi = P["AGAC_VIDA_CAP_MM"] * (1 + P["AGAC_VIDA_CAP_TOL"])
    k_lo = P["AGAC_VIDA_KESIT_MM2"] * (1 - P["AGAC_VIDA_KESIT_TOL"])
    k_hi = P["AGAC_VIDA_KESIT_MM2"] * (1 + P["AGAC_VIDA_KESIT_TOL"])
    satirlar = []
    for i, eksen in enumerate("xyz"):
        yanal = [kenar[j] for j in range(3) if j != i]
        derinlik = kenar[i]
        kesit = vol / derinlik if derinlik > 1e-9 else float("inf")
        sebep = []
        if not all(cap_lo <= y <= cap_hi for y in yanal):
            sebep.append(f"yanal {yanal[0]:.2f}/{yanal[1]:.2f} ∉ çap[{cap_lo:.2f},{cap_hi:.2f}]")
        if not (P["AGAC_VIDA_DERINLIK_MIN_MM"] <= derinlik <= P["AGAC_VIDA_DERINLIK_MAX_MM"]):
            sebep.append(f"derinlik {derinlik:.2f} sınır dışı")
        if not (k_lo <= kesit <= k_hi):
            sebep.append(f"kesit {kesit:.3f} ∉ [{k_lo:.3f},{k_hi:.3f}]")
        durum = "TUTTU" if not sebep else "red: " + "; ".join(sebep)
        satirlar.append(f"eksen {eksen}: derinlik={derinlik:.3f} kesit={kesit:.3f} → {durum}")
    return satirlar


def main():
    import datetime
    baslangic = datetime.datetime.now()
    print("=" * 66)
    print(f">> agac_vidasi_empty BAŞLADI  {baslangic:%H:%M:%S}")
    print("=" * 66)

    # Edit/Pose modundayken bpy.ops çağrıları patlar (boolean adımı OBJECT modu
    # ister) — sessiz/anlaşılmaz hata yerine baştan OBJECT moduna geç.
    if bpy.context.mode != 'OBJECT':
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
            print("[BİLGİ] OBJECT moduna geçildi.")
        except RuntimeError:
            print("[HATA] OBJECT moduna geçilemedi — viewport'ta Object Mode'a al ve tekrar dene.")
            return

    P = _parca_sayim_yukle()
    koleksiyon = _teshis_koleksiyonu()

    # Önceki çalıştırmanın empty'lerini temizle (yalnızca bu aracın önekleri)
    eski_empty = [o for o in bpy.data.objects
                  if o.type == 'EMPTY' and o.name.startswith(ONEKLER)]
    for o in eski_empty:
        bpy.data.objects.remove(o, do_unlink=True)
    if eski_empty:
        print(f"[BİLGİ] Önceki çalıştırmadan {len(eski_empty)} empty silindi.")

    secili = [o for o in bpy.context.selected_objects if o.type == 'MESH']
    atlanan_arkalik = []
    tarama_bilgi = ""
    if secili:
        tarama_bilgi = f"{len(secili)} SEÇİLİ mesh tarandı: {', '.join(o.name for o in secili)}"
        print(f"[BİLGİ] {tarama_bilgi}")
        print("[BİLGİ] Not: birden çok parça seçersen hepsi taranır; hiçbir şey")
        print("        seçmezsen tüm sahne taranır (arkalık kalınlığındakiler atlanır).")
    else:
        hepsi = [o for o in bpy.context.scene.objects
                 if o.type == 'MESH' and not o.name.startswith("Temp_")]
        secili = []
        for o in hepsi:   # boru hattı gibi: arkalık kalınlığındakiler taranmaz
            th = P["part_thickness"](o)
            if th is not None and th <= P["ARKALIK_MAX_KALINLIK"]:
                atlanan_arkalik.append(o.name)
            else:
                secili.append(o)
        tarama_bilgi = (f"Seçim yok → sahnedeki {len(secili)} mesh tarandı "
                        f"({len(atlanan_arkalik)} arkalık-kalınlığında parça atlandı)")
        print(f"[BİLGİ] {tarama_bilgi}")

    secili, duplicate_parts = P["prepare_unique_parts"](secili)
    tarama_bilgi += f"; kopya temizliği sonrası {len(secili)} mesh"

    rapor = []
    rapor.append("agac_vidasi_empty_raporu — güncel 3-yollu ağaç vidası sınıflandırması")
    rapor.append(f"Çalıştırma zamanı: {baslangic:%Y-%m-%d %H:%M:%S}  (bu satır eskiyse rapor yenilenmemiştir)")
    rapor.append(f"Sabitler: ESKI=14.57 %5 | TAM={P['CATEGORIES']['agacvidasiTam']} "
                 f"%{P['CATEGORY_TOL']['agacvidasiTam']*100:.0f} | "
                 f"DGSK kesit={P['AGAC_VIDA_KESIT_MM2']} ±%{P['AGAC_VIDA_KESIT_TOL']*100:.1f}, "
                 f"çap={P['AGAC_VIDA_CAP_MM']} ±%{P['AGAC_VIDA_CAP_TOL']*100:.0f}, "
                 f"derinlik [{P['AGAC_VIDA_DERINLIK_MIN_MM']}, {P['AGAC_VIDA_DERINLIK_MAX_MM']}] mm")
    rapor.append(f"Tarama: {tarama_bilgi}")
    for removed, kept in duplicate_parts:
        rapor.append(f"KOPYA: {removed} kaldırıldı; kalan: {kept}")
    if atlanan_arkalik:
        rapor.append(f"Atlanan arkalık parçaları: {', '.join(atlanan_arkalik)}")
    rapor.append("")

    gruplar = {"VIDA_ESKI": 0, "VIDA_TAM": 0, "VIDA_DGSK": 0,
               "RAYBAND": 0, "BILINMEZ": 0, "DIGER_KATEGORI": 0}
    ray_isimleri = []

    for o in secili:
        try:
            holes = P["execute_double_boolean"](o)
        except Exception as e:
            print(f"  [UYARI] {o.name}: delik taraması başarısız ({e})")
            rapor.append(f"[UYARI] {o.name}: delik taraması başarısız ({e})")
            continue

        print(f"   {o.name}: {len(holes)} boşluk taranıyor...")
        rapor.append(f"── {o.name} — {len(holes)} boşluk ──")
        part_ray_centers = []
        i = 0
        for h in holes:
            v = h["volume"]
            hp = h["object"]
            dim, _ = P["get_perfect_local_bounds"](hp)
            bbox = f"{dim.x:.2f}×{dim.y:.2f}×{dim.z:.2f}" if dim else "?"
            c = P["world_center"](hp)
            poz = f"({c.x*1000:.0f},{c.y*1000:.0f},{c.z*1000:.0f})mm"

            # count_order ile AYNI sıra:
            cat = P["match_category"](v)
            if cat == "agacvidasi":
                grup = "VIDA_ESKI"
                add_empty(f"VIDA_ESKI_{_safe(o.name)}#{i}", c, "VIDA_ESKI", koleksiyon, o)
            elif cat == "agacvidasiTam":
                grup = "VIDA_TAM"
                add_empty(f"VIDA_TAM_{_safe(o.name)}#{i}", c, "VIDA_TAM", koleksiyon, o)
            elif cat:
                grup = f"kategori:{cat}"
                gruplar["DIGER_KATEGORI"] += 1
            elif P["is_ray_hole"](v):
                grup = "RAYBAND"
                part_ray_centers.append(c)
                add_empty(f"RAYBAND_{_safe(o.name)}#{i}", c, "RAYBAND", koleksiyon, o)
            elif P["agac_vidasi_degisken_mi"](hp, v):
                grup = "VIDA_DGSK"
                # tutan ekseni rapor detayından değil addan da oku
                det = _dgsk_detay(P, hp, v)
                tutan = next((s for s in det if "TUTTU" in s), "")
                kd = tutan.split("derinlik=")[1].split(" ")[0] if tutan else "?"
                ks = tutan.split("kesit=")[1].split(" ")[0] if tutan else "?"
                add_empty(f"VIDA_DGSK_{ks}x{kd}_{_safe(o.name)}#{i}", c, "VIDA_DGSK", koleksiyon, o)
            else:
                grup = "BILINMEZ"
                add_empty(f"BILINMEZ_{v:.1f}_{_safe(o.name)}#{i}", c, "BILINMEZ", koleksiyon, o)

            if grup in gruplar:
                gruplar[grup] += 1
            satir = f"  #{i:<3} {grup:<14} hacim={v:<10.4f} bbox={bbox}  {poz}"
            rapor.append(satir)
            if grup in ("VIDA_DGSK", "BILINMEZ"):
                for s in _dgsk_detay(P, hp, v):
                    rapor.append(f"        {s}")
            i += 1
            bpy.data.objects.remove(hp, do_unlink=True)

        # ray deseni (count_order gibi: sadece ray bandı havuzunda aranır)
        if part_ray_centers:
            part_rays, _dis = P["detect_rays"](part_ray_centers)
            if part_rays:
                ray_isimleri.extend(part_rays)
                rapor.append(f"  → ray deseni: {part_rays}")
        rapor.append("")

    havuz = gruplar["VIDA_ESKI"] + gruplar["VIDA_TAM"] + gruplar["VIDA_DGSK"]
    ray_delik_toplam = sum(len(P["RAY_HOLE_POSITIONS"][n]) for n in ray_isimleri)
    tahmin = havuz + 2 * P["L_BAGLANTI_ADET"] - ray_delik_toplam

    ozet = [
        "═══ ÖZET ═══",
        f"VIDA_ESKI (14.57 bandı)      : {gruplar['VIDA_ESKI']}",
        f"VIDA_TAM  (83.2121 bandı)    : {gruplar['VIDA_TAM']}",
        f"VIDA_DGSK (kesit kuralı)     : {gruplar['VIDA_DGSK']}",
        f"RAYBAND   (vida değil)       : {gruplar['RAYBAND']}  → desen: {ray_isimleri or 'yok'}",
        f"BILINMEZ                     : {gruplar['BILINMEZ']}",
        f"Diğer kategoriler (linco vb.): {gruplar['DIGER_KATEGORI']}",
        "",
        f"Ağaç vidası havuzu (ESKI+TAM+DGSK)          : {havuz}",
        f"count_order formülü: havuz + 2×L({P['L_BAGLANTI_ADET']}) − ray delikleri({ray_delik_toplam}) = {tahmin}",
        "",
        "Eski algoritma yalnızca VIDA_ESKI'yi sayardı — artış = VIDA_TAM + VIDA_DGSK.",
        "Şüpheli empty'nin üstüne gidip deliğin GERÇEKTE ne deliği olduğuna bak.",
        "",
        f"Sahneye konan Empty: {sum(gruplar[g] for g in ('VIDA_ESKI','VIDA_TAM','VIDA_DGSK','RAYBAND','BILINMEZ'))} "
        f"→ Outliner'da '{KOLEKSIYON_ADI}' koleksiyonu.",
        "Empty biçimleri: ESKI=küre, TAM=küp, DGSK=eksen(en büyük), RAYBAND=çember, BILINMEZ=koni.",
    ]
    rapor.extend(ozet)
    print("\n" + "\n".join(ozet))

    cikti_dizini = _resolve_output_dir()
    yol = os.path.join(cikti_dizini, "agac_vidasi_empty_raporu.txt")
    with open(yol, "w", encoding="utf-8") as f:
        f.write("\n".join(rapor) + "\n")
    print(f"\n>> Rapor: {yol}")
    print(">> Empty önekleri: VIDA_ESKI_ / VIDA_TAM_ / VIDA_DGSK_ / RAYBAND_ / BILINMEZ_")


if __name__ == "__main__":
    main()
