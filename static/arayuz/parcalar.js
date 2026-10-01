/* Parça sözlüğü: sıra, gram eşlemesi, birim ağırlık, açıklama ve kalem türetme.
   Tek kaynak; DOM'a dokunmaz (node ile de test edilebilir).

   Bu dosyadaki ROWS ve GRAM_KEY, pdf_uret.py'deki ROWS/GRAM_KEY ile aynı kalmalıdır.
   Ağırlıklar.md'ye parça eklenirse GRAM_KEY, BIRIM_GRAM ve ACIKLAMA birlikte güncellenir
   (yoksa parça gramını ve "Tartılarak sayılan" grubunu kaybeder). */

/* Checklist satır sırası (PDF ile aynı). Ray setleri 'L Bağlantı Seti'nin,
   askılık boru boyları 'Askılık Borusu'nun yerine girer. */
export const ROWS = [
  'Frenli Menteşe', 'Frensiz Menteşe', 'Menteşe Tabanı', 'Modülleri Birbirine Bağlama',
  'Raf Pimi', 'Linco Gövde', 'Linco Kapak', 'Linco Dübel', 'Minifix', 'Uzun Linco Pimi',
  'Ayarlı Ayak', 'Allen', 'Tıpa', 'Kulp', 'Kulp Vidası', 'L Bağlantı Seti',
  'Askılık Flanşı', 'Askılık Borusu', 'Ağaç Vidası', 'Arkalık Çivisi',
];

/* Tartılarak sayılan parça -> /api/durum `gram` sözlüğündeki anahtar (adlar farklı olabilir). */
export const GRAM_KEY = {
  'Raf Pimi': 'Raf Pimi', 'Linco Gövde': 'Linco', 'Linco Kapak': 'Linco Kapak',
  'Linco Dübel': 'Linco Dübel', 'Minifix': 'Minifix', 'Ağaç Vidası': 'Ağaç Vidası',
  'Arkalık Çivisi': 'Çivi',
};

/* Birim ağırlık (g/adet), Ağırlıklar.md. Yuvarlanmış toplamdan türetmek yanıltır, o yüzden sabit. */
export const BIRIM_GRAM = {
  'Raf Pimi': 2.7, 'Ağaç Vidası': 1.108, 'Minifix': 3.401, 'Linco Dübel': 4.4,
  'Linco Gövde': 4.631, 'Linco Kapak': 0.216, 'Arkalık Çivisi': 0.335,
};

/* Tek cümlelik açıklama: yeni toplayıcı benzer parçaları karıştırmasın. */
export const ACIKLAMA = {
  'Frenli Menteşe': 'Kapağı yavaş ve sessiz kapatan frenli menteşe.',
  'Frensiz Menteşe': 'Fren mekanizması olmayan sade menteşe.',
  'Menteşe Tabanı': 'Menteşenin gövdeye vidalandığı taban plakası.',
  'Modülleri Birbirine Bağlama': 'Yan yana modülleri birbirine tutturan bağlantı aparatı.',
  'Raf Pimi': 'Rafı yerinde tutan küçük pim.',
  'Linco Gövde': 'Panelleri birbirine kilitleyen linco bağlantısının gövdesi.',
  'Linco Kapak': 'Linco gövdesinin üstünü örten küçük plastik kapak.',
  'Linco Dübel': 'Linco kilidine eşlik eden ahşap dübel.',
  'Minifix': 'Linco ile birlikte çalışan çelik kilit cıvatası.',
  'Uzun Linco Pimi': 'L biçimli modüllerde iki linco yerine konan tek uzun pim.',
  'Ayarlı Ayak': 'Dolabın yüksekliğini ayarlayan ayak.',
  'Allen': 'Ayarlı ayakları ayarlamak için allen anahtarı.',
  'Tıpa': 'Delik ya da ayak yuvasını kapatan küçük tıpa.',
  'Kulp': 'Kapak ve çekmece tutamağı.',
  'Kulp Vidası': 'Kulpları sabitleyen vida.',
  'L Bağlantı Seti': 'Dolabı duvara bağlayan L braket; vida ve dübeli dahil.',
  'Askılık Flanşı': 'Askılık borusunu tutan flanş.',
  'Askılık Borusu': 'Elbise asmak için boru; boyu siparişe göre kesilir.',
  'Ağaç Vidası': 'Ahşaba vidalanan genel amaçlı vida.',
  'Arkalık Çivisi': 'Arkalık panelini çerçeveye çakan çivi.',
  'Ray Seti': 'Çekmece rayı; sol ve sağ iki ray bir set sayılır.',
};

/* Beyaz plastik parçalar: renderlar koyu zemine göre pozlandığı için açık temalarda gri kalır;
   panel.css bunlara tema başına bir parlaklık filtresi (--bf) uygular. Yeni beyaz parça eklenirse buraya. */
export const BEYAZ = new Set(['Linco Kapak', 'Tıpa']);

/* Koyu (siyah) parçalar koyu temada --kucuk-zemin'e karışır; panel.css bunlara yalnız koyu temada parlaklık filtresi uygular
   ('g' güçlü: Allen neredeyse tamamen siyah; 'h' hafif: Ayarlı Ayak'ın yalnız tabanı siyah, gövdesi metal). Ölçüm ve gerekçe:
   PANEL.md "Temalar". Yeni siyah parça eklenirse buraya. */
export const KOYU = new Map([['Allen', 'g'], ['Ayarlı Ayak', 'h']]);

/* Checklist anahtarından insan etiketi. */
export function etiket(key) {
  if (key === 'Modülleri Birbirine Bağlama') return 'Modül Bağlantı';
  // \u00a0: "96 cm" satır sonunda bölünmesin
  if (key.startsWith('ray:')) return 'Ray Seti ' + key.slice(4).replace(/(\d)\s*cm$/i, '$1\u00a0cm');
  if (key === 'boru:?') return 'Askılık Borusu · boy belirsiz'; // "? cm" ham gösterilmesin
  if (key.startsWith('boru:')) return 'Askılık Borusu ' + key.slice(5) + '\u00a0cm';
  return key;
}

/* Boru/ray anahtarının boyu ayrı (Genel bakış kartında adın altında değil, gram yuvasında): '96 cm' | 'boy belirsiz' | null. */
export function boyEtiketi(key) {
  if (key === 'boru:?') return 'boy belirsiz';
  let m = /^boru:(\d+(?:[.,]\d+)?)$/.exec(key);
  if (m) return m[1] + '\u00a0cm';
  m = /^ray:(\d+)\s*cm$/i.exec(key);
  return m ? m[1] + '\u00a0cm' : null;
}

/* Checklist anahtarı -> görsel/açıklama/birim ağırlık sözlüklerindeki anahtar. */
export function temelAnahtar(key) {
  if (key.startsWith('ray:')) return 'Ray Seti';
  if (key.startsWith('boru:')) return 'Askılık Borusu';
  return key;
}

/* Siparişteki adet. Ray: set sayısı (2 ray = 1 set). Boru: boy satırı. */
export function adetOf(o, key) {
  if (key.startsWith('ray:')) return (o.ray_setleri || {})[key.slice(4)] ?? 0;
  if (key.startsWith('boru:')) {
    const b = (o.askilik_boylari || []).find((x) => String(x[0]) === key.slice(5));
    return b ? b[1] : 0;
  }
  return (o.adet || {})[key] ?? 0;
}

/* Siparişin kalemleri: checklist anahtarlarından türer (ROWS'tan değil), böylece sunucu
   yeni bir parça anahtarı üretirse satır kaybolmaz. Sıra: önce tartılanlar, sonra adetle
   sayılanlar; grup içinde ROWS sırası, ray setleri 'L Bağlantı Seti'nin, boru boyları
   'Askılık Borusu'nun yerinde (raylar büyükten küçüğe). Sonuç siparişte önbelleklenir
   (sipariş nesnesi her poll'de yenilenir, önbellek kendiliğinden düşer). */
export function kalemler(o) {
  if (o.__k) return o.__k;
  const ck = o.checklist || {};
  const tum = Object.keys(ck);
  const kalan = new Set(tum);
  const sira = [];
  const ekle = (k) => { if (kalan.has(k)) { sira.push(k); kalan.delete(k); } };
  const raylar = tum.filter((k) => k.startsWith('ray:')).sort((a, b) => parseInt(b.slice(4), 10) - parseInt(a.slice(4), 10));
  const borular = Array.isArray(o.askilik_boylari) ? o.askilik_boylari.map((x) => 'boru:' + x[0]) : tum.filter((k) => k.startsWith('boru:'));
  for (const k of ROWS) {
    if (k === 'Askılık Borusu') { borular.forEach(ekle); ekle(k); } else ekle(k);
    if (k === 'L Bağlantı Seti') raylar.forEach(ekle);
  }
  [...kalan].forEach(ekle);
  const ogeler = sira.map((key) => {
    const gk = GRAM_KEY[key];
    const gram = gk ? (o.gram || {})[gk] : null;
    return {
      key, mk: temelAnahtar(key), ad: etiket(key), adet: adetOf(o, key),
      adTemel: key.startsWith('ray:') ? 'Ray Seti' : key.startsWith('boru:') ? 'Askılık Borusu' : etiket(key),
      boy: boyEtiketi(key), belirsiz: key === 'boru:?',
      gram: typeof gram === 'number' && gram > 0 ? gram : null,
      tartili: !!gk, birim: key.startsWith('ray:') ? 'set' : 'adet',
    };
  });
  o.__k = [...ogeler.filter((x) => x.tartili), ...ogeler.filter((x) => !x.tartili)];
  return o.__k;
}

/* "Boy" bilgisi: boru/ray boyu anahtardan (cm, kesin); diğerleri manifest `boy_mm`
   (FBX ölçeği dosyadan dosyaya değiştiği için çoğu yaklaşık: boy_tahmin). */
export function boyBilgisi(key, man) {
  let m = /^boru:(\d+)$/.exec(key);
  if (m) return { mm: +m[1] * 10, yaklasik: false };
  m = /^ray:(\d+)\s*cm$/i.exec(key);
  if (m) return { mm: +m[1] * 10, yaklasik: false };
  if (man && typeof man.boy_mm === 'number' && man.boy_mm > 0) return { mm: man.boy_mm, yaklasik: !!man.boy_tahmin };
  return null;
}

/* Parça görsel yolları (manifest girdisinden). Küçük önizleme: 'kucuk' yoksa 'gorsel';
   büyük dönüş şeridi: 'tur_512' yoksa 'tur' (manifest yeni alanlarla genişleyince kendiliğinden geçer). */
export function gorselYollari(man) {
  if (!man || !man.gorsel) return null;
  const y = (p) => (p ? '/static/' + p : '');
  return { kucuk: y(man.kucuk || man.gorsel), buyuk: y(man.gorsel), tur: y(man.tur), tur512: y(man.tur_512 || man.tur) };
}
