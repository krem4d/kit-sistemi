#!/usr/bin/env bash
# Adaptx Otonom Kit — sayım + PDF orkestratörü
# Kullanım: bash calistir.sh
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[1/2] Blender sayım motoru (fbx/ -> pdf/*.json) ..."
blender --background --python "$DIR/parca_sayim.py"

echo "[2/2] PDF üretimi (pdf/*.json -> pdf/*.pdf) ..."
python3 "$DIR/pdf_uret.py"

echo "Bitti. Çıktılar: $DIR/pdf/"
