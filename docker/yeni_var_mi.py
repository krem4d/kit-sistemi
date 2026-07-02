#!/usr/bin/env python3
"""yeni_var_mi.py — fbx/ içinde henüz işlenmemiş sipariş var mı?

Çıkış kodu 0 → en az bir FBX'in jsons/<order>.json'u yok (işlenecek yeni iş var).
Çıkış kodu 1 → her FBX zaten işlenmiş (yapılacak yeni iş yok).

parca_sayim.py ile AYNI sipariş-no çıkarımını kullanır; böylece watcher gereksiz
yere Blender'ı başlatmaz. Veri klasörü ADAPTX_BASE'ten okunur (Docker/servis).
"""
import os
import re
import glob
import sys

BASE = os.environ.get("ADAPTX_BASE") or os.path.dirname(os.path.abspath(__file__))
FBX_DIR = os.path.join(BASE, "fbx")
JSON_DIR = os.path.join(BASE, "jsons")


def order_from_name(path):
    m = re.search(r'(\d{4,}(?:-\d+)?)', os.path.basename(path))
    return m.group(1) if m else "0000"


for fbx in glob.glob(os.path.join(FBX_DIR, "*.fbx")):
    if not os.path.exists(os.path.join(JSON_DIR, order_from_name(fbx) + ".json")):
        sys.exit(0)   # işlenecek yeni sipariş var
sys.exit(1)           # yeni iş yok
