/* Adaptx Toplama İstasyonu — uygulama.
   Modüller: veri.js (saf mantık), parcalar.js (parça sözlüğü), uc.js (three.js, tembel).
   Bölümler: 1 Sabitler/Durum · 2 API · 3 Türetmeler · 4 Çizim (üst/ray/başlık/sahne/şerit/sistem)
   5 Görsel döndürücü · 6 Eylemler (seçim, kalem, işaretleme) · 7 Notlar · 8 Yüzen katmanlar/tema
   9 Video/büyük görünüm/3B · 10 Olaylar/klavye · 11 Açılış */
import {
  esc, sayi0, sayi1, sayi3, zamanStr, isoStr, saatStr, saatDk, boyutStr, trKucuk, noHtml,
  kk, ilerleme, tamamMi, FILTRELER, gecer, listele, gezinmeListesi, birlestir, hataMetni,
} from './veri.js';
import { ACIKLAMA, BIRIM_GRAM, BEYAZ, KOYU, kalemler, gorselYollari, boyBilgisi } from './parcalar.js';

const $ = (s, k = document) => k.querySelector(s);
const $$ = (s, k = document) => [...k.querySelectorAll(s)];
const ikon = (ad, cls = '') => `<svg class="i ${cls}" aria-hidden="true"><use href="#i-${ad}"/></svg>`;
const EASE = 'cubic-bezier(.23,1,.32,1)';
const azHareket = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
const genis = () => matchMedia('(min-width: 1200px)').matches;
const P = new URLSearchParams(location.search);

/* Kalıcı tercihler: hepsi try/catch içinde (gizli mod / kapalı depolama çökertmesin). */
const depo = {
  al(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
  yaz(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* kapalı depolama */ } },
};

/* ====================================================================== 1. Sabitler / Durum */
const DURUM = { islendi: 'İşlendi', bekliyor: 'Bekliyor', isleniyor: 'İşleniyor', hatali: 'Hatalı' };
const PENCERELER = [50, 100, 200, 0];
const TEMALAR = [
  { id: 'acik', ad: 'Açık', not: 'Gün ışığı, çelik gri', a: '#eceff1', b: '#ffffff', c: '#14171a', m: '#d21c5d' },
  { id: 'koyu', ad: 'Koyu', not: 'Loş depo', a: '#0f1114', b: '#171a1e', c: '#eceef0', m: '#d6275f' },
  { id: 'kagit', ad: 'Kâğıt', not: 'Kontrplak sıcaklığı', a: '#f3efe6', b: '#fbf9f3', c: '#231e17', m: '#c81a58' },
  { id: 'kontrast', ad: 'Yüksek kontrast', not: 'Uzaktan okuma', a: '#ffffff', b: '#ffffff', c: '#000000', m: '#b00040' },
];
const TEMA_TAKMA = { grafit: 'koyu', dark: 'koyu', light: 'acik', paper: 'kagit' };
const GECIS_MS = 300;      // işaretleme -> sıradaki kaleme otomatik geçiş gecikmesi
const KILIT_MS = 650;      // otomatik geçişten sonra Toplandı/Space/Enter'ın yok sayıldığı süre
const ONAY_MS = 3500;      // toplu işaretleme ikinci tık penceresi (fare/dokunma)
const ONAY_KLAVYE_MS = 8000; // klavye ile açılan onayda pencere uzun: Tab+Enter ve ekran okuyucu duyurusu yetişsin
const POST_ZAMAN_ASIMI = 15000;
const POLL_ZAMAN_ASIMI = 8000;   // /api/durum yanıtsız kalırsa bağlantı pili çıksın (sunucu TCP'yi kabul edip asılabilir)
const BAYAT_MS = 30000;          // son başarılı veri bundan eskiyse "Güncellendi" uyarı rengine döner

function pencereOku() {
  const v = depo.al('adaptx_pencere');
  return v !== null && PENCERELER.includes(+v) ? +v : 50;
}
const S = {
  veri: null, by: new Map(), sel: null, gorunum: 'toplama', kalem: {}, filtre: 'tumu', q: '', yon: -1,
  pencere: pencereOku(),
  bitenGizle: depo.al('adaptx_biten_gizle') !== '0', manifest: {}, bagli: true,
  incele: new Set(),        // tamamlanmış olsa da kalem kalem gözden geçirilen siparişler
  bekle: null,              // işaretlendi, otomatik geçiş bekleniyor (bitti ekranı gecikir)
  sahneImza: '', son: null, odak: depo.al('adaptx_odak') === '1', pop: null, sistemAcik: false, rayAcik: false, ucAcik: false,
  ucIdx: 0, kilit: 0, tumOnay: null, ilk: true, tema: 'acik',
  yazma: {}, notYazma: {},  // no -> son yazım zamanı (bayat poll koruması)
  seqNo: {}, seqKey: new Map(),
  kayitsiz: new Map(),      // kk -> {no, key, mesaj, istenen}: sunucuya yazılamayan işaretler (istenen: işaretlenmek mi, geri alınmak mı isteniyordu)
  kutlaYeni: false, zorla: false, ilkSerit: true, belgeGizli: [], buyukTepsi: null,
  sonGirdi: 'fare', sonTus: 0,  // son girdi türü (klavye mi fare mi) ve zamanı: odak yönetimi yalnız klavyede devreye girer
  tekTus: depo.al('adaptx_kisayol') !== '0',  // tek harfli kısayollar (WCAG 2.1.4: kapatılabilir)
  popKlavye: false, sonBasari: 0, hazir: false, manifestSoz: null,
  ilkHata: 0,               // veri hiç gelmeden art arda başarısız /api/durum denemesi (2'de iskelet yerine hata sahnesi)
  bantGordu: depo.al('adaptx_bant_gordu') || '', bantImza: '', bantGorunur: false, bantAcik: false, // uyarı bandı: "Gördüm" imzası
};
const ucusta = new Map();   // kk -> istek kimliği (yanıtı gelmemiş işaretler; poll bunları ezmez)
let ucusSayac = 0;
const cur = () => S.by.get(S.sel) || null;
const zamanOf = (o, key) => (o.checklist || {})[key] || null;
const gorselYol = (mk) => gorselYollari(S.manifest[mk]);
/* Görsel özniteliği: beyaz parça açık temada, koyu parça koyu temada aydınlatılır (panel.css --bf / --kf). */
const ozel = (mk) => (BEYAZ.has(mk) ? ' data-beyaz' : KOYU.has(mk) ? ` data-koyu="${KOYU.get(mk)}"` : '');

/* ====================================================================== 2. API */
async function veriCek(url, secenek = {}) {
  const { zamanAsimi, ...ek } = secenek;
  let ac = null, zt = 0;
  if (zamanAsimi) { ac = new AbortController(); zt = setTimeout(() => ac.abort(), zamanAsimi); ek.signal = ac.signal; }
  try {
    const r = await fetch(url, ek);
    let j = null;
    try { j = await r.json(); } catch (e) { /* gövde JSON değil */ }
    if (!r.ok) throw new Error((j && j.hata) || `HTTP ${r.status}`);
    return j;
  } finally { clearTimeout(zt); }
}
const postJson = (url, govde) => veriCek(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(govde), zamanAsimi: POST_ZAMAN_ASIMI });

let yenileSeq = 0;
async function yenile() {
  const benim = ++yenileSeq;
  const basla = performance.now();
  try {
    // manifest ve /api/durum paralel başlar (zincir kısalır); manifest yalnız ilk çizimden önce beklenir
    const d = await veriCek('/api/durum', { cache: 'no-store', zamanAsimi: POLL_ZAMAN_ASIMI });
    const bekle = S.manifestSoz; S.manifestSoz = null; // yalnız başarıda tüketilir: ilk deneme düşerse yeniden deneme de manifesti bekler
    if (bekle) await bekle;
    if (benim !== yenileSeq) return; // daha yeni bir istek başladı
    S.bagli = true; S.sonBasari = Date.now(); S.ilkHata = 0;
    uygula(d, basla);
  } catch (e) {
    if (benim !== yenileSeq) return;
    S.bagli = false; // son veri ekranda kalır
    if (!S.veri) { // hiç veri yok: sonsuz iskelet yerine ikinci başarısız denemede açıklayıcı durum
      S.ilkHata++;
      if (S.ilkHata < 2) setTimeout(yenile, 1500); else ilkHataCiz();
    }
    renderUst();
  }
}
/* İlk yüklemede sunucuya ulaşılamıyor: iskelet (10 döngüden sonra donuyor ve yanıltıyor) yerine sahne mesajı + Tekrar dene,
   raya "Liste yüklenemedi". Veri gelince render() ikisini de kendiliğinden değiştirir (sahneImza/liste imzası boş). */
function ilkHataCiz() {
  degistir(`<div class="mesaj kritik"><div class="muhur">${ikon('uyari')}<h2>Sunucuya ulaşılamıyor</h2><p>Panel servisi yanıt vermiyor. 10 saniyede bir yeniden deneniyor.</p><div class="mesaj-eylem"><button class="btn-ana" data-act="yenile"><span class="btn-dolgu"></span>${ikon('yenile', 'ikon-eylem')}Tekrar dene</button></div></div></div>`, 'ilk', 1);
  $('#gozSirasi').hidden = true;
  const l = $('#liste'); l.dataset.imza = 'hata'; l.innerHTML = '<div class="liste-bos">Liste yüklenemedi.</div>';
  $('#listeBilgi').textContent = 'Bağlanılamadı';
  duyur('Sunucuya ulaşılamıyor. 10 saniyede bir yeniden deneniyor.');
}
/* Kaydedilemedi diye işaretlenmiş ama sunucu sonradan o değeri gösteriyorsa (istemci zaman aşımı, işlem aslında yapılmış)
   ya da anahtar sunucudan kalkmışsa kayıt temizlenir; aksi hâlde uyarı ve gerçek durum yan yana kalırdı. */
function kayitsizTemizle(basla) {
  S.kayitsiz.forEach((v, k) => {
    const o = S.by.get(v.no);
    if (!o || !(v.key in (o.checklist || {}))) { S.kayitsiz.delete(k); return; }
    if ((S.yazma[v.no] || 0) > basla || ucusta.has(k)) return; // bayat poll: karar verme
    if (!!o.checklist[v.key] === v.istenen) S.kayitsiz.delete(k);
  });
}
function uygula(d, basla) {
  birlestir(d.siparisler, S.by, { basla, yazma: S.yazma, notYazma: S.notYazma, ucusta });
  S.veri = d;
  S.by = new Map(d.siparisler.map((o) => [o.no, o]));
  kayitsizTemizle(basla);
  if (!S.hazir) { S.hazir = true; $('#app').dataset.hazir = '1'; }
  if (!S.sel || !S.by.has(S.sel)) S.sel = varsayilanSecim();
  if (S.ilk) { S.ilk = false; ilkAyar(); }
  render();
}
function varsayilanSecim() {
  const dep = depo.al('adaptx_siparis');
  if (dep && S.by.has(dep)) return dep;
  const l = gorunenler();
  const is = l.find((o) => { const [t, n] = ilerleme(o); return o.durum === 'islendi' && n > 0 && t < n; });
  return (is || l[0] || (S.veri && S.veri.siparisler[0]) || {}).no || null;
}

/* ====================================================================== 3. Türetmeler */
const qNorm = () => trKucuk(S.q.trim());
const listeSecenek = () => ({ q: qNorm(), filtre: S.filtre, bitenGizle: S.bitenGizle, pencere: S.pencere, yon: S.yon, secili: S.sel });
const sonucu = () => (S.veri ? listele(S.veri.siparisler, listeSecenek()) : { liste: [], eslesen: 0, kirpik: false });
const gorunenler = () => sonucu().liste;
/* j/k ve 'Sıradaki sipariş' pencere dilimi/sabitleme olmadan, süzülmüş TAM liste üzerinden gezer. */
const gezinme = () => (S.veri ? gezinmeListesi(S.veri.siparisler, { q: qNorm(), filtre: S.filtre, bitenGizle: S.bitenGizle, yon: S.yon, secili: S.sel }) : []);

function curKey(o) {
  const ks = kalemler(o);
  const k = S.kalem[o.no];
  if (k && ks.some((x) => x.key === k)) return k;
  const ilk = ks.find((x) => !zamanOf(o, x.key)) || ks[0];
  if (ilk) S.kalem[o.no] = ilk.key; // seçimi sabitle: işaretleyince kalem kendiliğinden değişmesin
  return ilk ? ilk.key : null;
}
const curIdx = (o) => kalemler(o).findIndex((x) => x.key === curKey(o));
const kayitsizKalemler = (no) => [...S.kayitsiz.values()].filter((x) => x.no === no);

/* ====================================================================== 4. Çizim */
function render() {
  renderBanner(); // renderUst'tan önce: bant görünürken üst şeritteki "Hatalı" pili gizlenir (aynı bilgi iki yerde olmasın)
  renderUst();
  renderFiltre();
  renderRay();
  renderBaslik();
  renderSahne();
  if (S.sistemAcik) renderSistem();
  notGuncelle();
  aramaTekSonuc();
}

/* ----- üst şerit ----- */
function renderUst() {
  const d = S.veri;
  const sis = d && d.sistem;
  let nokta = 'nokta n-uyari', yazi = 'Durum bilinmiyor', kisa = '';
  if (sis) {
    if (sis.servis_calisiyor) { nokta = 'nokta n-uyari n-nabiz'; yazi = 'Tur çalışıyor…'; kisa = 'Çalışıyor'; }
    else if (!sis.timer_aktif) { nokta = 'nokta n-uyari'; yazi = 'Timer kapalı'; kisa = 'Timer'; } // işletim uyarısı: kritik (kırmızı) değil
    else if (sis.sonraki_tur) {
      nokta = 'nokta n-iyi';
      yazi = sonrakiTurYazi(sis); kisa = saatDk(sis.sonraki_tur);
    }
  }
  if ($('#turNokta').className !== nokta) $('#turNokta').className = nokta;
  if ($('#turYazi').textContent !== yazi) $('#turYazi').textContent = yazi;
  if ($('#turKisa').textContent !== kisa) $('#turKisa').textContent = kisa; // dar ekranda renk tek başına kalmasın
  if ($('#turSr').textContent !== yazi) $('#turSr').textContent = yazi;
  const gy = d ? 'Güncellendi ' + zamanStr(d.zaman) : '';
  if ($('#guncellendi').textContent !== gy) $('#guncellendi').textContent = gy;
  // görünür metin erişilebilir adın içinde kalır (WCAG 2.5.3); ikon-only dar ekranda da ad bunu taşır
  $('#yenileBtn').setAttribute('aria-label', gy ? 'Yenile. ' + gy : 'Yenile');
  const bayat = !!(S.sonBasari && Date.now() - S.sonBasari > BAYAT_MS);
  $('#yenileBtn').classList.toggle('bayat', bayat);
  $('#yenileBtn').title = bayat ? 'Veri 30 sn’den eski; yenilemek için tıkla' : 'Yenile';
  $('#baglantiPil').hidden = S.bagli;
  $('#baglantiUzun').hidden = !d; // "son veri gösteriliyor" yalnız gösterilecek bir veri varsa
  // hatalı / bekleyen sayısı: Hat durumu paneli açılmadan görünsün. Hatalı pili yalnız uyarı bandı kapalıyken (band zaten söylüyor).
  const c = (d && d.sayac) || {};
  const bek = (c.bekleyen || 0) + (c.isleniyor || 0);
  const kritikPil = c.hatali > 0 && !S.bantGorunur;
  const rh = (kritikPil ? `<span class="sayi-rozet r-kritik" title="Hatalı sipariş"><span class="rz-uzun">Hatalı </span><span class="rz-kisa" aria-hidden="true">!</span>${c.hatali}</span>` : '') + (bek > 0 ? `<span class="sayi-rozet r-uyari" title="Bekleyen sipariş">Bekleyen ${bek}</span>` : '');
  const re = $('#sayiRozet'); if (re.dataset.h !== rh) {
    re.dataset.h = rh; re.innerHTML = rh;
    re.setAttribute('aria-label', ['Hat durumunu aç', kritikPil ? `Hatalı ${c.hatali}` : '', bek > 0 ? `Bekleyen ${bek}` : ''].filter(Boolean).join('. '));
  }
  renderKayitPil();
}
function sonrakiTurYazi(sis) {
  const fark = Math.round((sis.sonraki_tur - Date.now() / 1000) / 60);
  const sa = saatDk(sis.sonraki_tur);
  return fark > 0 ? `Sonraki tur: ${sa} (${fark} dk)` : `Sonraki tur: şimdi (${sa})`;
}
/* Yazılamayan işaret/not: kalıcı uyarı (toast tek başına yetmez). */
function kayitSorunlari() {
  const l = [];
  S.kayitsiz.forEach((v) => l.push({ tur: 'kalem', no: v.no, key: v.key }));
  NOT.yerel.forEach((y, no) => { if (y.hata) l.push({ tur: 'not', no }); });
  return l;
}
function renderKayitPil() {
  const l = kayitSorunlari();
  const p = $('#kayitPil');
  p.hidden = !l.length;
  if (!l.length) { if ($('#kayitDuyuru').textContent) $('#kayitDuyuru').textContent = ''; return; }
  const k = l.filter((x) => x.tur === 'kalem').length, n = l.length - k;
  const y = [k ? `${k} kalem` : '', n ? `${n} not` : ''].filter(Boolean).join(' · ') + ' kaydedilmedi';
  if ($('#kayitPilYazi').textContent !== y) { $('#kayitPilYazi').textContent = y; $('#kayitDuyuru').textContent = y; } // düğme düğme kalır; duyuru ayrı canlı bölgede
}
/* Uyarı bandı: yalnız YENİ bir olayda görünür. İçerik imzası (metinler sayıları taşır) "Gördüm"de saklanır; imza değişene
   kadar kapalı kalır, uyarı tümden kalkarsa imza silinir (aynı hata yeniden çıkarsa yine görünür). Kapalıyken üst şeritteki
   "Hatalı N" pili tek kalıcı göstergedir. Dar ekranda tek satırlık şerit (kisa), ⌄ ile ayrıntı. */
function renderBanner() {
  const d = S.veri;
  const l = [];
  if (d) {
    const s = d.sistem || {};
    if (s.no_suz_fbx && s.no_suz_fbx.length) l.push({ tam: `${s.no_suz_fbx.length} FBX dosyasında sipariş no okunamadı: ${s.no_suz_fbx.join(', ')}`, kisa: `${s.no_suz_fbx.length} FBX’te sipariş no yok` });
    if (d.sayac && d.sayac.hatali > 0) l.push({ tam: `${d.sayac.hatali} sipariş hatalı durumda (boş/bozuk JSON).`, kisa: `${d.sayac.hatali} hatalı sipariş`, git: true });
    (s.uyarilar || []).forEach((u) => l.push({ tam: u, kisa: u }));
  }
  const imza = l.map((x) => x.tam).join('|');
  S.bantImza = imza;
  if (d && !l.length && S.bantGordu) { S.bantGordu = ''; depo.yaz('adaptx_bant_gordu', ''); }
  const gor = !!l.length && S.bantGordu !== imza;
  S.bantGorunur = gor;
  const kutu = $('#uyariKutu');
  const kisa = l.length === 1 ? l[0].kisa : `${l.length} uyarı`;
  const h = gor ? `${ikon('uyari')}<div class="uyari-ic" id="uyariIc"><ul class="u-tam">${l.map((x) => `<li>${esc(x.tam)}${x.git ? ' <button class="uyari-link" data-act="bant-git">Hatalı’ya git</button>' : ''}</li>`).join('')}</ul><p class="u-kisa" data-act="bant-ac">${esc(kisa)}</p></div>
    <div class="uyari-eylem"><button class="uyari-btn uyari-ac" data-act="bant-ac" aria-expanded="${S.bantAcik}" aria-controls="uyariIc" aria-label="Uyarı ayrıntısını aç / kapat">${ikon('sag')}</button><button class="uyari-btn uyari-gordum" data-act="bant-gordum" aria-label="Gördüm, uyarıyı kapat">${ikon('kapat')}<span class="uzun">Gördüm</span></button></div>` : '';
  if (kutu.dataset.h !== h) { kutu.dataset.h = h; kutu.innerHTML = h; }
  kutu.hidden = !gor;
  kutu.classList.toggle('acik', gor && S.bantAcik);
  kutu.classList.toggle('u-kritik', !!(d && d.sayac && d.sayac.hatali > 0)); // renk içeriği izler: hatalı = kritik, gerisi sarı
}
function bantGordum() {
  S.bantGordu = S.bantImza; depo.yaz('adaptx_bant_gordu', S.bantImza); S.bantAcik = false;
  const odakta = $('#uyariKutu').contains(document.activeElement);
  renderBanner(); renderUst();
  if (odakta) $('#sahne').focus({ preventScroll: true }); // düğme kalktı: odak gövdeye düşmesin
}
function bantGit() { S.filtre = 'hatali'; ilkineDon(); render(); }
function bantAcKapat() { S.bantAcik = !S.bantAcik; renderBanner(); }
/* Bant yüksekliği (+alt boşluk) --bant-h olarak yazılır: mobil tepsi bütçesi ve sığdırma bunu hesaba katar. */
function bantOlc() {
  const k = $('#uyariKutu');
  const h = k.hidden ? 0 : k.offsetHeight + (parseFloat(getComputedStyle(k).marginBottom) || 0);
  document.documentElement.style.setProperty('--bant-h', h + 'px');
  mobilSigdir();
}

/* ----- ray: filtre + liste ----- */
function renderFiltre() {
  if (!S.veri) return;
  const q = qNorm();
  const h = FILTRELER.map(([id, ad]) => {
    const say = S.veri.siparisler.filter((o) => gecer(o, q, id, S.bitenGizle)).length;
    if (!say && S.filtre !== id && (id === 'bekleyen' || id === 'hatali')) return '';
    return `<button class="cip" data-act="filtre" data-f="${id}" aria-pressed="${S.filtre === id}">${ad}<span class="cip-say">${say}</span></button>`;
  }).join('');
  const b = $('#filtreBar');
  if (b.dataset.h !== h) { b.dataset.h = h; b.innerHTML = h; }
  $('#bitenBtn').setAttribute('aria-checked', String(S.bitenGizle));
  const ps = $('#pencereSec'); if (ps.value !== String(S.pencere)) ps.value = String(S.pencere);
  const yb = $('#yonBtn');
  const yh = `${ikon('ok', S.yon < 0 ? 'yon-asagi' : 'yon-yukari')}No`;
  if (yb.dataset.h !== yh) { yb.dataset.h = yh; yb.innerHTML = yh; }
  yb.setAttribute('aria-label', S.yon < 0 ? 'Sıralama: sipariş no azalan' : 'Sıralama: sipariş no artan');
}
/* Dört biçim: "T içinden son C" / "E eşleşmeden son C (toplam T)" (kırpık, vurgulu) / "T sipariş" / "E eşleşme / T". */
function pencereBilgi(top, sn) {
  const { eslesen, kirpik } = sn;
  const suzulmus = eslesen !== top;
  if (kirpik) return { metin: suzulmus ? `${eslesen} eşleşmeden son ${S.pencere} (toplam ${top})` : `${top} içinden son ${S.pencere}`, vurgu: true };
  return { metin: suzulmus ? `${eslesen} eşleşme / ${top}` : `${top} sipariş`, vurgu: false };
}
function renderRay() {
  if (!S.veri) return;
  const sn = sonucu();
  const l = sn.liste;
  const top = S.veri.siparisler.length;
  const pb = pencereBilgi(top, sn);
  const lb = $('#listeBilgi');
  if (lb.textContent !== pb.metin) lb.textContent = pb.metin;
  lb.classList.toggle('vurgu', pb.vurgu);
  renderRayOzet();
  const imza = l.map((o) => { const [t, n] = ilerleme(o); return `${o.no}:${o.durum}:${t}/${n}:${kayitsizKalemler(o.no).length}${o.no === S.sel ? '*' : ''}`; }).join(',');
  const c = $('#liste');
  if (c.dataset.imza === imza) return;
  const odakNo = c.contains(document.activeElement) ? document.activeElement.dataset.no : null; // yeniden çizimde klavye odağı düşmesin
  const sabit = l.some((x) => x.no === S.sel) ? S.sel : (l[0] && l[0].no); // tek Tab durağı: seçili (ya da ilk) satır
  const secDegisti = c.dataset.sel !== String(S.sel);
  c.dataset.imza = imza; c.dataset.sel = String(S.sel);
  if (!l.length) {
    const gizli = S.bitenGizle && S.filtre === 'tumu' ? S.veri.siparisler.filter((o) => gecer(o, qNorm(), 'tamam', false) && !gecer(o, qNorm(), 'tumu', true)).length : 0;
    c.innerHTML = `<div class="liste-bos">Eşleşen sipariş yok.${gizli ? `<small>${gizli} tamamlanmış sipariş “Bitenleri gizle” yüzünden listede yok; “Tamamlanan” filtresinde bulunur.</small>` : ''}</div>`;
    return;
  }
  c.innerHTML = l.map((o) => {
    const [t, n] = ilerleme(o);
    const tam = n > 0 && t === n;
    const rozet = o.durum !== 'islendi' ? `<span class="s-durum ${o.durum === 'hatali' ? 'd-kritik' : 'd-uyari'}">${DURUM[o.durum] || esc(o.durum)}</span>` : '';
    const kay = kayitsizKalemler(o.no).length ? `<span class="s-kayitsiz" title="Kaydedilmemiş kalem var">!</span>` : '';
    return `<button class="satir" data-act="sec" data-no="${esc(o.no)}" data-tam="${tam ? 1 : 0}" tabindex="${o.no === sabit ? 0 : -1}" aria-current="${o.no === S.sel}" title="${esc(o.no)} — ${DURUM[o.durum] || ''}${n ? ` — ${t}/${n}` : ''}">
      <span class="s-no"><span>${noHtml(o.no)}</span>${tam ? ikon('tik', 'tamam-ikon') : ''}${rozet}${kay}</span>
      <span class="s-say">${n ? `${t}/${n}` : ''}</span>
      ${t > 0 ? `<span class="s-bar" style="--p:${t / n}"></span>` : ''}
    </button>`;
  }).join('');
  if (secDegisti) {
    // scrollIntoView yerine elle kaydırma: Chrome scrollIntoView'u sıralı odak başlangıcı sayar (ilk Tab satıra düşerdi)
    const a = c.querySelector('[aria-current="true"]');
    if (a) {
      const ust = a.offsetTop - 8, alt = a.offsetTop + a.offsetHeight + 8;
      if (ust < c.scrollTop) c.scrollTop = ust; else if (alt > c.scrollTop + c.clientHeight) c.scrollTop = alt - c.clientHeight;
    }
  }
  if (odakNo) { const y = [...c.querySelectorAll('.satir')].find((x) => x.dataset.no === odakNo); if (y) y.focus({ preventScroll: true }); }
}
/* Panel açılmadan hat özeti: Tamamlanan n/N · Disk %x */
function renderRayOzet() {
  const d = S.veri; if (!d) return;
  const tam = d.siparisler.filter(tamamMi).length;
  const dk = d.sistem && d.sistem.disk;
  const h = `<button class="ray-ozet-btn" data-act="sistem" title="Hat durumunu aç">Tamamlanan <b>${tam}/${d.siparisler.length}</b>${dk ? ` · Disk <b>%${dk.yuzde}</b>` : ''}</button>`;
  const e = $('#rayOzet'); if (e.dataset.h !== h) { e.dataset.h = h; e.innerHTML = h; }
}
function aramaTekSonuc() {
  if (!S.q.trim() || !S.veri) return;
  const l = gorunenler();
  if (l.length === 1 && l[0].no !== S.sel) sec(l[0].no, { arama: true });
}

/* ----- sahne başlığı ----- */
function renderBaslik() {
  const o = cur();
  const no = o ? o.no : '—';
  const nh = noHtml(no);
  const sn = $('#sbNo'); if (sn.dataset.h !== nh) { sn.dataset.h = nh; sn.innerHTML = nh; }
  const [t, n] = o ? ilerleme(o) : [0, 0];
  const meta = [];
  if (o) {
    if (o.parca) meta.push(`${o.parca} parça`);
    if (n) meta.push(`${n} kalem`);
    if (o.durum === 'islendi') meta.push('işlendi');
  }
  const rozet = o && o.durum !== 'islendi' ? `<span class="rozet ${o.durum === 'hatali' ? 'd-kritik' : 'd-uyari'}"><i class="nokta ${o.durum === 'hatali' ? 'n-kritik' : 'n-uyari'}"></i>${DURUM[o.durum] || esc(o.durum)}</span>` : '';
  const mh = (meta.length ? `<span>${meta.join(' · ')}</span>` : '') + rozet;
  const me = $('#sbMeta'); if (me.dataset.h !== mh) { me.dataset.h = mh; me.innerHTML = mh; }
  $('#sbSay').innerHTML = n ? `<b>${t}</b> / ${n} kalem toplandı` : '';
  const l = gezinme();
  const i = l.findIndex((x) => x.no === S.sel);
  $('#oncekiSip').disabled = !(i > 0);
  $('#sonrakiSip').disabled = !(i >= 0 && i < l.length - 1);
  $('#notSar').hidden = !o; // veri gelmeden tek başına görünmesin (yer değiştirmesin)
  const bh = o ? belgelerHtml(o) : '';
  const be = $('#belgeler');
  if (be.dataset.h !== bh) { be.dataset.h = bh; be.innerHTML = bh + `<button class="belge belge-daha" data-act="belge-daha" aria-expanded="false" aria-controls="belgeMenu" aria-label="Diğer belgeler" title="Diğer belgeler" hidden>${ikon('daha')}</button>`; belgelerSigdir(); }
  const uc = $('#ucBtn');
  const var_ = !!(o && o.fbx && o.fbx.length);
  uc.disabled = !var_;
  uc.title = var_ ? '3B model (m)' : 'Bu sipariş için FBX yok';
  const seg = $('#seg');
  seg.dataset.g = S.gorunum;
  const pasif = !o || o.durum !== 'islendi'; // bekleyen/hatalı: iki görünüm de aynı mesajı gösterir, düğmeler işlevsiz
  seg.toggleAttribute('data-pasif', pasif);
  $$('button', seg).forEach((b) => { b.setAttribute('aria-pressed', String(b.dataset.g === S.gorunum)); b.disabled = pasif; });
  renderIlerleme(o, t, n);
}
function belgelerHtml(o) {
  const p = [];
  const ad = encodeURIComponent(o.no);
  if (o.pdf) p.push(`<a class="belge" href="/pdf/siparis/${ad}" target="_blank" rel="noopener">${ikon('pdf')}PDF</a>`);
  else if (o.durum === 'islendi') p.push(`<span class="belge belge-yok" title="Bu sipariş için PDF üretilmemiş"><i class="nokta n-uyari"></i>PDF yok</span>`);
  if (o.ozet_no) p.push(`<a class="belge" href="/pdf/ozet/${Number(o.ozet_no)}" target="_blank" rel="noopener">${ikon('pdf')}Özet ${Number(o.ozet_no)}</a>`);
  (o.fbx || []).forEach((f, i, a) => {
    p.push(`<a class="belge" href="/fbx/${encodeURIComponent(f.ad)}" download title="${esc(f.ad)} — ${boyutStr(f.boyut)}">${ikon('indir')}FBX${a.length > 1 ? ' ' + (i + 1) : ''}</a>`);
  });
  if (o.renk_dosya) {
    const rk = o.renk && o.renk.siparis_rengi ? ` · ${esc(o.renk.siparis_rengi)}` : '';
    p.push(`<a class="belge" href="/renk/${encodeURIComponent(o.renk_dosya.ad)}" download title="${esc(o.renk_dosya.ad)} — ${boyutStr(o.renk_dosya.boyut)}">${ikon('renk')}Renk${rk}</a>`);
  }
  if (o.video) {
    p.push(`<button class="belge" data-act="video" title="Animasyonu oynat — ${esc(o.video.ad)} (${boyutStr(o.video.boyut)})"><i class="nokta n-iyi"></i>${ikon('oynat')}Animasyon</button>`);
    p.push(`<a class="belge belge-ikon" href="/video/${ad}" download="${esc(o.no)}.mp4" aria-label="Animasyonu indir" title="Animasyonu indir (${esc(o.no)}.mp4, ${boyutStr(o.video.boyut)})">${ikon('indir')}</a>`);
  } else {
    if (tamamMi(o)) p.push(`<span class="belge belge-yok belge-uyar" title="Tüm kalemler toplandı ama Drive klasöründe ${esc(o.no)}.mp4 bulunamadı; sipariş listede görünmeye devam eder"><i class="nokta n-uyari"></i>${ikon('oynat-bos')}Animasyon yok</span>`);
    else p.push(`<span class="belge belge-yok" title="Drive klasöründe ${esc(o.no)}.mp4 bulunamadı">${ikon('oynat-bos')}Animasyon yok</span>`);
  }
  return p.join('');
}
/* Belgeler tek satırda sessiz kalır; sığmayanlar ⋯ menüsüne gider. */
function belgelerSigdir() {
  const c = $('#belgeler'); if (!c) return;
  const daha = $('.belge-daha', c);
  if (!daha) return; // henüz çizilmedi
  const ogeler = $$(':scope > .belge:not(.belge-daha)', c);
  ogeler.forEach((x) => { x.hidden = false; }); daha.hidden = true;
  const sbAlt = $('.sb-alt');
  const komsu = $('#notSar').offsetWidth + $('#sbSay').offsetWidth;
  const bosluk = parseFloat(getComputedStyle(sbAlt).columnGap) || 8;
  const kap = sbAlt.clientWidth - komsu - bosluk * 3 - 8;
  const gcs = parseFloat(getComputedStyle(c).columnGap) || 4;
  const gen = ogeler.map((x) => x.getBoundingClientRect().width);
  const top = gen.reduce((a, b) => a + b, 0) + gcs * Math.max(0, gen.length - 1);
  S.belgeGizli = [];
  if (top <= kap || !ogeler.length) { closeBelgeMenu(); return; }
  const dw = 44;
  let k = 0, w = 0;
  while (k < gen.length && w + gen[k] + (k ? gcs : 0) + dw + gcs <= kap) { w += gen[k] + (k ? gcs : 0); k++; }
  ogeler.forEach((x, i) => {
    if (i < k) return;
    x.hidden = true;
    const kopya = x.cloneNode(true); kopya.hidden = false;
    if (kopya.classList.contains('belge-ikon')) kopya.insertAdjacentHTML('beforeend', '<span>Animasyonu indir</span>'); // menüde yalnız simge kalmasın
    S.belgeGizli.push(kopya.outerHTML);
  });
  daha.hidden = false;
}
function closeBelgeMenu() { if (S.pop === 'belge') popKapat(); }
function renderIlerleme(o, t, n) {
  const el = $('#ilerleme');
  el.setAttribute('aria-valuemax', n); el.setAttribute('aria-valuenow', t);
  el.setAttribute('aria-valuetext', n ? `${t} / ${n} kalem` : '');
  el.hidden = !n;
  $('#ustCizgi').style.setProperty('--p', n ? t / n : 0);
  if (!n) { el.innerHTML = ''; el.dataset.k = ''; return; }
  if (el.dataset.k !== o.no + ':' + n) {
    el.dataset.k = o.no + ':' + n;
    el.innerHTML = kalemler(o).map((it, i) => `<i data-i="${i}" data-d="0"></i>`).join('');
  }
  const ci = S.gorunum === 'toplama' ? curIdx(o) : -1;
  const ks = kalemler(o);
  $$('i', el).forEach((s, i) => {
    const d = zamanOf(o, ks[i].key) ? '1' : '0';
    if (s.dataset.d !== d) s.dataset.d = d;
    if (i === ci) s.setAttribute('aria-current', 'true'); else s.removeAttribute('aria-current');
  });
}

/* ----- sahne gövdesi ----- */
function sahneDurum(o) {
  if (!o) return ['yok', ''];
  if (o.durum !== 'islendi') return ['mesaj', ''];
  const ks = kalemler(o);
  if (!ks.length) return ['bos', ''];
  if (S.gorunum === 'genel') return ['genel', ''];
  const [t, n] = ilerleme(o);
  if (t === n && !S.incele.has(o.no) && S.bekle !== o.no) return ['bitti', ''];
  return ['kalem', curKey(o)];
}
function renderSahne() {
  if (!S.veri) return;
  const o = cur();
  const [durum, key] = sahneDurum(o);
  // İmza kalem anahtar kümesini ve adetleri de taşır: sipariş JSON'u yeniden işlenip bir kalem eklenir/çıkar/değişirse
  // sahne ve Genel bakış kartları yeniden kurulur (eski indekse bağlı kart yanlış kalemi işaretlerdi).
  const ks = o ? kalemler(o) : [];
  const kimlik = (x) => `${x.key}:${x.adet}:${x.gram || 0}`;
  const ek = durum === 'genel' ? ks.map(kimlik).join(',') : durum === 'kalem' ? ks.map((x) => x.key).join(',') + '#' + kimlik(ks.find((x) => x.key === key) || {}) : '';
  const imza = [o && o.no, durum, key, ek].join('|');
  const idx = durum === 'kalem' ? curIdx(o) : -1;
  if (imza !== S.sahneImza) {
    const son = S.son;
    let tur = 'ilk', yon = 1;
    if (son) {
      if (son.no !== (o && o.no)) tur = 'siparis';
      else if (son.durum === 'kalem' && durum === 'kalem' && son.key !== key) { tur = 'kalem'; yon = idx >= son.idx ? 1 : -1; }
      else tur = 'sade';
    }
    if (S.zorla) { tur = 'sade'; S.zorla = false; }
    S.sahneImza = imza;
    sahneKur(o, durum, key, tur, yon, !!(son && S.kutlaYeni));
    S.kutlaYeni = false;
  } else {
    sahneYama(o, durum, key);
  }
  S.son = { no: o && o.no, durum, key, idx };
  renderSerit(o, durum);
  mobilSigdir();
}
/* Mobil sığdırma: adet, tartı ve Birim/Boy satırı yapışkan eylem çubuğunun (+ şerit) üstünde kalmalı; tepsi ölçülerek küçülür.
   Sabit bir bütçe formülü (100dvh - 655px) bant, iki satırlı ad/açıklama, 360 px genişlik gibi durumları bilemiyordu.
   Sırayla: tepsi 280 -> 104 px; yetmezse açıklama gizlenir (1), Birim/Boy satırı (2), tepsi (3). Yalnız sayfa başındaki ilk görünüm
   hedeflenir (koordinatlar belge düzleminde; giriş animasyonunun dönüşümünden etkilenmez). */
const mobilMq = matchMedia('(max-width: 720px)');
function mobilSigdir() {
  const n = $('#icSahne'); const k = n && $('.kalem', n);
  if (!k) return;
  const kok = document.documentElement;
  if (!mobilMq.matches) { k.style.removeProperty('--tepsi-w'); delete k.dataset.sikisik; kok.style.removeProperty('--eylem-h'); return; }
  const eylem = $('.eylem', k), serit = $('#gozSirasi'), ic = $('#ic');
  if (!eylem) return;
  kok.style.setProperty('--eylem-h', eylem.offsetHeight + 'px');
  const yapisik = !serit.hidden && getComputedStyle(serit).position === 'sticky';
  const limit = innerHeight - eylem.offsetHeight - (yapisik ? serit.offsetHeight : 0) - 8;
  const dip = () => {
    const alt = (e) => (e && e.offsetParent !== null ? e.getBoundingClientRect().bottom : 0);
    const b = Math.max(alt($('.olcu', k)), alt($('.olcu-alt', k)));
    return ic.getBoundingClientRect().top + scrollY + 1 + (b - n.getBoundingClientRect().top);
  };
  const MIN = 104, MAX = 280;
  for (let lvl = 0; lvl <= 3; lvl++) {
    if (lvl) k.dataset.sikisik = String(lvl); else delete k.dataset.sikisik;
    if (lvl === 3) { k.style.setProperty('--tepsi-w', '0px'); break; }
    k.style.setProperty('--tepsi-w', MAX + 'px');
    const fazla = dip() - limit;
    if (fazla <= MAX - MIN) { k.style.setProperty('--tepsi-w', Math.max(MIN, Math.min(MAX, MAX - fazla)) + 'px'); break; }
  }
}
function degistir(html, tur, yon) {
  const ic = $('#ic');
  const eski = $('#icSahne');
  { const a = document.activeElement; S.odakKayip = !a || a === document.body || !!(eski && eski.contains(a)); } // eski sahne inert olunca odak BODY'ye düşer
  const yeni = document.createElement('div');
  yeni.className = 'ic-sahne'; yeni.id = 'icSahne'; yeni.innerHTML = html;
  const hareket = !azHareket();
  if (eski) {
    if (eski._tepsi) eski._tepsi.iptal();
    eski.id = '';
    if (hareket && tur !== 'ilk' && eski.firstChild) {
      eski.classList.add('cikan'); eski.setAttribute('inert', ''); eski.setAttribute('aria-hidden', 'true');
      const kf = tur === 'kalem' ? [{ opacity: 1, transform: 'none' }, { opacity: 0, transform: `translateX(${-yon * 28}px)` }] : [{ opacity: 1 }, { opacity: 0 }];
      const a = eski.animate(kf, { duration: 160, easing: 'cubic-bezier(.4,0,1,1)', fill: 'forwards' });
      a.onfinish = () => eski.remove();
      ic.appendChild(yeni);
    } else { eski.remove(); ic.appendChild(yeni); }
  } else ic.appendChild(yeni);
  if (hareket) {
    const kf = tur === 'kalem' ? [{ opacity: 0, transform: `translateX(${yon * 28}px)` }, { opacity: 1, transform: 'none' }]
      : tur === 'siparis' ? [{ opacity: 0, transform: 'translateY(10px)' }, { opacity: 1, transform: 'none' }]
        : [{ opacity: 0 }, { opacity: 1 }];
    yeni.animate(kf, { duration: 220, easing: EASE, fill: 'backwards' });
  }
  return yeni;
}
function sahneKur(o, durum, key, tur, yon, kutla) {
  let html = '';
  if (durum === 'yok') html = S.veri ? mesajHtml('kutu', 'Sipariş yok', 'Listede gösterilecek sipariş bulunamadı.') : '';
  else if (durum === 'mesaj') html = mesajDurumHtml(o);
  else if (durum === 'bos') html = mesajHtml('tik', 'İşaretlenecek parça yok', 'Bu siparişte işaretlenecek parça yok.');
  else if (durum === 'genel') html = genelHtml(o);
  else if (durum === 'bitti') html = bittiHtml(o, kutla);
  else html = kalemHtml(o, key);
  const n = degistir(html, tur, yon);
  const tep = $('.tepsi', n);
  if (tep) n._tepsi = tepsiKur(tep);
  if (durum === 'kalem') yukleOnden(o);
  // Klavyeyle tetiklenen değişimde odak yeni sahnenin ana düğmesine taşınır (fare/dokunmada dokunulmaz);
  // sahne duyurusu ekran okuyucuya yeni kalemi söyler (WCAG 2.4.3, 4.1.3).
  if (tur !== 'ilk') {
    if (S.odakKayip && S.sonGirdi === 'klavye' && performance.now() - S.sonTus < 2500) { const h = $('.btn-ana', n); if (h) h.focus({ preventScroll: true }); }
    duyur(sahneDuyuru(o, durum, key));
  }
}
function duyur(m, zorla) {
  const e = $('#duyuru'); if (!m) return;
  if (zorla && e.textContent === m) { e.textContent = ''; setTimeout(() => { e.textContent = m; }, 60); return; } // aynı metin yeniden okunsun
  if (e.textContent !== m) e.textContent = m;
}
function sahneDuyuru(o, durum, key) {
  if (!o) return '';
  if (durum === 'kalem') {
    const ks = kalemler(o); const i = ks.findIndex((x) => x.key === key); const it = ks[i];
    return it ? `${it.ad}, ${sayi0(it.adet)} ${it.birim}. Kalem ${i + 1} / ${ks.length}${zamanOf(o, key) ? ', toplandı' : ''}` : '';
  }
  if (durum === 'bitti') return `Sipariş ${o.no} tamamlandı`;
  if (durum === 'genel') return `Sipariş ${o.no}, genel bakış`;
  if (durum === 'mesaj') return `Sipariş ${o.no}: ${DURUM[o.durum] || ''}`;
  return '';
}
function sahneYama(o, durum, key) {
  const n = $('#icSahne');
  if (!n) return;
  if (durum === 'kalem') {
    const ks = kalemler(o); const it = ks.find((x) => x.key === key);
    if (!it) return;
    const d = zamanOf(o, key);
    const hata = S.kayitsiz.get(kk(o.no, key));
    const k = $('.kalem', n);
    if (!k) return;
    k.dataset.durum = d ? 'tamam' : 'bekliyor';
    const ba = $('.btn-ana', k); ba.dataset.durum = d ? 'tamam' : 'bekliyor'; ba.setAttribute('aria-pressed', String(!!d));
    const bi = $('.btn-ikinci', k);
    const bh = d ? `${ikon('geri')}Geri al` : `Atla${ikon('atla')}`;
    if (bi.dataset.h !== bh) { bi.dataset.h = bh; bi.innerHTML = bh; bi.dataset.act = d ? 'geri-al' : 'atla'; }
    const kz = $('.kalem-zaman', k); const kzt = d ? `${ikon('tik')}İşaretlendi ${saatStr(d)}` : '';
    if (kz.dataset.h !== kzt) { kz.dataset.h = kzt; kz.innerHTML = kzt; }
    const kh = $('.kalem-hata', k); const kht = hata ? kayitHataMetni(hata) : '';
    if (kh.dataset.h !== kht) { kh.dataset.h = kht; kh.innerHTML = kht; kh.hidden = !hata; }
  } else if (durum === 'genel') {
    genelYama(o, n);
  } else if (durum === 'mesaj') {
    mesajTurYama();
  }
}
function mesajHtml(ik, baslik, metin, ton = '') {
  return `<div class="mesaj ${ton}"><div class="muhur">${ikon(ik)}<h2>${esc(baslik)}</h2><p>${esc(metin)}</p></div></div>`;
}
/* Bekleyen / işleniyor / hatalı: simge durumu anlatır, başlık somuttur (rozet zaten durumu söylüyor), eylem vardır. */
function mesajTurMetni() {
  const sis = S.veri && S.veri.sistem;
  if (!sis) return '';
  if (sis.servis_calisiyor) return 'Tur şu anda çalışıyor.';
  if (!sis.timer_aktif) return 'Timer kapalı: tur kendiliğinden başlamaz.';
  return sis.sonraki_tur ? sonrakiTurYazi(sis) : '';
}
function mesajTurYama() { const e = $('#mesajTur'); if (e) { const m = mesajTurMetni(); if (e.textContent !== m) e.textContent = m; } }
function mesajDurumHtml(o) {
  const hata = o.durum === 'hatali';
  const ik = hata ? 'uyari' : (o.durum === 'bekliyor' || o.durum === 'isleniyor') ? 'saat' : 'kutu';
  const baslik = hata ? 'JSON okunamadı' : o.durum === 'bekliyor' ? 'Henüz işlenmedi' : o.durum === 'isleniyor' ? 'İşleniyor' : 'Durum bilinmiyor';
  const s = sonrakiIs(o);
  const f = o.fbx && o.fbx[0];
  const eylem = [
    s ? `<button class="btn-ana" data-act="sec-sonraki" data-no="${esc(s.no)}" data-durum="bekliyor"><span class="btn-dolgu"></span>Sıradaki siparişe geç${ikon('ok', 'ikon-eylem')}</button>` : '',
    hata && f ? `<a class="btn-ikinci-kucuk" href="/fbx/${encodeURIComponent(f.ad)}" download>${ikon('indir', 'ikon-eylem')}<span>FBX’i indir</span></a>` : '',
    hata ? `<button class="btn-ikinci-kucuk" data-act="sistem">${ikon('liste', 'ikon-eylem')}<span>Hat durumu ve günlük</span></button>` : '',
  ].join('');
  return `<div class="mesaj ${hata ? 'kritik' : ''}"><div class="muhur">${ikon(ik)}<h2>${baslik}</h2><p>${esc(durumMesaji(o))}</p>${hata ? '' : `<p class="mesaj-tur" id="mesajTur">${esc(mesajTurMetni())}</p>`}${eylem ? `<div class="mesaj-eylem">${eylem}</div>` : ''}</div></div>`;
}
function durumMesaji(o) {
  switch (o.durum) {
    case 'bekliyor': return 'Bu sipariş henüz işlenmedi; bir sonraki turda Blender tarafından sayılacak.';
    case 'isleniyor': return 'Bu sipariş şu anda işleniyor olabilir. Birazdan tekrar kontrol edin.';
    case 'hatali': return 'Bu siparişin JSON dosyası boş veya bozuk görünüyor. Elle kontrol gerekebilir.';
    default: return 'Durum bilinmiyor.';
  }
}

/* --- kalem sahnesi --- */
/* Gram Inter + tabular-nums yazılır (mono virgül sayıdan kopuyordu). */
const gramHtml = (n) => sayi1(n);
function boyYazi(b) {
  if (!b) return '';
  if (!b.yaklasik && b.mm >= 100) return `Boy ${sayi1(b.mm / 10)} cm`;
  return `Boy ${b.yaklasik ? '≈ ' : ''}${sayi0(b.mm)} mm`;
}
/* "Birim 3,401 g · Boy ≈ 17 mm": tartıyla tek parça sağlaması. */
function olcuAlt(it) {
  const b = boyYazi(boyBilgisi(it.key, S.manifest[it.mk]));
  const bg = it.tartili && BIRIM_GRAM[it.key] ? `Birim ${sayi3(BIRIM_GRAM[it.key])} g` : '';
  return [bg, b].filter(Boolean).join(' · ');
}
const kayitHataMetni = (h) => `${ikon('uyari')}Kaydedilemedi: ${esc(h.mesaj)}. Durumu kontrol et; gerekirse Toplandı’ya yeniden bas.`;
function kalemHtml(o, key) {
  const ks = kalemler(o);
  const i = ks.findIndex((x) => x.key === key);
  const it = ks[i];
  const d = zamanOf(o, key);
  const hata = S.kayitsiz.get(kk(o.no, key));
  const g = gorselYol(it.mk);
  const bz = ozel(it.mk);
  const tur = g && g.tur512 ? `<div class="tepsi-tur" data-tur="${esc(g.tur512)}"${bz}></div>` : '';
  const img = g ? `<img class="tepsi-img" src="${esc(g.buyuk)}" alt="${esc(it.ad)}" draggable="false" data-g="1"${bz}>` : `<span class="tepsi-yok">${ikon('kutu')}</span>`;
  const ipucu = g && tur ? `<span class="tepsi-ipucu">${ikon('cevir')}<span class="ipucu-fare">Üzerinde gez, çevir</span><span class="ipucu-dokun">Sürükle, çevir</span></span>` : '';
  const buyut = g ? `<button class="buyut-btn" data-act="buyut" aria-label="Görseli büyüt" title="Büyük görünüm">${ikon('buyut')}</button>` : '';
  const grupTxt = it.tartili ? `${ikon('tarti')}tartarak sayılır` : 'adetle sayılır';
  const tarti = it.tartili && it.gram ? `<div class="tarti"><span class="tarti-ad">${ikon('tarti')}Tartı hedefi</span><span class="tarti-deger">${gramHtml(it.gram)}<small>g</small></span></div>` : '';
  const oa = olcuAlt(it);
  const aciklama = [ACIKLAMA[it.mk], it.belirsiz ? 'Boyu siparişte okunamadı; PDF’e bak.' : ''].filter(Boolean).join(' ');
  const bh = d ? `${ikon('geri')}Geri al` : `Atla${ikon('atla')}`;
  const kzt = d ? `${ikon('tik')}İşaretlendi ${saatStr(d)}` : '';
  const kht = hata ? kayitHataMetni(hata) : '';
  return `<div class="kalem" data-durum="${d ? 'tamam' : 'bekliyor'}">
    <button class="nav nav-geri" data-act="onceki" aria-label="Önceki kalem" title="Önceki kalem (←)" ${i === 0 ? 'disabled' : ''}>${ikon('sol')}</button>
    <div class="tepsi">${img}${tur}${ipucu}${buyut}</div>
    <div class="kalem-bilgi">
      <h2 class="kalem-ad">${esc(it.ad)}</h2>
      ${aciklama ? `<p class="kalem-aciklama">${esc(aciklama)}</p>` : ''}
      <p class="kalem-alt">Kalem ${i + 1} / ${ks.length} <span aria-hidden="true">·</span> ${grupTxt}</p>
      <div class="olcu"><div class="sayi"><span class="sayi-deger">${sayi0(it.adet)}</span><span class="sayi-birim">${it.birim}</span></div>${tarti}</div>
      ${oa ? `<p class="olcu-alt">${oa}</p>` : ''}
      <div class="eylem">
        <button class="btn-ana" data-act="isaretle" data-durum="${d ? 'tamam' : 'bekliyor'}" aria-pressed="${!!d}" title="Toplandı (Space)"><span class="btn-dolgu"></span><span class="btn-halka">${ikon('tik')}</span>Toplandı</button>
        <button class="btn-ikinci" data-act="${d ? 'geri-al' : 'atla'}" data-h="${esc(bh)}">${bh}</button>
      </div>
      <p class="kalem-zaman" data-h="${esc(kzt)}">${kzt}</p>
      <p class="kalem-hata" role="alert" data-h="${esc(kht)}" ${hata ? '' : 'hidden'}>${kht}</p>
    </div>
    <button class="nav nav-ileri" data-act="sonraki" aria-label="Sonraki kalem" title="Sonraki kalem (→)" ${i === ks.length - 1 ? 'disabled' : ''}>${ikon('sag')}</button>
  </div>`;
}
function yukleOnden(o) {
  const ks = kalemler(o); const i = curIdx(o);
  [1, 2, -1].forEach((dlt) => { const it = ks[i + dlt]; const g = it && gorselYol(it.mk); if (g) { const im = new Image(); im.src = g.buyuk; } });
}

/* --- genel bakış --- */
function gkHtml(o, it) {
  const d = !!zamanOf(o, it.key);
  const dz = zamanOf(o, it.key);
  const kayitsiz = S.kayitsiz.has(kk(o.no, it.key));
  const g = gorselYol(it.mk);
  // gram yuvası: tartılanlarda gram; boru/ray'de boy (adı iki satıra kırmadan, sayı satırı hizalı kalsın)
  const gr = it.tartili && it.gram ? `<span class="gk-gram">${gramHtml(it.gram)} g</span>` : it.boy ? `<span class="gk-gram">${esc(it.boy)}</span>` : '<span class="gk-gram"></span>';
  const aciklama = [ACIKLAMA[it.mk], it.belirsiz ? 'Boyu siparişte okunamadı; PDF’e bak.' : ''].filter(Boolean).join(' ');
  const bz = ozel(it.mk);
  return `<div class="gk" data-key="${esc(it.key)}" data-d="${d ? 1 : 0}" ${kayitsiz ? 'data-kayitsiz="1"' : ''} title="${esc(aciklama)}">
    <button class="gk-ac" data-act="kalem-ac" data-key="${esc(it.key)}" aria-label="${esc(it.ad)}, ${it.adet} ${it.birim}"><span class="gk-img">${g ? `<img src="${esc(g.kucuk)}" alt="" decoding="async" draggable="false" data-g="1"${bz}>` : `<span class="yok-ikon">${ikon('kutu')}</span>`}</span>
      <span class="gk-ad" title="${esc(it.ad)}">${esc(it.adTemel || it.ad)}</span><span class="gk-sayi">${sayi0(it.adet)}<small>${it.birim}</small></span>${gr}<span class="gk-saat">${d ? `${saatStr(dz)} toplandı` : kayitsiz ? 'kaydedilmedi' : ''}</span></button>
    <button class="gk-tik" data-act="tik" data-key="${esc(it.key)}" role="checkbox" aria-checked="${d}" aria-label="${esc(it.ad)} toplandı"><span>${ikon('tik')}</span></button>
  </div>`;
}
const tumOnayAktif = (o) => !!(S.tumOnay && S.tumOnay.no === o.no && Date.now() - S.tumOnay.t < S.tumOnay.ms);
const tumBtnHtml = (onay, kalan) => `<button class="btn-ikinci-kucuk ${onay ? 'onay-bekler' : ''}" data-act="tumunu" aria-pressed="${!!onay}">${ikon('tik')}<span style="display:inline">${onay ? `Emin misin? ${kalan} kalemi işaretle` : `Tümünü işaretle (${kalan})`}</span></button>`;
function genelUstHtml(o) {
  const [t, n] = ilerleme(o);
  const kalan = n - t;
  return `<div class="genel-baslik"><h2>Tüm kalemler</h2><span class="genel-say" data-h="${t}/${n}"><b>${t}</b> / ${n} toplandı</span></div>` + (kalan > 0 ? tumBtnHtml(tumOnayAktif(o), kalan) : '');
}
/* Yerinde güncelleme: düğmeyi yeniden yaratmak odağı BODY'ye düşürüyordu (Enter ile onay istemi + her poll). */
function genelUstYama(u, o) {
  const [t, n] = ilerleme(o);
  const kalan = n - t, onay = tumOnayAktif(o);
  const say = $('.genel-say', u);
  if (say && say.dataset.h !== `${t}/${n}`) { say.dataset.h = `${t}/${n}`; say.innerHTML = `<b>${t}</b> / ${n} toplandı`; }
  let b = $('[data-act="tumunu"]', u);
  if (kalan <= 0) { if (b) { const odakta = document.activeElement === b; b.remove(); if (odakta) $('#sahne').focus({ preventScroll: true }); } return; }
  if (!b) { u.insertAdjacentHTML('beforeend', tumBtnHtml(onay, kalan)); return; }
  const sp = $('span', b), y = onay ? `Emin misin? ${kalan} kalemi işaretle` : `Tümünü işaretle (${kalan})`;
  if (sp.textContent !== y) sp.textContent = y;
  if (b.getAttribute('aria-pressed') !== String(onay)) b.setAttribute('aria-pressed', String(onay));
  b.classList.toggle('onay-bekler', onay);
}
function genelHtml(o) {
  const ks = kalemler(o);
  const t = ks.filter((x) => x.tartili); const a = ks.filter((x) => !x.tartili);
  const topG = t.reduce((s, x) => s + (x.gram || 0), 0);
  const grup = (ad, l, ek) => l.length ? `<section class="genel-grup"><h3>${ad}<small>${l.length} kalem${ek || ''}</small></h3><div class="genel-izgara">${l.map((it) => gkHtml(o, it)).join('')}</div></section>` : '';
  return `<div class="genel"><div class="genel-ust">${genelUstHtml(o)}</div>${grup('Tartılarak sayılan', t, topG > 0 ? ` · ${sayi1(topG)} g` : '')}${grup('Adetle sayılan', a)}</div>`;
}
function genelYama(o, n) {
  const ks = kalemler(o);
  $$('.gk', n).forEach((g) => {
    const it = ks.find((x) => x.key === g.dataset.key); if (!it) return;
    const dz = zamanOf(o, it.key);
    const d = dz ? '1' : '0';
    const kayitsiz = S.kayitsiz.has(kk(o.no, it.key));
    if (g.dataset.d !== d) { g.dataset.d = d; $('.gk-tik', g).setAttribute('aria-checked', d === '1' ? 'true' : 'false'); }
    const sh = dz ? `${saatStr(dz)} toplandı` : kayitsiz ? 'kaydedilmedi' : '';
    const se = $('.gk-saat', g); if (se.textContent !== sh) se.textContent = sh;
    if (kayitsiz) g.dataset.kayitsiz = '1'; else delete g.dataset.kayitsiz;
  });
  const u = $('.genel-ust', n);
  if (u) genelUstYama(u, o);
}

/* --- tamamlandı --- */
function sonrakiIs(o) {
  const l = gezinme();
  const i = l.findIndex((x) => x.no === o.no);
  const aday = (x) => x.no !== o.no && x.durum === 'islendi' && (() => { const [t, n] = ilerleme(x); return n > 0 && t < n; })();
  return l.slice(i + 1).find(aday) || l.slice(0, Math.max(i, 0)).find(aday) || null;
}
function bittiHtml(o, yeni) {
  const ks = kalemler(o);
  const top = ks.reduce((a, x) => a + x.adet, 0);
  const s = sonrakiIs(o);
  const son = ks.map((x) => zamanOf(o, x.key)).filter(Boolean).sort().pop();
  return `<div class="bitti ${yeni ? 'yeni' : ''}"><div class="muhur">
    <div class="onay"><svg viewBox="0 0 88 88" aria-hidden="true"><circle class="onay-halka" cx="44" cy="44" r="33"/><path class="onay-tik" d="M30 45l10 10 19-22"/></svg><i class="onay-dalga"></i></div>
    <h2>Sipariş tamamlandı</h2>
    <dl class="etiket-say">
      <div><dt>Sipariş</dt><dd>${noHtml(o.no)}</dd></div>
      <div><dt>Kalem</dt><dd>${ks.length}</dd></div>
      <div><dt>Adet</dt><dd>${sayi0(top)}</dd></div>
      ${son ? `<div><dt>Saat</dt><dd>${saatStr(son)}</dd></div>` : ''}
    </dl>
    <div class="bitti-eylem">
      ${s ? `<button class="btn-ana" data-act="sec-sonraki" data-no="${esc(s.no)}" data-durum="bekliyor"><span class="btn-dolgu"></span><span>Sıradaki<span class="uzun-ek"> sipariş</span> · ${noHtml(s.no)}</span>${ikon('ok')}</button>` : ''}
      <button class="btn-ikinci" data-act="gorunum" data-g="genel">Kalemleri gözden geçir</button>
    </div>
    ${o.video ? '' : `<p class="bitti-not">Animasyonu henüz yok; bu sipariş listede görünmeye devam edecek.</p>`}
  </div></div>`;
}

/* --- parça şeridi (gözlü kutu) --- */
function renderSerit(o, durum) {
  const sr = $('#gozSirasi');
  const goster = o && (durum === 'kalem' || durum === 'bitti');
  sr.hidden = !goster;
  if (!goster) { sr.dataset.k = ''; document.documentElement.style.setProperty('--serit-h', '0px'); return; }
  const ks = kalemler(o);
  const k = o.no + '|' + ks.map((x) => x.key).join('|') + '|' + Object.keys(S.manifest).length;
  if (sr.dataset.k !== k) {
    sr.dataset.k = k; sr.dataset.ck = ''; S.ilkSerit = true;
    sr.style.setProperty('--n', ks.length);
    let h = '';
    ks.forEach((it, i) => {
      if (i > 0 && ks[i - 1].tartili && !it.tartili) h += '<i class="goz-ayrac" aria-hidden="true"><b>ADET</b></i>';
      const g = gorselYol(it.mk);
      const bz = ozel(it.mk);
      h += `<button class="goz" data-act="kalem-git" data-key="${esc(it.key)}" data-d="0" title="${esc(it.ad)}" aria-label="${esc(it.ad)}, ${it.adet} ${it.birim}">
        <span class="goz-img">${g ? `<img src="${esc(g.kucuk)}" alt="" decoding="async" draggable="false" data-g="1"${bz}>` : `<span class="yok-ikon">${ikon('kutu')}</span>`}</span>
        <span class="goz-say">${sayi0(it.adet)}</span><span class="goz-tik">${ikon('tik')}</span><span class="goz-hata" aria-hidden="true">!</span></button>`;
    });
    sr.innerHTML = h;
  }
  document.documentElement.style.setProperty('--serit-h', sr.offsetHeight + 'px');
  const ck = durum === 'kalem' ? curKey(o) : null;
  let aktif = null;
  $$('.goz', sr).forEach((b) => {
    const it = ks.find((x) => x.key === b.dataset.key); if (!it) return;
    const dz = zamanOf(o, it.key);
    const d = dz ? '1' : '0';
    const ky = S.kayitsiz.has(kk(o.no, it.key));
    if (b.dataset.d !== d) { b.dataset.d = d; b.title = it.ad + (dz ? ` — ${saatStr(dz)} toplandı` : ''); }
    if (ky) { b.dataset.kayitsiz = '1'; b.title = it.ad + ' — kaydedilmedi'; } else delete b.dataset.kayitsiz;
    const ad = `${it.ad}, ${it.adet} ${it.birim}${dz ? ', toplandı' : ''}${ky ? ', kaydedilmedi' : ''}`; // durum yalnız title'da kalmasın
    if (b.getAttribute('aria-label') !== ad) b.setAttribute('aria-label', ad);
    if (it.key === ck) { b.setAttribute('aria-current', 'true'); aktif = b; } else b.removeAttribute('aria-current');
  });
  // 20+ kalemde şerit taşsa da aktif hücre görünür kalır
  if (aktif && sr.dataset.ck !== ck) {
    sr.dataset.ck = ck;
    const sol = aktif.offsetLeft - (sr.clientWidth - aktif.offsetWidth) / 2;
    sr.scrollTo({ left: sol, behavior: azHareket() || S.ilkSerit ? 'auto' : 'smooth' });
    S.ilkSerit = false;
  }
  seritMaske();
}
/* Şerit taşıyorsa kenarda solma: gizli kalem olan yönde (sayaç yerine). */
function seritMaske() {
  const sr = $('#gozSirasi'); if (!sr || sr.hidden) return;
  const tasar = sr.scrollWidth > sr.clientWidth + 1;
  sr.toggleAttribute('data-tasar', tasar);
  sr.style.setProperty('--ms', tasar && sr.scrollLeft > 2 ? '36px' : '0px');
  sr.style.setProperty('--mg', tasar && sr.scrollLeft + sr.clientWidth < sr.scrollWidth - 2 ? '36px' : '0px');
}

/* ----- sistem paneli (Hat durumu) ----- */
function renderSistem() {
  const d = S.veri; if (!d) return;
  const s = d.sistem || {}; const c = d.sayac || {};
  let topPar = 0, isPar = 0;
  d.siparisler.forEach((o) => { const [t, n] = ilerleme(o); topPar += n; isPar += t; });
  const yuzde = topPar ? Math.round((isPar * 100) / topPar) : 0;
  const tam = d.siparisler.filter(tamamMi).length;
  const satir = (a, b, uz) => `<div class="sp-satir${uz ? ' uzun' : ''}"><span>${a}</span><span>${b}</span></div>`;
  const tur = { tamamlandi: 'Tamamlandı', hata: 'Hata', atlandi: 'Yeni sipariş yok', bilinmiyor: 'Bilinmiyor' };
  const dk = s.disk;
  const gb = (b) => sayi1(b / 1e9);
  const diskH = dk ? `<div class="sp-satir"><span>Disk kullanımı</span><span>%${dk.yuzde}</span></div><div class="disk-bar ${dk.yuzde >= 90 ? 'd-kritik' : dk.yuzde >= 80 ? 'd-uyari' : ''}" style="--p:${dk.yuzde / 100}"><i></i></div>${satir('Alan', `${gb(dk.bos)} GB boş · toplam ${gb(dk.toplam)} GB`, true)}` : satir('Disk kullanımı', 'Bilinmiyor');
  // Özet PDF'lere sipariş aralığı ile ad verilir ("Özet 1 · 9304–9340")
  const aralik = (i) => {
    const n = d.siparisler.filter((x) => x.ozet_no === i).map((x) => parseInt(x.no, 10)).filter((x) => !isNaN(x));
    if (!n.length) return '';
    const a = Math.min(...n), b = Math.max(...n);
    return ` · ${a === b ? a : a + '–' + b}`;
  };
  const ozet = s.ozet_adet ? Array.from({ length: s.ozet_adet }, (_, i) => `<a class="belge" href="/pdf/ozet/${i + 1}" target="_blank" rel="noopener">${ikon('pdf')}Özet ${i + 1}${aralik(i + 1)}</a>`).join('') : '<span class="sp-bos">Henüz yok</span>';
  const yuk = typeof s.yuk === 'number' ? s.yuk.toLocaleString('tr-TR', { maximumFractionDigits: 2 }) : (s.yuk ?? '—');
  const h = `
    <div class="sp-grup"><h3>Siparişler</h3>
      ${satir('Toplam sipariş', sayi0(c.toplam ?? 0))}${satir('İşlendi', sayi0(c.islendi ?? 0))}${satir('Bekleyen', sayi0((c.bekleyen || 0) + (c.isleniyor || 0)))}${satir('Hatalı', sayi0(c.hatali ?? 0))}
      ${satir('Tamamlanan sipariş', `${sayi0(c.tamamlanan ?? tam)} / ${sayi0(c.toplam ?? 0)}`)}${satir('Parça toplama', `%${yuzde}`)}
    </div>
    <div class="sp-grup"><h3>Sistem</h3>
      ${satir('Timer', s.timer_aktif ? 'Açık' : 'Kapalı')}
      ${satir('Tur servisi', s.servis_calisiyor ? 'Çalışıyor' : 'Beklemede')}
      ${satir('Sonraki tur', s.sonraki_tur ? `${saatDk(s.sonraki_tur)}` : '—')}
      ${diskH}
      ${satir('Son tur', `${tur[(s.son_tur || {}).sonuc] || 'Bilinmiyor'}${(s.son_tur || {}).zaman ? ' — ' + zamanStr(s.son_tur.zaman) : ''}`, true)}
      ${satir('rclone son hata', s.rclone && s.rclone.son_satir ? `${esc(s.rclone.son_satir)} — ${zamanStr(s.rclone.err_mtime)}` : 'Yok', true)}
      ${satir('Son inen FBX', s.son_fbx ? `${esc(s.son_fbx.ad)} — ${zamanStr(s.son_fbx.zaman)}` : '—', true)}
      ${satir('Sistem yükü', yuk)}
    </div>
    <div class="sp-grup"><h3>Son günlük satırları</h3><pre class="sp-log">${(s.son_loglar || []).length ? esc(s.son_loglar.join('\n')) : 'Kayıt yok.'}</pre></div>
    <div class="sp-grup"><h3>Özet PDF’ler (${s.ozet_adet || 0})</h3><div class="sp-linkler">${ozet}</div></div>
    <p class="sp-alt">kit-sistemi · ${esc(location.host)}</p>`;
  const g = $('#spGovde');
  if (g.dataset.h !== h) { g.dataset.h = h; g.innerHTML = h; }
}

/* ====================================================================== 5. Görsel döndürücü */
/* 24 karelik şerit; fare üstünde gezerken (yalnız görsel döner, seçim değişmez) ya da
   parmakla sürüklenince döner; bırakınca başlangıç karesine yumuşakça geri gelir. */
function tepsiKur(el) {
  const tur = $('.tepsi-tur', el);
  if (!tur) return { iptal() {}, basla() {} };
  const N = 24;
  let kare = 0, x0 = 0, k0 = 0, aktif = false, sur = false, hazir = false, istek = false, zt = 0;
  /* Şerit (~300 KB) her kalemde hover olmadan inmesin: ilk fare girişi/dokunuşta; ya da kalem 4 sn ekranda kalıp tarayıcı boştaysa. */
  let yuklendi = false, bekZ = 0;
  const yukle = () => {
    if (yuklendi) return; yuklendi = true; clearTimeout(bekZ);
    const im = new Image();
    im.onload = () => { hazir = true; tur.style.backgroundImage = `url("${tur.dataset.tur}")`; if (istek) el.classList.add('don'); };
    im.src = tur.dataset.tur;
  };
  bekZ = setTimeout(() => { if (window.requestIdleCallback) requestIdleCallback(yukle, { timeout: 3000 }); else yukle(); }, 4000);
  const pos = (k) => { kare = ((k % N) + N) % N; tur.style.backgroundPosition = `${(kare / (N - 1)) * 100}% 0`; };
  const ac = () => { yukle(); istek = true; if (hazir) el.classList.add('don'); };
  const kapa = () => { istek = false; el.classList.remove('don'); };
  const geri = () => {
    clearTimeout(zt);
    const adim = () => { if (kare === 0) { kapa(); return; } pos(kare + (kare <= N / 2 ? -1 : 1)); zt = setTimeout(adim, 24); };
    adim();
  };
  const basla = (x) => { clearTimeout(zt); x0 = x; k0 = kare; aktif = true; ac(); };
  const hareket = (x) => { const px = Math.max(10, el.clientWidth / 28); pos(k0 + Math.round((x - x0) / px)); };
  const dugme = (e) => e.target.closest && e.target.closest('button');
  el.addEventListener('pointerenter', (e) => { if (e.pointerType === 'mouse') basla(e.clientX); });
  el.addEventListener('pointermove', (e) => { if (aktif) hareket(e.clientX); });
  el.addEventListener('pointerleave', (e) => { if (e.pointerType === 'mouse' && !sur) { aktif = false; geri(); } });
  el.addEventListener('pointerdown', (e) => {
    if (dugme(e)) return;
    sur = true; try { el.setPointerCapture(e.pointerId); } catch (x) { /* yok say */ }
    if (e.pointerType !== 'mouse') basla(e.clientX);
  });
  const birak = (e) => {
    sur = false;
    if (e.pointerType !== 'mouse') { aktif = false; zt = setTimeout(geri, 700); }
    else if (!el.matches(':hover')) { aktif = false; geri(); }
  };
  el.addEventListener('pointerup', birak);
  el.addEventListener('pointercancel', birak);
  return { iptal() { clearTimeout(zt); clearTimeout(bekZ); }, basla, yukle };
}

/* ====================================================================== 6. Eylemler */
function sec(no, opt = {}) {
  if (!S.by.has(no)) return;
  if (no === S.sel && !opt.zorla) { if (!opt.arama) rayKapat(); return; }
  notGecis(S.sel); // yarım kalan not kaybolmasın
  if (S.ucAcik) ucKapat();
  S.sel = no;
  S.incele.delete(no); S.bekle = null; S.tumOnay = null;
  depo.yaz('adaptx_siparis', no);
  if (!opt.arama) rayKapat();
  render();
  notVurgula();
}
/* Kullanıcı filtre/arama/pencere/biten-gizle değiştirdi: seçim artık listede yoksa ilkine dön
   (poll seçimi ve kaydırmayı bozmaz; yalnız kullanıcı eylemleri buraya gelir). */
function ilkineDon() {
  if (!S.veri) return;
  $('#liste').scrollTop = 0;
  const q = qNorm();
  const { liste } = listele(S.veri.siparisler, { q, filtre: S.filtre, bitenGizle: S.bitenGizle, pencere: S.pencere, yon: S.yon, secili: null });
  if (liste.length && !liste.some((o) => o.no === S.sel)) {
    const hedef = liste[0];
    notGecis(S.sel); if (S.ucAcik) ucKapat();
    S.sel = hedef.no; S.incele.delete(hedef.no); S.bekle = null; S.tumOnay = null; depo.yaz('adaptx_siparis', hedef.no);
  }
}
function siparisGez(d) {
  const l = gezinme();
  const i = l.findIndex((x) => x.no === S.sel);
  const j = Math.min(l.length - 1, Math.max(0, (i < 0 ? 0 : i + d)));
  if (l[j]) sec(l[j].no);
}
function kalemGit(k, opt = {}) {
  const o = cur(); if (!o) return;
  const ks = kalemler(o); const it = typeof k === 'string' ? ks.find((x) => x.key === k) : ks[k]; if (!it) return;
  S.kalem[o.no] = it.key;
  if (opt.ac) { S.gorunum = 'toplama'; S.incele.add(o.no); }
  else if (S.gorunum === 'toplama') { const [t, n] = ilerleme(o); if (t === n) S.incele.add(o.no); }
  render();
}
function kalemYon(d) {
  const o = cur(); if (!o || S.gorunum !== 'toplama') return;
  const [durum] = sahneDurum(o);
  if (durum === 'bitti') { if (d < 0) kalemGit(kalemler(o).length - 1, { ac: true }); return; }
  if (durum !== 'kalem') return;
  const i = curIdx(o) + d;
  if (i >= 0 && i < kalemler(o).length) kalemGit(i);
}
function atla() {
  const o = cur(); if (!o) return;
  const ks = kalemler(o); if (!ks.length) return;
  kalemGit((curIdx(o) + 1) % ks.length);
}
function gorunumDegistir(g) {
  if (S.gorunum === g) return;
  S.gorunum = g;
  S.incele.delete(S.sel); S.tumOnay = null;
  render();
}

/* Checklist işaretleme: iyimser güncelle -> POST -> başarıda sunucunun haritası; hatada geri al,
   kalemi 'kaydedilmedi' işaretle, sahneyi o kaleme döndür (toast tek başına yetmez). */
let kilitZ = 0;
/* Çift basış kilidi: süre dolana kadar Toplandı/Space/Enter yok sayılır; ~1 sn'lik kilitte düğme soluk görünür (sessiz yutulmasın). */
function kilitle(ms) {
  S.kilit = performance.now() + ms;
  clearTimeout(kilitZ);
  if (ms >= 600) { document.body.dataset.kilit = '1'; kilitZ = setTimeout(() => { delete document.body.dataset.kilit; }, ms); } else delete document.body.dataset.kilit;
}
/* Aynı anahtar için istekler SIRAYLA gider: işaretle ve geri al ters sırada sunucuya ulaşırsa (ilk POST takılırsa) sunucudaki son
   yazan kullanıcının son kararı olmazdı (ekran "işaretsiz", sunucu "işaretli"). Önceki bitmeden (başarı ya da hata) yenisi başlamaz. */
const postZinciri = new Map();
function postSirali(k, govde) {
  const onceki = postZinciri.get(k) || Promise.resolve();
  const bu = onceki.catch(() => {}).then(() => postJson('/api/checklist', govde));
  postZinciri.set(k, bu);
  const temizle = () => { if (postZinciri.get(k) === bu) postZinciri.delete(k); };
  bu.then(temizle, temizle);
  return bu;
}
async function isaretle(no, key, durum, sessiz) {
  const o = S.by.get(no); if (!o) return;
  const k = kk(no, key);
  const eski = zamanOf(o, key);
  o.checklist[key] = durum ? new Date().toISOString() : null;
  const id = ++ucusSayac;
  ucusta.set(k, id);
  S.yazma[no] = performance.now();
  const sira = S.seqNo[no] = (S.seqNo[no] || 0) + 1;
  const siraK = (S.seqKey.get(k) || 0) + 1; S.seqKey.set(k, siraK);
  S.kayitsiz.delete(k);
  if (!sessiz) render();
  try {
    const r = await postSirali(k, { siparis: no, parca: key, durum });
    const o2 = S.by.get(no);
    if (o2 && r && r.checklist) {
      if (S.seqNo[no] === sira) { // en son istek: sunucunun haritası yerel haritayı değiştirir (uçuştaki diğer anahtarlar hariç)
        for (const kx of Object.keys(r.checklist)) if (kx === key || !ucusta.has(kk(no, kx))) o2.checklist[kx] = r.checklist[kx];
      } else if (key in r.checklist && S.seqKey.get(k) === siraK) o2.checklist[key] = r.checklist[key];
    }
  } catch (e) {
    if (S.seqKey.get(k) === siraK) { // daha yeni bir işlem yoksa geri al
      const o2 = S.by.get(no); if (o2) o2.checklist[key] = eski;
      const mesaj = hataMetni(e);
      S.kayitsiz.set(k, { no, key, mesaj, istenen: !!durum });
      toast('Kaydedilemedi: ' + mesaj);
      if (S.sel === no && S.gorunum === 'toplama') { S.kalem[no] = key; S.incele.add(no); S.bekle = null; }
      if (e && e.name === 'AbortError') setTimeout(yenile, 0); // zaman aşımı: işlem sunucuda yapılmış olabilir, durumu hemen doğrula
    }
  } finally {
    if (ucusta.get(k) === id) ucusta.delete(k);
    S.yazma[no] = performance.now();
    render();
  }
}
function isaretleGecerli() {
  const o = cur(); if (!o) return;
  const [durum, key] = sahneDurum(o);
  if (durum !== 'kalem') return;
  const simdi = performance.now();
  if (simdi < S.kilit) return; // çift basış / otomatik geçiş sonrası refleks basış yok sayılır
  const yap = !zamanOf(o, key);
  const i = curIdx(o);
  let bitiyor = false;
  if (yap) {
    const [t, n] = ilerleme(o);
    bitiyor = t + 1 === n;
    S.bekle = o.no;
    if (bitiyor) S.kutlaYeni = true;
    kilitle(GECIS_MS + KILIT_MS);
  } else { S.bekle = null; kilitle(350); }
  isaretle(o.no, key, yap);
  if (yap) {
    setTimeout(() => {
      if (S.bekle !== o.no) return;
      S.bekle = null;
      if (S.sel !== o.no) return;
      if (bitiyor) { S.incele.delete(o.no); kilitle(KILIT_MS); render(); return; }
      const ks = kalemler(o);
      if (curKey(o) !== key) { render(); return; }
      for (let s = 1; s <= ks.length; s++) {
        const j = (i + s) % ks.length;
        if (!zamanOf(o, ks[j].key)) { kilitle(KILIT_MS); kalemGit(j); return; }
      }
      render();
    }, azHareket() ? 0 : GECIS_MS);
  }
}
const tikSon = new Map(); // kk -> son tık zamanı
function tikGenel(key) {
  const o = cur(); if (!o) return;
  const it = kalemler(o).find((x) => x.key === key); if (!it) return; // anahtarla çöz: kart dizisi eskiyse bile doğru kalem
  const k = kk(o.no, it.key), t = performance.now();
  if (t - (tikSon.get(k) || 0) < 350) return; // eldiven/çift dokunuş: aynı kutuya 350 ms içinde ikinci tık yok sayılır (toplamadaki 350 ms geri-al kilidiyle aynı)
  tikSon.set(k, t);
  isaretle(o.no, it.key, !zamanOf(o, it.key));
}
/* Toplu işaretleme: yalnız Genel bakışta, iki adımlı onayla; hiçbir kısayol tetiklemez. */
function tumunuIsaretle() {
  const o = cur(); if (!o || S.gorunum !== 'genel') return;
  const simdi = Date.now();
  if (!tumOnayAktif(o)) {
    const ms = S.sonGirdi === 'klavye' ? ONAY_KLAVYE_MS : ONAY_MS; // klavye/ekran okuyucu için pencere uzun
    S.tumOnay = { no: o.no, t: simdi, ms }; render();
    const kalan = kalemler(o).filter((x) => !zamanOf(o, x.key)).length;
    duyur(`Emin misin? ${kalan} kalem işaretlenecek. Onaylamak için düğmeye tekrar bas.`, true);
    setTimeout(() => { if (S.tumOnay && Date.now() - S.tumOnay.t >= ms - 100) { S.tumOnay = null; render(); } }, ms + 100);
    return;
  }
  S.tumOnay = null;
  kalemler(o).filter((x) => !zamanOf(o, x.key)).forEach((x) => isaretle(o.no, x.key, true, true));
  render();
}
/* Kaydedilemeyen ilk kaleme/nota git. */
function kayitGit() {
  const l = kayitSorunlari(); if (!l.length) return;
  const x = l[0];
  if (x.tur === 'kalem') {
    if (x.no !== S.sel) sec(x.no, { zorla: true });
    const o = cur(); if (!o) return;
    const i = kalemler(o).findIndex((k) => k.key === x.key);
    if (i < 0) { S.kayitsiz.delete(kk(x.no, x.key)); render(); return; } // anahtar sunucudan kalkmış: kayıt anlamsız
    S.gorunum = 'toplama'; kalemGit(i, { ac: true });
  } else {
    if (x.no !== S.sel) sec(x.no);
    popAc('not');
  }
}

/* ====================================================================== 7. Notlar */
/* Yerel not kaydı (kirli/kayıt/hata) sunucu metninin önündedir: poll yazılan notu ezmez.
   Başarısız kayıtta metin korunur ve kalıcı durum metni + üst pili görünür. */
const NOT = { yerel: new Map(), zaman: {} };
const notMetni = (o) => { const y = NOT.yerel.get(o.no); return y ? y.metin : (o.not_metin || ''); };
function notEtiketi(o) {
  const m = o ? notMetni(o).trim() : '';
  const y = o && NOT.yerel.get(o.no);
  const e = $('#notEtiket');
  const h = m ? `Not <i class="nokta n-ink" aria-hidden="true"></i><span class="not-ozet">${esc(m.length > 26 ? m.slice(0, 26) + '…' : m.replace(/\s+/g, ' '))}</span>${y && y.hata ? '<span class="not-hata" title="Kaydedilemedi">!</span>' : ''}` : 'Not';
  if (e.dataset.h !== h) { e.dataset.h = h; e.innerHTML = h; belgelerSigdir(); }
}
function notGuncelle() {
  const o = cur();
  notEtiketi(o);
  const ta = $('#notMetin');
  if (!o) return;
  const y = NOT.yerel.get(o.no);
  const hedef = notMetni(o);
  if (ta.dataset.no !== o.no) { ta.value = hedef; ta.dataset.no = o.no; }
  else if (document.activeElement !== ta && !(y && y.kirli) && ta.value !== hedef) ta.value = hedef;
  notDurumYaz(o);
}
function notPopGoster() { const o = cur(); if (!o) return; const ta = $('#notMetin'); ta.dataset.no = o.no; ta.value = notMetni(o); notDurumYaz(o); }
function notDurumYaz(o) {
  const y = NOT.yerel.get(o.no);
  const el = $('#notDurum');
  let yazi = '', hata = false;
  if (y && y.hata) { yazi = 'Kaydedilemedi — metin burada duruyor'; hata = true; }
  else if (y && y.kayit) yazi = 'Kaydediliyor…';
  else if (y && y.kirli) yazi = 'Kaydedilmedi';
  else if (o.not_zaman) yazi = 'Kaydedildi ' + isoStr(o.not_zaman);
  el.classList.toggle('hata', hata);
  const h = `<span>${esc(yazi)}${hata ? ' <button class="not-tekrar" data-act="not-tekrar">Tekrar dene</button>' : ''}</span><span>${$('#notMetin').value.length}/4000</span>`;
  if (el.dataset.h !== h) { el.dataset.h = h; el.innerHTML = h; }
}
function notPlanla(no) {
  clearTimeout(NOT.zaman[no]);
  NOT.zaman[no] = setTimeout(() => notKaydet(no), 1200);
}
/* Sipariş değişirken yarım kalan not hemen kaydedilir. */
function notGecis(eskiNo) {
  if (eskiNo && NOT.yerel.get(eskiNo) && NOT.yerel.get(eskiNo).kirli) notKaydet(eskiNo);
}
async function notKaydet(no) {
  clearTimeout(NOT.zaman[no]);
  const y = NOT.yerel.get(no);
  if (!y || !y.kirli || y.kayit) return;
  const o = S.by.get(no);
  const metin = y.metin.trim();
  if (o && metin === (o.not_metin || '').trim()) { NOT.yerel.delete(no); notGuncelle(); renderKayitPil(); return; }
  y.kayit = true; y.hata = false;
  S.notYazma[no] = performance.now();
  if (cur() && cur().no === no) notDurumYaz(cur());
  try {
    const r = await postJson('/api/not', { siparis: no, metin });
    const o2 = S.by.get(no);
    if (o2) { o2.not_metin = r.not_metin; o2.not_zaman = r.not_zaman; }
    y.kayit = false;
    if (NOT.yerel.get(no) === y && y.metin.trim() === metin) NOT.yerel.delete(no);
    else { y.kirli = true; notPlanla(no); }
  } catch (e) {
    y.kayit = false; y.hata = true;
    toast('Not kaydedilemedi: ' + hataMetni(e));
  } finally { S.notYazma[no] = performance.now(); }
  notGuncelle(); renderKayitPil();
}
/* Notu olan siparişe girince önizleme kısa süre vurgulanır (gözden kaçmasın). */
let notVurguZ = 0;
function notVurgula() {
  const o = cur(); const b = $('#notBtn');
  clearTimeout(notVurguZ); b.classList.remove('vurgu');
  if (o && notMetni(o).trim()) { b.classList.add('vurgu'); notVurguZ = setTimeout(() => b.classList.remove('vurgu'), 3000); }
}

/* ====================================================================== 8. Yüzen katmanlar / tema */
const POP = () => ({
  tema: [$('#temaMenu'), $('#temaBtn')], kisayol: [$('#kisayolPop'), $('#kisayolBtn')],
  not: [$('#notPop'), $('#notBtn')], belge: [$('#belgeMenu'), $('.belge-daha')],
});
function popAc(ad) {
  popKapat();
  const [el, tetik] = POP()[ad];
  if (!el || !tetik) return;
  if (ad === 'belge') {
    el.innerHTML = S.belgeGizli.map((h) => `<div class="belge-oge">${h}</div>`).join('');
    const r = tetik.getBoundingClientRect();
    el.style.top = r.bottom + 6 + 'px'; el.style.left = Math.max(8, Math.min(innerWidth - 240, r.left)) + 'px';
  }
  S.pop = ad; S.popKlavye = S.sonGirdi === 'klavye'; el.classList.add('ac'); el.removeAttribute('inert'); tetik.setAttribute('aria-expanded', 'true');
  if (ad === 'not') { notPopGoster(); setTimeout(() => $('#notMetin').focus(), 40); }
  if (ad === 'tema') { const a = $('[aria-checked="true"]', el); if (a) a.focus({ preventScroll: true }); }
  if (ad === 'kisayol') setTimeout(() => $('#kisayolAnahtar').focus({ preventScroll: true }), 40); // diyalog açılınca odak içinde
  if (ad === 'belge' && S.popKlavye) { const a = $('a, button', el); if (a) a.focus({ preventScroll: true }); }
}
function popKapat() {
  if (!S.pop) return;
  const ad = S.pop; S.pop = null;
  const [el, tetik] = POP()[ad];
  if (!el) return;
  el.classList.remove('ac'); el.setAttribute('inert', ''); if (tetik) tetik.setAttribute('aria-expanded', 'false');
  if (ad === 'not') { const no = $('#notMetin').dataset.no; if (no) notKaydet(no); }
  // Klavyeyle açıldıysa odak tetik düğmeye döner; fareyle açıldıysa gövdede kalır (tetikte kalan odak Space'i yutup paneli yeniden açardı)
  if (tetik && el.contains(document.activeElement)) { if (S.popKlavye) tetik.focus({ preventScroll: true }); else document.activeElement.blur(); }
}
/* Modal benzeri katmanlar açıkken arka yüzey inert olur (odak/okuyucu içeride kalır) ve kapanınca odak yerine döner. */
const inertle = (liste, ac) => liste.forEach((e) => { if (e) { if (ac) e.setAttribute('inert', ''); else e.removeAttribute('inert'); } });
const ARKA_SISTEM = () => [$('#app'), $('.atla-bag')];
const ARKA_RAY = () => [$('.ust'), $('#uyariKutu'), $('#sahne'), $('.atla-bag')];
const ARKA_UC = () => [$('.ust'), $('#uyariKutu'), $('#ray'), $('.sb'), $('#ic'), $('#gozSirasi'), $('.atla-bag')];
function odakGeri(icerik, tetik, klavye) {
  const a = document.activeElement;
  if (!icerik || !(a === document.body || !a || icerik.contains(a))) return; // odak başka yere gitmişse dokunma
  if (klavye && tetik) tetik.focus({ preventScroll: true }); else if (a && a !== document.body) a.blur();
}
function sistemAc(ac) {
  S.sistemAcik = ac;
  const p = $('#sistemPanel');
  if (ac) S.sistemKlavye = S.sonGirdi === 'klavye';
  p.classList.toggle('ac', ac); if (ac) p.removeAttribute('inert'); else p.setAttribute('inert', '');
  $('#sistemBtn').setAttribute('aria-expanded', String(ac));
  perdeGuncelle();
  inertle(ARKA_SISTEM(), ac);
  if (ac) { renderSistem(); setTimeout(() => $('.ikon-btn', p).focus({ preventScroll: true }), 50); } else odakGeri(p, $('#sistemBtn'), S.sistemKlavye);
}
function rayAc() {
  if (genis()) { odakDegistir(); return; }
  S.rayAcik = true; S.rayKlavye = S.sonGirdi === 'klavye'; $('#ray').classList.add('ac'); perdeGuncelle();
  inertle(ARKA_RAY(), true);
  setTimeout(() => { const k = $('.ray-kapat'); if (k && S.rayAcik) k.focus({ preventScroll: true }); }, 60);
}
function rayKapat() {
  if (!S.rayAcik) return;
  S.rayAcik = false; $('#ray').classList.remove('ac'); perdeGuncelle();
  inertle(ARKA_RAY(), false);
  odakGeri($('#ray'), $('#rayAcBtn'), S.rayKlavye);
}
function perdeGuncelle() { $('#perde').classList.toggle('ac', S.sistemAcik || S.rayAcik); }
function odakDegistir(v) {
  S.odak = v === undefined ? !S.odak : v;
  document.documentElement.classList.toggle('odak', S.odak);
  $('#rayAcBtn').setAttribute('aria-pressed', String(S.odak));
  depo.yaz('adaptx_odak', S.odak ? '1' : '0');
  requestAnimationFrame(belgelerSigdir);
}
let toastZ = 0;
function toast(m) {
  const t = $('#toast'); t.textContent = m; t.classList.add('ac');
  clearTimeout(toastZ); toastZ = setTimeout(() => t.classList.remove('ac'), 3000);
}
function temaUygula(id, kaydet = true) {
  if (!TEMALAR.some((t) => t.id === id)) id = 'acik';
  S.tema = id;
  document.documentElement.dataset.theme = id;
  const m = $('meta[name="color-scheme"]'); if (m) m.content = id === 'koyu' ? 'dark' : 'light';
  const tc = $('meta[name="theme-color"]'); if (tc) tc.content = getComputedStyle(document.documentElement).getPropertyValue('--tezgah').trim() || '#eceff1';
  if (kaydet) depo.yaz('adaptx_tema', id);
  $$('#temaMenu .tema-ogesi').forEach((b) => b.setAttribute('aria-checked', String(b.dataset.id === id)));
  if (UC.k) UC.k.renkleriGuncelle();
}
function temaMenuKur() {
  $('#temaMenu').innerHTML = TEMALAR.map((t) => `<button class="tema-ogesi" role="radio" data-act="tema-sec" data-id="${t.id}" aria-checked="false">
    <span class="tema-ornek" style="--tm:${t.m};background:linear-gradient(90deg, ${t.a} 50%, ${t.b} 50%)"><i style="background:${t.c}"></i></span><span>${t.ad}<small>${t.not}</small></span>${ikon('tik', 'i-tik')}</button>`).join('');
}
function temaDevir() {
  const i = TEMALAR.findIndex((t) => t.id === S.tema);
  temaUygula(TEMALAR[(i + 1) % TEMALAR.length].id);
}

/* ====================================================================== 9. Video / büyük görünüm / 3B */
/* Video: <video src="/video/<no>"> (Range destekli). Sunucu eşzamanlı akışı 3 ile sınırlar;
   kapanınca src kaldırılır (bağlantı yuvası serbest kalsın). */
const videoUrl = (no) => '/video/' + encodeURIComponent(no);
/* Durumlar (dialog[data-durum]): '' oynatıcı (tarayıcı kontrolleri açık) · 'yukle' ortada çubuk · 'sorun' boş durum (ikon, iki satır, Tekrar dene + İndir).
   Yükleme ve sorunda <video> gizlenir ve controls kapanır: tarayıcının kendi kontrolleri boş durumun altından görünmesin. */
function videoDurum(d) {
  const dlg = $('#videoDlg'), v = $('#videoEl');
  if (d) dlg.dataset.durum = d; else delete dlg.dataset.durum;
  v.controls = !d;
}
function videoSorun(baslik, metin) {
  $('#videoSorunBaslik').textContent = baslik;
  $('#videoMesaj').textContent = metin;
  videoDurum('sorun');
  const du = $('#videoDuyuru'); if (du) du.textContent = `${baslik}. ${metin}`;
}
let videoZ = 0;
/* Akış başlamazsa (Drive yavaş / yuva dolu) sessiz kalma: önce "yükleniyor", 8 sn sonra açıklayıcı ileti. Akış sonradan başlarsa kendiliğinden oynatıcıya döner. */
function videoBeklemeKur(v) {
  clearTimeout(videoZ);
  videoDurum('yukle');
  const du = $('#videoDuyuru'); if (du) du.textContent = 'Video yükleniyor';
  videoZ = setTimeout(() => { if (v.getAttribute('src') && v.readyState < 1) videoSorun('Video hâlâ başlamadı', 'Drive yavaş ya da akış yuvaları dolu olabilir. Beklemeye devam edebilir, tekrar deneyebilir ya da indirebilirsin.'); }, 8000);
}
function videoAc() {
  const o = cur(); if (!o || !o.video) return;
  const d = $('#videoDlg'); const v = $('#videoEl');
  $('#videoBaslik').textContent = `${o.no} · Animasyon`;
  $('#videoBilgi').textContent = `${o.video.ad} — ${boyutStr(o.video.boyut)}`;
  ['#videoIndir', '#videoIndir2'].forEach((id) => { const a = $(id); a.href = videoUrl(o.no); a.setAttribute('download', o.no + '.mp4'); });
  videoBeklemeKur(v);
  v.src = videoUrl(o.no);
  if (!d.open) d.showModal();
  v.play().catch(() => { /* otomatik oynatma engellenirse kullanıcı oynat'a basar */ });
}
/* Oynatma hatası: nedeni öğrenmek için 1 baytlık aralık isteği (503 = akış sınırı, 404 = video yok). */
function videoTekrar() {
  const v = $('#videoEl'); if (!v.getAttribute('src')) return;
  videoBeklemeKur(v); v.load(); v.play().catch(() => { /* kullanıcı oynat'a basar */ });
}
async function videoHata() {
  const v = $('#videoEl'); const src = v.getAttribute('src');
  if (!src) return;
  videoSorun('Video açılamadı', 'Birazdan tekrar dene ya da indir.');
  let m = 'Video şu an açılamadı. Birazdan tekrar dene ya da indir.';
  try {
    const ac = new AbortController();
    const r = await fetch(src, { headers: { Range: 'bytes=0-0' }, signal: ac.signal });
    ac.abort();
    if (r.status === 503) m = 'Şu an çok fazla video akışı var; birazdan tekrar dene ya da indir.';
    else if (r.status === 404) m = 'Bu siparişin videosu Drive’da bulunamadı.';
  } catch (e) { /* ağ hatası: genel ileti */ }
  if (v.getAttribute('src') === src) videoSorun('Video açılamadı', m);
}
function videoKapat() {
  const d = $('#videoDlg'); const v = $('#videoEl');
  if (d.open) d.close(); else videoTemizle();
}
function videoTemizle() {
  clearTimeout(videoZ);
  const v = $('#videoEl');
  v.pause(); v.removeAttribute('src'); v.load(); videoDurum('');
}

/* Büyük 360° görünüm: tepsideki görsel 768 px kareye büyür; dönüş şeridi 512 px. */
function buyukAc() {
  const o = cur(); if (!o) return;
  const key = curKey(o); const it = kalemler(o).find((x) => x.key === key); if (!it) return;
  const g = gorselYol(it.mk); if (!g) return;
  $('#buyukBaslik').textContent = it.ad;
  const bz = ozel(it.mk);
  const tur = g.tur512 ? `<div class="tepsi-tur" data-tur="${esc(g.tur512)}"${bz}></div>` : '';
  $('#buyukTepsi').innerHTML = `<div class="tepsi buyuk"><img class="tepsi-img" src="${esc(g.buyuk)}" alt="${esc(it.ad)}" draggable="false"${bz}>${tur}</div>`;
  $('#buyukAlt').textContent = [ACIKLAMA[it.mk], olcuAlt(it)].filter(Boolean).join(' · ');
  const dlg = $('#buyukDlg'); if (!dlg.open) dlg.showModal();
  const t = $('#buyukTepsi .tepsi'); if (t) { S.buyukTepsi = tepsiKur(t); S.buyukTepsi.yukle(); } // büyük görünümde şerit hemen iner
}
function buyukKapat() { const d = $('#buyukDlg'); if (d.open) d.close(); else buyukTemizle(); }
function buyukTemizle() { if (S.buyukTepsi) S.buyukTepsi.iptal(); S.buyukTepsi = null; $('#buyukTepsi').innerHTML = ''; }

/* 3B: uc.js ilk açılışta yüklenir; sahne kapanınca/sipariş değişince serbest bırakılır. */
const UC = { k: null, modul: null, jeton: 0, kenar: true };
function ucMesaj(html) { $('#ucMesaj').innerHTML = html ? `<div>${html}</div>` : ''; }
function ucModelListe(o) {
  $('#ucModeller').innerHTML = o.fbx.length > 1 ? o.fbx.map((f, i) => `<button class="btn-ikinci-kucuk" data-act="uc-model" data-i="${i}" aria-pressed="${i === S.ucIdx}"><span style="display:inline">Model ${i + 1}</span></button>`).join('') : '';
}
function ucOlcuYaz(ham) {
  const e = $('#ucOlcu');
  // FBX birimi doğrulanmadı: ölçü etiketi yalnız ?olcu=1 ile görünür.
  if (!ham || P.get('olcu') !== '1') { e.hidden = true; e.textContent = ''; return; }
  e.textContent = `${Math.round(ham.x)} × ${Math.round(ham.y)} × ${Math.round(ham.z)} mm`; e.hidden = false;
}
async function ucAc() {
  const o = cur(); if (!o || !o.fbx || !o.fbx.length || S.ucAcik) return;
  S.ucAcik = true; S.ucIdx = Math.min(S.ucIdx, o.fbx.length - 1);
  const benim = ++UC.jeton;
  const el = $('#uc'); el.hidden = false;
  S.ucKlavye = S.sonGirdi === 'klavye';
  inertle(ARKA_UC(), true); // modal davranışı: arka yüzey inert, odak 3B diyaloğuna
  el.tabIndex = -1; el.focus({ preventScroll: true });
  if (!azHareket()) el.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 200, easing: EASE });
  $('#ucBaslik').innerHTML = `${esc(o.no)}<span class="uc-ek"> · 3B model</span>`;
  $('#ucDurum').textContent = '';
  ucModelListe(o);
  ucMesaj(`<div class="yuk" id="ucYuk"><i></i></div><span>Model yükleniyor…</span>`);
  try {
    UC.modul = UC.modul || await import('./uc.js');
    if (benim !== UC.jeton || !S.ucAcik) return;
    if (!UC.k) UC.k = UC.modul.ucOlustur($('#ucTuval'), { azHareket: azHareket(), olcuEtiketi: ucOlcuYaz, etiket: `3B model, sipariş ${o.no}`, ipucu: 'ucIpucu' });
    UC.k.kenar(UC.kenar);
    await ucYukle(o, S.ucIdx, benim);
  } catch (e) {
    if (benim !== UC.jeton) return;
    console.error('3B açılamadı', e);
    ucHataMesaji(e);
  }
}
/* İleti nedene göre ayrılır: dosya sorunu ile cihaz (WebGL) sorunu aynı şey değildir. */
function ucHataMesaji(e) {
  let ilk = '3B görünüm bu cihazda açılamadı.';
  if (e && e.durum === 404) ilk = 'FBX dosyası sunucuda bulunamadı.';
  else if (e && e.durum) ilk = `FBX dosyası indirilemedi (HTTP ${e.durum}).`;
  ucMesaj(`${ikon('kutu')}<span>${ilk}</span><span class="soluk">Dosyayı FBX olarak indirip kendi programında açabilirsin.</span>`);
}
async function ucYukle(o, i, benim) {
  const f = o.fbx[i];
  $('#ucDurum').textContent = f.ad;
  ucMesaj(`<div class="yuk" id="ucYuk"><i></i></div><span>Model yükleniyor…</span>`);
  const sonuc = await UC.k.yukle('/fbx/' + encodeURIComponent(f.ad), (p) => { const y = $('#ucYuk'); if (y) y.style.setProperty('--p', Math.max(.05, p)); });
  if (sonuc && benim === UC.jeton) ucMesaj('');
}
function ucKapat() {
  if (!S.ucAcik) return;
  S.ucAcik = false; UC.jeton++;
  if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
  inertle(ARKA_UC(), false);
  odakGeri($('#uc'), $('#ucBtn'), S.ucKlavye); // gizlemeden önce: gizli öğeden odak zaten düşmüş olurdu
  $('#uc').hidden = true;
  if (UC.k) { UC.k.kapat(); UC.k = null; } // sahne, geometri, malzeme, ortam dokusu serbest; renderer paylaşımlı kalır
  ucOlcuYaz(null);
  ucMesaj('');
}

/* ====================================================================== 10. Olaylar */
function aksiyon(act, t) {
  switch (act) {
    case 'yenile': { const s = $('#yenileBtn svg'); if (s && !azHareket()) s.animate([{ transform: 'rotate(0)' }, { transform: 'rotate(360deg)' }], { duration: 600, easing: EASE }); yenile(); break; }
    case 'sec': case 'sec-sonraki': sec(t.dataset.no); break;
    case 'filtre': S.filtre = t.dataset.f; ilkineDon(); render(); break;
    case 'biten': S.bitenGizle = !S.bitenGizle; depo.yaz('adaptx_biten_gizle', S.bitenGizle ? '1' : '0'); ilkineDon(); render(); break;
    case 'yon': S.yon = -S.yon; $('#liste').scrollTop = 0; render(); break;
    case 'onceki-siparis': siparisGez(-1); break;
    case 'sonraki-siparis': siparisGez(1); break;
    case 'ray-ac': rayAc(); break;
    case 'ray-kapat': rayKapat(); break;
    case 'perde': sistemAc(false); rayKapat(); break;
    case 'sistem': sistemAc(!S.sistemAcik); break;
    case 'sistem-kapat': sistemAc(false); break;
    case 'tema': S.pop === 'tema' ? popKapat() : popAc('tema'); break;
    case 'tema-sec': temaUygula(t.dataset.id); break;
    case 'kisayol': S.pop === 'kisayol' ? popKapat() : popAc('kisayol'); break;
    case 'belge-daha': S.pop === 'belge' ? popKapat() : popAc('belge'); break;
    case 'not': S.pop === 'not' ? popKapat() : popAc('not'); break;
    case 'not-tekrar': { const no = $('#notMetin').dataset.no; if (no) notKaydet(no); break; }
    case 'kayit-git': kayitGit(); break;
    case 'bant-gordum': bantGordum(); break;
    case 'bant-git': bantGit(); break;
    case 'bant-ac': bantAcKapat(); break;
    case 'gorunum': gorunumDegistir(t.dataset.g); break;
    case 'isaretle': isaretleGecerli(); break;
    case 'atla': atla(); break;
    case 'geri-al': { const o = cur(); if (o) { const k = curKey(o); if (zamanOf(o, k)) { kilitle(350); isaretle(o.no, k, false); } } break; }
    case 'onceki': kalemYon(-1); break;
    case 'sonraki': kalemYon(1); break;
    case 'kalem-git': kalemGit(t.dataset.key); break;
    case 'kalem-ac': kalemGit(t.dataset.key, { ac: true }); break;
    case 'tik': tikGenel(t.dataset.key); break;
    case 'tumunu': tumunuIsaretle(); break;
    case 'video': videoAc(); break;
    case 'video-kapat': videoKapat(); break;
    case 'buyut': buyukAc(); break;
    case 'buyuk-kapat': buyukKapat(); break;
    case 'uc': ucAc(); break;
    case 'uc-kapat': ucKapat(); break;
    case 'uc-kenar': UC.kenar = !UC.kenar; if (UC.k) UC.k.kenar(UC.kenar); t.setAttribute('aria-pressed', String(UC.kenar)); break;
    case 'uc-sifirla': if (UC.k) UC.k.sifirla(); break;
    case 'uc-tam': { const el = $('#uc'); if (document.fullscreenElement) document.exitFullscreen(); else if (el.requestFullscreen) el.requestFullscreen().catch(() => {}); break; }
    case 'uc-model': { const o = cur(); S.ucIdx = +t.dataset.i; if (o && UC.k) { ucModelListe(o); ucYukle(o, S.ucIdx, UC.jeton).catch((e) => ucHataMesaji(e)); } break; }
    case 'uc-sol': if (UC.k) UC.k.dondur(-1, 0); break;
    case 'uc-sag': if (UC.k) UC.k.dondur(1, 0); break;
    case 'uc-yaklas': if (UC.k) UC.k.yakinlastir(1.2); break;
    case 'uc-uzaklas': if (UC.k) UC.k.yakinlastir(1 / 1.2); break;
    case 'video-tekrar': videoTekrar(); break;
    case 'kisayol-anahtar': kisayolAnahtar(!S.tekTus); break;
    default: break;
  }
}
document.addEventListener('click', (e) => {
  const t = e.target.closest('[data-act]');
  if (!t) return;
  if (e.detail > 0 && t.matches('button, a')) t.blur(); // fare tıklaması: odak düğmede kalmaz (Space işaretlemek yerine düğmeyi yeniden tetiklerdi)
  if (S.pop === 'belge' && t.closest('#belgeMenu')) popKapat();
  aksiyon(t.dataset.act, t);
});
/* Genel bakış kartlarında fare üstünde yalnız görsel döner (seçim/işaret değişmez). */
document.addEventListener('pointerover', (e) => {
  if (e.pointerType !== 'mouse') return;
  const gi = e.target.closest && e.target.closest('.gk-img');
  if (!gi || gi._tepsi) return;
  const o = cur(); const gk = gi.closest('.gk'); if (!o || !gk) return;
  const it = kalemler(o).find((x) => x.key === gk.dataset.key); const g = it && gorselYol(it.mk); if (!g || !g.tur) return;
  const t = document.createElement('div'); t.className = 'tepsi-tur'; t.dataset.tur = g.tur; if (BEYAZ.has(it.mk)) t.dataset.beyaz = ''; else if (KOYU.has(it.mk)) t.dataset.koyu = KOYU.get(it.mk); gi.appendChild(t);
  gi._tepsi = tepsiKur(gi); gi._tepsi.basla(e.clientX);
});
document.addEventListener('pointerdown', (e) => {
  S.sonGirdi = 'fare';
  if (S.pop && !e.target.closest('.pop, #temaBtn, #kisayolBtn, #notBtn, .belge-daha')) popKapat();
}, true);
document.addEventListener('keydown', () => { S.sonGirdi = 'klavye'; S.sonTus = performance.now(); }, true);
document.addEventListener('fullscreenchange', () => {
  const b = $('#ucTam span'); if (b) b.textContent = document.fullscreenElement ? 'Tam ekrandan çık' : 'Tam ekran';
});
if (!document.fullscreenEnabled) $('#ucTam').hidden = true;

const arama = $('#aramaKutu');
arama.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); arama.blur(); } }); // Enter aramayı kabul eder; odak gövdeye döner (Space işaretlesin)
/* Sipariş listesi: tek Tab durağı + ok tuşlarıyla gezinme (roving tabindex). */
$('#liste').addEventListener('keydown', (e) => {
  if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(e.key)) return;
  const l = $$('.satir', $('#liste')); if (!l.length) return;
  const i = l.indexOf(document.activeElement);
  const j = e.key === 'Home' ? 0 : e.key === 'End' ? l.length - 1 : Math.min(l.length - 1, Math.max(0, i + (e.key === 'ArrowDown' ? 1 : -1)));
  e.preventDefault(); e.stopPropagation();
  l.forEach((x, k) => { x.tabIndex = k === j ? 0 : -1; });
  l[j].focus();
});
/* Tema menüsü: ok tuşları; Tab menüden çıkarken menüyü kapatır. */
$('#temaMenu').addEventListener('keydown', (e) => {
  const l = $$('.tema-ogesi', $('#temaMenu')); const i = l.indexOf(document.activeElement);
  if (['ArrowDown', 'ArrowRight', 'ArrowUp', 'ArrowLeft', 'Home', 'End'].includes(e.key)) {
    e.preventDefault(); e.stopPropagation();
    const j = e.key === 'Home' ? 0 : e.key === 'End' ? l.length - 1 : (i + (e.key === 'ArrowDown' || e.key === 'ArrowRight' ? 1 : -1) + l.length) % l.length;
    l[j].focus();
  } else if (e.key === 'Tab') popKapat();
});
let aramaZ = 0;
arama.addEventListener('input', () => { clearTimeout(aramaZ); aramaZ = setTimeout(() => { S.q = arama.value; ilkineDon(); render(); }, 180); });
$('#pencereSec').addEventListener('change', (e) => { S.pencere = +e.target.value; depo.yaz('adaptx_pencere', String(S.pencere)); ilkineDon(); render(); });
function kisayolAnahtar(v) {
  S.tekTus = v; depo.yaz('adaptx_kisayol', v ? '1' : '0');
  $('#kisayolAnahtar').setAttribute('aria-checked', String(v));
}
const nt = $('#notMetin');
nt.addEventListener('input', () => {
  const no = nt.dataset.no; if (!no) return;
  let y = NOT.yerel.get(no);
  if (!y) { y = { kayit: false }; NOT.yerel.set(no, y); }
  y.metin = nt.value; y.kirli = true; y.hata = false; // aynı nesne güncellenir: uçuştaki kayıt bitince yeni metni görür
  notEtiketi(cur()); notPlanla(no); const o = S.by.get(no); if (o) notDurumYaz(o);
  renderKayitPil();
});
nt.addEventListener('focusout', () => { const no = nt.dataset.no; if (no) notKaydet(no); });
$('#videoDlg').addEventListener('close', videoTemizle);
$('#videoDlg').addEventListener('click', (e) => { if (e.target === e.currentTarget) videoKapat(); });
$('#videoEl').addEventListener('error', () => { clearTimeout(videoZ); videoHata(); });
$('#videoEl').addEventListener('loadedmetadata', () => { clearTimeout(videoZ); videoDurum(''); const du = $('#videoDuyuru'); if (du) du.textContent = ''; });
$('#buyukDlg').addEventListener('close', buyukTemizle);
$('#buyukDlg').addEventListener('click', (e) => { if (e.target === e.currentTarget) buyukKapat(); });
new ResizeObserver(() => belgelerSigdir()).observe($('.sb-alt'));
if (document.fonts && document.fonts.ready) document.fonts.ready.then(belgelerSigdir); // yazı tipi gelince genişlikler değişir
document.addEventListener('visibilitychange', () => {
  if (document.hidden) { NOT.yerel.forEach((y, no) => { if (y.kirli && !y.hata) notKaydet(no); }); } else yenile();
});
window.addEventListener('beforeunload', (e) => {
  if (kayitSorunlari().length || [...NOT.yerel.values()].some((y) => y.kirli)) { e.preventDefault(); e.returnValue = ''; }
});

document.addEventListener('keydown', (e) => {
  const t = e.target;
  const yaziyor = t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || t.isContentEditable);
  if ($('#videoDlg').open || $('#buyukDlg').open) return; // modal kendi Esc/odak yönetimini yapar
  if (e.key === 'Escape') {
    if (S.pop) { popKapat(); return; }
    if (S.ucAcik) { if (!document.fullscreenElement) ucKapat(); return; }
    if (S.sistemAcik) { sistemAc(false); return; }
    if (S.rayAcik) { rayKapat(); return; }
    if (t === arama && (arama.value || S.q)) { arama.value = ''; S.q = ''; ilkineDon(); render(); return; }
    if (yaziyor) { t.blur(); return; }
    if (S.odak) odakDegistir(false);
    return;
  }
  if (yaziyor || e.ctrlKey || e.metaKey || e.altKey) return;
  const k = e.key;
  // WCAG 2.1.4: tek karakterli kısayollar kapatılabilir (Kısayollar penceresindeki anahtar); kapalıyken yalnız Enter/oklar/Esc kalır
  if (!S.tekTus && k.length === 1) return;
  if (S.ucAcik) { if (k === '?') { S.pop === 'kisayol' ? popKapat() : popAc('kisayol'); } return; }
  if (k === '/') { e.preventDefault(); if (S.odak) odakDegistir(false); if (!genis()) rayAc(); arama.focus(); arama.select(); return; }
  if (k === '?') { S.pop === 'kisayol' ? popKapat() : popAc('kisayol'); return; }
  const bt = t && t.closest && t.closest('button, a, summary, [role="radio"], [role="tab"], [role="switch"]');
  if (k === ' ' || k === 'Enter') {
    if (bt) return; // odaktaki düğme kendi tıklamasını yapar
    if (k === ' ') e.preventDefault();
    if (!e.repeat && S.gorunum === 'toplama') isaretleGecerli();
    return;
  }
  if (S.pop === 'tema') return;
  const toplama = S.gorunum === 'toplama';
  switch (k) {
    case 'j': siparisGez(1); break;
    case 'k': siparisGez(-1); break;
    case 'ArrowRight': case 'l': kalemYon(1); break;
    case 'ArrowLeft': case 'h': kalemYon(-1); break;
    case 'ArrowDown': if (toplama) { e.preventDefault(); kalemYon(1); } break;
    case 'ArrowUp': if (toplama) { e.preventDefault(); kalemYon(-1); } break;
    case 'g': case 'G': gorunumDegistir(S.gorunum === 'toplama' ? 'genel' : 'toplama'); break;
    case 'm': case 'M': ucAc(); break;
    case 't': case 'T': temaDevir(); break;
    case 'f': case 'F': odakDegistir(); break;
    default: break;
  }
});

/* ====================================================================== 11. Açılış */
/* URL kancaları: ?tema ?siparis ?gorunum=genel ?kalem ?tam=1 ?ara ?uc=1 ?olcu=1 ?sistem=1 ?liste=1 ?not=1 ?kisayol=1 ?video=1 */
function ilkAyar() {
  const s = P.get('siparis');
  if (s && S.by.has(s)) S.sel = s;
  const g = P.get('gorunum');
  if (g === 'genel' || g === 'toplama') S.gorunum = g;
  const kl = P.get('kalem');
  const o = S.by.get(S.sel);
  if (kl !== null && o) { const ks = kalemler(o); const i = /^\d+$/.test(kl) ? +kl : ks.findIndex((x) => x.key === kl); if (ks[i]) S.kalem[o.no] = ks[i].key; }
  if (P.get('tam') === '1' && o) S.incele.add(o.no);
  if (S.odak) odakDegistir(true);
  notVurgula();
  setTimeout(() => {
    if (P.get('uc') === '1') ucAc();
    if (P.get('sistem') === '1') sistemAc(true);
    if (P.get('liste') === '1' && !genis()) rayAc(); // dar ekranda liste çekmecesi; geniş ekranda liste zaten açık
    if (P.get('not') === '1') popAc('not');
    if (P.get('kisayol') === '1') popAc('kisayol');
    if (P.get('video') === '1') videoAc();
  }, 60);
}
function baslat() {
  const adaylar = [P.get('tema'), depo.al('adaptx_tema')].map((x) => TEMA_TAKMA[x] || x);
  const t = adaylar.find((x) => TEMALAR.some((y) => y.id === x)) || (matchMedia('(forced-colors: active), (prefers-contrast: more)').matches ? 'kontrast' : matchMedia('(prefers-color-scheme: dark)').matches ? 'koyu' : 'acik');
  temaMenuKur();
  temaUygula(t, !P.get('tema'));
  if (S.odak) document.documentElement.classList.add('odak');
  $('#rayAcBtn').setAttribute('aria-pressed', String(S.odak));
  kisayolAnahtar(S.tekTus);
  const q = P.get('ara'); if (q) { arama.value = q; S.q = q; }
  // manifest ve /api/durum paralel (zincir kısalır); ilk çizim manifest gelince yapılır
  S.manifestSoz = fetch('/static/parcalar/manifest.json').then((r) => (r.ok ? r.json() : {})).catch(() => ({})).then((m) => { S.manifest = m || {}; });
  yenile();
  { const sr = $('#gozSirasi'); sr.addEventListener('scroll', seritMaske, { passive: true }); new ResizeObserver(seritMaske).observe(sr); }
  new ResizeObserver(bantOlc).observe($('#uyariKutu')); // bant açılıp kapanınca / satır sayısı değişince
  { let gen = innerWidth; window.addEventListener('resize', () => { if (scrollY < 4 || innerWidth !== gen) mobilSigdir(); gen = innerWidth; }); } // adres çubuğu kayarken sayfa ortasında tepsi oynamasın
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(mobilSigdir);
  setInterval(() => { if (!document.hidden) yenile(); }, 10000);
  setInterval(() => { if (S.veri && !document.hidden) { renderUst(); mesajTurYama(); } }, 30000); // "Sonraki tur: N dk" sayacı
  // Görsel yüklenemezse (404) kutu simgesine düş
  document.addEventListener('error', (e) => {
    const im = e.target;
    if (im && im.tagName === 'IMG' && im.dataset.g) { const s = document.createElement('span'); s.className = 'yok-ikon'; s.innerHTML = ikon('kutu'); im.replaceWith(s); }
  }, true);
}
baslat();
