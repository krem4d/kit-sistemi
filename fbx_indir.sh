#!/bin/bash
# fbx_indir.sh — Google Drive'dan yeni FBX siparişlerini ve renk JSON'larını
# indirir, ana özet PDF'lerini Drive'a yükler. Montaj videosu envanteri ayrı
# betikte (video_envanter.sh, kendi 15 sn'lik timer'ı); burada her turun başında
# yedek olarak çağrılır (timer kurulu değilse de envanter güncel kalsın).
# flock ile kilitlenir; yalnızca henüz yerelde olmayan FBX'leri indirir.
# Kurulu kopya: /usr/local/bin/fbx_indir.sh (cron: her dakika); repodaki
# kopya referanstır, değişince kuruluya kopyala.
set -u

DRIVE_IN_ID="1_pi5GtrrGXjABLOi9kRPlg3CD7_fY-51"
DRIVE_OUT_ID="1DTt81x4rj7I6CbZ_qqjAz18B4jpHoJxW"
FBX_HEDEF="/opt/adaptx/fbx"
RENK_HEDEF="/opt/adaptx/renkler"
PDF_KAYNAK="/opt/adaptx/pdf"
LOCK_FILE="/var/lock/adaptx_fbx_indir.lock"
LOG="[fbx_indir] $(date '+%F %T')"

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    echo "$LOG — önceki çalışma hâlâ sürüyor, bu tur atlandı."
    exit 0
fi

mkdir -p "$FBX_HEDEF" "$RENK_HEDEF" "$PDF_KAYNAK"

# Ortak rclone ayarları: sınırlı yeniden deneme, makul zaman aşımı.
RCLONE_OPTS=(--low-level-retries 3 --retries 2 --timeout 3m --contimeout 30s)

# --- 0) Video envanteri önce (FBX indirmesini beklemesin; kendi kilidi var,
# timer'ın taraması o an sürüyorsa bu çağrı hemen döner) ---
VIDEO_BETIK="$(dirname "$(readlink -f "$0")")/video_envanter.sh"
if [ -x "$VIDEO_BETIK" ]; then
    "$VIDEO_BETIK" || echo "$LOG — UYARI: video envanteri güncellenemedi."
fi

# --- 1) Uzaktaki .fbx ve .json dosyalarını TEK taramada düz (flatten) listele ---
# --max-depth 2: Drive_Kök/<sipariş_no>/<dosya> yapısına denk gelir.
# Daha derin bir taramaya (ör. ARŞİV-1 gibi arşiv klasörlerinin içine) GİRMEZ
# — bu, önceki tıkanmanın asıl sebebiydi (rekürsif tarama zaman aşımına uğruyordu).
# --fast-list: klasörleri toplu sorgular. Eskiden fbx ve json için iki ayrı tam
# tarama vardı (~60 sn'er); tek --fast-list taraması ~5 sn (ölçüm 2026-09-30).
TUM_ERR="$(mktemp)"
TUM_LISTE="$(rclone lsf gdrive: --drive-root-folder-id "$DRIVE_IN_ID" \
    -R --files-only --max-depth 2 --fast-list \
    --include "*.{fbx,json}" --ignore-case \
    "${RCLONE_OPTS[@]}" 2>"$TUM_ERR")"
LISTE_RC=$?
if [ $LISTE_RC -ne 0 ]; then
    echo "$LOG — HATA: uzak liste alınamadı (rc=$LISTE_RC): $(cat "$TUM_ERR")"
    rm -f "$TUM_ERR"
    exit 1
fi
rm -f "$TUM_ERR"
LISTE="$(printf '%s\n' "$TUM_LISTE" | grep -i '\.fbx$')"
RLISTE="$(printf '%s\n' "$TUM_LISTE" | grep -i '\.json$')"

YENI=0
HATA=0
while IFS= read -r UZAK_YOL; do
    [ -z "$UZAK_YOL" ] && continue
    DOSYA_ADI="$(basename "$UZAK_YOL")"
    HEDEF="$FBX_HEDEF/$DOSYA_ADI"

    # Zaten yerelde varsa tekrar indirme (bu kontrol darboğazı ve
    # "No space left on device" hatasını önleyen ana mekanizma).
    if [ -e "$HEDEF" ]; then
        continue
    fi

    GECICI="$HEDEF.indiriliyor.$$"
    if rclone copyto "gdrive:$UZAK_YOL" "$GECICI" \
        --drive-root-folder-id "$DRIVE_IN_ID" "${RCLONE_OPTS[@]}" --no-traverse 2>>/var/log/adaptx_fbx_indir.err; then
        mv -f "$GECICI" "$HEDEF"
        YENI=$((YENI+1))
        echo "$LOG — indirildi: $DOSYA_ADI"
    else
        HATA=$((HATA+1))
        echo "$LOG — HATA: indirilemedi: $UZAK_YOL"
        rm -f "$GECICI"
    fi
done <<< "$LISTE"

echo "$LOG — indirme turu bitti: $YENI yeni, $HATA hata."

# --- 1a-2) Renk JSON'larını indir: aynı Drive klasöründeki <sipariş>.json'lar ---
# Mert'in parça-başına renk bilgisi (user_data.renk) içeren dosyaları — FBX ile
# aynı mantık: zaten yerelde varsa tekrar indirilmez, parca_sayim.py bunları
# renkler/ altından okuyup siparişin baskın rengini + Linco/Tıpa renklerini türetir.
# (Liste yukarıdaki tek taramadan geliyor; o tarama başarısızsa betik zaten çıktı.)
{
    RYENI=0
    RHATA=0
    while IFS= read -r UZAK_YOL; do
        [ -z "$UZAK_YOL" ] && continue
        DOSYA_ADI="$(basename "$UZAK_YOL")"
        HEDEF="$RENK_HEDEF/$DOSYA_ADI"

        if [ -e "$HEDEF" ]; then
            continue
        fi

        GECICI="$HEDEF.indiriliyor.$$"
        if rclone copyto "gdrive:$UZAK_YOL" "$GECICI" \
            --drive-root-folder-id "$DRIVE_IN_ID" "${RCLONE_OPTS[@]}" --no-traverse 2>>/var/log/adaptx_fbx_indir.err; then
            mv -f "$GECICI" "$HEDEF"
            RYENI=$((RYENI+1))
            echo "$LOG — renk json indirildi: $DOSYA_ADI"
        else
            RHATA=$((RHATA+1))
            echo "$LOG — HATA: renk json indirilemedi: $UZAK_YOL"
            rm -f "$GECICI"
        fi
    done <<< "$RLISTE"
    echo "$LOG — renk json turu bitti: $RYENI yeni, $RHATA hata."
}
find "$RENK_HEDEF" -maxdepth 1 -name "*.indiriliyor.*" -mmin +30 -delete 2>/dev/null

# --- 2) Yarım kalmış / kilitli rclone parça dosyalarını temizle ---
find "$FBX_HEDEF" -maxdepth 1 -name "*.indiriliyor.*" -mmin +30 -delete 2>/dev/null
find "$FBX_HEDEF" -maxdepth 1 -name "*.partial" -mmin +60 -delete 2>/dev/null

# --- 3) Sadece kök dizindeki ana özet PDF'lerini Drive çıkış klasörüne yükle ---
# --max-depth 1: alt klasörlerdeki parça PDF'ler asla yüklenmez.
rclone copy "$PDF_KAYNAK" gdrive: --drive-root-folder-id "$DRIVE_OUT_ID" \
    --max-depth 1 --include "*ozet*.pdf" --ignore-case \
    "${RCLONE_OPTS[@]}" --quiet 2>>/var/log/adaptx_fbx_indir.err

echo "$LOG — tur tamamlandı."
