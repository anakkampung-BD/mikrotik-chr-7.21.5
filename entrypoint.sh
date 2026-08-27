#!/usr/bin/env bash
set -euo pipefail

CHR_BASE_IMG="${CHR_BASE_IMG:-/opt/chr/chr.img}"
DATA_DIR="${DATA_DIR:-/data}"
DISK_IMG="${DATA_DIR}/chr-disk.img"
RAM_MB="${RAM_MB:-512}"
SMP="${SMP:-1}"

# OVMF (UEFI) — CHR 7.x x86 raw image pakai EFI/BOOT, MBR boot code kosong
OVMF_CODE="${OVMF_CODE:-/usr/share/OVMF/OVMF_CODE_4M.fd}"
OVMF_VARS_TEMPLATE="${OVMF_VARS_TEMPLATE:-/usr/share/OVMF/OVMF_VARS_4M.fd}"
OVMF_VARS="${DATA_DIR}/OVMF_VARS.fd"

# Guest IP di QEMU user-mode (slirp DHCP)
GUEST_IP="${GUEST_IP:-10.0.2.15}"
PORT_FWD_START="${PORT_FWD_START:-10000}"
PORT_FWD_END="${PORT_FWD_END:-10999}"

mkdir -p "${DATA_DIR}"

if [[ -f "${DATA_DIR}/chr-disk.qcow2" ]] && [[ ! -f "${DISK_IMG}" ]]; then
  echo "[chr] Menghapus overlay qcow2 lama..."
  rm -f "${DATA_DIR}/chr-disk.qcow2"
fi

if [[ ! -f "${DISK_IMG}" ]]; then
  echo "[chr] Menyalin image CHR ke volume data (raw)..."
  cp -f "${CHR_BASE_IMG}" "${DISK_IMG}"
fi

if [[ ! -f "${OVMF_VARS}" ]]; then
  echo "[chr] Menyiapkan variabel firmware UEFI (OVMF)..."
  cp -f "${OVMF_VARS_TEMPLATE}" "${OVMF_VARS}"
fi

if [[ ! -f "${OVMF_CODE}" ]]; then
  echo "[chr] ERROR: OVMF tidak ditemukan di ${OVMF_CODE}" >&2
  exit 1
fi

QEMU_ACCEL=()
if [[ -e /dev/kvm ]] && [[ -r /dev/kvm ]] && [[ -w /dev/kvm ]]; then
  echo "[chr] KVM tersedia — memakai akselerasi hardware"
  QEMU_ACCEL=(-enable-kvm -cpu host)
else
  echo "[chr] KVM tidak tersedia — memakai emulasi software (lebih lambat)"
  QEMU_ACCEL=(-accel tcg,thread=multi,tb-size=256 -cpu qemu64)
fi

HOSTFWD=(
  hostfwd=tcp::22-:22
  hostfwd=tcp::80-:80
  hostfwd=tcp::443-:443
  hostfwd=tcp::8291-:8291
  hostfwd=tcp::8728-:8728
  hostfwd=tcp::8729-:8729
  hostfwd=udp::500-:500
  hostfwd=udp::4500-:4500
  hostfwd=udp::1701-:1701
)
NETDEV_OPTS=$(IFS=,; echo "${HOSTFWD[*]}")

start_port_forwarders() {
  echo "[chr] Menyiapkan socat forward ${PORT_FWD_START}-${PORT_FWD_END} → ${GUEST_IP}..."
  for port in $(seq "$PORT_FWD_START" "$PORT_FWD_END"); do
    socat "TCP-LISTEN:${port},fork,reuseaddr" "TCP:${GUEST_IP}:${port}" &
  done
}

wait_for_guest() {
  echo "[chr] Menunggu CHR boot..."
  for _ in $(seq 1 120); do
    if (echo >/dev/tcp/127.0.0.1/8291) 2>/dev/null; then
      echo "[chr] CHR siap (Winbox port open)"
      sleep 3
      if (echo >/dev/tcp/${GUEST_IP}/8291) 2>/dev/null; then
        echo "[chr] Guest ${GUEST_IP} reachable via slirp"
        return 0
      fi
      echo "[chr] Guest belum reachable via slirp, lanjut socat ke ${GUEST_IP}..."
      return 0
    fi
    sleep 2
  done
  echo "[chr] WARNING: timeout menunggu CHR boot"
}

echo "[chr] Menjalankan RouterOS CHR (UEFI/OVMF)..."
echo "[chr] Akses: Winbox :8291 | WebFig :8080/:8443 | SSH :2222"
echo "[chr] VPN ports: ${PORT_FWD_START}-${PORT_FWD_END}/tcp"

qemu-system-x86_64 \
  "${QEMU_ACCEL[@]}" \
  -machine q35 \
  -m "${RAM_MB}" \
  -smp "${SMP}" \
  -drive "if=pflash,format=raw,readonly=on,file=${OVMF_CODE}" \
  -drive "if=pflash,format=raw,file=${OVMF_VARS}" \
  -drive "file=${DISK_IMG},format=raw,if=virtio" \
  -netdev "user,id=net0,${NETDEV_OPTS}" \
  -device virtio-net-pci,netdev=net0 \
  -nographic \
  -serial mon:stdio \
  -monitor none \
  -no-reboot &

QEMU_PID=$!

wait_for_guest
start_port_forwarders

wait "$QEMU_PID"
