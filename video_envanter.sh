#!/bin/bash
# video_envanter.sh — Drive'daki montaj videolarının (<sipariş_no>.mp4) ENVANTERİNİ
# çıkarır; video İNDİRİLMEZ (panel oynatma anında Drive'dan akıtır).
#
# Neden ayrı betik (2026-09-30): envanter eskiden fbx_indir.sh'ın dakikalık turunun
# SONUNDA, FBX indirmelerinden sonra ve ayrı bir tam Drive taramasıyla (~60 sn)
# çıkıyordu; tur 3 tarama + indirme ile dakikaları buluyor, flock sonraki turları
# atlatıyordu → yeni video panele çok geç düşüyordu. Burada tek bir --fast-list
# taraması (~5 sn) yapılır ve kendi kilidiyle, FBX indirmesini beklemeden koşar.
#
# Kurulu kopya: /usr/local/bin/video_envanter.sh — systemd/adaptx-video.timer
# (15 sn'de bir) çağırır; fbx_indir.sh de her turun başında yedek olarak çağırır.
# Repodaki kopya referanstır, değişince kuruluya kopyala.
set -u

DRIVE_IN_ID="${DRIVE_IN_ID:-1_pi5GtrrGXjABLOi9kRPlg3CD7_fY-51}"
VIDEO_ENVANTER="${VIDEO_ENVANTER:-/opt/adaptx/video_envanteri.json}"
LOCK_FILE="${VIDEO_LOCK_FILE:-/var/lock/adaptx_video_envanter.lock}"
LOG="[video_envanter] $(date '+%F %T')"

exec 8>"$LOCK_FILE"
if ! flock -n 8; then
    exit 0   # önceki tarama sürüyor; zaten taze envanter gelecek
fi

# --max-depth 2: Drive_Kök/<sipariş_no>/<no>.mp4 yapısı; arşiv klasörlerinin
# içine girilmez. --fast-list: klasörleri tek tek değil toplu sorgular
# (ölçüm 2026-09-30: 57.6 sn → 6.9 sn, aynı 276 video).
VLISTE_ERR="$(mktemp)"
VLISTE="$(rclone lsf gdrive: --drive-root-folder-id "$DRIVE_IN_ID" \
    -R --files-only --max-depth 2 --fast-list \
    --include "*.mp4" --ignore-case --format "sp" \
    --low-level-retries 3 --retries 2 --timeout 1m --contimeout 30s 2>"$VLISTE_ERR")"
RC=$?
if [ $RC -ne 0 ]; then
    # Liste alınamazsa eldeki envanter dosyasına DOKUNULMAZ (bayat > boş).
    echo "$LOG — UYARI: video listesi alınamadı (rc=$RC): $(cat "$VLISTE_ERR")"
    rm -f "$VLISTE_ERR"
    exit 1
fi
rm -f "$VLISTE_ERR"

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

# Boş liste = büyük ihtimalle kota/ağ hatası (rclone Drive kotasına takılınca rc=0
# ile boş dönebiliyor, görüldü 2026-09-30). Boşla eskiyi ezme: panelde bütün
# siparişler "Video yok"a düşerdi. Bayat > boş.
if not videolar:
    print("[video_envanter] UYARI: Drive listesi boş geldi, envanter korunuyor", file=sys.stderr)
    sys.exit(1)

# İçerik değişmediyse dosyaya yazma: 15 sn aralıkla gereksiz disk yazımı olmasın.
try:
    with open(hedef, encoding="utf-8") as f:
        if json.load(f).get("videolar") == videolar:
            sys.exit(0)
except (OSError, ValueError, AttributeError):
    pass

govde = {"surum": 1, "guncelleme": int(__import__("time").time()), "videolar": videolar}
f = tempfile.NamedTemporaryFile("w", dir=os.path.dirname(hedef) or ".", delete=False,
                                prefix=".video_envanteri.tmp", encoding="utf-8")
json.dump(govde, f, ensure_ascii=False, indent=1)
f.flush(); os.fsync(f.fileno()); f.close()
os.chmod(f.name, 0o644)
os.replace(f.name, hedef)
print(f"[video_envanter] envanter güncellendi: {len(videolar)} video")
' "$VIDEO_ENVANTER"
