import secrets
import string
from typing import Optional

import librouteros
from librouteros import connect

import config


def _api():
    return connect(
        host=config.MIKROTIK_HOST,
        username=config.MIKROTIK_USER,
        password=config.MIKROTIK_PASSWORD,
        port=config.MIKROTIK_PORT,
    )


def _close(api):
    try:
        api.close()
    except Exception:
        pass


def generate_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def ensure_l2tp_server():
    """Pastikan L2TP server aktif dengan IPsec."""
    api = _api()
    try:
        path = api.path("/interface/l2tp-server/server")
        for row in path:
            path.update(**{row[".id"]: {
                "enabled": "yes",
                "use-ipsec": "required",
                "ipsec-secret": config.L2TP_IPSEC_SECRET,
                "default-profile": "default-encryption",
            }})
    finally:
        _close(api)


def create_vpn_user(
    vpn_username: str,
    vpn_password: str,
    tunnel_ip: str,
    port_mappings: list[tuple[int, int, str]],
) -> None:
    """
    Buat PPP secret + dst-nat rules di MikroTik.
    port_mappings: list of (public_port, internal_port, comment_suffix)
    """
    api = _api()
    try:
        secrets_path = api.path("/ppp/secret")
        secrets_path.add(
            name=vpn_username,
            password=vpn_password,
            service="l2tp",
            profile="default-encryption",
            **{"remote-address": tunnel_ip},
            comment=f"vpn-bot:{vpn_username}",
        )

        nat_path = api.path("/ip/firewall/nat")
        for pub_port, int_port, suffix in port_mappings:
            nat_path.add(
                chain="dstnat",
                action="dst-nat",
                protocol="tcp",
                **{"dst-port": str(pub_port), "to-addresses": tunnel_ip, "to-ports": str(int_port)},
                comment=f"vpn-bot:{vpn_username}:{suffix}",
            )
    finally:
        _close(api)


def remove_vpn_user(vpn_username: str, public_ports: list[int]) -> None:
    api = _api()
    try:
        p = api.path("/ppp/secret")
        for row in p:
            if row.get("name") == vpn_username:
                p.remove(row[".id"])

        nat_path = api.path("/ip/firewall/nat")
        for row in nat_path:
            comment = row.get("comment", "")
            if comment.startswith(f"vpn-bot:{vpn_username}:"):
                nat_path.remove(row[".id"])
    finally:
        _close(api)


def get_active_l2tp_session(vpn_username: str) -> Optional[dict]:
    api = _api()
    try:
        for row in api.path("/ppp/active"):
            if row.get("name") == vpn_username or row.get("user") == vpn_username:
                return dict(row)
    finally:
        _close(api)
    return None


def get_used_tunnel_ips() -> set[str]:
    ips: set[str] = set()
    api = _api()
    try:
        for row in api.path("/ppp/secret"):
            addr = row.get("remote-address")
            if addr:
                ips.add(str(addr))
    finally:
        _close(api)
    return ips


def test_connection() -> bool:
    try:
        api = _api()
        try:
            list(api.path("/system/resource"))
            return True
        finally:
            _close(api)
    except Exception:
        return False
