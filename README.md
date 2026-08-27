# MikroTik CHR 7.21.5 — Docker Container

Jalankan **MikroTik Cloud Hosted Router (CHR) 7.21.5** di dalam Docker menggunakan **QEMU + UEFI/OVMF**. Cocok untuk lab, testing, atau menjalankan RouterOS di VPS tanpa nested virtualization penuh.

Image siap pakai tersedia di Docker Hub: **[lsiribere/mikrotik-chr](https://hub.docker.com/r/lsiribere/mikrotik-chr)**

---

## Daftar Isi

- [Persyaratan](#persyaratan)
- [Instalasi Docker](#instalasi-docker)
- [Cara Cepat (Docker Hub)](#cara-cepat-docker-hub)
- [Docker Compose](#docker-compose)
- [Build dari Source](#build-dari-source)
- [Akses RouterOS](#akses-routeros)
- [Konfigurasi](#konfigurasi)
- [ZeroTier (Opsional)](#zerotier-opsional)
- [Troubleshooting](#troubleshooting)
- [Lisensi](#lisensi)

---

## Persyaratan

| Item | Minimum | Disarankan |
|------|---------|------------|
| OS Host | Linux (Ubuntu/Debian) | Ubuntu 22.04+ |
| RAM Host | 2 GB | 4 GB+ |
| RAM CHR | 512 MB | 4096 MB |
| CPU | 1 vCPU | 4 vCPU |
| Docker | 20.10+ | Terbaru |
| Storage | 2 GB | 5 GB+ |

> **Catatan:** CHR di-boot via QEMU. Jika host **tidak** punya `/dev/kvm` (nested KVM), QEMU memakai emulasi software (TCG) — boot lebih lambat (~2–5 menit) tapi tetap jalan.

---

## Instalasi Docker

### Ubuntu / Debian

```bash
# 1. Hapus paket lama (jika ada)
sudo apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

# 2. Install dependensi
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg

# 3. Tambah GPG key & repository resmi Docker
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 4. Install Docker Engine + Compose plugin
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 5. Jalankan Docker & aktifkan saat boot
sudo systemctl enable --now docker

# 6. (Opsional) Jalankan Docker tanpa sudo
sudo usermod -aG docker $USER
# Logout & login ulang agar grup docker aktif
```

### Verifikasi instalasi

```bash
docker --version
docker compose version
docker run --rm hello-world
```

---

## Cara Cepat (Docker Hub)

Cara termudah — **tidak perlu build**, image sudah include disk CHR:

```bash
docker pull lsiribere/mikrotik-chr:7.21.5

docker run -d \
  --name mikrotik-chr \
  --restart unless-stopped \
  -p 2222:22 \
  -p 8080:80 \
  -p 8443:443 \
  -p 8291:8291 \
  -p 8728:8728 \
  -p 8729:8729 \
  -e RAM_MB=4096 \
  -e SMP=4 \
  -v chr-data:/data \
  lsiribere/mikrotik-chr:7.21.5
```

Tunggu 2–5 menit (TCG) atau ~30 detik (KVM) sampai CHR selesai boot.

---

## Docker Compose

### Opsi A — Pull dari Docker Hub (disarankan)

```bash
git clone https://github.com/anakkampung-BD/mikrotik-chr-7.21.5.git
cd mikrotik-chr-7.21.5

docker compose -f docker-compose.hub.yml up -d
docker compose -f docker-compose.hub.yml logs -f
```

### Opsi B — Build lokal

Butuh file `chr-7.21.5.img` (lihat [Build dari Source](#build-dari-source)).

```bash
git clone https://github.com/anakkampung-BD/mikrotik-chr-7.21.5.git
cd mikrotik-chr-7.21.5
# letakkan chr-7.21.5.img di folder ini

docker compose up -d --build
docker compose logs -f
```

### Perintah berguna

```bash
docker compose ps          # status container
docker compose logs -f     # log boot CHR
docker compose stop        # stop
docker compose down        # stop + hapus container (volume tetap)
docker compose down -v     # stop + hapus volume (reset disk CHR!)
```

---

## Build dari Source

File disk `chr-7.21.5.img` (**128 MB**) tidak disertakan di repo GitHub karena melebihi batas ukuran file. Dapatkan dengan salah satu cara:

1. **Pakai image Docker Hub** (sudah include disk) — disarankan
2. Download image CHR resmi dari [MikroTik Download](https://download.mikrotik.com/routeros/) lalu convert ke raw
3. Salin dari volume Docker yang sudah pernah jalan:  
   `docker cp mikrotik-chr:/data/chr-disk.img ./chr-7.21.5.img`

```bash
# Setelah chr-7.21.5.img tersedia di folder proyek:
docker build -t lsiribere/mikrotik-chr:7.21.5 .
docker run -d --name mikrotik-chr ... lsiribere/mikrotik-chr:7.21.5
```

---

## Akses RouterOS

Setelah container running dan CHR selesai boot:

| Layanan | Alamat dari Host |
|---------|------------------|
| **SSH** | `ssh admin@<IP-HOST> -p 2222` |
| **Winbox** | `<IP-HOST>:8291` |
| **WebFig HTTP** | `http://<IP-HOST>:8080` |
| **WebFig HTTPS** | `https://<IP-HOST>:8443` |
| **API** | `<IP-HOST>:8728` |

### Login default CHR

- User: `admin`
- Password: *(kosong saat first boot — wajib set password saat login pertama)*

### IP internal CHR (`ether1`)

IP di interface `ether1` **bukan** dari Docker bridge. CHR mendapat IP dari **QEMU user-mode networking (slirp)**:

| Parameter | Nilai |
|-----------|-------|
| Subnet | `10.0.2.0/24` |
| IP CHR | `10.0.2.15` (DHCP) |
| Gateway | `10.0.2.2` |
| DNS | `10.0.2.3` |

---

## Konfigurasi

### Environment variables

| Variable | Default | Keterangan |
|----------|---------|------------|
| `RAM_MB` | `512` | RAM untuk CHR (MB) |
| `SMP` | `1` | Jumlah vCPU |
| `DATA_DIR` | `/data` | Lokasi persist disk |
| `CHR_BASE_IMG` | `/opt/chr/chr.img` | Image dasar (di dalam container) |

### Port mapping

Port di **host** → port di **guest CHR**:

```
2222 → 22    (SSH)
8080 → 80    (WebFig HTTP)
8443 → 443   (WebFig HTTPS)
8291 → 8291  (Winbox)
8728 → 8728  (API)
8729 → 8729  (API-SSL)
```

### Aktifkan KVM (jika tersedia)

Nested KVM mempercepat boot secara signifikan. Uncomment di `docker-compose.yml`:

```yaml
devices:
  - /dev/kvm:/dev/kvm
```

### Persist data

Volume `chr-data` menyimpan:

- `chr-disk.img` — disk CHR (konfigurasi RouterOS persist di sini)
- `OVMF_VARS.fd` — variabel firmware UEFI

> **Peringatan:** `docker compose down -v` akan **menghapus semua konfigurasi** RouterOS.

---

## ZeroTier (Opsional)

CHR x86 **tidak** mendukung paket ZeroTier native. Solusi: jalankan ZeroTier via **RouterOS Container package** + image `zyclonite/zerotier`.

Ringkasan setup (setelah login ke CHR):

```routeros
/system package enable container
/container config set registry-url=https://registry-1.docker.io tmpdir=container/pull

/interface bridge add name=bridge1 comment="LAN+ZeroTier"
/ip address add address=172.30.0.1/24 interface=bridge1
/interface veth add name=veth-zt address=172.30.0.2/24 gateway=172.30.0.1
/interface bridge port add bridge=bridge1 interface=veth-zt

/container envs add list=zt key=net value=host
/container envs add list=zt key=cap-add value=NET_ADMIN
/container envs add list=zt key=device value=/dev/net/tun
/container add remote-image=zyclonite/zerotier:latest interface=veth-zt \
  root-dir=container/zerotier envlist=zt hostname=zerotier start-on-boot=yes
```

Join network via shell container (`zerotier-cli join <NETWORK_ID>`), authorize di [my.zerotier.com](https://my.zerotier.com).

Untuk managed route (mis. `172.30.0.0/24 via <IP-ZT>`), tambahkan di RouterOS:

```routeros
/ip route add dst-address=172.25.25.0/24 gateway=172.30.0.2 comment="ZT return via container"
/ip firewall filter add chain=forward action=accept src-address=172.25.25.0/24 dst-address=172.30.0.0/24
/ip firewall filter add chain=forward action=accept src-address=172.30.0.0/24 dst-address=172.25.25.0/24
```

---

## Troubleshooting

### Hang di "Booting from Hard Disk..."

CHR 7.x membutuhkan boot **UEFI**. Image ini sudah memakai OVMF. Pastikan volume `/data` tidak korup — coba reset volume jika perlu.

### Boot sangat lambat

Normal di host tanpa KVM. Tunggu 2–5 menit. Aktifkan `/dev/kvm` jika host mendukung nested virtualization.

### Port tidak bisa diakses

```bash
docker ps                          # pastikan container running
docker compose logs -f             # cek log boot
ss -tlnp | grep -E '2222|8291'    # port listening di host
```

### SSH "Connection refused"

CHR belum selesai boot. Pantau log sampai muncul prompt login RouterOS.

### Reset CHR ke kondisi awal

```bash
docker compose down -v
docker compose up -d
```

---

## Arsitektur

```
┌─────────────────────────────────────────────┐
│  Host Linux (Docker)                        │
│  ┌───────────────────────────────────────┐  │
│  │  Container: mikrotik-chr              │  │
│  │  ┌─────────────────────────────────┐  │  │
│  │  │  QEMU (UEFI/OVMF)               │  │  │
│  │  │  ┌───────────────────────────┐  │  │  │
│  │  │  │  RouterOS CHR 7.21.5      │  │  │  │
│  │  │  │  ether1: 10.0.2.15 (slirp)│  │  │  │
│  │  │  └───────────────────────────┘  │  │  │
│  │  └─────────────────────────────────┘  │  │
│  │  Port map: 2222→22, 8291→8291, ...   │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

---

## Lisensi

- **RouterOS CHR** — lisensi MikroTik ([mikrotik.com](https://mikrotik.com))
- **Docker wrapper (QEMU/OVMF)** — open source, repo ini
- Image CHR tidak disertakan di repo GitHub; gunakan Docker Hub atau download resmi MikroTik

---

## Links

- Docker Hub: [lsiribere/mikrotik-chr](https://hub.docker.com/r/lsiribere/mikrotik-chr)
- GitHub: [anakkampung-BD/mikrotik-chr-7.21.5](https://github.com/anakkampung-BD/mikrotik-chr-7.21.5)
- MikroTik CHR: [https://mikrotik.com/download](https://mikrotik.com/download)
