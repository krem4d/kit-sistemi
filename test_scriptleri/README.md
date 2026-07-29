# test_scriptleri/

Blender içinde elle çalıştırılan ölçüm ve teşhis araçları. Otomatik boru hattının
(`calistir.sh`) parçası **değildir** — hiçbiri `fbx/`, `jsons/`, `pdf/` klasörlerine
dokunmaz, sadece seçili objeleri ölçer.

## ⚠️ Scriptleri Blender'a YAPIŞTIRMA

Bir scripti Text Editor'e kopyala-yapıştır yaparsan, blend dosyasının içinde o kodun
donmuş bir kopyası kalır. Diskteki `.py`'yi sonradan düzeltsen bile Blender eski
kopyayı çalıştırmaya devam eder.

`delik bulma.blend` içinde tam olarak bu olmuştu: içeride `parca_sayim.py`'nin
**382 satırlık** eski bir kopyası duruyordu (diskteki hali 1085 satır). Rapor yazma
düzeltmeleri gerçekte çalışan koda hiç ulaşmadığı için raporlar "kaybolmuş"
görünüyordu.

## Kullanım

**Kurulum (bir kez):**
1. Blender > Scripting > Text Editor > **Open** (yapıştırma değil!)
2. `BLENDER_CALISTIR.py` dosyasını seç
3. Blend'i kaydet

**Her ölçümde:**
1. Viewport'ta objeleri seç
2. `BLENDER_CALISTIR.py` içindeki `ARAC = "..."` satırını değiştir
3. Run Script (Alt+P)

Çıktı yolu her çalıştırmada konsola basılır.

## Klasörler

| Klasör | İçerik |
|---|---|
| `ciktilar/` | Yeni rapor `.txt`'leri buraya düşer. Silinebilir, yeniden üretilir. |
| `olcumler/` | **Arşiv — silme.** `parca_sayim.py`'deki bazı sabitlerin tek yazılı dayanağı. Çalıştırmalar burayı asla ezmez. |

`olcumler/` içeriğinin koddaki karşılığı:

| Dosya | Neyin kanıtı |
|---|---|
| `hacim_bul_raporu.txt` | `RAY_DELIK_HACIM = 84.9181` (`parca_sayim.py:93`) |
| `iki_obje_mesafe_raporu.txt` | Ayak dikdörtgeni 32×40 mm (`parca_sayim.py:195`) |

## Araçlar

### Ölçüm (rapor üretir → `ciktilar/`)

| Araç | Ne yapar | Seçim |
|---|---|---|
| `hacim_bul` | Objenin kendi hacmi + içindeki delik hacimleri, bilinen kategorilerle eşleştirir | 1+ obje |
| `iki_obje_mesafe` | Seçili tüm objelerin ikili mesafeleri (rapora **ekler**, üzerine yazmaz) | 2+ obje |
| `kalinlik_bul` | MDF kalınlığı (en kısa kenar) — arkalık eşiği için | 1+ obje |
| `kulp_mesafe_bul` | Parçadaki delik mesafeleri | 1 obje |
| `linco_mesafe_bul` | İki parça arasındaki linco delik mesafeleri | 2 obje |
| `linco_uzun_pim_teshis` | Uzun linco pimi adayları + görsel Empty işaretleri | — |
| `collider_kutusu_goster` | Collider box boyutları | 1+ obje |

### Görsel (sahneye Empty koyar, rapor üretmez)

| Araç | Ne gösterir |
|---|---|
| `arkalik_civi_empty` | Arkalık paneli + çivi yerleşimi |
| `ray_delik_empty` | Ray'e özgü delikler |
| `ray_seti_empty` | Tespit edilen ray desenleri |
| `moduller_baglama_empty` | Modül-modül bağlantı delikleri |

## Çıktı yolu nasıl belirlenir

Her ölçüm scriptindeki `_resolve_output_dir()` sırayla dener:

| # | Aday | Ne zaman devreye girer |
|---|---|---|
| 1 | `ADAPTX_TEST_CIKTI` ortam değişkeni | Elle ayarlarsan |
| 2 | Scriptin kendi klasörü + `/ciktilar` | Diskten çalıştırıldığında (launcher) |
| 3 | Blend'in klasöründeki `test_scriptleri/ciktilar` | Blend proje içinde kaydedilmişse |
| 4 | **`SABIT_CIKTI_DIZINI`** | Yapıştırılmış script + kaydedilmemiş blend |
| 5 | `~/adaptx_test_ciktilari` | Hiçbiri olmazsa (uyarı basar) |

**4. adım neden sabit yazılı:** Script Text Editor'e yapıştırılıp blend
kaydedilmediğinde Blender `__file__`'ı `/Text` yapar ve `bpy.data.filepath` boş
olur — scriptin kendi yerini bulmasının *hiçbir* yolu kalmaz. Kaydetmeden test
etmek normal bir çalışma biçimi olduğu için yol scriptlerin başında sabittir:

```python
SABIT_CIKTI_DIZINI = "/home/rocket/Jupiter/Projects/otonom_kit/test_scriptleri/ciktilar"
```

> **Projeyi taşırsan** 7 ölçüm scriptindeki bu satırı güncelle. Boru hattı
> scriptleri (`parca_sayim.py`, `pdf_uret.py`, `panel.py`) hâlâ tamamen
> taşınabilir — sabit yol yalnızca bu teşhis araçlarında var, çünkü onlar
> sadece bu makinede Blender GUI'sinde çalışıyor.

1-3 dinamik olduğu için proje taşınsa bile launcher'la çalıştırdığında doğru
yeri kendiliğinden bulur; sabit yol yalnızca dinamik çözümün mümkün olmadığı
senaryoyu kurtarır.

**Tarihçe:** 5. adım eskiden sessizce `os.getcwd()` idi. Blender bir menüden
başlatıldığında cwd rastgele bir klasör oluyor, rapor oraya düşüyor ve
"hiç yazılmadı" sanılıyordu. Sonra `isdir()` kontrolü eklendi ama o da
yapıştırılmış scriptte `/` dizinini geçerli sayıp `/ciktilar` yaratmaya
çalıştı (`PermissionError`). Şimdiki sürüm dizini `BLENDER_CALISTIR.py`
işaret dosyasıyla doğruluyor ve her adayı önce yazılabilirlik testinden
geçiriyor — hiçbir adımda istisna fırlatmıyor.

## Algoritma dokümantasyonu

Bu araçların ölçtüğü sabitlerin nerede ve nasıl kullanıldığı:
[`../algoritmalar/`](../algoritmalar/00-genel-bakis.md)
