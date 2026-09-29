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
import sys
from collections import Counter

# ── Modül ayırıcı (module_ayirici/) — kod dizininden yüklenir ────────────────
# Veri kökü (BASE) ADAPTX_BASE ile başka yerde olabilir; ayırıcı ise bu dosyanın
# yanındaki module_ayirici/ klasöründedir. İçe aktarma başarısız olursa sayım
# durmaz: L Bağlantı Seti eski sabite (L_BAGLANTI_ADET) düşer ve JSON'da görünür.
try:
    _KOD_DIZINI = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _KOD_DIZINI = os.getcwd()
_MODUL_AYIRICI_DIZINI = os.path.join(_KOD_DIZINI, "module_ayirici")
if os.path.isdir(_MODUL_AYIRICI_DIZINI) and _MODUL_AYIRICI_DIZINI not in sys.path:
    sys.path.insert(0, _MODUL_AYIRICI_DIZINI)
try:
    import module_segmenter
    import sutunlar
    _MODUL_AYIRICI_HATA = None
except Exception as _e:   # ayırıcı yoksa/bozuksa sayım yine çalışsın
    module_segmenter = sutunlar = None
    _MODUL_AYIRICI_HATA = repr(_e)
# Askılık borusu boyu (karşılıklı flanş eşleştirme, saf Python). Yüklenemezse boru
# ADEDİ yine flanş // 2 çıkar; yalnız boylar boş kalır ve JSON'da hata görünür.
try:
    import askilik
    _ASKILIK_HATA = None
except Exception as _e:
    askilik = None
    _ASKILIK_HATA = repr(_e)

# ── Yol çözümü (proje dizini) ────────────────────────────────────────────────
def _base_dir():
    # 1) ADAPTX_BASE ortam değişkeni (Docker/servis): veri klasörü (fbx/jsons/pdf).
    #    Böylece dosya yolları statiktir ve her makineye/CT'ye uyar.
    env = os.environ.get("ADAPTX_BASE")
    if env and os.path.isdir(env):
        return env
    # 2) __file__ (script diskten çalıştırıldığında). Blender Text editöründe
    #    __file__ ".../x.blend/Text" gibi gerçek olmayan bir yol olabilir; isdir
    #    kontrolü bunu otomatik eler.
    try:
        d = os.path.dirname(os.path.abspath(__file__))
        if os.path.isdir(d):
            return d
    except NameError:
        pass
    # 3) Açık .blend dosyasının klasörü (Text editöründe __file__ yoksa).
    if bpy.data.filepath:
        d = os.path.dirname(bpy.data.filepath)
        if os.path.isdir(d):
            return d
    return os.getcwd()


BASE = _base_dir()
FBX_DIR = os.path.join(BASE, "fbx")
OUT_DIR = os.path.join(BASE, "jsons")
RENK_DIR = os.path.join(BASE, "renkler")  # Mert'in yüklediği <sipariş>.json renk verisi (girdi)
# Bellek: daha önce işlenmiş siparişlerin İŞLENME sırası. JSON'u zaten olan sipariş
# tekrar işlenmez (ağır Blender adımı atlanır); yeni siparişler bu listenin SONUNA
# eklenir (pdf_uret.py özeti bu sıraya göre üretir → var olanın sonuna eklenmiş olur).
MANIFEST = os.path.join(BASE, "islem_gecmisi.json")

# ── Hacim eşikleri (delikbulma.py + yeni_hacimler.md) ────────────────────────
CATEGORIES = {
    "linco": 9680.0,
    "pim": 936.0,             # Linco Dübel deliği (linco'ya eşit; çapraz kontrol)
    "agacvidasi": 14.57,     # Ağaç vidası standart kör delik (gerçek FBX ölçümü: ~14.57)
    "agacvidasiTam": 83.2121, # Ağaç vidası KARŞIYA ÇIKAN delik: 18mm panel × sabit kesit
                               # 4.6229 mm² (bkz. AGAC_VIDA_KESIT_MM2). Aynı havuza girer.
    "rafpimi": 234.0,
    "modulbaglanti": 351.35,
    "menteseTabani": 11454.0131,   # yeni_hacimler.md
    "tipa": 1392.7481,        # Tıpa (ayarlı ayak deliği; gerçek FBX ölçümü ~1392.75, %1 tol)
}
TOLERANCE = 0.05           # %5 varsayılan (güncel delikbulma.py ile aynı)
# Arkalık boşluğu üründen ürüne değiştiği için bazı deliklerin hacmi sallanıyor;
# %5 global tolerans linco'da yanlış pozitif sayıma yol açıyordu. Linco artık %1'e
# sabitlendi (hacimler.md'de zaten %1 olarak kayıtlı). Kategori-bazlı tolerans:
# burada olmayanlar TOLERANCE'tan (%5) devralır.
CATEGORY_TOL = {"linco": 0.03,   # linco = %3 (9680 merkez; arkalık boşluğu ürünler arası oynaklık yaratıyor, %1 gerçek delikleri dışarıda bırakıyordu; %3 hem 47 gerçeği yakalar hem 10053'lük sahteyi eler)
                "tipa": 0.01,    # tipa = %1 (tekil ölçüm, kendi deliği; kullanıcı ölçümü tutarlı, tolerans yeter de artar)
                "agacvidasiTam": 0.01}  # %1 → [82.38, 84.04]; iki ray bandının ([80.02, 81.63] / [84.07, 85.76])
                                         # TAM ARASINA sıkışıyor, genişletme — bandlara değerse ray/vida karışır
KULP_DELIK_MESAFE = 0.192  # m — kulp deliği çifti arasındaki sabit mesafe (192 mm)
KULP_DELIK_TOL = 0.05      # %5 tolerans (±~10 mm)

# ── Modül-modül bağlantı deliği çifti (kulp'tan arta kalan modulbaglanti
# delikleri arasında) ─────────────────────────────────────────────────────
# Ölçüm (diag_modul_mesafe.py, gerçek FBX'ler): iki AYRI modülün birbirine
# dayanan panellerindeki modül bağlantı delikleri TAM 18.000 mm ayrı; bir
# sonraki en yakın (alakasız) mesafe 136mm+ — net bir ayrım var, bu yüzden
# dar (±%0.1) bir kesin-mesafe toleransı güvenli.
MODUL_BAGLANTI_MESAFE = 0.018   # m — modül bağlantı deliği çifti arası sabit mesafe (18 mm)
MODUL_BAGLANTI_TOL = 0.001      # %0.1 tolerans

# ── Ray deliği hacmi (ağaç vidasından FARKLI, kendine özgü delik) ───────────
# Keşif (test_scriptleri/olcumler/hacim_bul_raporu.txt, Object_23): ray'e ait delikler CATEGORIES'teki
# hiçbir hacimle eşleşmiyor ([BİLİNMİYOR]) — 3 delik: 84.9189 / 84.9188 / 84.9175.
# Bu, agacvidasi (14.57) ile AYNI delik DEĞİL, kendine özgü bir hacim. Eskiden
# detect_rays() agacvidasi (gerçek ağaç vidası) havuzunda arıyordu; bu yüzden
# rastgele aralıklı gerçek vidalar ray desenine tesadüfen uyup yanlış ray sanılıyordu
# (ör. gerçek 55cm ray'in 25cm bulunması). Ray'ler artık SADECE bu kendine özgü
# hacim bandındaki deliklerden aranır — ağaç vidası/ayarlı ayak havuzuna DOKUNMAZ.
# Güncel ölçüm (son hacim raporu): 84.9186 / 84.9185 / 84.9172 → ortalama 84.9181.
#
# İKİ AYRI HACİM VAR (2026-07-29, test_scriptleri/ray_hacim_tarama.py ile 26 FBX tarandı):
# 26 FBX'te çekmece yan duvarı imzasına (tam 2 linco + 2-3 eşit hacimli delik) uyan
# 18 parça bulundu. Bunlardan 16'sı 84.9174–84.9198 (yayılım 0.0024), 2'si (9363'ün
# Object_4/Object_5) tam olarak 80.8258 (yayılım 0.0000). Küme içi yayılım pratikte
# sıfır olduğu için bu ÖLÇÜM GÜRÜLTÜSÜ DEĞİL — modellerde iki farklı delik geometrisi
# var (9363'te linco dübel deliği de 859.76 vs 937.10, yani parçanın tamamı farklı).
# Doğru çözüm Mert'in 9363'ü standart geometriyle yeniden üretmesi; ancak eski
# siparişler yeniden işlenebilsin diye her iki bilinen hacim de tanınır.
# Doğrulama: 80.83 tanınınca 9363'ün delik aralıkları 148.0/222.0 mm ölçülüyor,
# 55cm imzası (149/222) ile sapma 1.0/0.0 mm → referans BoM'daki "1x55cm" ile birebir.
# Bandlar: [80.017, 81.634] ve [84.072, 85.764] — birbirleriyle de, CATEGORIES'teki
# hiçbir hacimle de (en yakını rafpimi 234) kesişmiyor.
RAY_DELIK_HACIMLERI = [84.9181, 80.8258]  # bilinen ray deliği hacimleri (mm³)
RAY_DELIK_TOL = 0.01       # %1 (tekil ölçüm, linco/pim gibi hassas delik tipi)

# ── Ağaç vidası: değişken derinlikli kör delik — sabit olan KESİT ────────────
# Ağaç vidası deliğinde üründen ürüne değişmeyen şey hacim değil KESİT alanıdır:
# çap sabit (2.46 mm), derinlik ürüne göre değişir → hacim de değişir. Karşıya
# çıkan delik 18mm panelde sabit 83.2121 mm³ (CATEGORIES → agacvidasiTam); kör
# delik ise her hacimde gelebilir ve hacim bandıyla YAKALANAMAZ. Kör delik,
# boolean boşluğunun bbox'undan tanınır: boşluk objesi parçanın LOKAL ekseninde
# durduğundan iki yanal bbox kenarı ≈ çap, üçüncü kenar = derinlik, ve
# hacim/derinlik ≈ sabit kesit. Ray-cast gerekmez.
# Ölçümler (2026-09-01, 'delik bulma.blend' test sahnesi, pipeline boolean'ı ile):
#   kör örnek 13.83 mm³ / 2.988 mm derinlik → 4.629 mm²; karşıya çıkan
#   83.2121/18 → 4.6229; delik ağzı kapak yüzeyi → 4.632. Çap her ölçümde 2.46.
# Dairesellik için ayrıca RANSAC gerekmez: iki yanal kenarın d×d çıkması + kesit
# denetimi birlikte A/d² ≈ 0.765 oranını (16-gen silindir) zorlar; kare kanal
# (A/d²=1.0) ya da eşkenar-dörtgen profil (0.5) iki denetimden birine takılır.
AGAC_VIDA_KESIT_MM2 = 4.627    # delik kesit alanı (mm²) = hacim/derinlik, sabit
AGAC_VIDA_KESIT_TOL = 0.015    # ±%1.5 — gerçek yayılım ±%0.2; ray kesiti (84.92/18≈4.718) DIŞARIDA kalsın
AGAC_VIDA_CAP_MM = 2.46        # delik çapı (mm) — boşluk bbox'unun iki yanal kenarı
AGAC_VIDA_CAP_TOL = 0.05       # ±%5
AGAC_VIDA_DERINLIK_MIN_MM = 1.0   # bundan sığ boşluk = boolean kırıntısı sayılır
AGAC_VIDA_DERINLIK_MAX_MM = 40.0  # panel kalınlığı üstü sağduyu sınırı

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

# Bazı arkalık panelleri paketleme kolaylığı için üretimde İKİYE KESİLİP
# bantlanıp/katlanıp gönderiliyor; FBX'te bu, aynı arkalığın İKİ AYRI mesh
# parçası (yarım-yarım, birbirleriyle AYNI HACİMDE) olarak görünüyor. Çivi
# sayımından önce bu çiftler TEK PARÇA mesh'te birleştirilmeli — yoksa boyut
# (W×H) yarım okunur ve çivi sayısı yanlış (iki kez, küçük panelmiş gibi) çıkar.
#
# ÖNEMLİ — sadece HACİM eşleşmesi YETERLİ DEĞİL: müşteri aynı boyda 2 ayrı
# modül sipariş edebilir (bu da aynı hacimde 2 AYRI arkalık demektir, ama
# bunlar GERÇEKTEN ayrı paneldir, birleştirilmemeli). Ayrım için EK şart:
# adaylar TAM BİR YÜZEYDE birbirine temas etmeli (bkz. _tam_yuzey_temasi) —
# gerçek ikiye-kesilmiş yarılar, kesim hattı boyunca sıfır boşlukla ve tam
# örtüşerek bitişir; ayrı modüllerin arkalıkları bunu sağlamaz.
ARKALIK_ESLESME_TOL = 0.03   # %3 — aynı arkalığın iki yarısı aynı hacimde olmalı
ARKALIK_TEMAS_TOL_MM = 2.0   # mm — temas/örtüşme için izin verilen sıfıra-yakın sapma

# ── Renk (Mert'in ayrı yüklediği renkler/<sipariş>.json'undan) ───────────────
# Eksikler.md §5'te ertelenen "renkli parçaların hangi renk olduğunu bulma" işi:
# Mert artık FBX'e gömülü texture yerine parça başına user_data.renk kodu içeren
# ayrı bir <sipariş>.json yüklüyor (bkz. "Sisteme renklerin entegre edilmesi.md").
# Siparişin rengi, o json'daki parçalar arasında EN ÇOK GEÇEN renk kodudur; buna
# göre görünür parçaların (Linco Gövde/Kapak, Tıpa) rengi eşlenir. Minifix/Linco
# Dübel'in rengi görünmediği için eşlenmez.
RENK_KOD_ADI = {"0": "Beyaz", "1": "Meşe", "2": "Gri"}
PARCA_RENK_KURALI = {
    "Beyaz": {"Linco Gövde": "Beyaz", "Linco Kapak": "Beyaz", "Tıpa": "Beyaz"},
    "Meşe":  {"Linco Gövde": "Siyah", "Linco Kapak": "Siyah", "Tıpa": "Kahverengi"},
    "Gri":   {"Linco Gövde": "Siyah", "Linco Kapak": "Siyah", "Tıpa": "Siyah"},
}

# ── L Bağlantı Seti = duvar bağlantı braketi ─────────────────────────────────
# Kural (Kerem, 2026-09-29): braket = 2 × modül sütunu (her sütunun en üst
# modülüne sol + sağ). Sütunlar geometriden bulunur: module_segmenter modülleri
# ayırır, sutunlar.py plan izdüşümü örtüşen modülleri aynı sütuna koyar (bkz.
# modul_sutun_bilgisi). L_BAGLANTI_ADET yalnız YEDEK: ayırıcı yüklenemez, hata
# verir ya da hiç modül bulamazsa kullanılır; o durum JSON'da "moduller.kaynak"
# = "yedek_sabit" olarak görünür.
L_BAGLANTI_ADET = 2          # yedek: sipariş başına 2 L bağlantı seti (set+vida+dübel dahil)

# ── Askılık flanşı (ağaç vidası üçgeninden tespit) ───────────────────────────
# Bir parçadaki ağaç vidası deliklerinin 3'lü kombinasyonlarından kenarları
# %FLANS_KENAR_TOL içinde eşit (eşkenar, ~60°) üçgen oluşturanlar = 1 askılık flanşı.
FLANS_KENAR_TOL = 0.02       # kenar uzunlukları %2 toleransla eşit
FLANS_ACI_LO = 59.0          # eşkenar üçgen açı alt sınırı (derece)
FLANS_ACI_HI = 61.0          # eşkenar üçgen açı üst sınırı (derece)
# Askılık borusu BOYU: karşılıklı flanş çiftinden (module_ayirici/askilik.py —
# sabitler orada: ASKILIK_KESINTI_MM = 10, ASKILIK_HIZA_TOL_MM = 15). Boru ADEDİ
# değişmedi: flanş // 2. Eşleşen çift sayısı bundan farklıysa JSON
# "askilik_eslesme.tutarli" = false olur ve [UYARI] basılır.
MODEL_MM = 1000.0            # model birimi → mm (kulp 0.192 ↔ 192 mm; RAY_SCALE_MM ile aynı)

# ── Ray seti (RAY_DELIK_HACIMLERI bandındaki deliklerin ray deseninden tespiti) ──
# Kalibrasyon: kulp deliği modelde 0.192 birim ↔ gerçek 192 mm → 1 birim = 1000 mm.
# Ray delikleri ağaç vidasıyla AYNI delik DEĞİL (bkz. RAY_DELIK_HACIMLERI); parçadaki
# RAY_DELIK_HACIMLERI bandına giren delikler arasından doğrusal + ardışık aralıkları bir
# ray boyunun imzasına (aşağıdaki RAY_GAPS) uyanlar = 1 ray. İmzalar, kullanıcının
# referans-noktasına göre ölçtüğü delik KONUMLARINDAN (RAY_HOLE_POSITIONS) türetilir.
RAY_SCALE_MM = 1000.0        # model birimi → mm çarpanı (kulp 0.192 ↔ 192 mm)
RAY_TOL_MM = 8.0             # delik-aralığı eşleşme toleransı (mm)
RAY_COLINEAR_TOL_MM = 8.0    # doğrusallık: en uzun kenar ≈ diğer ikisinin toplamı (mm)

# Ray boyu → deliklerin REFERANS-NOKTASINDAN uzaklıkları (mm). Kaynak: kullanıcı
# ölçümü — rayla AYNI doğrultudaki sabit bir referans noktasına göre her deliğin
# konumu ölçüldü. Ardışık delikler arası FARK = o ray'in desen aralıkları (imzası).
# ÖNEMLİ: ray boyu ile aralıklar DOĞRU ORANTILI DEĞİL; her boyun aralık imzası
# kendine ÖZGÜ (unique) — eşleştirme boydan değil, bu imzadan yapılır.
RAY_HOLE_POSITIONS = {
    "55cm": [63.0, 212.0, 434.0],
    "50cm": [64.0, 214.0, 375.0],
    "45cm": [64.0, 216.0, 318.0],
    "40cm": [64.0, 193.0, 275.0],
    "35cm": [64.0, 141.0, 224.0],
    "30cm": [63.0, 172.0],
    "25cm": [43.0, 231.0],
}
# Ardışık aralıklar konumlardan TÜRETİLİR (elle yazılmaz → kayma/tutarsızlık olmaz).
# ör. 55cm: 212-63=149, 434-212=222 → [149, 222].
RAY_GAPS = {name: [round(pos[i + 1] - pos[i], 1) for i in range(len(pos) - 1)]
            for name, pos in RAY_HOLE_POSITIONS.items()}

# ── Ayarlı ayak (4 ağaç vidası = sabit dikdörtgen) ──────────────────────────
# Ölçüm (test_scriptleri/olcumler/iki_obje_mesafe_raporu.txt, Object_55): ayağın 4 vida deliği, kenarları ~32 ve ~40 mm,
# köşegeni ~51.22 mm olan bir DİKDÖRTGEN oluşturur (4 delik hep aynı mesafelerde).
# Bir parçadaki ağaç vidası delikleri arasından bu dikdörtgeni oluşturan 4'lü = 1 ayak.
# Eski kural ("parçada TAM 4 vida → 1 ayak") panele DAĞILMIŞ 4 yapısal vidayı da ayak
# sayıyordu → olması gerekenden fazla (9262: 11 sayılıyordu, gerçek ~1). Dikdörtgen
# şekli bu yanlış pozitifleri eler; ağaç vidası/ray/flanş sayımına DOKUNMAZ.
#
# Tespit yöntemi (geometrik, sıralı-mesafe listesiyle KIYASLAMAZ — bkz. count_ayak_feet
# yorumu): "paralelkenarın köşegenleri birbirini ortalar VE dikdörtgende bu köşegenler
# EŞİT uzunluktadır" teoremini kullanır. Sıralı 6-mesafe karşılaştırması hangi mesafenin
# kenar/köşegen olduğunu KAYBEDER (topolojiyi görmez) → hem yanlış pozitif hem yanlış
# negatif üretebilir. Köşegen+orta-nokta yöntemi bu belirsizliği ortadan kaldırır.
AYAK_KENAR_A_MM = 32.0     # kısa kenar (mm)
AYAK_KENAR_B_MM = 40.0     # uzun kenar (mm)
AYAK_KENAR_TOL_PCT = 0.03  # kenar/köşegen/orta-nokta eşleşme toleransı (%3, diğer
                           # kategorilerle tutarlı bağıl tolerans — ör. TOLERANCE=%5)
AYAK_SCALE_MM = 1000.0     # model birimi → mm (kulp 0.192 ↔ 192 mm ile aynı ölçek)
_AYAK_DIAG_MM = math.hypot(AYAK_KENAR_A_MM, AYAK_KENAR_B_MM)   # 51.22 mm

# ── Birim ağırlıklar (gram) — Ağırlıklar.md ──────────────────────────────────
WEIGHTS = {
    "rafpimi": 2.7,
    "agacvidasi": 1.108,
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
        tol = CATEGORY_TOL.get(cat_name, TOLERANCE)
        if target * (1 - tol) <= vol <= target * (1 + tol):
            return cat_name
    return None


def is_ray_hole(vol):
    """Delik hacmi bilinen ray deliği hacimlerinden birinin bandında mı?

    Ray deliği agacvidasi ile AYNI delik DEĞİL (bkz. RAY_DELIK_HACIMLERI).
    Modellerde iki farklı geometri var, bu yüzden tek değer değil liste kontrol edilir.
    """
    for hacim in RAY_DELIK_HACIMLERI:
        if hacim * (1 - RAY_DELIK_TOL) <= vol <= hacim * (1 + RAY_DELIK_TOL):
            return True
    return False


def agac_vidasi_degisken_mi(hole_obj, vol):
    """Bilinen kategorilere uymayan boşluk, değişken derinlikli ağaç vidası deliği mi?

    is_ray_hole()'dan SONRA çağrılmalı: bilinen ray hacim bandları (±%1) önce
    ayıklanır, bu kural kalanlara bakar. (Bilinen sınır durumu: 18mm panelde
    ~17.4mm derinlikli kör vida hacmi 80.83 ray bandına düşer ve ray sanılır;
    bilinen modellerde bu derinlik yok — çıkarsa bandları geometriyle ayrıştır.)
    """
    dim, _ = get_perfect_local_bounds(hole_obj)
    if dim is None:
        return False
    kenar = (dim.x, dim.y, dim.z)
    cap_lo = AGAC_VIDA_CAP_MM * (1 - AGAC_VIDA_CAP_TOL)
    cap_hi = AGAC_VIDA_CAP_MM * (1 + AGAC_VIDA_CAP_TOL)
    for i in range(3):
        yanal = [kenar[j] for j in range(3) if j != i]
        if not all(cap_lo <= y <= cap_hi for y in yanal):
            continue
        derinlik = kenar[i]
        if not (AGAC_VIDA_DERINLIK_MIN_MM <= derinlik <= AGAC_VIDA_DERINLIK_MAX_MM):
            continue
        kesit = vol / derinlik
        if (AGAC_VIDA_KESIT_MM2 * (1 - AGAC_VIDA_KESIT_TOL) <= kesit
                <= AGAC_VIDA_KESIT_MM2 * (1 + AGAC_VIDA_KESIT_TOL)):
            return True
    return False


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


def detect_modul_baglanti_pairs(centers):
    """Kulp'tan arta kalan modulbaglanti delikleri arasından GERÇEK modül-modül
    bağlantı çiftlerini ayır.

    ESKİ yöntem (pair_count) "en yakın komşu, 200mm eşik altında" mantığıyla
    greedy eşleştiriyordu — bu, birbirine hiç bağlı OLMAYAN ama tesadüfen en
    yakın düşen delikleri de (ör. 136-137mm mesafedeki farklı modül köşe
    delikleri) yanlışlıkla çift sayıyordu (bkz. Algoritmaların_testi.md).

    GERÇEK modül-modül bağlantısı: iki AYRI modülün birbirine dayanan
    panellerindeki modül bağlantı delikleri TAM MODUL_BAGLANTI_MESAFE (18mm,
    ±%0.1 tolerans) kadar birbirinden uzaktadır — ölçüm (diag_modul_mesafe.py)
    gerçek çiftlerin tam 18.000mm, bir sonraki en yakın (alakasız) mesafenin
    ise 136mm+ olduğunu gösterdi; net bir ayrım var. Bu yüzden yakınlık yerine
    KESİN mesafe eşleşmesi kullanılır (detect_kulp_pairs ile aynı desen)."""
    lo = MODUL_BAGLANTI_MESAFE * (1 - MODUL_BAGLANTI_TOL)
    hi = MODUL_BAGLANTI_MESAFE * (1 + MODUL_BAGLANTI_TOL)
    used = [False] * len(centers)
    pairs = 0
    for i in range(len(centers)):
        if used[i]:
            continue
        for j in range(i + 1, len(centers)):
            if used[j]:
                continue
            d = (centers[i] - centers[j]).length
            if lo <= d <= hi:
                used[i] = used[j] = True
                pairs += 1
                break
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


def _ray_signature_match(gaps_mm):
    """Ölçülen ardışık aralıklara EN İYİ uyan ray boyunu döndürür (yoksa None).

    Her boyun "imzası" sıralı-aralık listesidir (RAY_GAPS, konumlardan türetilir).
    İmzalar unique olduğundan normalde tek boy uyar; yine de sağlamlık için TÜM
    aralıkları ±RAY_TOL_MM içinde olan boylar arasından EN DÜŞÜK toplam sapmalı
    seçilir (ilk-uyan değil). Bu, ilk aralıkları çok yakın olan 55/50/45 boylarını
    (149/150/152) güvenle ayırır — ayrımı ikinci aralık (222/161/102) yapar."""
    measured = sorted(gaps_mm)
    best_name, best_dev = None, None
    for name, gaps in RAY_GAPS.items():
        if len(gaps) != len(measured):
            continue
        ref = sorted(gaps)
        if all(abs(m - r) <= RAY_TOL_MM for m, r in zip(measured, ref)):
            dev = sum(abs(m - r) for m, r in zip(measured, ref))
            if best_dev is None or dev < best_dev:
                best_name, best_dev = name, dev
    return best_name


def detect_rays(centers):
    """Parçadaki ray-deliği (RAY_DELIK_HACIMLERI) merkezlerinden ray desenlerini ayır.

    Model: Bir ray'in delikleri, rayla aynı doğrultuda DOĞRUSAL dizilir; ardışık
    aralıkları o boya özgü unique imzayı (RAY_GAPS) verir. 3-delikli boylar (55–35cm)
    daha spesifik olduğu için ÖNCE, sonra kalan deliklerde 2-delikli boylar (30/25cm)
    aranır. Her eşleşme = 1 çekmece rayı. Her delik en fazla bir ray'de kullanılır
    (greedy). Returns (ray_isimleri:list, kalan_merkezler:list).

    Not: Bu havuz agacvidasi/ayarlı ayak havuzuyla KESİŞMEZ (bkz. RAY_DELIK_HACIMLERI),
    dolayısıyla ray tespiti ağaç vidası/ayak sayımını hiç etkilemez."""
    n = len(centers)
    used = [False] * n
    rays = []

    # 3-delikli raylar (doğrusal üçlü + iki ardışık aralığın imzası)
    for i, j, k in itertools.combinations(range(n), 3):
        if used[i] or used[j] or used[k]:
            continue
        dij = (centers[i] - centers[j]).length * RAY_SCALE_MM
        djk = (centers[j] - centers[k]).length * RAY_SCALE_MM
        dik = (centers[i] - centers[k]).length * RAY_SCALE_MM
        p, q, r = sorted([dij, djk, dik])          # p,q = iki ardışık aralık; r = açıklık
        if abs(r - (p + q)) > RAY_COLINEAR_TOL_MM:  # doğrusal mı? (açıklık ≈ aralıkların toplamı)
            continue
        name = _ray_signature_match([p, q])
        if name:
            used[i] = used[j] = used[k] = True
            rays.append(name)

    # 2-delikli raylar (kalan deliklerde; tek aralık imzası)
    for i, j in itertools.combinations(range(n), 2):
        if used[i] or used[j]:
            continue
        d = (centers[i] - centers[j]).length * RAY_SCALE_MM
        name = _ray_signature_match([d])
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


def find_equilateral_flanges(centers):
    """Ağaç vidası delik merkezlerinden eşkenar (~60°, kenarları %FLANS_KENAR_TOL
    içinde eşit) üçgen oluşturan 3'lüleri bul. Her delik en fazla bir üçgende
    kullanılır (greedy). Her üçgen = 1 askılık flanşı.
    Returns: [(i, j, k), ...] — centers indeks üçlüleri (flanş konumu = ağırlık merkezi)."""
    n = len(centers)
    if n < 3:
        return []
    used = [False] * n
    flanges = []
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
        flanges.append((i, j, k))
    return flanges


def count_equilateral_flanges(centers):
    """find_equilateral_flanges'in yalnız adet döndüren kısayolu (teşhis/test için)."""
    return len(find_equilateral_flanges(centers))


def _dunya_kutusu_mm(obj):
    """Objenin dünya-uzayı eksene hizalı kutusu, vertexlerden, mm: (lo, hi) listeleri."""
    pts = [obj.matrix_world @ v.co for v in obj.data.vertices]
    if not pts:
        return None, None
    lo = [min(p[i] for p in pts) * MODEL_MM for i in range(3)]
    hi = [max(p[i] for p in pts) * MODEL_MM for i in range(3)]
    return lo, hi


def _ayak_dikdortgen_adaylari(centers):
    """Ayağın 32×40 mm dikdörtgenini GEOMETRİK olarak bulur (sıralı-mesafe listesiyle
    KIYASLAMAZ). Kullanılan teorem: bir paralelkenarın köşegenleri birbirini ortalar;
    bu köşegenler EŞİT uzunluktaysa şekil bir DİKDÖRTGENDİR. Adımlar:
      1) Her ikili vida mesafesini tara; ~51.22 mm (köşegen) olanları ADAY köşegen say.
      2) İki aday köşegen (4 AYRI delik) ORTAK bir orta noktayı paylaşıyorsa (±tolerans)
         → köşegenler birbirini ortalıyor → dikdörtgen/paralelkenar.
      3) Bitişik kenar uzunlukları (32 ve 40 mm) tutuyor mu diye doğrula.
    Sıralı-mesafe karşılaştırması hangi mesafenin kenar/köşegen olduğunu KAYBEDER
    (topolojisiz); bu yöntem köşegen+orta-nokta ile topolojiyi doğrudan kullanır →
    hem yanlış pozitif hem yanlış negatif riskini azaltır.
    Returns: [(sapma, frozenset(4 delik indeksi)), ...] — sapma küçük = daha iyi uyum."""
    n = len(centers)
    if n < 4:
        return []
    diag_lo = _AYAK_DIAG_MM * (1 - AYAK_KENAR_TOL_PCT)
    diag_hi = _AYAK_DIAG_MM * (1 + AYAK_KENAR_TOL_PCT)
    mid_tol_mm = _AYAK_DIAG_MM * AYAK_KENAR_TOL_PCT

    # 1) Aday köşegenler: ~51.22 mm mesafedeki ikili delikler + orta noktaları.
    diagonaller = []
    for i, j in itertools.combinations(range(n), 2):
        d = (centers[i] - centers[j]).length * AYAK_SCALE_MM
        if diag_lo <= d <= diag_hi:
            mid = (centers[i] + centers[j]) / 2.0
            diagonaller.append((i, j, d, mid))

    # 2) İki aday köşegen ortak orta noktalı mı (4 AYRI delik)? + 3) kenar doğrulaması.
    adaylar = []
    for (i, j, d1, m1), (k, l, d2, m2) in itertools.combinations(diagonaller, 2):
        if len({i, j, k, l}) < 4:
            continue
        if (m1 - m2).length * AYAK_SCALE_MM > mid_tol_mm:
            continue
        # i-k ve i-l birbirini tamamlayan iki bitişik kenar (biri ~32, diğeri ~40).
        kenar1 = (centers[i] - centers[k]).length * AYAK_SCALE_MM
        kenar2 = (centers[i] - centers[l]).length * AYAK_SCALE_MM
        kisa, uzun = sorted([kenar1, kenar2])
        sapma = max(abs(kisa - AYAK_KENAR_A_MM) / AYAK_KENAR_A_MM,
                    abs(uzun - AYAK_KENAR_B_MM) / AYAK_KENAR_B_MM,
                    abs(d1 - _AYAK_DIAG_MM) / _AYAK_DIAG_MM,
                    abs(d2 - _AYAK_DIAG_MM) / _AYAK_DIAG_MM)
        if sapma <= AYAK_KENAR_TOL_PCT:
            adaylar.append((sapma, frozenset((i, j, k, l))))
    return adaylar


def extract_ayak_feet(centers):
    """Ağaç vidası delik merkezleri arasından ayağın ~32×40 mm dikdörtgenini oluşturan
    4'lüleri ayıklar (bkz. _ayak_dikdortgen_adaylari). En iyi uyan dikdörtgen önce
    (greedy); her delik en fazla bir ayakta kullanılır. Her dikdörtgen = 1 ayarlı ayak.

    ÖNEMLİ — bu ayıklama detect_rays()'DEN ÖNCE, HAM agacvidasi listesi üzerinde
    çağrılmalı (detect_kulp_pairs'in modulbaglanti listesini ray'den/başka bir şeyden
    önce ayırması gibi). Gerçek veri teşhisinde (9304-2/Object_18) görüldü: bir ayak
    köşesi, ray deseni önce çalıştırılırsa YANLIŞLIKLA 'ray' sanılıp havuzdan
    kayboluyor (ray mesafe pencereleri gevşek + bağlamsız greedy eşleşme) → ayak
    dikdörtgeni 3 köşeye düşüp hiç yakalanamıyor (sessiz eksik sayım — tolerans
    büyütmekle DÜZELMEZ, çünkü eksik köşe zaten aday havuzunda yok). Ayağı ÖNCE
    ayırıp kilitlemek bu çalınmayı önler; ray kendi kuralıyla SADECE ayak-dışı
    delikler üzerinde aranmaya devam eder (ray mantığı değişmez).

    Returns: (ayak_adedi, ayak_noktalari, ayak_disi_noktalar)"""
    adaylar = sorted(_ayak_dikdortgen_adaylari(centers), key=lambda t: t[0])
    used = set()
    feet = 0
    for _sapma, idxset in adaylar:
        if used & idxset:
            continue
        used |= idxset
        feet += 1
    ayak_noktalari = [c for i, c in enumerate(centers) if i in used]
    ayak_disi = [c for i, c in enumerate(centers) if i not in used]
    return feet, ayak_noktalari, ayak_disi


def count_ayak_feet(centers):
    """extract_ayak_feet'in sadece adet döndüren kısayolu (teşhis/test için)."""
    feet, _ayak_noktalari, _ayak_disi = extract_ayak_feet(centers)
    return feet


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


def mesh_volume(obj):
    """Kapalı mesh'in dünya-uzayı hacmi (arkalık yarım-parça eşleştirme için;
    delik hacminden FARKLI — burada parçanın TÜMÜNÜN hacmi ölçülür)."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.transform(obj.matrix_world)
    vol = abs(bm.calc_volume())
    bm.free()
    return vol


def _world_aabb(obj):
    """Objenin dünya-uzayı eksene-hizalı kutusu (min, max) — Vector çifti
    (world_center'daki gibi bound_box köşeleri matrix_world ile dönüştürülür)."""
    wb = [obj.matrix_world @ mathutils.Vector(v) for v in obj.bound_box]
    xs = [c.x for c in wb]; ys = [c.y for c in wb]; zs = [c.z for c in wb]
    return (mathutils.Vector((min(xs), min(ys), min(zs))),
            mathutils.Vector((max(xs), max(ys), max(zs))))


def _tam_yuzey_temasi(a, b):
    """a ve b TAM bir yüzeyde temas halinde mi? (aynı arkalığın gerçek
    ikiye-kesilmiş yarıları böyle durur: bir eksende SIFIR boşlukla bitişik,
    diğer İKİ eksende TAM örtüşen — yani kesim hattı boyunca tam yapışık.

    Sadece hacim eşleşmesi yeterli değil: müşteri aynı boyda 2 AYRI modül
    sipariş edebilir (aynı hacimde ama gerçekten ayrı arkalık) — bunlar genelde
    tam bu şekilde bitişmez/örtüşmez, bu yüzden bu ek kontrol onları eler."""
    amin, amax = _world_aabb(a)
    bmin, bmax = _world_aabb(b)
    tol = ARKALIK_TEMAS_TOL_MM / RAY_SCALE_MM
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


def pair_split_arkalik(parts):
    """Paketleme için ikiye kesilip bantlanan/katlanan arkalık panellerini
    tespit edip TEK PARÇA mesh'te birleştirir.

    Yöntem: arkalık adayları arasından hem (a) hacmi birbirine ARKALIK_ESLESME_TOL
    içinde eşit olan HEM DE (b) tam bir yüzeyde temas halinde olan (bkz.
    _tam_yuzey_temasi) ikilileri bul, bpy.ops.object.join ile tek objede
    birleştir. Eşleşmeyen adaylar zaten bölünmemiş (tek parça) arkalık paneli
    olarak oldukları gibi döner.

    Returns: nihai arkalık parça listesi (birleşmiş + tekil), çivi sayımına
    hazır."""
    kalan = list(parts)
    sonuc = []
    while kalan:
        o = kalan.pop(0)
        vo = mesh_volume(o)
        eslesen = None
        for i, o2 in enumerate(kalan):
            if (abs(mesh_volume(o2) - vo) <= vo * ARKALIK_ESLESME_TOL
                    and _tam_yuzey_temasi(o, o2)):
                eslesen = i
                break
        if eslesen is not None:
            o2 = kalan.pop(eslesen)
            bpy.ops.object.select_all(action='DESELECT')
            o.select_set(True)
            o2.select_set(True)
            bpy.context.view_layer.objects.active = o
            bpy.ops.object.join()
            sonuc.append(o)
        else:
            sonuc.append(o)
    return sonuc


# ── Bellek (işlem geçmişi) ───────────────────────────────────────────────────
def order_from_name(fbx_path):
    """Dosya adından sipariş no'yu çıkar (import gerektirmez → atlama kontrolü için)."""
    m = re.search(r'(\d{4,}(?:-\d+)?)', os.path.basename(fbx_path))
    return m.group(1) if m else "0000"


def _renk_json_yolu(order):
    """renkler/ içinde bu siparişe ait renk json'unu bul. Önce `<order>.json` tam
    eşleşmesi denenir; yoksa klasördeki dosya adları order_from_name ile AYNI
    regex kullanılarak taranır (Mert'in yüklediği ad `9307-2-mert c..json` gibi
    ekstra metin içerebilir). Dosya/klasör yoksa None (henüz yüklenmemiş)."""
    tam = os.path.join(RENK_DIR, f"{order}.json")
    if os.path.exists(tam):
        return tam
    if not os.path.isdir(RENK_DIR):
        return None
    for ad in sorted(os.listdir(RENK_DIR)):
        if not ad.lower().endswith(".json"):
            continue
        m = re.search(r'(\d{4,}(?:-\d+)?)', ad)
        if m and m.group(1) == order:
            return os.path.join(RENK_DIR, ad)
    return None


def siparis_rengi_belirle(order):
    """renkler/<sipariş>.json'daki parça renklerinden (user_data.renk) siparişin
    BASKIN rengini (en çok geçen kod) ve buna göre Linco Gövde/Linco Kapak/Tıpa
    renklerini döndürür. Dosya yok/boş/tanınmayan kodsa None — PDF ve panel bunu
    sessizce atlar (renk bilgisi henüz yüklenmemiş demektir)."""
    yol = _renk_json_yolu(order)
    if not yol:
        return None
    try:
        with open(yol, encoding="utf-8") as f:
            ham = json.load(f)
    except Exception as e:
        print(f"  [UYARI] renk json okunamadı ({yol}): {e}")
        return None

    kodlar = Counter()
    for parca in ham.get("parcalar") or []:
        kod = (parca.get("user_data") or {}).get("renk")
        if kod is not None:
            kodlar[str(kod)] += 1
    if not kodlar:
        return None

    baskin_kod, _ = kodlar.most_common(1)[0]
    ad = RENK_KOD_ADI.get(baskin_kod)
    if not ad:
        print(f"  [UYARI] bilinmeyen renk kodu '{baskin_kod}' ({yol})")
        return None

    return {
        "siparis_rengi_kodu": baskin_kod,
        "siparis_rengi": ad,
        "kaynak_dosya": os.path.basename(yol),
        "parca_renkleri": dict(PARCA_RENK_KURALI[ad]),
    }


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


# Konum/geometri mesafesi: küçük parçanın en büyük dünya boyutunun on binde biri.
DUPLICATE_POSITION_RATIO = 0.0001


def _center_part_origin(obj):
    """Orijini geometri bbox merkezine al; dünya geometrisi ve çocuklar sabit kalır."""
    dim, center = get_perfect_local_bounds(obj)
    if center is None or center.length < 1e-12:
        return
    children = [(c, c.matrix_world.copy()) for c in obj.children]
    if obj.data.users > 1:
        obj.data = obj.data.copy()
    obj.data.transform(mathutils.Matrix.Translation(-center))
    obj.matrix_world = obj.matrix_world @ mathutils.Matrix.Translation(center)
    for child, matrix in children:
        child.matrix_world = matrix


def _part_geometry(obj):
    points = [obj.matrix_world @ v.co for v in obj.data.vertices]
    if not points:
        return None
    lo = mathutils.Vector(tuple(min(v[i] for v in points) for i in range(3)))
    hi = mathutils.Vector(tuple(max(v[i] for v in points) for i in range(3)))
    return points, (lo + hi) / 2, hi - lo


def _same_part_geometry(a, b, tolerance):
    """Dünya vertexleri VE yüz/kenar bağlantıları eşleşmeli; yalnız bbox yetmez.

    Yeniden üçgenlenmiş eş yüzeyler konservatif olarak ayrı kalır.
    Modifier/shape-key geometrisi bu statik FBX yolunda birleştirilmez.
    """
    oa, pa = a
    ob, pb = b
    if (len(pa) != len(pb) or len(oa.data.edges) != len(ob.data.edges)
            or len(oa.data.polygons) != len(ob.data.polygons)):
        return False
    if all((va - vb).length <= tolerance for va, vb in zip(pa, pb)):
        mapping = list(range(len(pb)))
    else:
        from mathutils.kdtree import KDTree
        tree = KDTree(len(pa))
        for i, point in enumerate(pa):
            tree.insert(point, i)
        tree.balance()
        mapping, used = [], set()
        for point in pb:
            choices = sorted(tree.find_range(point, tolerance), key=lambda item: (item[2], item[1]))
            index = next((i for _, i, _ in choices if i not in used), None)
            if index is None:
                return False
            mapping.append(index)
            used.add(index)

    def face_key(indices):
        seq = tuple(indices)
        # Başlangıç vertexi ve yüz sarım yönü farklı olabilir.
        rotations = [seq[i:] + seq[:i] for i in range(len(seq))]
        rev = seq[::-1]
        rotations.extend(rev[i:] + rev[:i] for i in range(len(rev)))
        return min(rotations)

    edges_a = Counter(tuple(sorted(e.vertices)) for e in oa.data.edges)
    edges_b = Counter(tuple(sorted(mapping[i] for i in e.vertices)) for e in ob.data.edges)
    if edges_a != edges_b:
        return False
    return (Counter(face_key(p.vertices) for p in oa.data.polygons)
            == Counter(face_key([mapping[i] for i in p.vertices]) for p in ob.data.polygons))


def prepare_unique_parts(meshes):
    """Orijinleri düzelt, sonra üst üste eş parçaların tek temsilcisini bırak.

    Tolerans = min(iki parçanın en büyük dünya boyutu) × 0.0001.
    Dünya sıfırına uzaklığa bağlı değildir. Çıkış: (kalan objeler, kaldırılan/kalan adları).
    Sadece verilen mesh'ler karşılaştırılır; kaynak FBX dosyasına yazılmaz.
    """
    meshes = sorted(meshes, key=lambda o: o.name)
    bpy.context.view_layer.update()
    for obj in meshes:
        if not obj.modifiers and not obj.data.shape_keys:
            _center_part_origin(obj)
    bpy.context.view_layer.update()
    kept, records, removed = [], [], []
    for obj in meshes:
        geometry = _part_geometry(obj)
        if geometry is None or obj.modifiers or obj.data.shape_keys:
            kept.append(obj)
            continue
        points, center, size = geometry
        duplicate = None
        for other, other_points, other_center, other_size in records:
            tolerance = min(max(size), max(other_size)) * DUPLICATE_POSITION_RATIO
            if tolerance <= 0 or (center - other_center).length > tolerance:
                continue
            if any(abs(size[i] - other_size[i]) > 2 * tolerance for i in range(3)):
                continue
            if _same_part_geometry((other, other_points), (obj, points), tolerance):
                duplicate = other
                break
        if duplicate is None:
            kept.append(obj)
            records.append((obj, points, center, size))
        else:
            removed.append((obj.name, duplicate.name))
            # Kopyaya bağlı yardımcıları silme; dünya dönüşümlerini koru.
            for child in list(obj.children):
                matrix = child.matrix_world.copy()
                child.parent = duplicate
                child.matrix_world = matrix
            bpy.data.objects.remove(obj, do_unlink=True)
    for name, kept_name in removed:
        print(f"  [KOPYA] {name} kaldırıldı; kalan: {kept_name}")
    return kept, removed


# ── Modül sütunları → duvar bağlantı braketi (L Bağlantı Seti) ───────────────
def modul_sutun_bilgisi(meshes, parca_modul=None):
    """Modülleri geometriden ayır, sütunlara grupla, braket sayısını çıkar.

    prepare_unique_parts()'tan SONRA, delik boolean'larından ÖNCE çağrılır (dünya
    geometrisi el değmemiş olmalı). Parça adı kullanılmaz. Sahneyi değiştirmez.
    parca_modul: dict verilirse ayırıcının üyelik ataması {obje adı: "M01"} ile
    doldurulur (askılık flanş eşleştirmesi için; ad yalnız obje anahtarıdır).
    Atanamayan parça sözlükte yer almaz.
    Dönüş (JSON'a "moduller" olarak yazılır):
      kaynak       "geometri" | "yedek_sabit"
      braket       L Bağlantı Seti adedi (geometri: 2 × sütun; yedek: L_BAGLANTI_ADET)
      modul_sayisi, sutun_sayisi, sutunlar ([[M01, M02], ...] alttan üste)
      kutular      {modül: {"lo": [...], "hi": [...]}} mm
      cozulemeyen_parca, ikiz_adayi  (ayırıcının belirsizlik göstergeleri)
    """
    bilgi = {"kaynak": "yedek_sabit", "braket": L_BAGLANTI_ADET, "modul_sayisi": 0,
             "sutun_sayisi": 0, "sutunlar": [], "kutular": {}}
    if module_segmenter is None:
        bilgi["hata"] = f"module_ayirici yüklenemedi: {_MODUL_AYIRICI_HATA}"
        return bilgi
    try:
        sonuc = module_segmenter.segment(meshes)
    except Exception as e:
        bilgi["hata"] = f"modül ayırma başarısız: {e!r}"
        return bilgi
    moduller = sonuc["modules"]
    bilgi["cozulemeyen_parca"] = len(sonuc["unresolved"])
    bilgi["ikiz_adayi"] = len(sonuc["twin_candidates"])
    if not moduller:
        bilgi["hata"] = "hiç modül (gövde) bulunamadı"
        return bilgi
    if parca_modul is not None:
        parca_modul.update({ad: a["module"] for ad, a in sonuc["assignment"].items()})
    gruplar = sutunlar.sutunlari_bul(moduller)
    bilgi.update(
        kaynak="geometri",
        braket=sutunlar.duvar_braketi_sayisi(len(gruplar)),
        modul_sayisi=len(moduller),
        sutun_sayisi=len(gruplar),
        sutunlar=[[moduller[i]["id"] for i in g] for g in gruplar],
        kutular={m["id"]: {"lo": [round(v, 1) for v in m["lo"]],
                           "hi": [round(v, 1) for v in m["hi"]]} for m in moduller},
    )
    return bilgi


# ── Sayım ────────────────────────────────────────────────────────────────────
def count_order(order):
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    meshes, duplicate_parts = prepare_unique_parts(meshes)
    # Modül/sütun tespiti delik boolean'larından ÖNCE (geometri henüz el değmemiş).
    parca_modul = {}            # obje adı → modül (askılık flanş eşleştirmesi için)
    modul_bilgisi = modul_sutun_bilgisi(meshes, parca_modul)
    if modul_bilgisi["kaynak"] != "geometri":
        print(f"  [UYARI] L Bağlantı Seti yedek sabite düştü: {modul_bilgisi.get('hata')}")

    counts = Counter()          # ham kategori sayıları
    kulp = 0
    ayak = 0
    parts_with_mentese = 0
    modulbag_centers = []
    linco_holes_by_part = []    # her parçanın linco delikleri: [(center, direction), ...]
    arkalik_civi = 0
    askilik_flansi = 0
    flanslar = []               # askılık flanşı konumları: {merkez, pano, modul, pano_lo, pano_hi} (mm)
    ray_isimleri = []           # tespit edilen ray boyları (ör. "55cm", "30cm")
    part_count = len(meshes)

    # Arkalık adaylarını (kalınlıktan) diğer parçalardan ayır. Paketleme için
    # ikiye kesilmiş arkalıklar varsa (aynı hacimde çift) önce tek parçada
    # birleştirilir, ANCAK BUNDAN SONRA çivi sayılır — yoksa yarım panel
    # boyutuyla (W×H) yanlış çivi sayısı çıkar.
    arkalik_adaylari = []
    diger_parcalar = []
    for o in meshes:
        th = part_thickness(o)
        if th is not None and th <= ARKALIK_MAX_KALINLIK:
            arkalik_adaylari.append(o)
        else:
            diger_parcalar.append(o)

    arkalik_parcalari = pair_split_arkalik(arkalik_adaylari)
    for o in arkalik_parcalari:
        arkalik_civi += arkalik_civi_count(o)

    for o in diger_parcalar:
        # Delikler
        try:
            holes = execute_double_boolean(o)
        except Exception as e:
            print(f"  [UYARI] {o.name}: delik taraması başarısız ({e})")
            continue

        part_mentese = 0
        part_agacvida_centers = []
        part_modul_centers = []
        part_linco_holes = []
        part_ray_centers = []
        for h in holes:
            v = h["volume"]
            obj_part = h["object"]
            cat = match_category(v)
            if cat == "modulbaglanti":
                part_modul_centers.append(world_center(obj_part))
            elif cat in ("agacvidasi", "agacvidasiTam"):
                # agacvidasiTam = karşıya çıkan ağaç vidası deliği; aynı havuz
                if cat == "agacvidasiTam":
                    counts["_agacvida_tam"] += 1        # teşhis (JSON _ham)
                part_agacvida_centers.append(world_center(obj_part))
            elif cat == "linco":
                counts["linco"] += 1
                part_linco_holes.append(
                    (world_center(obj_part), hole_signed_direction(o, obj_part)))
            elif cat:
                counts[cat] += 1
                if cat == "menteseTabani":
                    part_mentese += 1
            elif is_ray_hole(v):
                # ray'e özgü delik (agacvidasi DEĞİL, bkz. RAY_DELIK_HACIMLERI) — ray
                # deseni bu havuzda aranır, ağaç vidası/ayarlı ayak havuzuna girmez.
                part_ray_centers.append(world_center(obj_part))
            elif agac_vidasi_degisken_mi(obj_part, v):
                # değişken derinlikli kör ağaç vidası deliği (hacim bandı yok;
                # sabit KESİT üzerinden tanındı) — agacvidasi havuzuna girer
                counts["_agacvida_degisken"] += 1       # teşhis (JSON _ham)
                part_agacvida_centers.append(world_center(obj_part))
            bpy.data.objects.remove(obj_part, do_unlink=True)

        # Bu parçadaki modulbaglanti deliklerinden kulp çiftlerini ayır
        kulp_from_part, remaining_modul = detect_kulp_pairs(part_modul_centers)
        kulp += kulp_from_part
        modulbag_centers.extend(remaining_modul)

        # Ayarlı ayak: HAM agacvidasi listesinden ayıkla (izolasyon: ayak vidaları
        # ağaç vidası havuzunda KALIR, bkz. parca_kurallari.md).
        ayak_bu_parca, ayak_noktalari, ayak_disi = extract_ayak_feet(part_agacvida_centers)
        ayak += ayak_bu_parca

        # Ray desenleri artık KENDİNE ÖZGÜ delik havuzunda (part_ray_centers,
        # RAY_DELIK_HACIMLERI) aranır — agacvidasi havuzuyla hiç KESİŞMEZ. Böylece
        # rastgele aralıklı gerçek ağaç vidaları artık ray sanılıp çalınamaz;
        # ayarlı ayak/ağaç vidası sayımı ray tespitinden tamamen bağımsızdır.
        part_rays, _ray_disi = detect_rays(part_ray_centers)
        ray_isimleri.extend(part_rays)
        remaining_agacvida = ayak_noktalari + ayak_disi
        counts["agacvidasi"] += len(remaining_agacvida)

        if part_mentese > 0:
            parts_with_mentese += 1
        # Askılık flanşı: kalan ağaç vidası deliklerinden eşkenar üçgenler. Her flanş
        # konumunu (üçgen ağırlık merkezi) ve üstünde durduğu paneli saklar → boru boyu.
        ucgenler = find_equilateral_flanges(remaining_agacvida)
        askilik_flansi += len(ucgenler)
        if ucgenler:
            pano_lo, pano_hi = _dunya_kutusu_mm(o)
            for i, j, k in ucgenler:
                m = (remaining_agacvida[i] + remaining_agacvida[j] + remaining_agacvida[k]) / 3.0
                flanslar.append({"merkez": [m.x * MODEL_MM, m.y * MODEL_MM, m.z * MODEL_MM],
                                 "pano": o.name, "modul": parca_modul.get(o.name),
                                 "pano_lo": pano_lo, "pano_hi": pano_hi})

        # Uzun linco pimi için: bu parçanın linco delik/yön çiftlerini sakla
        if part_linco_holes:
            linco_holes_by_part.append(part_linco_holes)

    pairs = detect_modul_baglanti_pairs(modulbag_centers)
    # Farklı parçalardaki birbirine dayalı + yönü hizalı linco çiftleri → uzun linco pimi
    uzun_linco_pim = detect_long_linco_pins(linco_holes_by_part)
    # Arkalık çivisi: Mert'in %25 tamponu (2026-09-01). Mevcut hesap (2*nx+2*nz) düz
    # hesap — ek bir arttırma YOK, override edilecek bir şey yok; doğrudan ×1.25
    # uygulanır, en yakın tam sayıya yuvarlanır.
    arkalik_civi = round(arkalik_civi * 1.25)

    linco = counts["linco"]
    # Mert'in tedarik tamponu (2026-09-01): linco adedine boyut bazlı ekleme.
    # ≤20 → +1, 21–99 → +2, 100+ → +3 (100 sınırı +3'e sayılır). Mert'in yazdığı
    # sınıflar 21-49'u kapsamadığından Kerem kararıyla o aralık +2 kabul edildi.
    if linco <= 20:
        linco_ekle = 1
    elif linco < 100:
        linco_ekle = 2
    else:
        linco_ekle = 3
    linco_adj = linco + linco_ekle            # tamponlu sayı (Gövde/Kapak/Minifix/Dübel + gram)
    linco_dubel = linco_adj - 2 * uzun_linco_pim   # her uzun pim = 2 linco dübeli yerine 1
    mentese_tabani = counts["menteseTabani"]
    frenli = parts_with_mentese
    frensiz = mentese_tabani - frenli
    raf_pimi = counts["rafpimi"] // 3     # her raf pimi = 3 delik
    l_baglanti = modul_bilgisi["braket"]    # 2 × sütun (yedek: L_BAGLANTI_ADET)
    # Ray'lerde kullanılan delik sayısı (RAY_DELIK_HACIMLERI havuzundan, agacvidasi
    # havuzuna hiç girmedi — ama ray varsa o rayların delikleri de birer vidayla
    # kapatıldığından, genel ağaç vidası adedinden düşülür).
    ray_delik_toplam = sum(len(RAY_HOLE_POSITIONS[name]) for name in ray_isimleri)
    # Ağaç vidası = doğrudan hacimden sayılan delik sayısı + her L bağlantı seti
    # için 2 adet − ray'lerde kullanılan delik sayısı.
    agac_vidasi = counts["agacvidasi"] + 2 * l_baglanti - ray_delik_toplam
    askilik_borusu = askilik_flansi // 2     # her 2 flanşı için 1 boru (adet anlamı DEĞİŞMEDİ)
    # Boru boyları: aynı modülde X/Y boyunca birbirine bakan flanş çiftleri →
    # iç yüz orta noktaları arası mesafe − 1 cm, tam cm (module_ayirici/askilik.py).
    if askilik is not None:
        askilik_borulari, eslesmeyen_flanslar = askilik.eslestir(flanslar)
        askilik_eslesme = askilik.ozet(askilik_borulari, eslesmeyen_flanslar, askilik_flansi)
    else:
        askilik_borulari = []
        askilik_eslesme = {"flans": askilik_flansi, "eslesen_boru": 0,
                           "beklenen_boru": askilik_borusu, "tutarli": askilik_flansi == 0,
                           "eslesmeyen_flanslar": [],
                           "hata": f"askilik.py yüklenemedi: {_ASKILIK_HATA}"}
    if not askilik_eslesme["tutarli"]:
        print(f"  [UYARI] Askılık: {askilik_flansi} flanş → adet {askilik_borusu} boru, "
              f"ama {askilik_eslesme['eslesen_boru']} çift eşleşti "
              f"({len(askilik_eslesme['eslesmeyen_flanslar'])} flanş eşsiz); "
              f"boyu bulunamayan boru PDF'te '?'")
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
        "Linco Gövde": linco_adj,
        "Linco Kapak": linco_adj,
        "Linco Dübel": linco_dubel,
        "Minifix": linco_adj,
        "Uzun Linco Pimi": uzun_linco_pim,
        "Ayarlı Ayak": ayak,
        "Allen": 1 if ayak >= 1 else 0,
        "Tıpa": counts["tipa"],   # doğrudan tipa deliği hacmi (1392.75 mm³, %1) — ayarlı ayaktan türetme DEĞİL
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
        "Ağaç Vidası": gr(agac_vidasi, WEIGHTS["agacvidasi"]),
        "Minifix": gr(linco_adj, WEIGHTS["minifix"]),
        "Linco Dübel": gr(linco_dubel, WEIGHTS["lincodubel"]),
        "Linco": gr(linco_adj, WEIGHTS["linco"]),
        "Linco Kapak": gr(linco_adj, WEIGHTS["lincokapak"]),
        "Çivi": gr(arkalik_civi, WEIGHTS["civi"]),
    }

    return {
        "siparis": order,
        "parca_sayisi": part_count,
        "adet": adet,
        "gram": gram,
        "ray_setleri": ray_setleri,    # boy bazında ray seti adedi (ör. {"55cm": 2})
        "renk": siparis_rengi_belirle(order),  # None = renk json henüz yüklenmemiş
        "moduller": modul_bilgisi,     # modül/sütun tespiti; L Bağlantı Seti buradan
        "askilik_borulari": askilik_borulari,  # boru başına kesim boyu (uzunluk_cm), büyükten küçüğe
        "askilik_eslesme": askilik_eslesme,    # flanş/çift tutarlılığı + eşsiz flanşlar (teşhis)
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
        mb = res["moduller"]
        print(f"   [modül] {mb['modul_sayisi']} modül, {mb['sutun_sayisi']} sütun "
              f"→ L Bağlantı Seti {mb['braket']} ({mb['kaynak']})")
        if res["askilik_borulari"] or res["adet"]["Askılık Flanşı"]:
            print(f"   [askılık] boylar (cm): {[b['uzunluk_cm'] for b in res['askilik_borulari']]} "
                  f"tutarlı={res['askilik_eslesme']['tutarli']}")
        print(f"   >> {out_path}")

    _save_manifest(manifest)
    print(f"\n== Bitti: {yeni} yeni sipariş işlendi, {atlanan} atlandı (zaten işlenmiş).")


if __name__ == "__main__":
    main()
