# kit-sistemi — Adaptx Otonom Kit

Flat-pack mobilya siparişlerinin 3D modellerinden (`.fbx`) **donanım parçalarını otonom
sayan** ve **PDF toplama listeleri** üreten boru hattı. Tespit tamamen **geometriye**
dayanır (delik hacimleri, mesafeler, yönler, panel kalınlığı) — parça isimlerine değil.

## Akış

```
fbx/*.fbx ─▶ [Blender headless] parca_sayim.py ─▶ jsons/<sipariş>.json
                                                         │
             [python + matplotlib] pdf_uret.py ◀────────┘ ─▶ pdf/<sipariş>.pdf + özet
```

## Hızlı başlangıç (yerel)

```bash
bash calistir.sh          # fbx/ -> jsons/ -> pdf/
```

## Servis olarak (Docker, 5 dk'da bir otomatik)

`fbx/` klasörünü periyodik tarar, yeni sipariş gelince kendi çalışır, PDF'leri bırakır.
Zaten işlenmiş siparişler tekrar işlenmez; yeni siparişler özetin sonuna eklenir.

```bash
docker compose up -d --build
# FBX'leri data/fbx/ içine bırak → PDF'ler data/pdf/ altına düşer
```

Proxmox CT dahil kurulum: **[DOCKER.md](DOCKER.md)**.

## Dokümanlar

- **[AGENTS.md](AGENTS.md)** — mimari, tespit motoru, kurallar, konvansiyonlar (kapsamlı).
- **[parca_kurallari.md](parca_kurallari.md)** — her parçanın sayım kuralı (kaynak doğru).
- **[hacimler.md](hacimler.md)** — referans hacimler/toleranslar.
- **[DOCKER.md](DOCKER.md)** — servis/konteyner kurulumu.
- **[Eksikler.md](Eksikler.md)** — ertelenen işler / açık sorular.
