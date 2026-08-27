# MikroTik CHR 7.21.5 — dijalankan via QEMU di dalam container
FROM debian:bookworm-slim

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    qemu-system-x86 \
    qemu-utils \
    ovmf \
    socat \
    ca-certificates \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/chr

COPY chr-7.21.5.img /opt/chr/chr.img
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh \
  && mkdir -p /data

VOLUME ["/data"]

# SSH, WebFig, Winbox, API
EXPOSE 22 80 443 8291 8728 8729

ENV RAM_MB=512 \
    SMP=1 \
    DATA_DIR=/data \
    CHR_BASE_IMG=/opt/chr/chr.img

ENTRYPOINT ["/entrypoint.sh"]
