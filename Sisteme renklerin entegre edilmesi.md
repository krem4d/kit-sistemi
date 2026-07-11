Linco linco kapağı tıpa parçaları birden fazla renk seçeneği olan parçalara bunları jsondan ürünün hangi renk olduğunu çekip buna göre bu parçaların hangi renkte olucaklarını sana anlatıcam 

Beyaz  = "0"
Mese = "1"
Gri = "2"

Beyaz 
Linco ,Linco kapağı ,tıpa = beyaz 

Meşe 
Linco ,Linco kapağı = siyah
Tıpa = kahverengi

Gri 
Linco ,Linco kapağı ,tıpa = siyah

Her siparişin bir rengi olucak aradığımız renk en çok geçen renk olucak buna göre dosyayı inceleyip ayarlarsın dosya içindeki diğer bilgilere ihtiyacımız yok yine aynı şekilde fbx ve videoyada yaptığımız gibi kolayca indirme yeri olsun panelden 



Small update 

Panelde videonun olduğu basma tuşuna basınca direkt indirsin videoyu başka bir tabde açıyodu en son bunuda düzelt 

---

## Durum: Uygulandı

- `renkler/<sipariş>.json` — Mert'in fbx ile birlikte yüklediği, aynen buradaki gibi
  `parcalar[].user_data.renk` kodu içeren dosya; `fbx_indir.sh` fbx/video ile aynı Drive
  klasöründen indirir (bkz. `Örnekjson.json` örneği).
- `parca_sayim.py::siparis_rengi_belirle` — siparişteki en çok geçen renk kodunu bulur,
  yukarıdaki tabloya göre Linco Gövde/Linco Kapak/Tıpa rengini türetir, `jsons/<sipariş>.json`
  içine `"renk"` alanı olarak yazar (detaylar: `parca_kurallari.md` "Renk" bölümü,
  `AGENTS.md` §4g).
- `pdf_uret.py` — PDF'e "Sipariş Rengi" satırı + Linco/Tıpa hücrelerine parantez içi renk.
- `panel.py`/`panel.html` — fbx/video ile aynı şekilde **Renk** indirme butonu (ham
  `renkler/<sipariş>.json`'u indirir, etiketinde hesaplanan rengi gösterir).
- Video indirme küçük güncellemesi zaten uygulanmış durumdaydı: "Animasyon" butonu
  `download` attribute'u ve sunucu tarafında `Content-Disposition: attachment` ile
  doğrudan indiriyor, yeni sekmede açmıyor (bkz. `panel.html`/`panel.py::_video_akit`).