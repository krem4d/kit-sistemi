#!/bin/bash
# fbx_indir.sh — Google Drive'dan yeni FBX siparişlerini indirir, montaj
# videolarının (<sipariş_no>.mp4) ENVANTERİNİ çıkarır (video İNDİRİLMEZ —
# panel oynatma anında Drive'dan akıtır), ana özet PDF'lerini Drive'a yükler.
# flock ile kilitlenir; yalnızca henüz yerelde olmayan FBX'leri indirir.
# Kurulu kopya: /usr/local/bin/fbx_indir.sh (cron: her dakika); repodaki
# kopya referanstır, değişince kuruluya kopyala.
set -u

DRIVE_IN_ID="1_pi5GtrrGXjABLOi9kRPlg3CD7_fY-51"
DRIVE_OUT_ID="1DTt81x4rj7I6CbZ_qqjAz18B4jpHoJxW"
FBX_HEDEF="/opt/adaptx/fbx"
VIDEO_ENVANTER="/opt/adaptx/video_envanteri.json"
PDF_KAYNAK="/opt/adaptx/pdf"
LOCK_FILE="/var/lock/adaptx_fbx_indir.lock"
LOG="[fbx_indir] $(date '+%F %T')"

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    echo "$LOG — önceki çalışma hâlâ sürüyor, bu tur atlandı."
    exit 0
fi

mkdir -p "$FBX_HEDEF" "$PDF_KAYNAK"

# Ortak rclone ayarları: sınırlı yeniden deneme, makul zaman aşımı.
RCLONE_OPTS=(--low-level-retries 3 --retries 2 --timeout 3m --contimeout 30s)

# --- 1) Uzaktaki .fbx dosyalarını düz (flatten) listele ---
# --max-depth 2: Drive_Kök/<sipariş_no>/<dosya>.fbx yapısına denk gelir.
# Daha derin bir taramaya (ör. ARŞİV-1 gibi arşiv klasörlerinin içine) GİRMEZ
# — bu, önceki tıkanmanın asıl sebebiydi (rekürsif tarama zaman aşımına uğruyordu).
LISTE_ERR="$(mktemp)"
LISTE="$(rclone lsf gdrive: --drive-root-folder-id "$DRIVE_IN_ID" \
    -R --files-only --max-depth 2 \
    --include "*.fbx" --ignore-case \
    "${RCLONE_OPTS[@]}" 2>"$LISTE_ERR")"
LISTE_RC=$?
if [ $LISTE_RC -ne 0 ]; then
    echo "$LOG — HATA: uzak liste alınamadı (rc=$LISTE_RC): $(cat "$LISTE_ERR")"
    rm -f "$LISTE_ERR"
    exit 1
fi
rm -f "$LISTE_ERR"

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

# --- 1b) Montaj videosu ENVANTERİ: aynı Drive klasöründeki <no>.mp4'ler ---
# İndirme YOK — yalnızca "hangi siparişin videosu var" listesi çıkarılır ve
# video_envanteri.json'a atomik yazılır. Panel bu dosyayı okur ("Video var/yok"
# göstergesi) ve oynatma anında videoyu Drive'dan doğrudan akıtır (rclone cat).
# Liste alınamazsa eldeki envanter dosyasına DOKUNULMAZ (bayat > boş).
VLISTE_ERR="$(mktemp)"
VLISTE="$(rclone lsf gdrive: --drive-root-folder-id "$DRIVE_IN_ID" \
    -R --files-only --max-depth 2 \
    --include "*.mp4" --ignore-case --format "sp" \
    "${RCLONE_OPTS[@]}" 2>"$VLISTE_ERR")"
if [ $? -eq 0 ]; then
    printf '%s\n' "$VLISTE" | sort -t';' -k2 | python3 -c '
import json, os, sys, tempfile

hedef = sys.argv[1]
videolar = {}
for satir in sys.stdin:
    satir = satir.strip()
    if not satir or ";" not in satir:
        continue
    boyut, yol = satir.split(";", 1)
    kok, uzanti = os.path.splitext(os.path.basename(yol))
    if uzanti.lower() != ".mp4":
        continue
    # Aynı ada sahip iki uzak dosyadan (ör. 9231/9231-1.mp4 ile yanlış klasöre
    # konmuş 9239/9231-1.mp4) yol sıralamasında önce gelen — sipariş klasörüyle
    # eşleşen — kazanır (girdi yola göre sıralı gelir).
    if kok in videolar:
        continue
    try:
        videolar[kok] = {"yol": yol, "boyut": int(boyut)}
    except ValueError:
        continue

govde = {"surum": 1, "guncelleme": int(__import__("time").time()), "videolar": videolar}
f = tempfile.NamedTemporaryFile("w", dir=os.path.dirname(hedef), delete=False,
                                prefix=".video_envanteri.tmp", encoding="utf-8")
json.dump(govde, f, ensure_ascii=False, indent=1)
f.flush(); os.fsync(f.fileno()); f.close()
os.replace(f.name, hedef)
print(f"[fbx_indir] video envanteri: {len(videolar)} video")
' "$VIDEO_ENVANTER"
else
    echo "$LOG — UYARI: video listesi alınamadı: $(cat "$VLISTE_ERR")"
fi
rm -f "$VLISTE_ERR"

# --- 2) Yarım kalmış / kilitli rclone parça dosyalarını temizle ---
find "$FBX_HEDEF" -maxdepth 1 -name "*.indiriliyor.*" -mmin +30 -delete 2>/dev/null
find "$FBX_HEDEF" -maxdepth 1 -name "*.partial" -mmin +60 -delete 2>/dev/null

# --- 3) Sadece kök dizindeki ana özet PDF'lerini Drive çıkış klasörüne yükle ---
# --max-depth 1: alt klasörlerdeki parça PDF'ler asla yüklenmez.
rclone copy "$PDF_KAYNAK" gdrive: --drive-root-folder-id "$DRIVE_OUT_ID" \
    --max-depth 1 --include "*ozet*.pdf" --ignore-case \
    "${RCLONE_OPTS[@]}" --quiet 2>>/var/log/adaptx_fbx_indir.err

echo "$LOG — tur tamamlandı."
