import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ADMIN_TELEGRAM_IDS = {
    int(x.strip())
    for x in os.getenv("ADMIN_TELEGRAM_IDS", "").split(",")
    if x.strip().isdigit()
}

MIKROTIK_HOST = os.getenv("MIKROTIK_HOST", "127.0.0.1")
MIKROTIK_PORT = int(os.getenv("MIKROTIK_PORT", "8728"))
MIKROTIK_USER = os.getenv("MIKROTIK_USER", "admin")
MIKROTIK_PASSWORD = os.getenv("MIKROTIK_PASSWORD", "")

L2TP_IPSEC_SECRET = os.getenv("L2TP_IPSEC_SECRET", "ChangeMe!")
PUBLIC_HOST = os.getenv("PUBLIC_HOST", "127.0.0.1")
VPN_POOL_START = os.getenv("VPN_POOL_START", "10.80.0.2")
VPN_POOL_END = os.getenv("VPN_POOL_END", "10.80.0.254")

PORT_BASE = int(os.getenv("PORT_BASE", "10000"))
MAX_USERS = int(os.getenv("MAX_USERS", "100"))
DATABASE_PATH = os.getenv("DATABASE_PATH", "vpn-bot.db")

# service_index -> (label, internal_port)
SERVICES = {
    0: ("Custom", 6000),
    1: ("Www", 80),
    2: ("Winbox", 8291),
    3: ("Ssh", 22),
    4: ("API", 8728),
}


def pub_port(user_slot: int, service_index: int) -> int:
    return PORT_BASE + (user_slot * 10) + service_index
