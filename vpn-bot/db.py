import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

import config


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    vpn_username TEXT UNIQUE,
    vpn_password TEXT NOT NULL,
    tunnel_ip TEXT UNIQUE,
    user_slot INTEGER UNIQUE NOT NULL,
    status TEXT DEFAULT 'active',
    created_at TEXT NOT NULL,
    expires_at TEXT
);

CREATE TABLE IF NOT EXISTS port_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    service_index INTEGER NOT NULL,
    service_label TEXT NOT NULL,
    internal_port INTEGER NOT NULL,
    public_port INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(user_id, service_index)
);
"""


@contextmanager
def get_db():
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.executescript(SCHEMA)


def get_user_by_telegram(telegram_id: int) -> Optional[sqlite3.Row]:
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ).fetchone()


def get_user_by_vpn_username(username: str) -> Optional[sqlite3.Row]:
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE vpn_username = ?", (username,)
        ).fetchone()


def count_users() -> int:
    with get_db() as conn:
        return conn.execute("SELECT COUNT(*) FROM users WHERE status='active'").fetchone()[0]


def next_free_slot() -> Optional[int]:
    with get_db() as conn:
        used = {
            row[0]
            for row in conn.execute(
                "SELECT user_slot FROM users WHERE status='active'"
            ).fetchall()
        }
        for slot in range(1, config.MAX_USERS + 1):
            if slot not in used:
                return slot
    return None


def next_free_ip() -> Optional[str]:
    base = config.VPN_POOL_START.rsplit(".", 1)
    start = int(config.VPN_POOL_START.split(".")[-1])
    end = int(config.VPN_POOL_END.split(".")[-1])
    prefix = ".".join(config.VPN_POOL_START.split(".")[:-1])

    with get_db() as conn:
        used = {
            row[0]
            for row in conn.execute(
                "SELECT tunnel_ip FROM users WHERE status='active'"
            ).fetchall()
        }
        for host in range(start, end + 1):
            ip = f"{prefix}.{host}"
            if ip not in used:
                return ip
    return None


def create_user(
    telegram_id: int,
    username: str,
    vpn_username: str,
    vpn_password: str,
    tunnel_ip: str,
    user_slot: int,
) -> int:
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO users
               (telegram_id, username, vpn_username, vpn_password, tunnel_ip,
                user_slot, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (telegram_id, username, vpn_username, vpn_password, tunnel_ip, user_slot, now),
        )
        user_id = cur.lastrowid
        for svc_idx, (label, internal_port) in config.SERVICES.items():
            conn.execute(
                """INSERT INTO port_mappings
                   (user_id, service_index, service_label, internal_port, public_port)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    user_id,
                    svc_idx,
                    label,
                    internal_port,
                    config.pub_port(user_slot, svc_idx),
                ),
            )
        return user_id


def get_port_mappings(user_id: int) -> list[sqlite3.Row]:
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM port_mappings WHERE user_id = ? ORDER BY service_index",
            (user_id,),
        ).fetchall()


def deactivate_user(user_id: int):
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET status='inactive' WHERE id = ?", (user_id,)
        )
