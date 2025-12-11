#!/usr/bin/env python3
"""
Telegram VIP bot with payment proof collection and inline join buttons.
Requires: python-telegram-bot==20.3, aiosqlite, python-dotenv, httpx
"""

import os
import asyncio
import aiosqlite
from typing import Optional
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__),'config','.env') if os.path.exists(os.path.join(os.path.dirname(__file__),'config','.env')) else None)

BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")

ADMIN_IDS = set(int(x.strip()) for x in (os.getenv("ADMIN_IDS") or "").split(",") if x.strip())
DB_PATH = os.getenv("DB_PATH") or os.path.join(os.path.dirname(__file__),"..","shared","subscriptions.db")
FALLBACK_UPI = os.getenv("UPI_ID","yourupi@bank")
FALLBACK_AMOUNT = float(os.getenv("SUBS_AMOUNT","199"))

VIP_TOPIC = "VIP"

# --- DB init ---
async def init_db():
    # create DB dir
    d = os.path.dirname(DB_PATH)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
CREATE TABLE IF NOT EXISTS topics ( name TEXT PRIMARY KEY );
CREATE TABLE IF NOT EXISTS users ( user_id INTEGER PRIMARY KEY, first_name TEXT, username TEXT );
CREATE TABLE IF NOT EXISTS subscriptions ( user_id INTEGER, topic TEXT, PRIMARY KEY(user_id,topic) );
CREATE TABLE IF NOT EXISTS channels ( topic TEXT, chat_id_or_invite TEXT, description TEXT, PRIMARY KEY(topic, chat_id_or_invite) );
CREATE TABLE IF NOT EXISTS payments ( id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, method TEXT, amount REAL, details TEXT, proof_file_id TEXT, status TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP );
CREATE TABLE IF NOT EXISTS settings ( key TEXT PRIMARY KEY, value TEXT );
CREATE TABLE IF NOT EXISTS wallets ( symbol TEXT PRIMARY KEY, address TEXT );
""")
        await db.commit()

# --- helpers ---
async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
        await db.commit()

async def get_setting(key: str) -> Optional[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT value FROM settings WHERE key=?", (key,))
        row = await cur.fetchone()
        return row[0] if row else None

async def set_wallet(symbol: str, address: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO wallets(symbol,address) VALUES(?,?) ON CONFLICT(symbol) DO UPDATE SET address=excluded.address", (symbol.upper(), address))
        await db.commit()

async def list_wallets():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT symbol,address FROM wallets ORDER BY symbol")
        rows = await cur.fetchall()
        return [{"symbol": r[0], "address": r[1]} for r in rows]

async def add_channel_for_topic(topic: str, chat_id_or_invite: str, description: str=""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO channels(topic, chat_id_or_invite, description) VALUES(?,?,?)", (topic, chat_id_or_invite, description))
        await db.commit()

async def get_channels_for_topic(topic: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT chat_id_or_invite, description FROM channels WHERE topic=?", (topic,))
        rows = await cur.fetchall()
        return [{"link": r[0], "desc": r[1]} for r in rows]

async def ensure_user(user_id:int, first_name:str, username:Optional[str]):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO users(user_id, first_name, username) VALUES(?,?,?)", (user_id, first_name, username))
        await db.commit()

async def save_payment(user_id:int, method:str, amount:float, details:str, proof_file_id:Optional[str]):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("INSERT INTO payments (user_id, method, amount, details, proof_file_id, status) VALUES (?,?,?,?,?, 'pending')", (user_id, method, amount, details, proof_file_id))
        await db.commit()
        return cur.lastrowid

async def get_payment(pid:int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id,user_id,method,amount,details,proof_file_id,status,created_at FROM payments WHERE id=?", (pid,))
        return await cur.fetchone()

async def update_payment_status(pid:int, status:str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE payments SET status=? WHERE id=?", (status, pid))
        await db.commit()

# --- utils ---
def is_admin(uid:int) -> bool:
    return uid in ADMIN_IDS

def vip_keyboard():
    kb = [
        [InlineKeyboardButton("Pay via UPI", callback_data="pay_upi"),
         InlineKeyboardButton("Pay via Crypto", callback_data="pay_crypto")]
    ]
    return InlineKeyboardMarkup(kb)

# --- handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await ensure_user(user.id, user.first_name or "", user.username)
    text = (
        f"नमस्ते {user.first_name or ''}!\n\n"
        "VIP subscription bot.\n\n"
        "/buy_vip - buy VIP\n"
        "/pay_info - current payment details\n"
        "/my_subs - your subscriptions\n"
    )
    await update.message.reply_text(text)

async def pay_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    upi = await get_setting("upi_id") or FALLBACK_UPI
    amt_val = await get_setting("subs_amount")
    amount = float(amt_val) if (amt_val and amt_val.replace('.','',1).isdigit()) else FALLBACK_AMOUNT
    wallets = await list_wallets()
    text = f"Payment Details\n\nAmount: ₹{amount}\n\nUPI ID: `{upi}`\n\nCrypto wallets:\n"
    if wallets:
        for w in wallets:
            text += f"- {w['symbol']}: `{w['address']}`\n"
    else:
        text += "No crypto wallets configured.\n"
    text += "\nSend screenshot or tx-hash here after payment."
    await update.message.reply_text(text, parse_mode="Markdown")

async def buy_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Choose payment method:", reply_markup=vip_keyboard())

async def cb_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "pay_upi":
        upi = await get_setting("upi_id") or FALLBACK_UPI
        amt_val = await get_setting("subs_amount")
        amount = float(amt_val) if (amt_val and amt_val.replace('.','',1).isdigit()) else FALLBACK_AMOUNT
        await q.message.reply_text(f"Pay ₹{amount} to UPI ID: `{upi}`\nSend screenshot or UPI ref here.", parse_mode="Markdown")
    else:
        amt_val = await get_setting("subs_amount")
        amount = float(amt_val) if (amt_val and amt_val.replace('.','',1).isdigit()) else FALLBACK_AMOUNT
        wallets = await list_wallets()
        if not wallets:
            await q.message.reply_text("No crypto wallets configured. Contact admin.")
            return
        msg = f"Pay approx ₹{amount} to one of these wallets:\n"
        for w in wallets:
            msg += f"- {w['symbol']}: `{w['address']}`\n"
        msg += "\nSend screenshot or tx-hash here."
        await q.message.reply_text(msg, parse_mode="Markdown")

async def payment_proof_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    file_id = None
    details = ""
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        details = "photo"
    elif update.message.document:
        file_id = update.message.document.file_id
        details = "document"
    elif update.message.text:
        details = update.message.text.strip()
    else:
        await update.message.reply_text("Send screenshot or transaction id.")
        return

    amt_val = await get_setting("subs_amount")
    amount = float(amt_val) if (amt_val and amt_val.replace('.','',1).isdigit()) else FALLBACK_AMOUNT

    await ensure_user(user.id, user.first_name or "", user.username)
    pid = await save_payment(user.id, "manual", amount, details, file_id)
    await update.message.reply_text(f"Payment proof received (ID {pid}). Admin will verify.")

    # forward to admins
    for aid in ADMIN_IDS:
        try:
            cap = f"Payment ID:{pid}\nFrom: {user.id} ({user.first_name or ''} @{user.username or ''})\nAmt: ₹{amount}\nDetails:{details}\nUse /approve {pid} or /reject {pid}"
            if file_id:
                await context.bot.send_photo(chat_id=aid, photo=file_id, caption=cap)
            else:
                await context.bot.send_message(chat_id=aid, text=cap)
        except Exception:
            pass

# create invite link or use stored invite -> send inline join button
async def send_join_button_for_user(context: ContextTypes.DEFAULT_TYPE, target_chat: str, user_id: int, desc: Optional[str]=None):
    invite_url = None
    try:
        # if looks like a chat id or @username we try createChatInviteLink
        if target_chat.startswith("-") or target_chat.startswith("@"):
            res = await context.bot.create_chat_invite_link(chat_id=target_chat, expire_date=None, member_limit=None)
            invite_url = res.invite_link
    except Exception:
        invite_url = None

    if not invite_url:
        if target_chat.startswith("http://") or target_chat.startswith("https://") or target_chat.startswith("t.me/"):
            invite_url = target_chat if target_chat.startswith("http") else "https://" + target_chat
        elif target_chat.startswith("@"):
            invite_url = f"https://t.me/{target_chat.lstrip('@')}"

    if not invite_url:
        try:
            await context.bot.send_message(chat_id=user_id, text=f"VIP access active but no valid invite for {target_chat}. Contact admin.")
        except:
            pass
        return

    kb = InlineKeyboardMarkup([[InlineKeyboardButton("Join VIP ▶️", url=invite_url)]])
    try:
        await context.bot.send_message(chat_id=user_id, text=f"🎉 Your VIP access is active! {desc or ''}", reply_markup=kb)
    except:
        pass

async def approve_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        return await update.message.reply_text("Only admin.")
    if not context.args:
        return await update.message.reply_text("Usage: /approve <payment_id>")
    try:
        pid = int(context.args[0])
    except:
        return await update.message.reply_text("Payment id must be integer.")
    row = await get_payment(pid)
    if not row:
        return await update.message.reply_text("Payment not found.")
    _, uid, method, amount, details, proof_file_id, status, _ = row
    if status == "approved":
        return await update.message.reply_text("Already approved.")
    await update_payment_status(pid, "approved")
    # subscribe and send join buttons
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO subscriptions(user_id, topic) VALUES(?,?)", (uid, VIP_TOPIC))
        await db.commit()

    channels = await get_channels_for_topic(VIP_TOPIC)
    if not channels:
        try:
            await context.bot.send_message(chat_id=uid, text="🎉 Payment approved — you're VIP now. Admin hasn't configured join links yet.")
        except:
            pass
        return

    for ch in channels:
        await send_join_button_for_user(context, ch["link"], uid, ch.get("desc"))

    await update.message.reply_text(f"Approved {pid} and sent join links to {uid}.")

async def reject_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        return await update.message.reply_text("Only admin.")
    if not context.args:
        return await update.message.reply_text("Usage: /reject <payment_id> [reason]")
    try:
        pid = int(context.args[0])
    except:
        return await update.message.reply_text("Payment id must be integer.")
    reason = " ".join(context.args[1:]) if len(context.args) > 1 else "Rejected by admin"
    row = await get_payment(pid)
    if not row:
        return await update.message.reply_text("Payment not found.")
    _, uid, *_ = row
    await update_payment_status(pid, "rejected")
    try:
        await context.bot.send_message(chat_id=uid, text=f"Your payment (ID {pid}) was rejected. Reason: {reason}")
    except:
        pass
    await update.message.reply_text(f"Payment {pid} rejected.")

# admin: channel management, settings
async def add_channel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("Only admin.")
    if len(context.args) < 2:
        return await update.message.reply_text("Usage: /add_channel <topic> <chat_id_or_invite> [desc]")
    topic = context.args[0]
    link = context.args[1]
    desc = " ".join(context.args[2:]) if len(context.args) > 2 else ""
    await add_channel_for_topic(topic, link, desc)
    await update.message.reply_text(f"Added channel {link} for {topic}.")

async def set_upi_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("Only admin.")
    if not context.args:
        return await update.message.reply_text("Usage: /set_upi <upi>")
    await set_setting("upi_id", context.args[0])
    await update.message.reply_text("UPI set.")

async def set_amount_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("Only admin.")
    if not context.args:
        return await update.message.reply_text("Usage: /set_amount <amount>")
    try:
        a = float(context.args[0])
    except:
        return await update.message.reply_text("Amount must be numeric.")
    await set_setting("subs_amount", str(a))
    await update.message.reply_text("Amount set.")

async def set_crypto_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("Only admin.")
    if len(context.args) < 2:
        return await update.message.reply_text("Usage: /set_crypto <symbol> <address>")
    sym = context.args[0]
    addr = " ".join(context.args[1:])
    await set_wallet(sym, addr)
    await update.message.reply_text("Wallet set.")

async def list_wallets_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("Only admin.")
    w = await list_wallets()
    if not w:
        return await update.message.reply_text("No wallets configured.")
    text = "Wallets:\n" + "\n".join(f"- {x['symbol']}: {x['address']}" for x in w)
    await update.message.reply_text(text)

async def my_subs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT topic FROM subscriptions WHERE user_id=? ORDER BY topic", (user.id,))
        rows = await cur.fetchall()
    if not rows:
        await update.message.reply_text("You have no subscriptions.")
    else:
        await update.message.reply_text("Your subscriptions:\n" + "\n".join(f"- {r[0]}" for r in rows))

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Unknown command. /start")

# bootstrap
async def main():
    await init_db()
    # ensure VIP topic exists
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO topics(name) VALUES(?)", (VIP_TOPIC,))
        await db.commit()

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("pay_info", pay_info))
    app.add_handler(CommandHandler("buy_vip", buy_vip))
    app.add_handler(CallbackQueryHandler(cb_handler))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL | (filters.TEXT & (~filters.COMMAND)), payment_proof_handler))

    app.add_handler(CommandHandler("approve", approve_cmd))
    app.add_handler(CommandHandler("reject", reject_cmd))
    app.add_handler(CommandHandler("add_channel", add_channel_cmd))
    app.add_handler(CommandHandler("set_upi", set_upi_cmd))
    app.add_handler(CommandHandler("set_amount", set_amount_cmd))
    app.add_handler(CommandHandler("set_crypto", set_crypto_cmd))
    app.add_handler(CommandHandler("list_wallets", list_wallets_cmd))
    app.add_handler(CommandHandler("my_subs", my_subs_cmd))

    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    print("Bot starting (polling)...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
