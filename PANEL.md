# Adaptx Panel — Web İzleme + Checklist Arayüzü

Sayım hattını (rclone → `fbx/` → Blender → `jsons/` → `pdf/`) tarayıcıdan izlemek
ve her siparişi checklist ile takip etmek için native (Docker'sız, pip'siz)
bir web paneli. Sadece Python standart kütüphanesi kullanır — ek paket
kurulumu gerekmez.

Panel boru hattına karşı **salt okurdur**: `fbx/`, `jsons/`, `pdf/`,
`islem_gecmisi.json` yalnızca okunur. Yazdığı tek dosya `data/panel_checklist.json`'dur.
`adaptx.service`/`adaptx.timer` ve rclone cron'una hiçbir şekilde dokunmaz;
`adaptx-panel.service` içindeki `ProtectSystem=strict` + `ReadWritePaths=data/`
bunu systemd seviyesinde yapısal olarak garanti eder (panel bir hataya düşse bile
boru hattı verisine yazamaz).

PDF üretimi (özet + sipariş bazlı) aynen eskisi gibi çalışmaya devam eder; panel
sadece mevcut PDF'leri görüntüler/indirtir, yeni PDF üretmez.

---

## 1) Kurulum

```bash
cd /opt/adaptx
mkdir -p data
python3 -m py_compile panel.py    # sözdizimi doğrulaması
cp systemd/adaptx-panel.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now adaptx-panel.service
```

## 2) Erişim

Tarayıcıdan LAN üzerinden: **`http://<CT-IP>:8080`** (bugün: `http://192.168.1.111:8080`)

Varsayılan olarak şifresiz (yalnızca yerel ağdan erişim). Basit parola eklemek
istersen `adaptx-panel.service`'e şu iki satırı ekle, sonra `daemon-reload` +
`restart`:

```ini
Environment=PANEL_KULLANICI=kerem
Environment=PANEL_SIFRE=guclu-bir-parola
```

## 3) İzleme

```bash
systemctl status adaptx-panel.service     # çalışma durumu, bellek kullanımı
journalctl -u adaptx-panel.service -f     # canlı log (30 sn'lik durum/sağlık
                                           # sorgulamaları günlüğe yazılmaz;
                                           # yalnızca gerçek istekler/hatalar görünür)
```

## 4) Checklist adımlarını değiştirme

`panel.py` dosyasının en üstünde **tek satır**:

```python
CHECKLIST_ADIMLARI = ["Kontrol Edildi", "Paket Hazırlandı", "Teslim Edildi"]
```

Adım ekle/çıkar/yeniden adlandır, kaydet, sonra:

```bash
systemctl restart adaptx-panel.service
```

Eski adım adlarıyla kaydedilmiş ilerleme `data/panel_checklist.json` içinde
silinmeden korunur (yalnızca güncel listedeki adımlar sayılır); bir adımı
yeniden eski adıyla geri eklersen kaldığı yerden devam eder.

## 5) Checklist verisini sıfırlama

```bash
systemctl stop adaptx-panel.service
rm /opt/adaptx/data/panel_checklist.json
systemctl start adaptx-panel.service
```

Dosya bozulursa (ör. elektrik kesintisi sırasında yarım kalmış yazım) panel
onu silmez; `panel_checklist.json.bozuk-<zaman>` olarak kenara ayırıp sıfırdan
başlar — kanıt kaybolmaz, `data/` klasörüne bakıp elle kurtarabilirsin.

## 6) Bağımlılık / kaynak notları

- Python 3.13, sadece standart kütüphane (`http.server.ThreadingHTTPServer`).
  Bu CT'de `pip` kurulu değil (externally-managed Debian) — bu yüzden Flask
  gibi paketler yerine bilinçli olarak stdlib seçildi.
- Tek çekirdek + 4 GB RAM'e uygun: tek süreç, ~10-15 MB RSS, `Nice=10` ile
  Blender'a öncelik bırakır, `MemoryMax=256M` ile sınırlanmıştır.
- Sistem durumu (`sonraki tur`, `son tur sonucu` vb.) `systemctl`/`journalctl`
  salt-okur komutlarıyla toplanır, 5 saniyelik önbellekle sınırlanır; sipariş
  taraması (`fbx/`+`jsons/`) 3 saniyelik önbellekle sınırlanır — panel'i
  yenilemek boru hattını yavaşlatmaz.
- Sipariş no'su regex ile doğrulanır (`^\d{4,}(?:-\d+)?$`); yalnızca bu kalıba
  uyan istekler dosya sistemine dokunur — path traversal denemeleri sunucu
  tarafında engellenir.

## 7) Yol uyumu

`ADAPTX_BASE` diğer servislerle aynı mantığı kullanır (SERVIS.md'ye bakınız):
panel `ADAPTX_BASE=/opt/adaptx` altındaki `fbx/`, `jsons/`, `pdf/`,
`islem_gecmisi.json`'u okur. Farklı bir yola kurulursa `adaptx-panel.service`
içindeki `ADAPTX_BASE`'i (ve `ReadWritePaths`'i) ona göre güncelle.
