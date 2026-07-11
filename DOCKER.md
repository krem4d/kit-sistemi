# Docker Servisi — Proxmox CT Kurulumu

Adaptx Otonom Kit'i **arka planda çalışan bir servis** olarak paketler: `fbx/` klasörünü
her **5 dakikada bir** kontrol eder, yeni sipariş(ler) gelince kendi kendine çalışır ve
PDF'leri `pdf/` klasörüne bırakır. Zaten işlenmiş siparişler tekrar işlenmez
(bkz. `islem_gecmisi.json` belleği), yeni siparişler özetin **sonuna** eklenir.

## Mimarî (konteyner)

- **Blender headless** → `parca_sayim.py` → `jsons/*.json`
- **python3 + matplotlib** → `pdf_uret.py` → `pdf/*.pdf` + özet
- **entrypoint döngüsü** → `POLL_INTERVAL` (varsayılan 300 sn) aralıkla `fbx/`'i tarar;
  yeni iş varsa boru hattını çalıştırır.

**Yollar statiktir:** konteyner içinde her şey `/data` altında (`/data/fbx`,
`/data/jsons`, `/data/pdf`). Host tarafında bu klasör bind-mount ile bağlanır — makineye
özgü tek şey bu mount yoludur, gerisi her yerde aynı çalışır.

---

## 1) Proxmox CT hazırlığı (Docker'ı LXC içinde çalıştırma)

Bir **Debian 12** LXC konteyneri oluşturun. Docker'ın LXC içinde çalışması için CT'nin
**nesting** özelliği açık olmalı (Proxmox host kabuğunda, `<CTID>` = konteyner no):

```bash
pct set <CTID> -features nesting=1,keyctl=1
pct reboot <CTID>
```

> Alternatif: Docker'ı doğrudan bir VM'de veya herhangi bir Linux makinede de aynı
> adımlarla çalıştırabilirsiniz; LXC'ye özgü tek gereksinim yukarıdaki `nesting` ayarıdır.

CT içine girip Docker'ı kurun:

```bash
apt update && apt install -y docker.io docker-compose-plugin git
systemctl enable --now docker
```

## 2) Projeyi CT'ye kopyalayın

Bu klasörün tamamını CT'ye taşıyın (örn. `scp`, `git clone` veya Proxmox dosya
paylaşımı ile) — örneğin `/opt/adaptx/` altına:

```bash
mkdir -p /opt/adaptx && cd /opt/adaptx
# ...proje dosyalarını buraya kopyalayın (Dockerfile, docker-compose.yml, *.py, calistir.sh, docker/)...
```

## 3) Veri klasörünü hazırlayın

```bash
mkdir -p /opt/adaptx/data/fbx /opt/adaptx/data/jsons /opt/adaptx/data/pdf
```

`docker-compose.yml` varsayılan olarak `./data`'yı `/data`'ya bağlar. Veriyi başka bir
diskte tutmak isterseniz compose'daki mount'un **sol** tarafını mutlak yol yapın:

```yaml
    volumes:
      - /mnt/depo/adaptx:/data
```

## 4) İmajı derleyip servisi başlatın

```bash
cd /opt/adaptx
docker compose build      # ilk sefer Blender indirir (~birkaç dk)
docker compose up -d
```

## 5) Kullanım

- Yeni sipariş: FBX dosyasını **`data/fbx/`** içine kopyalayın (dosya adında sipariş no
  geçmeli, örn. `9281.fbx` veya `9281-2.fbx`).
- Renk (opsiyonel): aynı sipariş no'suyla eşleşen bir `<sipariş>.json`'u
  **`data/renkler/`** içine koyarsanız (Mert'in `user_data.renk` formatı — bkz.
  `parca_kurallari.md` "Renk" bölümü), Linco Gövde/Kapak ve Tıpa renkleri PDF'e işlenir.
  Yoksa sayım aynen çalışır, renk alanı boş kalır.
- En geç 5 dakika içinde servis işler; sonuç:
  - `data/pdf/siparişler pdf/<sipariş>.pdf` (sipariş başına)
  - `data/pdf/siparisler_ozet*.pdf` (özet — yeni sipariş sona eklenir)

Logları izleme:

```bash
docker compose logs -f
```

---

## Ayarlar

| Değişken | Varsayılan | Açıklama |
|----------|-----------|----------|
| `POLL_INTERVAL` | `300` | Kontrol aralığı (saniye). `docker-compose.yml`'de değiştirin. |
| `ADAPTX_BASE` | `/data` | Konteyner içi veri kökü. **Değiştirmeyin** (mount ile eşleşir). |
| `BLENDER_VERSION` / `BLENDER_MAJOR` | `4.2.3` / `4.2` | build-arg. Yerel Blender'ınızla eşleştirmek için değiştirip yeniden `build` alın. |

## Sık işlemler

```bash
docker compose restart              # servisi yeniden başlat
docker compose down                 # durdur
docker compose up -d --build        # kod/sürüm değişince yeniden derle + başlat
docker compose exec adaptx bash /app/calistir.sh   # elle tek sefer çalıştır (beklemeden)
```

## Yeniden işletme (bir siparişi tekrar hesaplatmak)

Servis işlenmiş siparişi atlar. Bir siparişi tekrar işletmek için ilgili
`data/jsons/<sipariş>.json` (ve isterseniz `data/pdf/siparişler pdf/<sipariş>.pdf`)
dosyasını silin; sıralamayı tamamen sıfırlamak için `data/islem_gecmisi.json`'u silin.

## Notlar / sorun giderme

- **İlk build uzun sürer** (Blender indirilir). Sonraki build'ler katman önbelleğinden hızlıdır.
- **Blender sürümü:** Boolean tespiti sürümden büyük ölçüde bağımsızdır; yine de üretim
  sonuçlarını yerelinizle bire bir tutmak isterseniz `blender --version` çıktısındaki
  sürümü build-arg olarak verin.
- **Bellek/CPU:** EXACT boolean parça başına saniyeler alır; büyük siparişlerde CT'ye
  yeterli CPU/RAM verin. Aynı anda tek boru hattı çalışır (döngü sıralıdır, çakışma olmaz).
- **matplotlib kilidi yok:** PDF'ler konteynerde üretildiğinden LibreOffice `.~lock`
  sorunu oluşmaz; host'ta bir PDF'i açıkken tutmayın (üzerine yazılamayabilir).
