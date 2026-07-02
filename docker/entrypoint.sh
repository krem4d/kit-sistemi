#!/usr/bin/env bash
# entrypoint.sh — Adaptx Otonom Kit servis döngüsü (Docker)
# fbx/ klasörünü POLL_INTERVAL saniyede bir kontrol eder; yeni sipariş varsa
# tüm boru hattını (Blender sayım + PDF) çalıştırır. Statik yollar ADAPTX_BASE altında.
set -u

INTERVAL="${POLL_INTERVAL:-300}"          # varsayılan 5 dakika
BASE="${ADAPTX_BASE:-/data}"

# Veri klasörleri yoksa oluştur (ilk kurulum / boş bind-mount)
mkdir -p "${BASE}/fbx" "${BASE}/jsons" "${BASE}/pdf"

echo "[adaptx] servis başladı — her ${INTERVAL}s kontrol. Veri klasörü: ${BASE}"
echo "[adaptx] FBX'leri ${BASE}/fbx içine bırakın; PDF'ler ${BASE}/pdf altına düşer."

while true; do
    if python3 /app/yeni_var_mi.py; then
        echo "[adaptx] $(date '+%F %T') — yeni sipariş bulundu, işleniyor..."
        if bash /app/calistir.sh; then
            echo "[adaptx] $(date '+%F %T') — tamamlandı."
        else
            echo "[adaptx] $(date '+%F %T') — HATA: boru hattı başarısız (bir sonraki turda yeniden denenecek)."
        fi
    fi
    sleep "${INTERVAL}"
done
