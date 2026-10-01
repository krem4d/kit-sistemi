/* Saf veri mantığı: biçimleyiciler, ilerleme, süzme, poll birleştirme.
   DOM ve durum nesnesi bilmez; node ile test edilebilir. */

export const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

/* ---------- sayı / zaman biçimi (tr-TR, ondalık virgül; 0/null boş) ---------- */
const nf0 = new Intl.NumberFormat('tr-TR');
const nf1 = new Intl.NumberFormat('tr-TR', { maximumFractionDigits: 1 });
const nf3 = new Intl.NumberFormat('tr-TR', { maximumFractionDigits: 3 });
export const sayi0 = (n) => nf0.format(n);
export const sayi1 = (n) => nf1.format(n);
export const sayi3 = (n) => nf3.format(n);
export const fmtSayi = (n) => (n == null || n === 0 ? '' : Number.isInteger(n) ? nf0.format(n) : nf1.format(n));
const p2 = (n) => String(n).padStart(2, '0');
/* epoch saniye -> "GG.AA SS:DD" */
export const zamanStr = (e) => { if (!e) return '—'; const d = new Date(e * 1000); return `${p2(d.getDate())}.${p2(d.getMonth() + 1)} ${p2(d.getHours())}:${p2(d.getMinutes())}`; };
/* ISO -> "GG.AA SS:DD" */
export const isoStr = (iso) => { const d = new Date(iso); return isNaN(d) ? '' : `${p2(d.getDate())}.${p2(d.getMonth() + 1)} ${p2(d.getHours())}:${p2(d.getMinutes())}`; };
/* ISO -> bugünse "SS:DD", değilse "GG.AA" */
export const saatStr = (iso) => {
  const d = new Date(iso); if (isNaN(d)) return '';
  return d.toDateString() === new Date().toDateString() ? `${p2(d.getHours())}:${p2(d.getMinutes())}` : `${p2(d.getDate())}.${p2(d.getMonth() + 1)}`;
};
export const saatDk = (epoch) => { const d = new Date(epoch * 1000); return `${p2(d.getHours())}:${p2(d.getMinutes())}`; };
export const boyutStr = (b) => (b >= 1048576 ? nf1.format(b / 1048576) + ' MB' : nf1.format(b / 1024) + ' KB');
export const trKucuk = (s) => String(s).toLocaleLowerCase('tr-TR');

/* Sipariş no tireli olabilir ("9364-2"); tirenin tabular genişliği açılmasın diye ayrı işaretlenir. */
export function noHtml(no) {
  const s = String(no ?? '');
  const i = s.indexOf('-');
  return i < 0 ? esc(s) : `${esc(s.slice(0, i))}<i class="tire">-</i>${esc(s.slice(i + 1))}`;
}

/* ---------- ilerleme ---------- */
export const kk = (no, key) => no + '\0' + key;
/* [işaretli, toplam]: toplam = checklist anahtarı sayısı (sunucu anlamıyla aynı). */
export function ilerleme(o) {
  const v = Object.values(o.checklist || {});
  let t = 0;
  for (const x of v) if (x) t++;
  return [t, v.length];
}
export const tamamMi = (o) => { const [t, n] = ilerleme(o); return n > 0 && t === n; };

/* ---------- süzme ---------- */
export const FILTRELER = [['tumu', 'Tümü'], ['eksik', 'Eksik'], ['tamam', 'Tamamlanan'], ['bekleyen', 'Bekleyen'], ['hatali', 'Hatalı']];

/* q: küçük harfe çevrilmiş arama; f: filtre; bitenGizle yalnız 'tumu' filtresinde etkilidir
   (animasyonu olan ve tüm parçaları işaretli sipariş gizlenir) — eski panelin kasıtlı davranışı. */
export function gecer(o, q, f, bitenGizle) {
  if (q && !trKucuk(o.no).includes(q)) return false;
  const [t, n] = ilerleme(o);
  switch (f) {
    case 'bekleyen': return o.durum === 'bekliyor' || o.durum === 'isleniyor';
    case 'hatali': return o.durum === 'hatali';
    case 'eksik': return n > 0 && t < n;
    case 'tamam': return n > 0 && t === n;
    default: return !(bitenGizle && o.video && n > 0 && t === n);
  }
}

/* Sıra: süz -> pencereyle dilimle -> yönü uygula. Seçili sipariş pencere dilimi dışında kaldıysa
   (arama yoksa ve süzgeçten geçiyorsa) sona eklenir ki görünür kalsın. pencere 0 = tümü. yon: -1 azalan, 1 artan. */
export function listele(siparisler, { q, filtre, bitenGizle, pencere, yon, secili }) {
  const eslesen = siparisler.filter((o) => gecer(o, q, filtre, bitenGizle));
  let l = pencere > 0 ? eslesen.slice(0, pencere) : eslesen.slice();
  // Seçili sipariş yalnız PENCERE KIRPMASI yüzünden düştüyse sabitlenir (süzgeçten geçiyorsa). Süzgeç dışıysa sabitlenmez:
  // aksi hâlde "0 eşleşme" yazısının altında bir satır görünür ve boş durum mesajına hiç ulaşılamazdı. Sahnede seçili kalır.
  if (!q && secili && !l.some((o) => o.no === secili)) {
    const s = siparisler.find((o) => o.no === secili);
    if (s && gecer(s, q, filtre, bitenGizle)) l.push(s);
  }
  if (yon > 0) l = l.reverse();
  return { liste: l, eslesen: eslesen.length, kirpik: pencere > 0 && eslesen.length > pencere };
}

/* Gezinme sırası (j/k ve 'Sıradaki sipariş'): pencere dilimi ve sondan sabitleme olmadan, yalnız
   süzülmüş TAM liste. Seçili sipariş süzgeçten ya da pencereden düşse bile kendi doğal sırasında kalır;
   böylece pencere dışına kayan sipariş komşularını yanlış hesaplatmaz. */
export function gezinmeListesi(siparisler, { q, filtre, bitenGizle, yon, secili }) {
  const l = siparisler.filter((o) => gecer(o, q, filtre, bitenGizle) || (!q && o.no === secili));
  return yon > 0 ? l.reverse() : l;
}

/* ---------- poll birleştirme ----------
   yeni: /api/durum.siparisler (yerinde düzeltilir), eskiMap: no -> önceki sipariş,
   b: { basla, yazma:{no: ts}, notYazma:{no: ts}, ucusta:Set(kk) }
   Kural 1: istek, o siparişe son checklist yazımının BİTİŞİNDEN önce başladıysa yanıt bayattır
            (sunucu işaretten önceki durumu görmüş olabilir) -> yerel işaretler korunur.
   Kural 2: uçuştaki (yanıtı gelmemiş) işaret her durumda korunur.
   Kural 3: not için aynı bayatlık kuralı (notYazma). */
export function birlestir(yeni, eskiMap, b) {
  for (const o of yeni) {
    o.checklist = o.checklist || {};
    const e = eskiMap.get(o.no);
    if (!e) continue;
    const bayat = (b.yazma[o.no] || 0) > b.basla;
    for (const k of Object.keys(e.checklist || {})) {
      if (k in o.checklist && (bayat || b.ucusta.has(kk(o.no, k)))) o.checklist[k] = e.checklist[k];
    }
    if ((b.notYazma[o.no] || 0) > b.basla) { o.not_metin = e.not_metin; o.not_zaman = e.not_zaman; }
  }
  return yeni;
}

/* ---------- ağ hata iletisi ---------- */
export function hataMetni(e) {
  if (e && e.name === 'AbortError') return 'sunucu zamanında yanıt vermedi';
  if (e instanceof TypeError) return 'sunucuya ulaşılamadı';
  return (e && e.message) || 'bilinmeyen hata';
}
