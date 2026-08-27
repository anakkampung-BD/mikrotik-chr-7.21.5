# VPN Remote Access Bot

Bot Telegram untuk otomasi VPN remote access ala VPNBersama — user pasang **L2TP client** di MikroTik mereka, bot assign **port forwarding publik** ke perangkat via CHR.

## Arsitektur

```
User MikroTik ──L2TP dial──► CHR (VPS) ──dst-nat──► tunnel IP user
                                    ▲
Telegram Bot ──API 8728─────────────┘
```

## Setup

### 1. Buat Bot Telegram

1. Chat [@BotFather](https://t.me/BotFather) → `/newbot`
2. Salin token ke `vpn-bot/.env`

### 2. Konfigurasi `.env`

```bash
cp vpn-bot/.env.example vpn-bot/.env
# Edit TELEGRAM_BOT_TOKEN, PUBLIC_HOST, MIKROTIK_PASSWORD, dll.
```

### 3. Rebuild CHR (port range 10000-10999)

```bash
docker compose build && docker compose up -d
```

### 4. Jalankan bot

```bash
docker compose -f docker-compose.vpn-bot.yml up -d --build
docker compose -f docker-compose.vpn-bot.yml logs -f
```

## Perintah Bot

| Perintah | Fungsi |
|----------|--------|
| `/start` | Menu utama |
| `/register` | Buat akun VPN + port forwarding |
| `/status` | Cek koneksi L2TP |
| `/info` | Lihat kredensial & port |
| `/delete` | Hapus akun & NAT rules |
| `/admin` | Statistik (admin only) |

## Skema Port

```
public_port = 10000 + (user_slot × 10) + service_index
```

| Index | Service | Port internal |
|-------|---------|---------------|
| 0 | Custom | 6000 |
| 1 | Www | 80 |
| 2 | Winbox | 8291 |
| 3 | Ssh | 22 |
| 4 | API | 8728 |

Contoh user slot 5: Winbox → `your.vps.ip.or.domain:10052`

## Firewall VPS / Cloud

Buka inbound:
- UDP 500, 4500, 1701 (L2TP/IPsec)
- TCP 10000-10999 (port forwarding)

## Alur Pelanggan

1. `/register` di Telegram
2. Pasang L2TP client di MikroTik (perintah dari bot)
3. Setelah connect → akses Winbox/SSH via port publik
