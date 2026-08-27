import re
import secrets

import db
import config
import mikrotik


def sanitize_username(telegram_id: int, name: str = "") -> str:
    slug = re.sub(r"[^a-z0-9]", "", (name or "user").lower())[:12]
    suffix = secrets.token_hex(2)
    return f"u{telegram_id % 100000}-{slug or 'vpn'}-{suffix}"


def provision_user(telegram_id: int, telegram_username: str = "") -> dict:
    existing = db.get_user_by_telegram(telegram_id)
    if existing and existing["status"] == "active":
        return {"error": "already_exists", "user": existing}

    if db.count_users() >= config.MAX_USERS:
        return {"error": "limit_reached"}

    slot = db.next_free_slot()
    used_ips = mikrotik.get_used_tunnel_ips()
    with db.get_db() as conn:
        db_used = {
            row[0]
            for row in conn.execute(
                "SELECT tunnel_ip FROM users WHERE status='active'"
            ).fetchall()
        }
    prefix = ".".join(config.VPN_POOL_START.split(".")[:-1])
    start = int(config.VPN_POOL_START.split(".")[-1])
    end = int(config.VPN_POOL_END.split(".")[-1])
    tunnel_ip = None
    for host in range(start, end + 1):
        ip = f"{prefix}.{host}"
        if ip not in used_ips and ip not in db_used:
            tunnel_ip = ip
            break
    if slot is None or tunnel_ip is None:
        return {"error": "pool_exhausted"}

    vpn_username = sanitize_username(telegram_id, telegram_username)
    vpn_password = mikrotik.generate_password()

    port_mappings = []
    for svc_idx, (label, internal_port) in config.SERVICES.items():
        pub = config.pub_port(slot, svc_idx)
        port_mappings.append((pub, internal_port, label.lower()))

    mikrotik.create_vpn_user(vpn_username, vpn_password, tunnel_ip, port_mappings)

    user_id = db.create_user(
        telegram_id=telegram_id,
        username=telegram_username or "",
        vpn_username=vpn_username,
        vpn_password=vpn_password,
        tunnel_ip=tunnel_ip,
        user_slot=slot,
    )

    user = db.get_user_by_telegram(telegram_id)
    mappings = db.get_port_mappings(user_id)
    return {"user": user, "mappings": mappings}


def format_success_message(user, mappings, session=None) -> str:
    lines = [
        "✅ *VPN Remote Access — Berhasil Dibuat*",
        "",
        f"*Server:* {config.PUBLIC_HOST}",
        f"*Username L2TP:* `{user['vpn_username']}`",
        f"*Password:* `{user['vpn_password']}`",
        f"*IPsec PSK:* `{config.L2TP_IPSEC_SECRET}`",
        f"*Tunnel IP:* `{user['tunnel_ip']}`",
    ]

    if session:
        lines.extend([
            "",
            "🟢 *Status:* CONNECTED",
            f"*Caller ID:* `{session.get('caller-id', '-')}`",
        ])
    else:
        lines.extend([
            "",
            "🟡 *Status:* Menunggu koneksi L2TP client",
            "",
            "Pasang *L2TP client* di MikroTik Anda:",
            "```",
            f"/interface l2tp-client add name=vpn-remote connect-to={config.PUBLIC_HOST} \\",
            f"  user={user['vpn_username']} password={user['vpn_password']} \\",
            f"  use-ipsec=yes ipsec-secret={config.L2TP_IPSEC_SECRET} \\",
            "  profile=default-encryption disabled=no",
            "```",
        ])

    lines.extend([
        "",
        "*Port forwarding publik:*",
    ])
    for m in mappings:
        lines.append(
            f"● {m['service_label']:<7} {m['internal_port']:<5} → "
            f"`{config.PUBLIC_HOST}:{m['public_port']}`"
        )

    lines.extend([
        "",
        "_Setelah L2TP client connect, port di atas aktif ke perangkat Anda._",
    ])
    return "\n".join(lines)


def deactivate_user(telegram_id: int) -> str:
    user = db.get_user_by_telegram(telegram_id)
    if not user or user["status"] != "active":
        return "Tidak ada akun VPN aktif."

    mappings = db.get_port_mappings(user["id"])
    public_ports = [m["public_port"] for m in mappings]
    mikrotik.remove_vpn_user(user["vpn_username"], public_ports)
    db.deactivate_user(user["id"])
    return f"Akun `{user['vpn_username']}` telah dinonaktifkan."
