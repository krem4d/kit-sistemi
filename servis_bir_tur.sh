#!/usr/bin/env bash
# servis_bir_tur.sh — Adaptx Otonom Kit tek servis turu (native/systemd)
# systemd timer bunu 5 dakikada bir çağırır. fbx/ içinde YENİ sipariş varsa
# tüm boru hattını (Blender sayım + PDF) çalıştırır; yoksa hiçbir şey yapmaz
# (Blender'ı boşuna başlatmaz). Veri kökü ADAPTX_BASE (varsayılan: script dizini).
set -u

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export ADAPTX_BASE="${ADAPTX_BASE:-$DIR}"

mkdir -p "$ADAPTX_BASE/fbx" "$ADAPTX_BASE/jsons" "$ADAPTX_BASE/pdf"

if python3 "$DIR/docker/yeni_var_mi.py"; then
    echo "[adaptx] $(date '+%F %T') — yeni sipariş bulundu, işleniyor..."
    if bash "$DIR/calistir.sh"; then
        echo "[adaptx] $(date '+%F %T') — tamamlandı."
    else
        echo "[adaptx] $(date '+%F %T') — HATA: boru hattı başarısız."
        exit 1
    fi
else
    echo "[adaptx] $(date '+%F %T') — yeni sipariş yok, atlandı."
fi
