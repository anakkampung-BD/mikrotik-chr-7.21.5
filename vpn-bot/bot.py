#!/usr/bin/env python3
"""Telegram bot untuk otomasi VPN remote access via MikroTik CHR."""

import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

import config
import db
import mikrotik
import provisioning

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_TELEGRAM_IDS


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛡 *VPN Remote Access Bot*\n\n"
        "Akses MikroTik/router Anda dari internet via L2TP tunnel + port forwarding.\n\n"
        "*Perintah:*\n"
        "/register — Buat akun VPN baru\n"
        "/status — Cek status koneksi\n"
        "/info — Lihat kredensial & port\n"
        "/delete — Hapus akun VPN\n"
        "/help — Bantuan setup client",
        parse_mode="Markdown",
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "*Setup L2TP Client di MikroTik Anda*\n\n"
        "1. Jalankan /register untuk dapat kredensial\n"
        "2. Paste perintah l2tp-client dari bot\n"
        "3. Setelah connect, gunakan port forwarding publik\n\n"
        "*Contoh akses Winbox:*\n"
        f"`{config.PUBLIC_HOST}:<port_winbox>`\n\n"
        "*Security Group VPS:* buka UDP 500, 4500, 1701 dan TCP 10000-10999",
        parse_mode="Markdown",
    )


async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        result = provisioning.provision_user(
            telegram_id=user.id,
            telegram_username=user.username or user.first_name or "",
        )
    except Exception as e:
        logger.exception("register failed")
        await update.message.reply_text(f"❌ Gagal: `{e}`", parse_mode="Markdown")
        return

    if "error" in result:
        err = result["error"]
        if err == "already_exists":
            u = result["user"]
            mappings = db.get_port_mappings(u["id"])
            session = mikrotik.get_active_l2tp_session(u["vpn_username"])
            msg = provisioning.format_success_message(u, mappings, session)
            await update.message.reply_text(msg, parse_mode="Markdown")
            return
        if err == "limit_reached":
            await update.message.reply_text("❌ Kuota user penuh. Hubungi admin.")
            return
        await update.message.reply_text(f"❌ Error: {err}")
        return

    msg = provisioning.format_success_message(result["user"], result["mappings"])
    await update.message.reply_text(msg, parse_mode="Markdown")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = db.get_user_by_telegram(update.effective_user.id)
    if not u or u["status"] != "active":
        await update.message.reply_text("Belum terdaftar. Gunakan /register")
        return

    session = mikrotik.get_active_l2tp_session(u["vpn_username"])
    mappings = db.get_port_mappings(u["id"])
    msg = provisioning.format_success_message(u, mappings, session)
    await update.message.reply_text(msg, parse_mode="Markdown")


async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await status(update, context)


async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        msg = provisioning.deactivate_user(update.effective_user.id)
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        logger.exception("delete failed")
        await update.message.reply_text(f"❌ Gagal: `{e}`", parse_mode="Markdown")


async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Unauthorized")
        return
    count = db.count_users()
    ok = mikrotik.test_connection()
    await update.message.reply_text(
        f"Users aktif: {count}/{config.MAX_USERS}\n"
        f"MikroTik API: {'✅ OK' if ok else '❌ FAIL'}\n"
        f"Public host: {config.PUBLIC_HOST}",
    )


def main():
    db.init_db()
    if not config.TELEGRAM_BOT_TOKEN or config.TELEGRAM_BOT_TOKEN == "your_bot_token_here":
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in .env")

    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("register", register))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(CommandHandler("delete", delete))
    app.add_handler(CommandHandler("admin", admin_stats))

    logger.info("Bot starting... API host=%s", config.MIKROTIK_HOST)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
