# Native systemd Servisi — Proxmox CT (Docker'sız)

Sayım boru hattını CT'de **native** (Docker'sız) çalıştırır: bir systemd **timer**
5 dakikada bir `servis_bir_tur.sh`'i tetikler; `fbx/` içinde yeni sipariş varsa
Blender sayımı + PDF üretimini çalıştırır, yoksa hiçbir şey yapmaz.

Akış: **rclone (cron) → `fbx/` → systemd timer (5 dk) → `jsons/` + `pdf/`**

Varsayılan proje yolu bu belgede `/opt/adaptx`. Başka yere klonladıysan
`systemd/adaptx.service` içindeki `WorkingDirectory` ve `ADAPTX_BASE`'i ona göre değiştir.

---

## 1) Bağımlılıklar (Blender + matplotlib)

```bash
apt update
apt install -y wget xz-utils python3-matplotlib \
  libx11-6 libxi6 libxxf86vm1 libxfixes3 libxrender1 libxkbcommon0 \
  libgl1 libegl1 libsm6 libice6 libxext6 libxrandr2 libxinerama1 \
  libxcursor1 libgomp1 libglib2.0-0

# Blender (headless) — sürümü yerelinle eşleştirmek istersen değiştir
BMAJ=4.2; BVER=4.2.3
wget -q "https://download.blender.org/release/Blender${BMAJ}/blender-${BVER}-linux-x64.tar.xz" -O /tmp/blender.tar.xz
mkdir -p /opt/blender
tar -xf /tmp/blender.tar.xz -C /opt/blender --strip-components=1
rm /tmp/blender.tar.xz
ln -s /opt/blender/blender /usr/local/bin/blender
blender --version    # doğrula
```

## 2) Repoyu güncelle (deploy key ile)

```bash
cd /opt/adaptx && git pull      # servis_bir_tur.sh + systemd/ dosyalarını çeker
chmod +x /opt/adaptx/servis_bir_tur.sh
```

## 3) Elle bir kez dene (kurulumdan önce doğrulama)

```bash
cd /opt/adaptx
ADAPTX_BASE=/opt/adaptx bash servis_bir_tur.sh
# fbx/ doluysa jsons/ ve pdf/ üretilmeli; boşsa "yeni sipariş yok" yazar.
```

## 4) systemd birimlerini kur ve etkinleştir

```bash
cp /opt/adaptx/systemd/adaptx.service /etc/systemd/system/
cp /opt/adaptx/systemd/adaptx.timer   /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now adaptx.timer
```

## 5) İzleme

```bash
systemctl list-timers adaptx.timer      # sonraki tetik zamanı
systemctl status adaptx.service         # son turun durumu
journalctl -u adaptx.service -f         # canlı log
```

---

## Yol uyumu (önemli)

rclone'un FBX'leri indirdiği klasör ile servisin taradığı klasör **aynı** olmalı:

- `ADAPTX_BASE=/opt/adaptx` → servis `fbx/` = **`/opt/adaptx/fbx`**
- rclone hedefi de **`/opt/adaptx/fbx`** olmalı.
- Çıktılar: **`/opt/adaptx/pdf`** (özet: `pdf/siparisler_ozet*.pdf`).

rclone'u farklı bir yola indiriyorsan ya rclone hedefini `/opt/adaptx/fbx` yap, ya da
`adaptx.service` içindeki `ADAPTX_BASE`'i rclone kökü ne ise ona ayarla.

## Ayarlar

- **Aralık:** `systemd/adaptx.timer` → `OnUnitActiveSec=5min` (istersen değiştir,
  sonra `cp` + `systemctl daemon-reload` + `systemctl restart adaptx.timer`).
- **Çakışma yok:** timer bir sonraki turu, önceki tur **bittikten** 5 dk sonra tetikler.

## Yeniden işletme (bir siparişi tekrar hesaplat)

Servis işlenmiş siparişi atlar. Tekrar işletmek için `jsons/<sipariş>.json`'u (ve
istersen `pdf/siparişler pdf/<sipariş>.pdf`) sil; sıralamayı sıfırlamak için
`islem_gecmisi.json`'u sil.
