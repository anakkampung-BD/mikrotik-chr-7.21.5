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

mkdir -p "${DATA_DIR}"

# Hapus overlay qcow2 lama jika ada (konfigurasi sebelumnya sering stuck di boot)
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
  echo "[chr] Install paket 'ovmf' di image container." >&2
  exit 1
fi

QEMU_ACCEL=()
if [[ -e /dev/kvm ]] && [[ -r /dev/kvm ]] && [[ -w /dev/kvm ]]; then
  echo "[chr] KVM tersedia — memakai akselerasi hardware"
  QEMU_ACCEL=(-enable-kvm -cpu host)
else
  echo "[chr] KVM tidak tersedia — memakai emulasi software (lebih lambat)"
  # tb-size memperbesar translation cache → boot TCG lebih cepat
  QEMU_ACCEL=(-accel tcg,thread=multi,tb-size=256 -cpu qemu64)
fi

# Port forwarding (host container -> guest CHR)
HOSTFWD=(
  hostfwd=tcp::22-:22
  hostfwd=tcp::80-:80
  hostfwd=tcp::443-:443
  hostfwd=tcp::8291-:8291
  hostfwd=tcp::8728-:8728
  hostfwd=tcp::8729-:8729
)

NETDEV_OPTS=$(IFS=,; echo "${HOSTFWD[*]}")

echo "[chr] Menjalankan RouterOS CHR (UEFI/OVMF)..."
echo "[chr] Akses dari host: Winbox :8291 | WebFig :8080/:8443 | SSH :2222 (guest tetap :22)"

# CHR 7.21+ butuh UEFI: MBR tidak punya bootloader BIOS (hang di "Booting from Hard Disk...")
# q35 + virtio: kompatibel dengan boot EFI RouterOS
exec qemu-system-x86_64 \
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
  -no-reboot
