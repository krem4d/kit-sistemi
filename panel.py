#!/usr/bin/env python3
"""panel.py — Adaptx Panel: sayım hattını tarayıcıdan izleme + sipariş checklist'i.

Sadece standart kütüphane (Flask/pip gerekmez). Boru hattına karşı SALT-OKUR:
fbx/, jsons/, pdf/, islem_gecmisi.json, video_envanteri.json yalnızca okunur;
yazılan dosyalar data/panel_checklist.json ile data/panel_notlar.json'dur
(atomik: temp + fsync + os.replace). Montaj videoları diske hiç yazılmaz:
istek anında Drive'dan akıtılır (rclone cat --offset/--count).

Çalıştırma:  python3 panel.py                 (systemd: adaptx-panel.service)
Arayüz:      http://<CT-IP>:8080
Parola (ops.): PANEL_KULLANICI + PANEL_SIFRE ortam değişkenleri ikisi de
setliyse HTTP Basic Auth zorunlu olur; boşsa panel açıktır (LAN kullanımı).
"""
import base64
import hmac
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# ---------------------------------------------------------------- AYARLAR ---
# Checklist artık sabit adımlar değil, siparişin KENDİ parçalarına göre otomatik
# oluşur (bkz. parca_anahtarlari) — burada değiştirilecek bir liste yok.

HOST = "0.0.0.0"
PORT = int(os.environ.get("PANEL_PORT") or 8080)
DURUM_TTL = 5.0     # sistem durumu önbellek süresi (sn)
SIPARIS_TTL = 3.0   # sipariş taraması önbellek süresi (sn)
OZET_BASINA = 14    # pdf_uret.py ile aynı: özet PDF başına sipariş sayısı
ISLENIYOR_ESIGI = 120  # bozuk json bu kadar sn'den tazeyse "yazım anı" say

BASE = os.environ.get("ADAPTX_BASE") or os.path.dirname(os.path.abspath(__file__))
FBX_DIR = os.path.join(BASE, "fbx")
VIDEO_ENVANTER = os.path.join(BASE, "video_envanteri.json")  # fbx_indir.sh yazar
JSON_DIR = os.path.join(BASE, "jsons")
PDF_DIR = os.path.join(BASE, "pdf")
ORDER_PDF_DIR = os.path.join(PDF_DIR, "siparişler pdf")  # Türkçe ad yalnız burada
MANIFEST = os.path.join(BASE, "islem_gecmisi.json")
DATA_DIR = os.path.join(BASE, "data")
CHECKLIST_DOSYA = os.path.join(DATA_DIR, "panel_checklist.json")
NOTLAR_DOSYA = os.path.join(DATA_DIR, "panel_notlar.json")
SAYFA_DOSYA = os.path.join(BASE, "panel.html")
RCLONE_ERR = "/var/log/adaptx_fbx_indir.err"

ORDER_RX = re.compile(r"^\d{4,}(?:-\d+)?$")      # URL'deki sipariş no doğrulaması
FBX_NO_RX = re.compile(r"(\d{4,}(?:-\d+)?)")     # parca_sayim.py ile aynı çıkarım

# Video akışı: fbx_indir.sh ile aynı Drive giriş klasörü; rclone yolu sabitlenir.
DRIVE_IN_ID = os.environ.get("ADAPTX_DRIVE_IN") or "1_pi5GtrrGXjABLOi9kRPlg3CD7_fY-51"
RCLONE = shutil.which("rclone") or "/usr/bin/rclone"
_video_sem = threading.BoundedSemaphore(3)  # 1 çekirdek + MemoryMax=256M sınırı için

try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Europe/Istanbul")
except Exception:
    IST = timezone(timedelta(hours=3))

# ------------------------------------------------------- CHECKLIST DEPOSU ---
_cl_kilit = threading.Lock()
_cl_veri = {}  # {"8518": {"Kontrol Edildi": "2026-07-02T16:41:00+03:00"|None}}


def _cl_yukle():
    """Checklist dosyasını yükle; bozuksa karantinaya al (asla silme)."""
    global _cl_veri
    try:
        with open(CHECKLIST_DOSYA, encoding="utf-8") as f:
            ham = json.load(f)
        sip = ham.get("siparisler") if isinstance(ham, dict) else None
        _cl_veri = sip if isinstance(sip, dict) else {}
    except FileNotFoundError:
        _cl_veri = {}
    except Exception as e:
        yedek = f"{CHECKLIST_DOSYA}.bozuk-{int(time.time())}"
        try:
            os.replace(CHECKLIST_DOSYA, yedek)
            print(f"[panel] UYARI: checklist dosyası bozuk ({e}); {yedek} olarak saklandı.")
        except OSError:
            print(f"[panel] UYARI: checklist dosyası okunamadı: {e}")
        _cl_veri = {}


def _cl_kaydet():
    """Atomik yaz: temp dosya + fsync + os.replace (aynı dizin = aynı dosya sistemi)."""
    govde = {"surum": 1, "siparisler": _cl_veri}
    f = tempfile.NamedTemporaryFile("w", dir=DATA_DIR, delete=False,
                                    prefix=".panel_checklist.tmp", encoding="utf-8")
    try:
        json.dump(govde, f, ensure_ascii=False, indent=1)
        f.flush()
        os.fsync(f.fileno())
        f.close()
        os.replace(f.name, CHECKLIST_DOSYA)
    except BaseException:
        f.close()
        try:
            os.unlink(f.name)
        except OSError:
            pass
        raise


# ------------------------------------------------------------ NOT DEPOSU ---
# Checklist ile aynı desen: kilit + atomik yazım + bozuk dosyayı karantinaya al.
_not_kilit = threading.Lock()
_not_veri = {}  # {"9314": {"metin": "…", "zaman": "2026-07-03T20:15:00+03:00"}}
NOT_MAX = 4000


def _not_yukle():
    global _not_veri
    try:
        with open(NOTLAR_DOSYA, encoding="utf-8") as f:
            ham = json.load(f)
        notlar = ham.get("notlar") if isinstance(ham, dict) else None
        _not_veri = notlar if isinstance(notlar, dict) else {}
    except FileNotFoundError:
        _not_veri = {}
    except Exception as e:
        yedek = f"{NOTLAR_DOSYA}.bozuk-{int(time.time())}"
        try:
            os.replace(NOTLAR_DOSYA, yedek)
            print(f"[panel] UYARI: not dosyası bozuk ({e}); {yedek} olarak saklandı.")
        except OSError:
            print(f"[panel] UYARI: not dosyası okunamadı: {e}")
        _not_veri = {}


def _not_kaydet():
    govde = {"surum": 1, "notlar": _not_veri}
    f = tempfile.NamedTemporaryFile("w", dir=DATA_DIR, delete=False,
                                    prefix=".panel_notlar.tmp", encoding="utf-8")
    try:
        json.dump(govde, f, ensure_ascii=False, indent=1)
        f.flush()
        os.fsync(f.fileno())
        f.close()
        os.replace(f.name, NOTLAR_DOSYA)
    except BaseException:
        f.close()
        try:
            os.unlink(f.name)
        except OSError:
            pass
        raise


def not_degistir(no, metin):
    """Sipariş notunu yaz (boş metin = notu sil); sunucu gerçeğini döndürür."""
    with _not_kilit:
        if metin:
            _not_veri[no] = {"metin": metin,
                             "zaman": datetime.now(IST).isoformat(timespec="seconds")}
        else:
            _not_veri.pop(no, None)
        _not_kaydet()
        return dict(_not_veri.get(no) or {"metin": "", "zaman": None})


def parca_anahtarlari(veri):
    """Bir siparişin işaretlenebilir parça anahtarları: nonzero `adet` anahtarları +
    nonzero `ray_setleri` anahtarları (çakışmayı önlemek için "ray:" önekiyle).
    Tek doğruluk kaynağı: hem checklist doğrulamasında hem özetinde kullanılır."""
    if not veri:
        return []
    anahtarlar = [k for k, v in (veri.get("adet") or {}).items() if v]
    anahtarlar += ["ray:" + str(k) for k, v in (veri.get("ray_setleri") or {}).items() if v]
    return anahtarlar


def checklist_degistir(no, parca, durum):
    """Bir parçayı işaretle/kaldır; sunucu gerçeğini (parça→zaman) döndürür."""
    with _cl_kilit:
        kayit = _cl_veri.setdefault(no, {})
        kayit[parca] = datetime.now(IST).isoformat(timespec="seconds") if durum else None
        _cl_kaydet()
        return dict(kayit)


def checklist_ozeti(no, veri):
    """Siparişin GÜNCEL parça listesine göre (checklist sözlüğü, tamam, toplam).
    Kilidi kendi almaz — çağıran _cl_kilit'i tutuyor olmalı (bkz. durum_yaniti)."""
    kayit = _cl_veri.get(no) or {}
    parcalar = parca_anahtarlari(veri)
    checklist = {p: kayit.get(p) for p in parcalar}
    tamam = sum(1 for v in checklist.values() if v)
    return checklist, tamam, len(parcalar)


# ------------------------------------------------------- YARDIMCI KOMUTLAR ---
def _komut(args, rc_onemli=True):
    """Salt-okur sistem komutu; zaman aşımı 4 sn. (çıktı|None, uyarı|None)."""
    try:
        s = subprocess.run(args, capture_output=True, text=True, timeout=4)
        if s.returncode != 0 and rc_onemli:
            return None, f"{' '.join(args[:2])} rc={s.returncode}"
        return s.stdout, None
    except Exception as e:
        return None, f"{args[0]}: {e.__class__.__name__}"


def _son_satir(yol, blok=4096):
    """Dosyanın son boş olmayan satırı + mtime; yoksa (None, None)."""
    try:
        st = os.stat(yol)
        with open(yol, "rb") as f:
            f.seek(max(0, st.st_size - blok))
            veri = f.read().decode("utf-8", "replace")
        satirlar = [s for s in veri.splitlines() if s.strip()]
        return (satirlar[-1] if satirlar else None), int(st.st_mtime)
    except OSError:
        return None, None


def _no_sirala(no):
    """'9304-1' → (9304, 1); sayısal azalan sıralama anahtarı için."""
    m = re.match(r"^(\d+)(?:-(\d+))?$", no)
    if not m:
        return (0, 0)
    return (int(m.group(1)), int(m.group(2) or 0))


# ------------------------------------------------------------ SİPARİŞLER ---
_sip_kilit = threading.Lock()
_sip_cache = {"t": 0.0, "sonuc": None}
_json_parse = {}     # yol -> (mtime_ns, boyut, veri|None) — değişmeyeni yeniden açma
_manifest_iyi = []   # son bilinen iyi siralama (manifest yazım anında yedek)


def _manifest_oku():
    """islem_gecmisi.json'u toleranslı oku (boru hattı atomik yazmıyor)."""
    global _manifest_iyi
    for deneme in range(2):
        try:
            with open(MANIFEST, encoding="utf-8") as f:
                ham = json.load(f)
            sira = ham.get("siralama") if isinstance(ham, dict) else None
            if isinstance(sira, list):
                _manifest_iyi = [str(x) for x in sira]
            return _manifest_iyi
        except FileNotFoundError:
            return _manifest_iyi
        except Exception:
            if deneme == 0:
                time.sleep(0.2)  # yazım anına denk gelmiş olabilir
    return _manifest_iyi


_video_iyi = {}   # son bilinen iyi video envanteri (okuma hatasında yedek)


def _video_envanteri_oku():
    """video_envanteri.json'u toleranslı oku: no → {yol, boyut}. Dosya atomik
    yazılır (fbx_indir.sh) ama yine de bozuksa eldeki son iyi kopya kullanılır."""
    global _video_iyi
    try:
        with open(VIDEO_ENVANTER, encoding="utf-8") as f:
            ham = json.load(f)
        v = ham.get("videolar") if isinstance(ham, dict) else None
        if isinstance(v, dict):
            _video_iyi = v
    except Exception:
        pass  # yoksa/bozuksa: eldeki son iyi kopya (ilk kurulumda boş)
    return _video_iyi


def _json_yukle(yol, st):
    """Tek sipariş json'unu parse-önbelleğiyle oku; bozuk/boş → None."""
    anahtar = (st.st_mtime_ns, st.st_size)
    onceki = _json_parse.get(yol)
    if onceki and onceki[0] == anahtar[0] and onceki[1] == anahtar[1]:
        return onceki[2]
    veri = None
    if st.st_size > 0:
        try:
            with open(yol, encoding="utf-8") as f:
                ham = json.load(f)
            if isinstance(ham, dict):
                veri = ham
        except Exception:
            veri = None
    _json_parse[yol] = (anahtar[0], anahtar[1], veri)
    return veri


def siparis_okumasi():
    """Tüm sipariş kayıtlarını topla (SIPARIS_TTL sn önbellekli).

    Dönen sözlük: kayitlar (no→kayıt), sirali (görüntüleme sırası, no listesi),
    no_suz_fbx, son_fbx. Kayıt: no, durum(islendi|bekliyor|isleniyor|hatali),
    parca, pdf, ozet_no, zaman, data (tam json|None), fbx ([{ad,zaman,boyut}]),
    video ({ad,boyut}|None — Drive'daki <no>.mp4; envanteri fbx_indir.sh çıkarır,
    dosya yerelde tutulmaz).
    """
    with _sip_kilit:
        simdi = time.time()
        if _sip_cache["sonuc"] is not None and simdi - _sip_cache["t"] < SIPARIS_TTL:
            return _sip_cache["sonuc"]

        # 1) fbx/ taraması: sipariş no → kaynak dosyalar; numarasızlar uyarıya
        fbx_gruplari, no_suz, son_fbx = {}, [], None
        try:
            for e in os.scandir(FBX_DIR):
                if not (e.is_file() and e.name.lower().endswith(".fbx")):
                    continue
                st = e.stat()
                kayit = {"ad": e.name, "zaman": int(st.st_mtime), "boyut": st.st_size}
                if son_fbx is None or kayit["zaman"] > son_fbx["zaman"]:
                    son_fbx = kayit
                m = FBX_NO_RX.search(e.name)
                if m:
                    fbx_gruplari.setdefault(m.group(1), []).append(kayit)
                else:
                    no_suz.append(e.name)
        except OSError:
            pass

        # 2) jsons/ taraması: varlık = işlendi; boş/bozuk = hatalı|işleniyor
        kayitlar = {}
        try:
            for e in os.scandir(JSON_DIR):
                if not (e.is_file() and e.name.endswith(".json")):
                    continue
                no = e.name[:-5]
                st = e.stat()
                veri = _json_yukle(e.path, st)
                if veri is not None:
                    durum = "islendi"
                elif simdi - st.st_mtime < ISLENIYOR_ESIGI:
                    durum = "isleniyor"  # Blender yazım anı olabilir (atomik değil)
                else:
                    durum = "hatali"     # boş/bozuk json (ör. 8548, 8553)
                kayitlar[no] = {
                    "no": no, "durum": durum,
                    "parca": (veri or {}).get("parca_sayisi"),
                    "pdf": os.path.exists(os.path.join(ORDER_PDF_DIR, no + ".pdf")),
                    "ozet_no": None,
                    "zaman": int(st.st_mtime),
                    "data": veri,
                    "fbx": fbx_gruplari.get(no, []),
                }
        except OSError:
            pass

        # 3) fbx'i olup json'u olmayanlar: sıradaki turda işlenecek → bekliyor
        for no, dosyalar in fbx_gruplari.items():
            if no not in kayitlar:
                kayitlar[no] = {
                    "no": no, "durum": "bekliyor", "parca": None, "pdf": False,
                    "ozet_no": None, "zaman": max(d["zaman"] for d in dosyalar),
                    "data": None, "fbx": dosyalar,
                }

        # 3b) video envanteri (fbx_indir.sh yazar): Drive'da <no>.mp4 var mı?
        videolar = _video_envanteri_oku()
        for no, k in kayitlar.items():
            v = videolar.get(no)
            k["video"] = ({"ad": os.path.basename(v["yol"]), "boyut": v.get("boyut")}
                          if isinstance(v, dict) and v.get("yol") else None)

        # 4) Manifest sırası → özet PDF sayfa numarası (idx//14 + 1)
        siralama = _manifest_oku()
        idx_map = {no: i for i, no in enumerate(siralama)}
        for no, k in kayitlar.items():
            if no in idx_map and k["durum"] == "islendi":
                k["ozet_no"] = idx_map[no] // OZET_BASINA + 1

        # 5) Görüntüleme sırası: sipariş no'suna göre azalan — en büyük numara en
        # başta (kullanıcı isteği; frontend gerekirse yön toggle'ıyla tersine çevirir).
        sirali = sorted(kayitlar, key=_no_sirala, reverse=True)

        sonuc = {"kayitlar": kayitlar, "sirali": sirali,
                 "no_suz_fbx": sorted(no_suz), "son_fbx": son_fbx}
        _sip_cache.update(t=simdi, sonuc=sonuc)
        return sonuc


# --------------------------------------------------------- SİSTEM DURUMU ---
_durum_kilit = threading.Lock()
_durum_cache = {"t": 0.0, "veri": None}


def sistem_durumu():
    """Boru hattı/makine durumu (DURUM_TTL sn önbellekli; alanlar null'a düşer)."""
    with _durum_kilit:
        simdi = time.time()
        if _durum_cache["veri"] is not None and simdi - _durum_cache["t"] < DURUM_TTL:
            return _durum_cache["veri"]

        uyarilar = []

        # Timer: sonraki/son tetik (list-timers; show -p NextElapse... boş döner)
        sonraki_tur = son_tur_zamani = None
        out, u = _komut(["systemctl", "list-timers", "adaptx.timer",
                         "--output=json", "--no-pager"])
        if u:
            uyarilar.append(u)
        elif out:
            try:
                satirlar = json.loads(out)
                if satirlar:
                    n, l = satirlar[0].get("next"), satirlar[0].get("last")
                    sonraki_tur = n // 1000000 if isinstance(n, int) else None
                    son_tur_zamani = l // 1000000 if isinstance(l, int) else None
            except Exception:
                uyarilar.append("list-timers çıktısı çözümlenemedi")

        out, _ = _komut(["systemctl", "is-active", "adaptx.timer"], rc_onemli=False)
        timer_aktif = (out or "").strip() == "active"

        out, _ = _komut(["systemctl", "show", "adaptx.service",
                         "-p", "ActiveState", "--value"], rc_onemli=False)
        servis_calisiyor = (out or "").strip() in ("activating", "active", "reloading")

        # Journal: son tur sonucu + son 5 anlamlı satır
        son_loglar, sonuc, mesaj = [], "bilinmiyor", None
        out, u = _komut(["journalctl", "-u", "adaptx.service", "-n", "80",
                         "-o", "cat", "--no-pager", "-q"])
        if u:
            uyarilar.append(u)
        elif out is not None:
            onemli = [s for s in out.splitlines()
                      if "[adaptx]" in s or s.startswith("== Bitti")]
            son_loglar = onemli[-5:]
            for s in reversed(onemli):
                if "yeni sipariş yok" in s:
                    sonuc, mesaj = "atlandi", s
                    break
                if "HATA" in s:
                    sonuc, mesaj = "hata", s
                    break
                if "tamamlandı" in s:
                    sonuc, mesaj = "tamamlandi", s
                    break

        rclone_satir, rclone_mtime = _son_satir(RCLONE_ERR)

        try:
            du = shutil.disk_usage(BASE)
            disk = {"toplam": du.total, "bos": du.free,
                    "yuzde": round(du.used * 100 / du.total)}
        except OSError:
            disk = None
            uyarilar.append("disk kullanımı okunamadı")

        try:
            yuk = round(os.getloadavg()[0], 2)
        except OSError:
            yuk = None

        # Kökteki özet PDF sayısı (siparisler_ozet*.pdf)
        ozet_adet = 0
        try:
            for ad in os.listdir(PDF_DIR):
                if re.fullmatch(r"siparisler_ozet(_\d+)?\.pdf", ad):
                    ozet_adet += 1
        except OSError:
            pass

        veri = {
            "sonraki_tur": sonraki_tur, "timer_aktif": timer_aktif,
            "servis_calisiyor": servis_calisiyor,
            "son_tur": {"zaman": son_tur_zamani, "sonuc": sonuc, "mesaj": mesaj},
            "son_loglar": son_loglar,
            "rclone": {"err_mtime": rclone_mtime, "son_satir": rclone_satir},
            "disk": disk, "yuk": yuk, "ozet_adet": ozet_adet,
            "uyarilar": uyarilar,
        }
        _durum_cache.update(t=simdi, veri=veri)
        return veri


# ------------------------------------------------------------ API GÖVDESİ ---
def durum_yaniti():
    """GET /api/durum gövdesi: sistem + sayaçlar + tüm siparişlerin TAM detayı (kart
    ızgarası artık her siparişi her zaman açık gösterdiği için ayrı /api/siparis
    çağrılarına gerek kalmadan tek yanıtta gelir — 292 sipariş için bile küçük payload)."""
    sistem = dict(sistem_durumu())
    okuma = siparis_okumasi()
    kayitlar, sirali = okuma["kayitlar"], okuma["sirali"]
    sistem["no_suz_fbx"] = okuma["no_suz_fbx"]
    sistem["son_fbx"] = okuma["son_fbx"]

    satirlar, sayac = [], {"toplam": 0, "islendi": 0, "bekleyen": 0,
                           "isleniyor": 0, "hatali": 0, "pdf": 0, "tamamlanan": 0}
    with _cl_kilit, _not_kilit:
        for no in sirali:
            k = kayitlar[no]
            veri = k["data"] or {}
            checklist, tamam, toplam = checklist_ozeti(no, veri)
            siparis_notu = _not_veri.get(no) or {}
            satirlar.append({
                "no": no, "durum": k["durum"], "parca": k["parca"],
                "pdf": k["pdf"], "ozet_no": k["ozet_no"], "zaman": k["zaman"],
                "adet": veri.get("adet") or {}, "gram": veri.get("gram") or {},
                "ray_setleri": veri.get("ray_setleri") or {},
                "checklist": checklist, "tamam": tamam, "toplam": toplam,
                "not_metin": siparis_notu.get("metin") or "",
                "not_zaman": siparis_notu.get("zaman"),
                "fbx": k["fbx"], "video": k["video"],
            })
            sayac["toplam"] += 1
            sayac["pdf"] += 1 if k["pdf"] else 0
            if toplam > 0 and tamam == toplam:
                sayac["tamamlanan"] += 1
            anahtar = {"islendi": "islendi", "bekliyor": "bekleyen",
                       "isleniyor": "isleniyor", "hatali": "hatali"}[k["durum"]]
            sayac[anahtar] += 1

    return {"zaman": int(time.time()), "sistem": sistem, "sayac": sayac, "siparisler": satirlar}


def siparis_yaniti(no, ham_goster=False):
    """GET /api/siparis/<no> gövdesi; yoksa None. Artık kart render'ı için birincil
    kaynak değil (/api/durum tam detayı zaten içeriyor) — ham/debug görünüm için kalır."""
    okuma = siparis_okumasi()
    k = okuma["kayitlar"].get(no)
    if k is None:
        return None
    veri = k["data"] or {}
    with _cl_kilit:
        checklist, tamam, toplam = checklist_ozeti(no, veri)
    yanit = {
        "no": no, "durum": k["durum"], "parca_sayisi": veri.get("parca_sayisi"),
        "adet": veri.get("adet") or {}, "gram": veri.get("gram") or {},
        "ray_setleri": veri.get("ray_setleri") or {},
        "fbx": k["fbx"], "video": k["video"], "pdf": k["pdf"], "ozet_no": k["ozet_no"],
        "zaman": k["zaman"], "checklist": checklist, "tamam": tamam, "toplam": toplam,
    }
    if ham_goster:
        yanit["ham"] = {a: veri.get(a) for a in ("_ham", "_kulp", "_raylar", "_uzun_linco")}
    return yanit


# --------------------------------------------------------------- SUNUCU ---
_KULLANICI = os.environ.get("PANEL_KULLANICI") or ""
_SIFRE = os.environ.get("PANEL_SIFRE") or ""
AUTH_GEREKLI = bool(_KULLANICI and _SIFRE)
_AUTH_BEKLENEN = base64.b64encode(f"{_KULLANICI}:{_SIFRE}".encode()).decode()

_sayfa_kilit = threading.Lock()
_sayfa = {"mtime": 0, "govde": b"<h1>panel.html eksik</h1>"}


def sayfa_govdesi():
    """panel.html'i bellekte tut; dosya değişince yeniden yükle (restart'sız UI güncellemesi)."""
    with _sayfa_kilit:
        try:
            st = os.stat(SAYFA_DOSYA)
            if st.st_mtime_ns != _sayfa["mtime"]:
                with open(SAYFA_DOSYA, "rb") as f:
                    _sayfa["govde"] = f.read()
                _sayfa["mtime"] = st.st_mtime_ns
        except OSError:
            pass  # okunamazsa eldeki son kopya servis edilir
        return _sayfa["govde"]


class PanelIstek(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "AdaptxPanel/1"
    timeout = 30

    # --- loglama: 30 sn'lik polling journal'ı doldurmasın
    def log_request(self, code="-", size="-"):
        yol = self.path.split("?", 1)[0]
        if str(code).startswith(("2", "3")) and (
                yol in ("/api/durum", "/saglik", "/favicon.ico")
                or yol.startswith("/video/")):  # sarma/atlama başına bir 206 düşer
            return
        BaseHTTPRequestHandler.log_request(self, code, size)

    # --- yanıt yardımcıları
    def _gonder(self, kod, govde, ctype, ek=None):
        self.send_response(kod)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(govde)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (ek or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(govde)

    def _json(self, kod, nesne):
        govde = json.dumps(nesne, ensure_ascii=False).encode("utf-8")
        self._gonder(kod, govde, "application/json; charset=utf-8")

    def _dosya(self, yol, kok, ctype, indirme_adi, inline=True):
        """kok dizini içindeki bir dosyayı akıtarak sun. HTTP Range destekler
        (video sarma/atlama için şart; MemoryMax=256M altında 60MB'lık mp4'ü
        belleğe almadan 64KB'lık parçalarla yazar)."""
        gercek = os.path.realpath(yol)
        if not gercek.startswith(os.path.realpath(kok) + os.sep):
            return self._json(404, {"hata": "bulunamadı"})
        try:
            f = open(gercek, "rb")
        except OSError:
            return self._json(404, {"hata": "dosya bulunamadı"})
        with f:
            boyut = os.fstat(f.fileno()).st_size
            bas, son, kod = 0, boyut - 1, 200
            m = re.fullmatch(r"bytes=(\d*)-(\d*)", (self.headers.get("Range") or "").strip())
            if m and (m.group(1) or m.group(2)) and boyut > 0:
                if m.group(1):
                    bas = int(m.group(1))
                    if m.group(2):
                        son = min(int(m.group(2)), boyut - 1)
                else:                       # "bytes=-N": son N bayt
                    bas = max(0, boyut - int(m.group(2)))
                if bas > son or bas >= boyut:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{boyut}")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                kod = 206
            uzunluk = son - bas + 1 if boyut else 0
            # Türkçe karakterli dosya adları başlıkta latin-1'e sığmaz → RFC 5987
            ascii_ad = indirme_adi.encode("ascii", "ignore").decode() or "dosya"
            utf8_ad = urllib.parse.quote(indirme_adi)
            self.send_response(kod)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(uzunluk))
            self.send_header("Accept-Ranges", "bytes")
            if kod == 206:
                self.send_header("Content-Range", f"bytes {bas}-{son}/{boyut}")
            dispo = "inline" if inline else "attachment"
            self.send_header("Content-Disposition",
                             f'{dispo}; filename="{ascii_ad}"; filename*=UTF-8\'\'{utf8_ad}')
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if self.command == "HEAD":
                return
            f.seek(bas)
            kalan = uzunluk
            while kalan > 0:
                parca = f.read(min(65536, kalan))
                if not parca:
                    break
                self.wfile.write(parca)
                kalan -= len(parca)

    def _pdf(self, yol, indirme_adi):
        return self._dosya(yol, PDF_DIR, "application/pdf", indirme_adi)

    def _video_akit(self, no):
        """Montaj videosunu Drive'dan DOĞRUDAN akıt — diske yazılmaz, önbellek
        yok. HTTP Range, `rclone cat --offset/--count`e çevrilir; tarayıcıda
        sarma/atlama böyle çalışır. Boyut envanterden bilinir (dakikada bir
        tazelenir); eşzamanlılık _video_sem ile sınırlıdır (bellek/CPU)."""
        kayit = _video_envanteri_oku().get(no)
        yol = kayit.get("yol") if isinstance(kayit, dict) else None
        boyut = kayit.get("boyut") if isinstance(kayit, dict) else None
        if not yol or not isinstance(boyut, int) or boyut <= 0:
            return self._json(404, {"hata": "bu siparişin videosu yok"})

        bas, son, kod = 0, boyut - 1, 200
        m = re.fullmatch(r"bytes=(\d*)-(\d*)", (self.headers.get("Range") or "").strip())
        if m and (m.group(1) or m.group(2)):
            if m.group(1):
                bas = int(m.group(1))
                if m.group(2):
                    son = min(int(m.group(2)), boyut - 1)
            else:                       # "bytes=-N": son N bayt
                bas = max(0, boyut - int(m.group(2)))
            if bas > son or bas >= boyut:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{boyut}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            kod = 206

        uzunluk = son - bas + 1
        if self.command != "HEAD" and not _video_sem.acquire(blocking=False):
            return self._json(503, {"hata": "şu an çok fazla video isteği var, birazdan dene"})
        try:
            self.send_response(kod)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Content-Length", str(uzunluk))
            self.send_header("Accept-Ranges", "bytes")
            if kod == 206:
                self.send_header("Content-Range", f"bytes {bas}-{son}/{boyut}")
            self.send_header("Content-Disposition", f'inline; filename="{no}.mp4"')
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if self.command == "HEAD":
                return
            proc = subprocess.Popen(
                [RCLONE, "cat", f"gdrive:{yol}",
                 "--drive-root-folder-id", DRIVE_IN_ID,
                 "--offset", str(bas), "--count", str(uzunluk),
                 "--buffer-size", "1M", "--low-level-retries", "3",
                 "--retries", "1", "--timeout", "3m", "--contimeout", "30s"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            try:
                kalan = uzunluk
                while kalan > 0:
                    parca = proc.stdout.read(min(65536, kalan))
                    if not parca:
                        break  # Drive tarafı erken kapandı — istemci eksikliği fark eder
                    self.wfile.write(parca)
                    kalan -= len(parca)
            finally:
                proc.stdout.close()
                proc.terminate()  # istemci koptuysa rclone'u arkada bırakma
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
        finally:
            if self.command != "HEAD":
                _video_sem.release()

    def _yetkili(self):
        if not AUTH_GEREKLI or self.path.split("?", 1)[0] == "/saglik":
            return True
        h = self.headers.get("Authorization", "")
        if h.startswith("Basic ") and hmac.compare_digest(h[6:].strip(), _AUTH_BEKLENEN):
            return True
        self._gonder(401, b"Yetki gerekli", "text/plain; charset=utf-8",
                     {"WWW-Authenticate": 'Basic realm="Adaptx Panel"'})
        return False

    # --- yönlendirme
    def do_GET(self):
        self._islet()

    def do_HEAD(self):
        self._islet()

    def do_POST(self):
        self._islet()

    def _islet(self):
        try:
            if not self._yetkili():
                return
            parcali = urllib.parse.urlsplit(self.path)
            yol = urllib.parse.unquote(parcali.path)
            sorgu = urllib.parse.parse_qs(parcali.query)

            if self.command in ("GET", "HEAD"):
                if yol == "/":
                    return self._gonder(200, sayfa_govdesi(), "text/html; charset=utf-8")
                if yol == "/saglik":
                    return self._json(200, {"ok": True, "zaman": int(time.time())})
                if yol == "/favicon.ico":
                    return self._gonder(204, b"", "image/x-icon")
                if yol == "/api/durum":
                    return self._json(200, durum_yaniti())
                if yol.startswith("/api/siparis/"):
                    no = yol[len("/api/siparis/"):]
                    if not ORDER_RX.fullmatch(no):
                        return self._json(400, {"hata": "geçersiz sipariş no"})
                    yanit = siparis_yaniti(no, ham_goster=sorgu.get("ham") == ["1"])
                    if yanit is None:
                        return self._json(404, {"hata": "sipariş bulunamadı"})
                    return self._json(200, yanit)
                if yol.startswith("/pdf/siparis/"):
                    no = yol[len("/pdf/siparis/"):]
                    if no.endswith(".pdf"):
                        no = no[:-4]
                    if not ORDER_RX.fullmatch(no):
                        return self._json(400, {"hata": "geçersiz sipariş no"})
                    return self._pdf(os.path.join(ORDER_PDF_DIR, no + ".pdf"), no + ".pdf")
                if yol.startswith("/pdf/ozet/"):
                    kuyruk = yol[len("/pdf/ozet/"):]
                    if not kuyruk.isdigit() or not 1 <= int(kuyruk) <= 500:
                        return self._json(400, {"hata": "geçersiz özet no"})
                    n = int(kuyruk)
                    ad = "siparisler_ozet.pdf" if n == 1 else f"siparisler_ozet_{n}.pdf"
                    return self._pdf(os.path.join(PDF_DIR, ad), ad)
                if yol.startswith("/video/"):
                    no = yol[len("/video/"):]
                    if no.endswith(".mp4"):
                        no = no[:-4]
                    if not ORDER_RX.fullmatch(no):
                        return self._json(400, {"hata": "geçersiz sipariş no"})
                    return self._video_akit(no)
                if yol.startswith("/fbx/"):
                    ad = yol[len("/fbx/"):]
                    # ad = fbx/ içindeki dosyanın birebir adı (boşluk/Türkçe olabilir);
                    # ayraç içeremez, realpath kontrolü _dosya'da ayrıca yapılır.
                    if ("/" in ad or "\\" in ad or ad.startswith(".")
                            or not ad.lower().endswith(".fbx")):
                        return self._json(400, {"hata": "geçersiz dosya adı"})
                    return self._dosya(os.path.join(FBX_DIR, ad), FBX_DIR,
                                       "application/octet-stream", ad, inline=False)
                return self._json(404, {"hata": "bulunamadı"})

            if self.command == "POST":
                if yol not in ("/api/checklist", "/api/not"):
                    return self._json(404, {"hata": "bulunamadı"})
                try:
                    uzunluk = int(self.headers.get("Content-Length") or 0)
                except ValueError:
                    uzunluk = 0
                if not 0 < uzunluk <= 32768:
                    return self._json(400, {"hata": "geçersiz istek gövdesi"})
                try:
                    govde = json.loads(self.rfile.read(uzunluk))
                except Exception:
                    return self._json(400, {"hata": "JSON çözümlenemedi"})
                no = str(govde.get("siparis") or "")
                if not ORDER_RX.fullmatch(no):
                    return self._json(400, {"hata": "geçersiz sipariş no"})
                kayit_sip = siparis_okumasi()["kayitlar"].get(no)
                if kayit_sip is None:
                    return self._json(404, {"hata": "sipariş bulunamadı"})

                if yol == "/api/not":
                    metin = govde.get("metin")
                    if not isinstance(metin, str):
                        return self._json(400, {"hata": "metin dize olmalı"})
                    metin = metin.strip()
                    if len(metin) > NOT_MAX:
                        return self._json(400, {"hata": f"not en fazla {NOT_MAX} karakter"})
                    kayit = not_degistir(no, metin)
                    return self._json(200, {"ok": True, "siparis": no,
                                            "not_metin": kayit["metin"],
                                            "not_zaman": kayit["zaman"]})

                parca = govde.get("parca")
                durum = govde.get("durum")
                if not kayit_sip["data"]:
                    return self._json(400, {"hata": "sipariş henüz işlenmedi"})
                gecerli = parca_anahtarlari(kayit_sip["data"])
                if parca not in gecerli:
                    return self._json(400, {"hata": "geçersiz parça"})
                if not isinstance(durum, bool):
                    return self._json(400, {"hata": "durum true/false olmalı"})
                kayit = checklist_degistir(no, parca, durum)
                checklist = {p: kayit.get(p) for p in gecerli}
                tamam = sum(1 for v in checklist.values() if v)
                return self._json(200, {"ok": True, "siparis": no, "checklist": checklist,
                                        "tamam": tamam, "toplam": len(gecerli)})

            return self._json(405, {"hata": "yöntem desteklenmiyor"})
        except (BrokenPipeError, ConnectionResetError):
            pass  # istemci bağlantıyı kapattı — sorun değil
        except Exception as e:
            print(f"[panel] HATA: {self.command} {self.path}: {e.__class__.__name__}: {e}")
            try:
                self._json(500, {"hata": "sunucu hatası"})
            except Exception:
                pass


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    _cl_yukle()
    _not_yukle()
    sayfa_govdesi()  # panel.html'i baştan yükle (eksikse yer tutucu servis edilir)

    sunucu = ThreadingHTTPServer((HOST, PORT), PanelIstek)
    sunucu.daemon_threads = True

    def durdur(_sig, _frm):
        threading.Thread(target=sunucu.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, durdur)
    signal.signal(signal.SIGINT, durdur)

    kim = "Basic Auth AÇIK" if AUTH_GEREKLI else "şifresiz (LAN)"
    print(f"[panel] Adaptx Panel http://{HOST}:{PORT} — {kim}; taban: {BASE}")
    sunucu.serve_forever()
    print("[panel] durduruldu.")


if __name__ == "__main__":
    sys.exit(main())
