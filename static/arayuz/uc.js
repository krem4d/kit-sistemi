/* Sipariş FBX görüntüleyicisi (three.js). panel.js bu dosyayı yalnız 3B açılınca
   dynamic import ile yükler; three importmap'ten gelir (panel.html).

   Görünüm: RoomEnvironment ışığı, tema zemininden belirgin ayrışan nötr yüzler
   (--m-panel), 30° üzerindeki kenarlara ince çizgi (--m-kenar). Sahne, geometri,
   malzeme ve ortam dokusu kapat()'ta serbest bırakılır; WebGLRenderer ise modül düzeyinde TEK kez
   yaratılıp paylaşılır (her açılışta yeni renderer yaratmak three r186'da yer tutucu doku önbelleği
   üzerinden canvas + WebGL bağlamı sızdırıyordu: 30 aç-kapa = 30 canvas). */
import * as T from 'three';
import { FBXLoader } from 'three/addons/loaders/FBXLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

const KENAR_ACISI = 30; // derece: bundan keskin kenarlara çizgi
const KLAVYE_ADIM = Math.PI / 12; // ok tuşu = 15°

let ortakR = null;
function ortakRenderer() {
  if (ortakR && !ortakR.getContext().isContextLost()) return ortakR;
  ortakR = new T.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
  return ortakR;
}

/* Temas gölgesi: model havada durmasın. Yumuşak radyal doku, modelin ayak izine ölçeklenir. */
function golgeDokusu() {
  const c = document.createElement('canvas'); c.width = c.height = 128;
  const g = c.getContext('2d');
  const gr = g.createRadialGradient(64, 64, 4, 64, 64, 62);
  gr.addColorStop(0, 'rgba(0,0,0,.34)'); gr.addColorStop(.55, 'rgba(0,0,0,.14)'); gr.addColorStop(1, 'rgba(0,0,0,0)');
  g.fillStyle = gr; g.fillRect(0, 0, 128, 128);
  const t = new T.CanvasTexture(c); t.colorSpace = T.SRGBColorSpace;
  return t;
}

function malzemeAt(m) {
  (Array.isArray(m) ? m : [m]).forEach((x) => {
    if (!x) return;
    for (const v of Object.values(x)) if (v && v.isTexture) v.dispose();
    x.dispose();
  });
}

/* tuval: canvas'ın ekleneceği kap. secenek: { azHareket, olcuEtiketi(boy)->void }.
   Dönen nesne: yukle(url, ilerleme), renkleriGuncelle(), kenar(bool), sifirla(), dondur(dx, dy), yakinlastir(oran), kapat().
   secenek.etiket / secenek.ipucu: tuvalin erişilebilir adı ve açıklayan öğenin id'si. */
export function ucOlustur(tuval, secenek = {}) {
  const r = ortakRenderer();
  r.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
  r.toneMapping = T.NeutralToneMapping || T.ACESFilmicToneMapping;
  const tv = r.domElement;
  tv.tabIndex = 0; tv.setAttribute('role', 'img'); tv.setAttribute('aria-label', secenek.etiket || '3B model');
  if (secenek.ipucu) tv.setAttribute('aria-describedby', secenek.ipucu);
  tuval.appendChild(tv);

  const sahne = new T.Scene();
  const pm = new T.PMREMGenerator(r);
  const ortam = pm.fromScene(new RoomEnvironment(), 0.04);
  sahne.environment = ortam.texture;
  pm.dispose();
  const gunes = new T.DirectionalLight(0xffffff, 1.2); gunes.position.set(60, 100, 80); sahne.add(gunes);
  sahne.add(new T.HemisphereLight(0xffffff, 0x8a8f96, 0.4));

  const kam = new T.PerspectiveCamera(32, 1, 0.1, 10000);
  const ctl = new OrbitControls(kam, r.domElement);
  ctl.enableDamping = true; ctl.dampingFactor = 0.08;
  ctl.autoRotate = !secenek.azHareket; ctl.autoRotateSpeed = 0.6;
  ctl.addEventListener('start', () => { ctl.autoRotate = false; });

  const golgeTex = golgeDokusu();
  const golge = new T.Mesh(new T.PlaneGeometry(1, 1), new T.MeshBasicMaterial({ map: golgeTex, transparent: true, depthWrite: false }));
  golge.rotation.x = -Math.PI / 2; golge.visible = false; golge.renderOrder = -1; sahne.add(golge);

  const panelMat = new T.MeshStandardMaterial({ roughness: 0.85, metalness: 0, side: T.DoubleSide, polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1 });
  const kenarMat = new T.LineBasicMaterial({ transparent: true, opacity: 0.55 });
  let kenarlar = [];
  let kenarAcik = true;
  let grup = null;
  let boy = null;
  let kirli = true;
  let raf = 0;
  let kapali = false;
  let abort = null;
  let jeton = 0;

  function renkleriGuncelle() {
    const cs = getComputedStyle(document.documentElement);
    panelMat.color.set(cs.getPropertyValue('--m-panel').trim() || '#e8eaed');
    kenarMat.color.set(cs.getPropertyValue('--m-kenar').trim() || '#2b3138');
    r.toneMappingExposure = parseFloat(cs.getPropertyValue('--m-poz')) || 1;
    kirli = true;
  }
  renkleriGuncelle();

  function boyutla() {
    const w = tuval.clientWidth, h = tuval.clientHeight;
    if (!w || !h) return;
    r.setSize(w, h, false); kam.aspect = w / h; kam.updateProjectionMatrix(); kirli = true;
  }
  const ro = new ResizeObserver(boyutla); ro.observe(tuval); boyutla();
  ctl.addEventListener('change', () => { kirli = true; });

  function tick() {
    raf = requestAnimationFrame(tick);
    if (document.hidden) return;
    const degisti = ctl.update();
    if (degisti || kirli) { r.render(sahne, kam); kirli = false; }
  }
  tick();

  function modeliBosalt() {
    if (!grup) return;
    sahne.remove(grup);
    grup.traverse((n) => {
      if (n.geometry) n.geometry.dispose();
      if (n.isMesh && n.material !== panelMat) malzemeAt(n.material);
    });
    grup = null; kenarlar = []; boy = null; golge.visible = false;
    if (secenek.olcuEtiketi) secenek.olcuEtiketi(null);
  }

  function kameraSifirla() {
    if (!boy) return;
    const R = Math.hypot(boy.x, boy.y, boy.z) / 2;
    // dar (dikey) ekranda yatay görüş alanı dardır: sığdırma küçük olan görüş alanına göre
    const vf = (kam.fov * Math.PI) / 180;
    const hf = 2 * Math.atan(Math.tan(vf / 2) * kam.aspect);
    const d = (R / Math.sin(Math.min(vf, hf) / 2)) * 1.12; // %12 pay: model kenara/tavana yapışmasın
    kam.position.set(0.62, 0.42, 0.66).normalize().multiplyScalar(d);
    kam.near = d / 200; kam.far = d * 40; kam.updateProjectionMatrix();
    ctl.target.set(0, 0, 0); ctl.update(); kirli = true;
  }

  /* Klavye / düğme karşılığı: sürükleme ve tekerleğin tek işaretçili alternatifi (WCAG 2.1.1, 2.5.7). */
  function dondur(dx, dy) {
    const fark = new T.Vector3().subVectors(kam.position, ctl.target);
    const sf = new T.Spherical().setFromVector3(fark);
    sf.theta -= (dx || 0) * KLAVYE_ADIM;
    sf.phi = Math.min(Math.PI - 0.05, Math.max(0.05, sf.phi - (dy || 0) * KLAVYE_ADIM));
    fark.setFromSpherical(sf); kam.position.copy(ctl.target).add(fark);
    ctl.autoRotate = false; ctl.update(); kirli = true;
  }
  function yakinlastir(oran) {
    const fark = new T.Vector3().subVectors(kam.position, ctl.target);
    const yeni = Math.min(ctl.maxDistance, Math.max(ctl.minDistance, fark.length() / oran));
    fark.setLength(yeni); kam.position.copy(ctl.target).add(fark);
    ctl.autoRotate = false; ctl.update(); kirli = true;
  }
  const tus = (e) => {
    const k = e.key; let ok = true;
    if (k === 'ArrowLeft') dondur(-1, 0); else if (k === 'ArrowRight') dondur(1, 0);
    else if (k === 'ArrowUp') dondur(0, 1); else if (k === 'ArrowDown') dondur(0, -1);
    else if (k === '+' || k === '=') yakinlastir(1.2); else if (k === '-' || k === '_') yakinlastir(1 / 1.2);
    else if (k === 'Home' || k === '0') kameraSifirla(); else ok = false;
    if (ok) { e.preventDefault(); e.stopPropagation(); }
  };
  tv.addEventListener('keydown', tus);

  /* FBX'i kendimiz indiririz (iptal + ilerleme), FBXLoader yalnız ayrıştırır. */
  async function yukle(url, ilerleme) {
    const benim = ++jeton;
    if (abort) abort.abort();
    abort = new AbortController();
    modeliBosalt();
    const yanit = await fetch(url, { signal: abort.signal });
    if (!yanit.ok) throw Object.assign(new Error('FBX indirilemedi (HTTP ' + yanit.status + ')'), { durum: yanit.status });
    const toplam = +yanit.headers.get('Content-Length') || 0;
    const okuyucu = yanit.body.getReader();
    const parcalar = []; let alinan = 0;
    for (;;) {
      const { done, value } = await okuyucu.read();
      if (done) break;
      parcalar.push(value); alinan += value.length;
      if (ilerleme && toplam) ilerleme(alinan / toplam);
    }
    if (benim !== jeton || kapali) return null;
    const tampon = new Uint8Array(alinan);
    let ofs = 0; for (const p of parcalar) { tampon.set(p, ofs); ofs += p.length; }
    // FBXLoader bilinen zararsız uyarıları (ortografik kamera, Z-UP) her dosyada konsola basar; ayrıştırma süresince susturulur.
    const uyari = console.warn;
    console.warn = (...a) => { if (!(typeof a[0] === 'string' && a[0].startsWith('THREE.FBXLoader:'))) uyari.apply(console, a); };
    let obj;
    try { obj = new FBXLoader().parse(tampon.buffer, ''); } finally { console.warn = uyari; }
    if (benim !== jeton || kapali) { obj.traverse((n) => { if (n.geometry) n.geometry.dispose(); }); return null; }
    const yuzeyler = [];
    obj.traverse((n) => {
      if (!n.isMesh) return;
      malzemeAt(n.material);
      n.material = panelMat;
      yuzeyler.push(n); // kenar çizgileri model göründükten SONRA, dilimler hâlinde (aşağıda kenarlariUret)
    });
    const kutu = new T.Box3().setFromObject(obj);
    const ham = kutu.getSize(new T.Vector3());
    obj.position.sub(kutu.getCenter(new T.Vector3()));
    grup = new T.Group(); grup.add(obj);
    const olcek = 100 / (Math.max(ham.x, ham.y, ham.z) || 1);
    grup.scale.setScalar(olcek);
    sahne.add(grup);
    boy = ham.clone().multiplyScalar(olcek);
    golge.scale.set(Math.max(boy.x, 1) * 1.5, Math.max(boy.z, 1) * 1.5, 1);
    golge.position.set(0, -boy.y / 2 - 0.05, 0); golge.visible = true;
    // Ölçü etiketi FBX birimine bağlıdır (birim doğrulanmadı): çağıran yalnız bayrakla gösterir.
    if (secenek.olcuEtiketi) secenek.olcuEtiketi(ham);
    kameraSifirla();
    kirli = true;
    kenarlariUret(yuzeyler, benim); // beklenmez: model hemen görünür, çizgiler arkadan gelir
    return ham;
  }

  /* EdgesGeometry büyük FBX'te ana iş parçacığını yüzlerce ms tutuyordu (9351-4.fbx, 3,3 MB: ~530 ms; 4x yavaş CPU'da >2 sn).
     Mesh başına üretilir; her ~8 ms'de bir tarayıcıya nefes aldırılır (animasyon/girdi akar, model önce görünür). Bu sırada
     sipariş değişir ya da görünüm kapanırsa (jeton) bırakılır. Tek devasa mesh bölünemez: yine tek dilim olur. */
  async function kenarlariUret(liste, benim) {
    let t0 = performance.now();
    for (const n of liste) {
      if (benim !== jeton || kapali) return;
      if (performance.now() - t0 > 8) {
        await new Promise((coz) => setTimeout(coz, 0));
        if (benim !== jeton || kapali) return;
        t0 = performance.now();
      }
      if (!n.parent) continue;
      const k = new T.LineSegments(new T.EdgesGeometry(n.geometry, KENAR_ACISI), kenarMat);
      k.visible = kenarAcik; kenarlar.push(k); n.add(k); kirli = true;
    }
  }

  function kapat() {
    if (kapali) return;
    kapali = true; jeton++;
    if (abort) abort.abort();
    cancelAnimationFrame(raf);
    ro.disconnect();
    ctl.dispose();
    tv.removeEventListener('keydown', tus);
    modeliBosalt();
    panelMat.dispose(); kenarMat.dispose();
    golge.geometry.dispose(); golge.material.dispose(); golgeTex.dispose(); sahne.remove(golge);
    ortam.dispose();
    sahne.environment = null;
    r.renderLists.dispose();
    tv.remove(); // renderer paylaşımlıdır: dispose/forceContextLoss çağrılmaz, bir sonraki açılışta yeniden kullanılır
  }

  return {
    yukle, kapat, sifirla: kameraSifirla, renkleriGuncelle, dondur, yakinlastir,
    kenar(v) { kenarAcik = v; kenarlar.forEach((k) => { k.visible = v; }); kirli = true; },
    get kapali() { return kapali; },
  };
}
