#!/usr/bin/env python3
"""
pdf_uret.py — Adaptx Otonom Kit PDF üretici (sistem python + matplotlib)
=======================================================================

parca_sayim.py'nin ürettiği pdf/<siparis>.json dosyalarını okur ve A4 boyutunda:
  - Her sipariş için  pdf/<siparis>.pdf
  - Özet             pdf/siparisler_ozet.pdf  (sayfa başına 14 sipariş: 7 yan yana,
                     altına 7 daha). 14'ten fazlaysa siparisler_ozet_2.pdf, _3 ...

Ağırlıklı parçalar hücrede "adet / gram" olarak yazılır (ayrı gram bölümü yok).

ÇALIŞTIRMA: python3 pdf_uret.py   (veya bash calistir.sh)
"""

import os
import re
import glob
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Veri klasörü: ADAPTX_BASE (Docker/servis) varsa onu kullan, yoksa scriptin dizini.
# Statik yollar → her makineye/CT'ye uyum (parca_sayim.py ile aynı mantık).
_env_base = os.environ.get("ADAPTX_BASE")
BASE = _env_base if (_env_base and os.path.isdir(_env_base)) else os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(BASE, "pdf")
ORDER_PDF_DIR = os.path.join(PDF_DIR, "siparişler pdf")   # sipariş başına PDF'ler burada
JSON_DIR = os.path.join(BASE, "jsons")
# Bellek: özet sıralaması. Özet, sipariş no'suna göre AZALAN dizilir (en büyük
# numara en başta); manifest her turda bu sırayla yeniden yazılır. parca_sayim.py
# yeni işlenenleri sona ekler; burada sıralama nihai halini alır.
MANIFEST = os.path.join(BASE, "islem_gecmisi.json")

A4 = (8.27, 11.69)          # inch, dikey
ORDERS_PER_BLOCK = 7        # bir tabloda yan yana sipariş
BLOCKS_PER_PAGE = 2         # sayfada alt alta blok → 14 sipariş/sayfa

# (görünen etiket, JSON adet anahtarı)
ROWS = [
    ("Frenli Menteşe", "Frenli Menteşe"),
    ("Frensiz Menteşe", "Frensiz Menteşe"),
    ("Menteşe Tabanı", "Menteşe Tabanı"),
    ("Modül Bağlantı", "Modülleri Birbirine Bağlama"),
    ("Raf Pimi", "Raf Pimi"),
    ("Linco Gövde", "Linco Gövde"),
    ("Linco Kapak", "Linco Kapak"),
    ("Linco Dübel", "Linco Dübel"),
    ("Minifix", "Minifix"),
    ("Uzun Linco Pimi", "Uzun Linco Pimi"),
    ("Ayarlı Ayak", "Ayarlı Ayak"),
    ("Allen", "Allen"),
    ("Tıpa", "Tıpa"),
    ("Kulp", "Kulp"),
    ("Kulp Vidası", "Kulp Vidası"),
    ("L Bağlantı Seti", "L Bağlantı Seti"),
    ("Askılık Flanşı", "Askılık Flanşı"),
    ("Askılık Borusu", "Askılık Borusu"),
    ("Ağaç Vidası", "Ağaç Vidası"),
    ("Arkalık Çivisi", "Arkalık Çivisi"),
]

# Ray Seti satırları buradan SONRA (boy bazında dinamik) eklenir.
RAY_INSERT_AFTER = "L Bağlantı Seti"

# ağırlıklı satır (adet anahtarı) → JSON gram anahtarı
GRAM_KEY = {
    "Raf Pimi": "Raf Pimi",
    "Ağaç Vidası": "Ağaç Vidası",
    "Minifix": "Minifix",
    "Linco Dübel": "Linco Dübel",
    "Linco Gövde": "Linco",
    "Linco Kapak": "Linco Kapak",
    "Arkalık Çivisi": "Çivi",
}


def fmt(v):
    # 0 / None → boş hücre (kullanıcı isteği: sıfır yazma, boş bırak)
    if v is None:
        return ""
    if isinstance(v, (int, float)) and v == 0:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def cell_value(d, key):
    # Ray Seti satırları: key = ("ray", "55cm") → o boydaki set adedi
    if isinstance(key, tuple) and key[0] == "ray":
        return fmt((d.get("ray_setleri") or {}).get(key[1], 0))
    s = fmt(d["adet"].get(key))
    if s == "":          # adet 0/None → hücre tamamen boş ("/ gram" da yazma)
        return ""
    if key in GRAM_KEY:
        g = d.get("gram", {}).get(GRAM_KEY[key])
        if g is not None:
            s = f"{s} / {fmt(g)}"
    return s


def _cm(label):
    """"55cm" → 55 (sıralama için)."""
    return int("".join(ch for ch in label if ch.isdigit()) or 0)


def ray_labels(order_keys, data):
    """Verilen siparişlerde geçen ray boylarını (büyükten küçüğe) döndürür."""
    lengths = set()
    for k in order_keys:
        for L, c in (data[k].get("ray_setleri") or {}).items():
            if c:
                lengths.add(L)
    return sorted(lengths, key=_cm, reverse=True)


def build_rows(order_keys, data):
    """ROWS'a, RAY_INSERT_AFTER'dan sonra boy bazında Ray Seti satırları ekler.
    Bu siparişlerde hiç ray yoksa tek bir 'Ray Seti' (0) satırı gösterir."""
    rays = ray_labels(order_keys, data)
    rows = []
    for disp, key in ROWS:
        rows.append((disp, key))
        if disp == RAY_INSERT_AFTER:
            if rays:
                for L in rays:
                    rows.append((f"Ray Seti {L}", ("ray", L)))
            else:
                rows.append(("Ray Seti", ("ray", None)))
    return rows


def load_manifest():
    try:
        with open(MANIFEST, encoding="utf-8") as f:
            return list(json.load(f).get("siralama", []))
    except (FileNotFoundError, ValueError):
        return []


def save_manifest(order_list):
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump({"siralama": order_list}, f, ensure_ascii=False, indent=2)


def _no_key(no):
    """'9304-1' → (9304, 1); sayısal sıralama anahtarı."""
    m = re.match(r"^(\d+)(?:-(\d+))?$", str(no))
    if not m:
        return (0, 0)
    return (int(m.group(1)), int(m.group(2) or 0))


def ordered_keys(data):
    """Siparişleri numaraya göre AZALAN dizer (en büyük numara en başta —
    kullanıcı isteği). Araya sonradan eklenen sipariş (ör. 9265, 9259 ile 9270
    arasına) özet düzeninde doğru yere oturur; özet zaten her turda baştan
    üretildiği için kayan sayfalar kendiliğinden yenilenir. Manifest de bu
    sırayla yazılır ki panel'in özet-sayfa numarası hesabı tutarlı kalsın."""
    manifest = load_manifest()
    ordered = sorted(data, key=_no_key, reverse=True)
    if ordered != manifest:
        save_manifest(ordered)
    return ordered


def load_orders():
    data = {}
    for p in sorted(glob.glob(os.path.join(JSON_DIR, "*.json"))):
        try:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
        except Exception as e:
            print(f"  [atla] {p}: {e}")
            continue
        key = str(d.get("siparis") or os.path.splitext(os.path.basename(p))[0])
        data[key] = d
    return data


def _draw_table(ax, order_keys, data, fontsize):
    ax.axis("off")
    col_labels = ["Parça"] + [str(k) for k in order_keys]
    cell_rows = [[disp] + [cell_value(data[k], key) for k in order_keys]
                 for disp, key in build_rows(order_keys, data)]

    tbl = ax.table(cellText=cell_rows, colLabels=col_labels,
                   cellLoc="center", bbox=[0, 0, 1, 1])
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(fontsize)

    ncol = len(col_labels)
    w0 = 0.34 if ncol <= 2 else 0.24
    wrest = (1 - w0) / (ncol - 1)
    for (r, c), cell in tbl.get_celld().items():
        cell.set_width(w0 if c == 0 else wrest)
        cell.set_edgecolor("#c2ccd4")
        if r == 0:
            cell.set_facecolor("#2f4858")
            cell.get_text().set_color("white")
            cell.set_text_props(fontweight="bold")
        else:
            if c == 0:
                cell.get_text().set_ha("left")
                cell.set_text_props(fontweight="bold")
            elif r % 2 == 0:
                cell.set_facecolor("#f4f7f9")


def render_order(path, k, data):
    fig = plt.figure(figsize=A4)
    fig.suptitle(f"Adaptx Kit — Sipariş {k}", fontsize=14, fontweight="bold", y=0.97)
    ax = fig.add_axes([0.18, 0.12, 0.64, 0.80])
    _draw_table(ax, [k], data, fontsize=10)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"   >> {path}")


def render_summary_page(path, blocks, data, title):
    fig = plt.figure(figsize=A4)
    fig.suptitle(title, fontsize=14, fontweight="bold", y=0.985)
    if len(blocks) == 1:
        rects = [[0.05, 0.28, 0.90, 0.62]]
    else:
        rects = [[0.05, 0.525, 0.90, 0.40], [0.05, 0.055, 0.90, 0.40]]
    for blk, rect in zip(blocks, rects):
        ax = fig.add_axes(rect)
        _draw_table(ax, blk, data, fontsize=7.5)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"   >> {path}")


def main():
    data = load_orders()
    if not data:
        print(f"!! {PDF_DIR} içinde JSON yok. Önce parca_sayim.py çalıştır.")
        return

    orders = ordered_keys(data)      # no'ya göre azalan (en büyük en başta)
    print(f"== pdf_uret: {len(orders)} sipariş ({orders})")

    # 1) Sipariş başına → "siparişler pdf" alt klasörü. Zaten üretilmiş olanlar
    #    atlanır (bellek): yalnızca yeni siparişlerin PDF'i oluşturulur.
    os.makedirs(ORDER_PDF_DIR, exist_ok=True)
    yeni = 0
    for k in orders:
        p = os.path.join(ORDER_PDF_DIR, f"{k}.pdf")
        if os.path.exists(p):
            continue
        render_order(p, k, data)
        yeni += 1
    print(f"   sipariş PDF: {yeni} yeni, {len(orders) - yeni} atlandı (zaten var)")

    # 2) Özet: her zaman baştan üretilir (araya giren sipariş doğru yere oturur).
    #    Bayat özet sayfalarını temizle (sipariş sayısı azaldığında kalıntı olmasın).
    for old in glob.glob(os.path.join(PDF_DIR, "siparisler_ozet*.pdf")):
        try:
            os.remove(old)
        except OSError:
            pass

    # 7'lik bloklar → sayfa başına 2 blok (14 sipariş)
    blocks = [orders[i:i + ORDERS_PER_BLOCK]
              for i in range(0, len(orders), ORDERS_PER_BLOCK)]
    pages = [blocks[i:i + BLOCKS_PER_PAGE]
             for i in range(0, len(blocks), BLOCKS_PER_PAGE)]
    for pi, page in enumerate(pages):
        name = "siparisler_ozet.pdf" if pi == 0 else f"siparisler_ozet_{pi + 1}.pdf"
        title = "Adaptx Kit — Sipariş Özeti" + ("" if pi == 0 else f" ({pi + 1})")
        render_summary_page(os.path.join(PDF_DIR, name), page, data, title)


if __name__ == "__main__":
    main()
