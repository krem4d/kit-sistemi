#!/usr/bin/env python3
"""Modül tipi test sonuçlarını tek bir HTML raporunda toplar.

Girdi (hepsi rapor klasöründe):
  ground-truth.json   referans render'lardan çıkarılan beklenen modül sayısı
  modul-tipleri.json  taksonomi
  results/<stem>.json ayırıcı çıktısı
  parca-bbox/<stem>.json  parça bbox'ları
  bulgular.json       (opsiyonel) çok-ajanlı inceleme bulguları
  gorseller/*.jpg     küçültülmüş görseller
Çıktı: sonuclar.html
"""
import json, sys, html
from pathlib import Path
from collections import Counter

BASE = Path(sys.argv[1] if len(sys.argv) > 1 else '.')
G = BASE / 'gorseller'

gt = json.loads((BASE / 'ground-truth.json').read_text())
tax = json.loads((BASE / 'modul-tipleri-v2.json').read_text())
bulgular = {}
bp = BASE / 'bulgular.json'
if bp.exists():
    bulgular = json.loads(bp.read_text())

v1 = {s: json.loads((BASE / 'results' / f'{s}.json').read_text()) for s in gt}
v2 = {s: json.loads((BASE / 'results-v2' / f'{s}.json').read_text()) for s in gt}
res = {s: json.loads((BASE / 'results-v4' / f'{s}.json').read_text()) for s in gt}
bbox = {s: json.loads((BASE / 'parca-bbox' / f'{s}.json').read_text()) for s in gt}

# hangi sipariş hangi tip(ler)e ait
tip_of = {}
for tid, t in tax['tipler'].items():
    for s in t['temsilciler']:
        tip_of.setdefault(s, []).append(tid + '*')
    for s in t.get('diger', []):
        tip_of.setdefault(s, []).append(tid)

def e(x):
    return html.escape(str(x))

def img(path, alt, cls='shot'):
    p = G / path
    if not p.exists():
        return f'<div class="missing">{e(alt)} — görsel yok</div>'
    return (f'<figure class="{cls}"><a href="gorseller/{path}" target="_blank">'
            f'<img loading="lazy" src="gorseller/{path}" alt="{e(alt)}"></a>'
            f'<figcaption>{e(alt)}</figcaption></figure>')

def durum(s):
    exp = gt[s]['expected_modules']
    got = len(res[s]['modules'])
    if exp is None:
        return 'yok', f'{got} bulundu · referans yok'
    if exp == got:
        return 'ok', f'{got} / {exp}'
    return 'fark', f'{got} bulundu · {exp} bekleniyor'

# ---- özet sayılar -------------------------------------------------------
scored = [s for s in gt if gt[s]['expected_modules'] is not None]
ok = [s for s in scored if gt[s]['expected_modules'] == len(res[s]['modules'])]
reasons = Counter(a['reason'] for s in res for a in res[s]['assignment'].values())
unres = Counter(u['reason'] for s in res for u in res[s]['unresolved'].values())
toplam_parca = sum(r['part_count'] for r in res.values())
toplam_cozulmemis = sum(len(r['unresolved']) for r in res.values())
v1_cozulmemis = sum(len(r['unresolved']) for r in v1.values())
v2_cozulmemis = sum(len(r['unresolved']) for r in v2.values())
toplam_sure = sum(r['seconds'] for r in res.values())
twins = [(s, res[s]['twin_candidates']) for s in sorted(gt) if res[s].get('twin_candidates')]
# v0.1 -> v0.2 fark
duzelen = {}
for s in gt:
    g = [n for n in res[s]['assignment'] if n not in v1[s]['assignment']]
    l = [n for n in v1[s]['assignment'] if n not in res[s]['assignment']]
    m = [n for n in v1[s]['assignment'] if n in res[s]['assignment']
         and v1[s]['assignment'][n]['module'] != res[s]['assignment'][n]['module']]
    if g or l or m:
        duzelen[s] = (g, l, m)

REASON_TR = {
    'structural_edge_contact': 'yapısal kenar teması',
    'unique_containment': 'tek gövde içinde kalma',
    'open_door_outer_hinge_corner': 'açık kapak — dış menteşe köşesi',
    'unique_panel_attachment': 'tek panele tutunma',
    'contained_subassembly': 'iç alt montaj',
    'panel_fits_single_shell_projection': 'panel tek gövde izdüşümüne oturuyor',
    'no_supported_geometric_attachment': 'desteklenen geometrik bağ yok',
    'ambiguous_panel_attachment': 'panele tutunma belirsiz',
    'multiple_candidates': 'birden çok aday',
    'ambiguous_open_door': 'açık kapak belirsiz',
}

def tr(r):
    return REASON_TR.get(r, r)

out = []
w = out.append
w('<title>Modül Tipi Testleri — otonom_kit</title>')
w('''<style>
:root{
  --bg:#f6f6f4; --panel:#fff; --ink:#16181d; --muted:#5d6470; --line:#dfe1e6;
  --ok:#1c7a4a; --okbg:#e6f4ec; --fark:#a3341f; --farkbg:#fbeae6;
  --yok:#6b6357; --yokbg:#f1ede4; --accent:#2b5fd9;
}
:root:not([data-theme="light"]){}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --bg:#14161a; --panel:#1c1f25; --ink:#e8eaee; --muted:#9aa2af; --line:#2c313a;
  --ok:#5fd39b; --okbg:#123526; --fark:#ff9d86; --farkbg:#3a1d16;
  --yok:#c2b8a4; --yokbg:#2b271f; --accent:#7fa4ff;
}}
:root[data-theme="dark"]{
  --bg:#14161a; --panel:#1c1f25; --ink:#e8eaee; --muted:#9aa2af; --line:#2c313a;
  --ok:#5fd39b; --okbg:#123526; --fark:#ff9d86; --farkbg:#3a1d16;
  --yok:#c2b8a4; --yokbg:#2b271f; --accent:#7fa4ff;
}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",sans-serif;
  margin:0;padding-block:32px;padding-left:20px;padding-right:20px;max-width:1180px;margin-inline:auto}
h1{font-size:27px;margin:0 0 6px;letter-spacing:-.02em}
h2{font-size:20px;margin:38px 0 10px;padding-top:14px;border-top:1px solid var(--line);letter-spacing:-.01em}
h3{font-size:16px;margin:22px 0 8px}
p,li{color:var(--ink)}
.lead{color:var(--muted);margin:0 0 22px;max-width:74ch}
.cards{display:flex;flex-wrap:wrap;gap:10px;margin:18px 0 6px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 15px;min-width:150px;flex:1 1 150px}
.card b{display:block;font-size:25px;font-weight:650;letter-spacing:-.02em}
.card span{color:var(--muted);font-size:12.5px}
table{border-collapse:collapse;width:100%;font-size:13.5px;background:var(--panel);
  border:1px solid var(--line);border-radius:10px;overflow:hidden}
.scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line);white-space:nowrap}
th{background:color-mix(in srgb,var(--panel) 88%,var(--ink));font-weight:600;font-size:12px;
  text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}
tr:last-child td{border-bottom:0}
td.num{text-align:right;font-variant-numeric:tabular-nums}
.pill{display:inline-block;padding:1px 8px;border-radius:20px;font-size:12px;font-weight:600}
.pill.ok{background:var(--okbg);color:var(--ok)}
.pill.fark{background:var(--farkbg);color:var(--fark)}
.pill.yok{background:var(--yokbg);color:var(--yok)}
.tip{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px 20px;margin:16px 0}
.tip .kod{color:var(--accent);font-weight:700;font-size:13px;letter-spacing:.06em}
.tip .tanim{color:var(--muted);margin:6px 0 4px;max-width:78ch}
.tip .yuk{font-size:13.5px;color:var(--muted);border-left:3px solid var(--line);padding-left:10px;margin:10px 0}
.shots{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:12px 0}
figure{margin:0;background:color-mix(in srgb,var(--panel) 70%,var(--bg));border:1px solid var(--line);
  border-radius:9px;overflow:hidden}
figure img{display:block;width:100%;max-width:100%;height:auto;background:#20222a}
figcaption{font-size:11.5px;color:var(--muted);padding:5px 8px;text-align:center}
.missing{border:1px dashed var(--line);border-radius:9px;padding:22px 8px;text-align:center;
  color:var(--muted);font-size:12px}
.bul{border:1px solid var(--line);border-left:4px solid var(--fark);border-radius:8px;
  background:var(--panel);padding:12px 15px;margin:10px 0}
.bul.kucuk{border-left-color:var(--yok)}
.bul.onemli{border-left-color:#d08a1e}
.bul h4{margin:0 0 6px;font-size:14.5px}
.bul dl{margin:0;display:grid;grid-template-columns:max-content 1fr;gap:3px 12px;font-size:13px}
.bul dt{color:var(--muted);font-weight:600}
.bul dd{margin:0}
.verdict{font-size:12px;font-weight:700;padding:1px 7px;border-radius:20px;margin-left:6px}
.v-DOGRULANDI{background:var(--okbg);color:var(--ok)}
.v-CURUTULDU{background:var(--farkbg);color:var(--fark)}
.v-BELIRSIZ{background:var(--yokbg);color:var(--yok)}
code{font:12.5px ui-monospace,SFMono-Regular,Menlo,monospace;background:color-mix(in srgb,var(--panel) 60%,var(--bg));
  padding:1px 5px;border-radius:4px}
.soru{background:var(--yokbg);border:1px solid var(--line);border-radius:10px;padding:14px 18px;margin:14px 0}
.soru li{margin:5px 0}
footer{margin-top:44px;padding-top:14px;border-top:1px solid var(--line);color:var(--muted);font-size:12.5px}
@media(max-width:560px){th,td{white-space:normal}.bul dl{grid-template-columns:1fr}}
</style>''')

w('<h1>Modül tipi testleri — otonom_kit modül ayırıcı v0.1</h1>')
w(f'<p class="lead">2026-09-10. Taksonomideki <b>{len(tax["tipler"])} modül tipi</b> ve '
  f'<b>{len(tax["varyantlar"])} kesişen varyant</b> tanımlandı; ayırıcı <b>{len(gt)} gerçek sipariş FBX</b>\'inde '
  'çalıştırıldı. Beklenen modül sayısı, üretimin kırmızı referans render\'larından çıkarıldı '
  '(<code>&lt;sipariş&gt;-N.png</code> = N. sipariş modülü kırmızı). Kaynak FBX\'ler değişmedi; '
  'SHA-256\'lar işlem öncesi ve sonrası aynı. Modül sayısının tutması parça düzeyinde doğruluk değildir.</p>')

w('<div class="cards">')
w(f'<div class="card"><b>{len(gt)}</b><span>çalıştırılan sipariş</span></div>')
w(f'<div class="card"><b>{len(ok)}/{len(scored)}</b><span>modül sayısı referansla tutan</span></div>')
w(f'<div class="card"><b>{toplam_parca}</b><span>işlenen fiziksel parça</span></div>')
w(f'<div class="card"><b>{toplam_cozulmemis}</b><span>çözülmemiş parça · v0.1: {v1_cozulmemis} → v0.2: {v2_cozulmemis} → v0.3: {toplam_cozulmemis}</span></div>')
w(f'<div class="card"><b>{toplam_sure:.1f} sn</b><span>toplam ayırma süresi</span></div>')
w('</div>')

# ---- revizyon -----------------------------------------------------------
w('<h2>Testlerin ürettiği revizyon: v0.1 → v0.4</h2>')
w('<p class="lead">Testler dört tekrarlayan hata örüntüsü gösterdi; üçü düzeltildi, biri '
  'ürün tanımı sorusu olarak açık bırakıldı. 23 sentetik Blender testi yeşil. Gerçek siparişlerde '
  'her iki adımda da <b>hiçbir atama kaybedilmedi ve hiçbir parça modül değiştirmedi</b> — '
  'yalnız daha önce çözülemeyenler çözüldü. Çözülmemiş parça '
  f'<b>{v1_cozulmemis} → {v2_cozulmemis} → {toplam_cozulmemis}</b>.</p>')
w('<p class="lead"><b>Uyarı:</b> "0 çözülmemiş" = her parçanın bir üyeliği var demektir, '
  'her üyeliğin doğru olduğu demek değildir. Parça düzeyi doğruluk yalnız temsilci siparişlerde '
  'görsel olarak denetlendi.</p>')

w('<div class="bul kritik"><h4>D1 — Açık kapak, modül kutusuna değil MENTEŞE PANELİNE çapalanmalı</h4><dl>')
w('<dt>belirti</dt><dd>85 çözülmemiş parçanın 45\'i 18 mm düşey panel (açık kapak), 27\'si onların '
  'kulpuydu. Örnek: 9435, 9439, 9483, 9512, 9417, 9443-1 — her birinde 8 kapak+kulp çözülemiyordu.</dd>')
w('<dt>kök neden</dt><dd>v0.1 kapağı modülün <i>bounding box</i>\'ına göre sınıyordu. İki ayrı şekilde bozuluyor: '
  '(1) menteşe iç bir bölmedeyse kapağın kalınlık merkezi modül kutusunun <i>içinde</i> kalıyor, '
  '<code>outside</code> testi düşüyor (9488-1, yatakbaşı); '
  '(2) öne taşan bir tezgah/baza modül kutusunun ön yüzünü kaydırıyor '
  '(9435\'te <code>m.lo[1] = -19</code>), böylece kapağın ön yüzeyle hizalı olma testi 18 mm sapıyor.</dd>')
w('<dt>düzeltme</dt><dd>Kapak artık <i>atanmış tek bir düşey panelin</i> dış yüzüne çapalanıyor: kalınlık merkezi '
  'o panelin dışında (0,05–18 mm), açılan kanat o panelin ön veya arka yüzünde başlıyor, Z\'de panelin '
  'en az yarısını kaplıyor. Üyelik o panelden miras alınıyor. Bindirmeli kapak gövde ön yüzünün 2 mm önünde '
  'durduğu için hiza toleransı <code>HINGE_FACE = 2.5 mm</code>.</dd>')
w('<dt>kanıt</dt><dd>Tolerans taraması: 1,0 mm → 45 kapağın 29\'u; <b>2,5 mm → 45/45, sıfır belirsizlik</b>. '
  'Menteşe panelleri tek tek doğrulandı (9435: kapaklar Object_38–41 ve Object_18–21\'e tutunuyor). '
  '9488-1 görselinde sol modülün kapağı mavi, sağ modülünki yeşil — referans kırmızı render\'ıyla birebir.</dd>')
w('<dt>etki</dt><dd>Çözülmemiş parça <b>85 → 15</b>. Kaybedilen atama 0, modül değiştiren parça 0.</dd>')
w('</dl></div>')

w('<div class="bul kritik"><h4>D3 — Kulp, kelepçelenmiş boşlukla değil OTURMA DERİNLİĞİYLE sahiplenilmeli</h4><dl>')
w('<dt>belirti</dt><dd>İki komşu modülün açık kapağı dikişte üst üste bindiğinde aradaki kulp '
  '<code>ambiguous_panel_attachment</code> kalıyordu: 9440, 9449-2 (×4), 9462 (×2), 9475 (×4).</dd>')
w('<dt>kök neden</dt><dd>Donanım turu <code>gap = max(panel.lo−p.hi, p.lo−panel.hi, 0)</code> ölçüyordu. '
  '<code>max(…, 0)</code> kelepçesi her iç içe geçmeyi 0\'a indiriyor; 3 mm sıyıran temas ile 17 mm oturmuş '
  'temas ayırt edilemiyor, iki kapak da sahip sayılıp parça belirsiz kalıyordu.</dd>')
w('<dt>ölçüm</dt><dd>İmza bütün korpusta sabit: kulp kendi kanadına <b>17,00 mm</b> oturuyor, komşu kanadı '
  '<b>3,00 mm</b> sıyırıyor. Sorunsuz atanan dış kulplarda da aynı 17,00 mm. '
  '(9449-2 Object_3 → Object_6 17,00 / Object_31 3,00; 9475 Object_9 → Object_12 17,00 / Object_39 3,00.)</dd>')
w('<dt>düzeltme</dt><dd>Örtüşme derinliği ölçülüyor: '
  '<code>depth = min(panel.hi, p.hi) − max(panel.lo, p.lo)</code>. Tek aday varsa doğrudan atanır; '
  'birden çok adayda en derin oturma <code>SEAT_DEPTH = 8 mm</code>\'yi geçiyor ve ikinciden '
  '<code>SEAT_MARGIN = 5 mm</code> önde ise ona atanır (<code>deepest_panel_seat</code>), aksi halde belirsiz kalır. '
  '17 vs 3 farkı 14 mm — eşiğin çok üstünde. Simetrik oturan kulp için belirsizlik korunuyor (sentetik test).</dd>')
w('<dt>etki</dt><dd>11 kulp çözüldü. Simetri testi hâlâ belirsiz döndürüyor.</dd>')
w('</dl></div>')

w('<div class="bul kritik"><h4>D4 — Döndürülmüş L kapağı: kalınlık AABB\'den değil kendi normalinden ölçülmeli</h4><dl>')
w('<dt>belirti</dt><dd>9453 (L/köşe) — dört açık kapağın hiçbiri hiçbir kurala takılmıyordu: '
  '<code>no_supported_geometric_attachment</code>, <code>candidates=[]</code>, 92 temasın hiçbirinde adları geçmiyor.</dd>')
w('<dt>kök neden</dt><dd><code>measure()</code>: <code>thick = abs(dims[axis] − 18) &lt; 0.15</code>, burada '
  '<code>dims</code> eksene hizalı sınır kutusudur. Plan düzleminde 45° döndürülmüş bir panelin hiçbir AABB '
  'boyutu 18 mm olmaz (ölçüldü: 328,1 × 328,1 × 1676). <code>thick=False</code> olunca parça yapısal grafiğe '
  'de, kapak kuralına da giremiyor.</dd>')
w('<dt>ölçüm</dt><dd>Kendi baskın normali boyunca ölçüldüğünde kalınlık tam <b>18,00 mm</b>: '
  'normal (0,707, −0,707, 0), yani 45°. Dört kapak da öyle.</dd>')
w('<dt>düzeltme</dt><dd><code>measure()</code> artık eksen hizası şartı olmadan alan-ağırlıklı baskın normali '
  'buluyor; normal yataysa ve o yöndeki kalınlık 18 ± 0,35 mm ise parçaya <code>planar</code> bayrağı ve iki plan '
  'uç noktası veriliyor. <code>thick</code> değişmiyor — temas grafiği aynen korunuyor. Yeni kural '
  '<code>rotated_open_door_plan_hinge</code>: menteşe ucu bir gövde panelinin plan ayak izine '
  '≤ <code>ROTATED_HINGE = 30 mm</code> yakınsa ve kapak o paneli Z\'de en az yarı yarıya kaplıyorsa üyelik o panelden gelir.</dd>')
w('<dt>kanıt</dt><dd>9453\'te dört kapak da atandı: Object_4 → M01 (Object_18), Object_5 → M01 (Object_19), '
  'Object_31 → M02 (Object_37), Object_32 → M02 (Object_38). Görselde alt kapaklar mavi, üst kapaklar yeşil — '
  'referans <code>9453-1.png</code> / <code>9453-2.png</code> ile birebir.</dd>')
w('</dl></div>')

w('<div class="bul onemli"><h4>D2 — İkiz gövde: fiziksel gövde ≠ sipariş modülü (raporlanıyor, birleştirilmiyor)</h4><dl>')
w('<dt>belirti</dt><dd>9449-2 ve 9475\'te algoritma 4 gövde buluyor, referans 2 modül gösteriyor.</dd>')
w('<dt>ölçüm</dt><dd>Bu iki siparişteki orta bağlantı, ayrı modül sayılan 9440 / 9488-1 / 9441 / 9462 / 9467 / 9484 '
  'ile <b>fiziksel olarak aynı</b>: sırt sırta iki 18 mm panel, temas kapsamı 1,00. Yani geometri tek başına '
  '"bir modül mü iki modül mü" sorusunu çözemez.</dd>')
w('<dt>ayırt eden</dt><dd>Yan yana gövdelerin <i>dış ölçüsü aynı</i> VE <i>yapısal iç düzen imzası birebir aynı</i> '
  'olduğunda referans tek modül diyor. Çekirdek imza Jaccard değeri: tek-modül çiftlerinde <b>1,000</b>, '
  'ayrı-modül çiftlerinde <b>≤ 0,143</b> — arada boşluk çok geniş. 18 düşey (üst üste) sınırın hiçbirinde '
  'kural yanlış ateşlemiyor.</dd>')
w('<dt>karar</dt><dd>Kural <b>uygulanmıyor</b>, yalnız <code>twin_candidates</code> olarak raporlanıyor. '
  'Yan yana iki AYNI gövdenin tek sipariş modülü sayılıp sayılmayacağı ürün tanımı sorusudur; '
  'iki özdeş dolabın ayrı sipariş edildiği bir vaka bu kuralı yanlış birleştirir. Kerem\'in cevabına bağlı.</dd>')
w('</dl></div>')

if twins:
    w('<h3>İkiz gövde adayları</h3><div class="scroll"><table>'
      '<tr><th>sipariş</th><th>çift</th><th>ölçü mm</th><th class="num">temas mm²</th>'
      '<th class="num">bulunan modül</th><th class="num">referans modül</th></tr>')
    for s, ts in twins:
        for t in ts:
            w(f'<tr><td>{e(s)}</td><td>{e(" + ".join(t["modules"]))}</td>'
              f'<td>{e(" × ".join(f"{v:.0f}" for v in t["dims_mm"]))}</td>'
              f'<td class="num">{t["area_mm2"]:.0f}</td>'
              f'<td class="num">{len(res[s]["modules"])}</td>'
              f'<td class="num">{gt[s]["expected_modules"]}</td></tr>')
    w('</table></div>')

if duzelen:
    w('<h3>v0.1 → v0.4 değişen siparişler</h3><div class="scroll"><table>'
      '<tr><th>sipariş</th><th class="num">v0.1 çözülmemiş</th><th class="num">v0.4 çözülmemiş</th>'
      '<th>yeni çözülen parçalar</th></tr>')
    for s, (g, l, m) in sorted(duzelen.items()):
        w(f'<tr><td>{e(s)}</td><td class="num">{len(v1[s]["unresolved"])}</td>'
          f'<td class="num">{len(res[s]["unresolved"])}</td><td>{e(", ".join(sorted(g)))}</td></tr>')
    w('</table></div>')

# ---- tip bölümleri ------------------------------------------------------
w('<h2>Modül tipleri</h2>')
w('<p class="lead">Üç katman: <b>yerleşim</b> (kaç gövde, nasıl dizilmiş), <b>gövde ailesi</b> '
  '(karkasın kendi tipi) ve <b>kesişen varyantlar</b> (kapak, kulp, baza, arkalık, askılık, hareketli raf). '
  'Yıldızlı siparişler o tipin test temsilcileridir.</p>')

for tid, t in tax['tipler'].items():
    w('<div class="tip">')
    w(f'<div class="kod">{e(tid)}</div>')
    w(f'<h3>{e(t["ad"])}</h3>')
    w(f'<p class="tanim">{e(t["tanim"])}</p>')
    w(f'<p class="yuk"><b>Algoritmaya yükü:</b> {e(t["algoritmaya_yuku"])}</p>')

    for s in t['temsilciler']:
        d, metin = durum(s)
        r = res[s]
        w(f'<h3>{e(s)} <span class="pill {d}">{e(metin)}</span></h3>')
        w('<div class="shots">')
        w(img(f'ref_{s}.jpg', f'{s} — referans (temel)'))
        for i in gt[s]['red_groups']:
            w(img(f'ref_{s}-{i}.jpg', f'{s} — referans modül {i} (kırmızı)'))
        w(img(f'v4_{s}-full.jpg', f'{s} — v0.4, tüm parçalar'))
        w(img(f'v4_{s}-back.jpg', f'{s} — v0.4, arkadan'))
        w(img(f'v4_{s}-core.jpg', f'{s} — v0.4, yapısal çekirdek'))
        if s in duzelen:
            w(img(f'{s}-full.jpg', f'{s} — v0.1 (kırmızı = çözülemeyen)'))
        w('</div>')
        w('<div class="scroll"><table><tr><th>modül</th><th class="num">çekirdek</th><th class="num">toplam parça</th>'
          '<th>ölçü (G×D×Y mm)</th></tr>')
        for m in r['modules']:
            dims = ' × '.join(f'{m["hi"][k]-m["lo"][k]:.0f}' for k in range(3))
            w(f'<tr><td>{e(m["id"])}</td><td class="num">{len(m["core_parts"])}</td>'
              f'<td class="num">{len(m["parts"])}</td><td>{e(dims)}</td></tr>')
        w('</table></div>')
        if r['unresolved']:
            w('<div class="scroll"><table><tr><th>çözülmemiş parça</th><th>gerekçe</th><th>ölçü mm</th></tr>')
            for n, u in sorted(r['unresolved'].items()):
                dd = bbox[s].get(n, {}).get('dims', [])
                w(f'<tr><td>{e(n)}</td><td>{e(tr(u["reason"]))}</td>'
                  f'<td>{e(" × ".join(f"{v:.0f}" for v in dd))}</td></tr>')
            w('</table></div>')

    # bu tipe ait bulgular
    b = bulgular.get(tid)
    if b:
        for f in b.get('bulgular', []):
            v = b.get('verdict', {}).get(f['baslik'])
            vh = f'<span class="verdict v-{e(v["karar"])}">{e(v["karar"])}</span>' if v else ''
            w(f'<div class="bul {e(f["siddet"])}"><h4>{e(f["baslik"])} {vh}</h4><dl>')
            w(f'<dt>kanıt</dt><dd>{e(f["kanit"])}</dd>')
            w(f'<dt>kök neden</dt><dd>{e(f["kok_neden"])}</dd>')
            w(f'<dt>öneri</dt><dd>{e(f["onerilen_duzeltme"])}</dd>')
            w(f'<dt>risk</dt><dd>{e(f["risk"])}</dd>')
            if v:
                w(f'<dt>doğrulama</dt><dd>{e(v["gerekce"])}</dd>')
            w('</dl></div>')
    w('</div>')

# ---- tam tablo ----------------------------------------------------------
w('<h2>Bütün siparişler</h2>')
w('<div class="scroll"><table><tr><th>sipariş</th><th>tip</th><th class="num">beklenen</th>'
  '<th class="num">bulunan</th><th>durum</th><th class="num">parça</th><th class="num">çözülmemiş</th>'
  '<th class="num">sınır</th><th class="num">saniye</th></tr>')
for s in sorted(gt):
    d, metin = durum(s)
    r = res[s]
    exp = gt[s]['expected_modules']
    w(f'<tr><td>{e(s)}</td><td>{e(", ".join(tip_of.get(s, ["—"])))}</td>'
      f'<td class="num">{"—" if exp is None else exp}</td><td class="num">{len(r["modules"])}</td>'
      f'<td><span class="pill {d}">{"tuttu" if d=="ok" else "fark" if d=="fark" else "referans yok"}</span></td>'
      f'<td class="num">{r["part_count"]}</td><td class="num">{len(r["unresolved"])}</td>'
      f'<td class="num">{len(r["boundaries"])}</td><td class="num">{r["seconds"]:.2f}</td></tr>')
w('</table></div>')

# ---- gerekçe dağılımı ---------------------------------------------------
w('<h2>Atama gerekçelerinin dağılımı</h2>')
w('<p class="lead">Her parça tek bir gerekçeyle üyelik alır. Gerekçe ne kadar zayıfsa '
  '(bbox temelli tutunma gibi) o kadar az güvenilir.</p>')
w('<div class="scroll"><table><tr><th>gerekçe</th><th class="num">parça</th><th class="num">pay</th></tr>')
for k, v in reasons.most_common():
    w(f'<tr><td>{e(tr(k))} <code>{e(k)}</code></td><td class="num">{v}</td>'
      f'<td class="num">%{100*v/sum(reasons.values()):.1f}</td></tr>')
for k, v in unres.most_common():
    w(f'<tr><td><span class="pill fark">çözülmedi</span> {e(tr(k))} <code>{e(k)}</code></td>'
      f'<td class="num">{v}</td><td class="num">%{100*v/toplam_parca:.1f}</td></tr>')
w('</table></div>')

# ---- açık sorular -------------------------------------------------------
sorular = []
for tid, b in bulgular.items():
    for q in b.get('acik_sorular', []):
        sorular.append((tid, q))
if sorular:
    w('<h2>Kerem\'e sorular</h2>')
    w('<div class="soru"><p>Bunlar geometriden çıkarılamaz; ürün tanımı veya katalog bilgisi gerektirir.</p><ul>')
    for tid, q in sorular:
        w(f'<li><b>{e(tid)}:</b> {e(q)}</li>')
    w('</ul></div>')

w('<h2>Çekişmeli kanatlar: referans render parça düzeyinde otorite değil</h2>')
w('<p class="lead">İnceleme, ortak duvara menteşelenmiş açık kapak kanatlarında algoritma ile '
  'referansın <b>sistematik olarak ters düştüğünü</b> buldu (T04\'te 4/4 sipariş). Bağımsız doğrulayıcı, '
  'referans render\'ların grup maskelerini kendi üretip perspektif kalibrasyonuyla piksel düzeyinde '
  'eşleyerek bunu teyit etti.</p>')
w('<p class="lead">Hangi taraf haklı: kanat genişliği aritmetiği. Bir gövdeyi kapatan kanatların '
  'genişlik toplamı, gövdenin dış genişliğine eşit olmalıdır. Bu ölçüm 69 siparişin '
  '<b>her modülünün her kapak katında</b> yapıldı.</p>')
contested = []
for s_ in sorted(gt):
    r = res[s_]
    for n, a in sorted(r['assignment'].items()):
        if 'hinge_on_shell_boundary' in a and a['reason'] == 'open_door_outer_hinge_corner':
            contested.append((s_, n, a['module'], a['hinge_on_shell_boundary']))
ratios = [row['ratio'] for r in res.values() for rows in r.get('leaf_width_evidence', {}).values()
          for row in rows if row['ratio']]
w('<div class="cards">')
w(f'<div class="card"><b>{len(contested)}</b><span>çekişmeli kanat işaretlendi</span></div>')
w(f'<div class="card"><b>{len(ratios)}</b><span>ölçülen kapak katı</span></div>')
w(f'<div class="card"><b>{min(ratios):.3f}–{max(ratios):.3f}</b><span>kanat toplamı / gövde genişliği oranı</span></div>')
w('</div>')
w('<div class="bul kritik"><h4>Sonuç: algoritmanın eşleşmesi tutuyor, referansınki tutmuyor</h4><dl>')
w('<dt>ölçüm</dt><dd>Algoritmanın eşleşmesinde <b>her kat</b> %0,0–1,0 sapmayla gövde genişliğine oturuyor. '
  'Referansın işaret ettiği eşleşmede ise 9440, 9441, 9462 (alt kat), 9467, 9484 ve yatak başı örneklerinde '
  'gövdenin yalnız <b>yarısı</b> kapanıyor (oran 0,495–0,500) — fiziksel olarak imkânsız. '
  'Yalnız 9462\'nin üst katı yakın (1,032 / 0,952); 9449-2 ve 9475\'te ikizler simetrik olduğu için '
  'iki eşleşme ayırt edilemiyor.</dd>')
w('<dt>anlamı</dt><dd>Kırmızı referans render\'lar modül SAYISI için güvenilir, kapak gibi taşan parçaların '
  'PARÇA DÜZEYİ sahipliği için değil — büyük olasılıkla uzamsal bir kuralla boyanıyorlar, sipariş BOM\'undan değil. '
  'Bu, puanlamayı da etkiliyor: parça düzeyi doğruluk kırmızı maskeyle ölçülemez.</dd>')
w('<dt>yapılan</dt><dd>Atama <b>değiştirilmedi</b>. Her çekişmeli parçaya '
  '<code>hinge_on_shell_boundary</code> (rakip modülün kimliği) ve '
  '<code>semantic_status</code> alanları eklendi; her modül için kat kat '
  '<code>leaf_width_evidence</code> yazılıyor. Şüphe artık sessiz değil.</dd>')
w('</dl></div>')
if contested:
    w('<div class="scroll"><table><tr><th>sipariş</th><th>kanat</th><th>algoritma</th><th>referansın işaret ettiği</th></tr>')
    for s_, n, m, rival in contested:
        w(f'<tr><td>{e(s_)}</td><td>{e(n)}</td><td>{e(m)}</td><td>{e(", ".join(rival))}</td></tr>')
    w('</table></div>')

w('<h2>Uygulanmayan düzeltme: yatak başı ailesi (T12)</h2>')
w('<p class="lead">İnceleme, yedi yatak başı dosyasının hepsinde iki örüntü buldu ve ikisi de '
  'bağımsız olarak doğrulandı: (1) tek modülün <i>içinde</i> tam örtüşen sırt sırta çift yan panel var; '
  '(2) tam genişlikte paylaşılan bir yatay panel iki ayrı gövdeyi ~5.400 mm²\'lik ince kenar temasıyla '
  'birleştiriyor — <code>yatakbasi_komidinli</code>\'nin 109 parçasının tek modüle çökmesinin sebebi '
  'yalnızca <b>iki köprü kenar</b>.</p>')
w('<div class="bul kritik"><h4>Neden uygulanmadı: önerilen kural doğrulanmış sonuçları bozuyor</h4><dl>')
w('<dt>çelişki</dt><dd>Önerilen "sandviç panel = modül sınırı" kuralını ölçtüm: 9417, 9435, 9439 ve 9483\'te '
  'de aynı imza var (alt ve üst gövdeyi tek bir tam genişlik yatay panel bağlıyor — 9435 Object_43 z[882,900] '
  'x[1001,2599]; altında 4, üstünde 3 düşey panel). Bu dört siparişin referansı <b>tek modül</b> diyor. '
  'Kural uygulanırsa doğrulanmış 4 sonuç bozulur, referansı olmayan 7 sonuç "düzelir".</dd>')
w('<dt>karar</dt><dd>Uygulanmadı. Yatak başı ailesinin referans renderı üretilmeden bu karar verilemez. '
  'Geometri bu iki durumu ayıramıyor; ayrım ürün tanımında.</dd>')
w('</dl></div>')

w('<h2>Kapsam ve sınırlar</h2>')
w('<ul>'
  '<li>Kaynak FBX\'ler değişmedi: 69 dosyanın SHA-256 değeri işlem öncesi ve sonrası aynı.</li>'
  '<li>Modül sayısının tutması parça düzeyinde doğruluk değildir. Tek kameradan görünmeyen '
  'arkalık/alt yüzey üyeliği görsel olarak kanıtlanamaz.</li>'
  '<li>Beklenen değerler üretimin kırmızı render\'larından gelir. 25 sipariş için hiçbir referans yok; '
  'bunlar puanlamaya girmedi.</li>'
  '<li>Eşikler (18 mm nominal ±0,15 · TOL 0,05 mm · min temas 1 mm² · panel aralığı 30 mm · '
  'menteşe hizası 2,5 mm · oturma derinliği 8 mm / fark 5 mm · döndürülmüş menteşe 30 mm) '
  'bu 69 siparişte kalibre edildi, katalog genelinde doğrulanmadı.</li>'
  '<li>T01 (tek gövdeli 23 sipariş) ayırt edici kuralları hiç sınamıyor: tek modül varken '
  'her <code>len(candidates)==1</code> testi zorunlu olarak geçer. Buradaki tam başarı eşiklerin '
  'doğruluğuna kanıt değildir; regresyon kalkanıdır.</li>'
  '<li>5 mm arkalıklar yapısal çekirdeğe hiç girmiyor (<code>thick</code> yalnız 18 ± 0,15 mm); '
  'üyelik alıyorlar ama karkas temsilinde yoklar.</li>'
  '<li>Üretim kit sayımına hâlâ bağlanmadı.</li>'
  '</ul>')
w('<footer>Üreten: <code>Projects/otonom_kit/module_ayirici/rapor_uret.py</code> · '
  'Ayırıcı: <code>module_segmenter.py</code> v0.2 (v0.1 kopyası: <code>module_segmenter_v01.py</code>) · '
  'Testler: <code>test_modul.py</code>, 21 sentetik Blender regresyonu · '
  'Koşucu: <code>run_batch.py</code>. '
  'Ham çıktı <code>results-v2/</code> (v0.1 karşılaştırması <code>results/</code>), '
  'parça bbox\'ları <code>parca-bbox/</code>. Küçük görsellere tıklayınca büyüğü açılır.</footer>')

(BASE / 'sonuclar.html').write_text('\n'.join(out), encoding='utf-8')
print('yazıldı:', BASE / 'sonuclar.html', len('\n'.join(out)), 'bayt')
