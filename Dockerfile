# Adaptx Otonom Kit — sayım servisi (Blender headless + system python/matplotlib)
# Veri klasörü /data'ya bind-mount edilir (fbx/ jsons/ pdf/). Yollar statik → taşınabilir.
FROM python:3.11-slim-bookworm

# Blender sürümü build-arg ile ayarlanabilir. YEREL Blender'ınızla eşleştirmeniz
# önerilir (boolean sonuçları sürümden bağımsız olsa da güvence için):
#   blender --version  →  aynı MAJOR/VERSION'ı buraya verin.
ARG BLENDER_MAJOR=4.2
ARG BLENDER_VERSION=4.2.3

ENV DEBIAN_FRONTEND=noninteractive \
    ADAPTX_BASE=/data \
    POLL_INTERVAL=300 \
    PYTHONUNBUFFERED=1

# Blender headless çalışma-zamanı kütüphaneleri (--background bile bunları dlopen eder)
RUN apt-get update && apt-get install -y --no-install-recommends \
      wget xz-utils ca-certificates tini \
      libx11-6 libxi6 libxxf86vm1 libxfixes3 libxrender1 libxkbcommon0 \
      libgl1 libegl1 libsm6 libice6 libxext6 libxrandr2 libxinerama1 \
      libxcursor1 libgomp1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Blender'ı indir ve kur
RUN wget -q "https://download.blender.org/release/Blender${BLENDER_MAJOR}/blender-${BLENDER_VERSION}-linux-x64.tar.xz" -O /tmp/blender.tar.xz \
    && mkdir -p /opt/blender \
    && tar -xf /tmp/blender.tar.xz -C /opt/blender --strip-components=1 \
    && rm /tmp/blender.tar.xz \
    && ln -s /opt/blender/blender /usr/local/bin/blender

# PDF aşaması için matplotlib (sistem python3'e)
RUN pip install --no-cache-dir matplotlib

WORKDIR /app
COPY parca_sayim.py pdf_uret.py calistir.sh /app/
COPY docker/entrypoint.sh docker/yeni_var_mi.py /app/
RUN chmod +x /app/entrypoint.sh /app/calistir.sh

VOLUME ["/data"]

# tini → düzgün sinyal/zombi yönetimi (uzun süreli döngü servisi)
ENTRYPOINT ["/usr/bin/tini", "--", "/app/entrypoint.sh"]
