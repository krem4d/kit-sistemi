# PROGRESS — Adaptx Otonom Kit

Güncel durum takibi. Ayrıntı için `PLAN.md`, `parca_kurallari.md`, `hacimler.md`.

## Faz 0 — Veri + Ölçüm araçları  ✅ tamam
- [x] `delikbulma.py` incelendi; `hacim_bul.py`, `kalinlik_bul.py`
- [x] Menteşe tabanı = 11454.0131, Kulp = 18665.5270 ölçüldü
- [x] Arkalık kalınlığı 5 mm vs gövde 18 mm ölçüldü

## Faz 1–2 — Sayım motoru + PDF  ✅ çalışıyor
- [x] `parca_sayim.py` (prep + tespit + türetme + gram), `pdf_uret.py`, `calistir.sh`
- [x] Path bug düzeltildi
- [x] Arkalık çivisi kalınlık-tabanlı entegre
- [x] **Raf pimi = delik/3** (her raf pimi 3 delik)
- [x] **Ayarlı ayak = orijinal kural** (parçada TAM 4 ağaç vidası → 1; `//4` hatası düzeltildi)
- [x] **PDF A4** + sayfa başına **14 sipariş** (7 yan yana + altına 7); >14 → `siparisler_ozet_2.pdf`
- [x] **Gram menüsü kaldırıldı**; ağırlıklı parçalar hücrede `adet / gram`
- [x] **Ağaç vidası kalibrasyonu**: `ahsapcivisi=19.48`, `TOLERANCE=%5` (güncel delikbulma.py)
- [x] **Ayarlı Ayak fix doğrulandı** (8990 → Object_5'te tam 4 → 1 ayak)
- [x] **L Bağlantı Seti = 2** (sabit); **Ağaç Vidası = türetme** (4×ayak+4×menteşe+4×L+3×askılık)
- [x] 21 sipariş işlendi; özet 14/sayfa → `siparisler_ozet.pdf` + `_2.pdf`

## 📊 Fotoğrafla doğrulama (gerçek siparişler)
**Birebir tutan (çekirdek sağlam):**
- Menteşe Tabanı, Frenli/Frensiz Menteşe → foto ile **tam uyum** (ör. 9285: 10/4/6)
- Kulp, Kulp Vidası → **tam uyum** (9285: 4/8) — kulp tespiti çalışıyor
- Modül yok / raf pimi yok olan siparişlerde 0'lar doğru

**Kalibrasyon/ince ayar gereken (sonraki iş):**
- [x] ~~Ayarlı Ayak~~ → 19.48 ile çözüldü (feet olan siparişte tetikleniyor)
- [ ] **Ağaç Vidası türetmesi** foto'dan düşük olabiliyor (9270: 32 vs 86) → formül rafine
      (gerçek L/askılık sayısı veya ek montaj vidaları eklenince)
- [ ] **Arkalık Çivisi** foto'dan düşük ve oran sabit değil (9285 80/100, 9303 20/50) →
      çivi formülü/aralığı yeniden bakılmalı (sadece aralık değil)
- [ ] **Modül bağlama** bazı siparişte sapıyor (9285 6/2) → eşleştirme eşiği gözden geçir
- [ ] **Raf Pimi & Linco** ~2 eksik çıkabiliyor (tolerans; linco 9646–9776 sınırda) →
      tolerans genişletme değerlendir
- [ ] **Linco ≠ Dübel** (linco 47, pim 53 tarzı) → +fark muhtemelen L Modül Uzun Linco Pimi

## Faz 4 — Ertelenenler (Mert)  ⬜ bekliyor
## Faz 5 — PDF format rötuşu  🟢 A4/14-sipariş/gram-inline tamam; renk/başlık ince ayar sonra

## Çalıştırma
`fbx/`'e sipariş FBX'leri → `bash calistir.sh` → `pdf/` altında `<sipariş>.pdf` + özet(ler).
(`parca_sayim.py` headless içindir; GUI'de açık sahneyi sıfırlar.)
