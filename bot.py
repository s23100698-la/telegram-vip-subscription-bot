#bot.py
import telebot
import logging
import time
import os
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

# ==================== CONFIGURATION ====================

# Validate and load configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_IDS")

# Validate configuration
if not BOT_TOKEN or "YOUR_TOKEN" in BOT_TOKEN or len(BOT_TOKEN) < 40:
    print("❌ ERROR: Bot token not set or invalid in .env file!")
    print("Please add your valid bot token to .env file")
    print("Get token from @BotFather on Telegram")
    print(f"Current token: {BOT_TOKEN}")
    exit(1)

if not ADMIN_ID or "YOUR" in ADMIN_ID:
    print("❌ ERROR: Admin ID not set in .env file!")
    print("Please add your Telegram user ID to .env file")
    print("Get your ID from @userinfobot on Telegram")
    exit(1)

try:
    ADMIN_ID = int(ADMIN_ID)
except ValueError:
    print("❌ ERROR: Admin ID must be a number!")
    print(f"Got: {ADMIN_ID}")
    exit(1)

# Load other configuration
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@StreamxPlayer")
CHANNEL_INVITE_LINK = os.getenv("CHANNEL_INVITE_LINK", "https://t.me/+wK-uZ4uhG3ozYjNl")
UPI_ID = os.getenv("UPI_ID", "yourbusiness@oksbi")

# Payment Details
BANK_DETAILS = {
    "account": os.getenv("BANK_ACCOUNT_NAME", "YOUR BUSINESS"),
    "bank": os.getenv("BANK_NAME", "STATE BANK OF INDIA"),
    "account_no": os.getenv("BANK_ACCOUNT_NUMBER", "123456789012"),
    "ifsc": os.getenv("BANK_IFSC", "SBIN0001234")
}

# Debug info
print("=" * 50)
print("🤖 STREAMX SUBSCRIPTION BOT - STARTING")
print("=" * 50)
print(f"✅ Bot Token: {'[VALID]' if BOT_TOKEN and len(BOT_TOKEN) > 40 else '[INVALID]'}")
print(f"✅ Admin ID: {ADMIN_ID}")
print(f"✅ Channel: {CHANNEL_USERNAME}")
print(f"✅ UPI ID: {UPI_ID}")
print("=" * 50)

# ==================== LOGGING SETUP ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== BOT INITIALIZATION ====================

bot = telebot.TeleBot(BOT_TOKEN)

# ==================== DATABASE UTILITIES ====================

# Simple thread-safe database connection manager
import sqlite3
import threading

class DatabaseManager:
    """Simple thread-safe database connection manager."""
    
    _local = threading.local()
    
    @staticmethod
    def get_connection():
        """Get a thread-local database connection."""
        if not hasattr(DatabaseManager._local, 'connection') or DatabaseManager._local.connection is None:
            try:
                conn = sqlite3.connect(
                    'subscriptions.db',
                    check_same_thread=False,
                    timeout=30,
                    detect_types=sqlite3.PARSE_DECLTYPES
                )
                # Enable WAL mode for better concurrency
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA busy_timeout=5000")
                DatabaseManager._local.connection = conn
            except Exception as e:
                logger.error(f"Failed to create database connection: {e}")
                raise
        return DatabaseManager._local.connection
    
    @staticmethod
    def execute_query(query, params=None, fetchone=False, fetchall=False, commit=False):
        """Execute a database query safely."""
        conn = DatabaseManager.get_connection()
        cursor = None
        try:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if commit:
                conn.commit()
            
            if fetchone:
                return cursor.fetchone()
            elif fetchall:
                return cursor.fetchall()
            else:
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Database query failed: {e}")
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            raise
        finally:
            if cursor:
                cursor.close()
            # DO NOT close connection here

# ==================== DATABASE / BUSINESS LOGIC ====================

def init_db():
    """Initialize database tables."""
    try:
        # Users table
        DatabaseManager.execute_query('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            name TEXT,
            join_date TEXT,
            expiry_date TEXT,
            plan TEXT DEFAULT 'free',
            status TEXT DEFAULT 'active',
            last_active TEXT
        )
        ''', commit=True)

        # Plans table
        DatabaseManager.execute_query('''
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY,
            name TEXT,
            days INTEGER,
            price INTEGER,
            description TEXT,
            features TEXT
        )
        ''', commit=True)

        # Payments table
        DatabaseManager.execute_query('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            plan_id INTEGER,
            amount INTEGER,
            method TEXT,
            status TEXT DEFAULT 'pending',
            timestamp TEXT,
            transaction_id TEXT
        )
        ''', commit=True)

        # Insert default plans if not present
        result = DatabaseManager.execute_query("SELECT COUNT(*) FROM plans", fetchone=True)
        if result and result[0] == 0:
            plans = [
                (1, '⭐ BASIC - 1 Week', 7, 99,
                 'Weekly access to private channel',
                 '✅ Channel Access\n✅ Basic Support\n✅ Weekly Updates'),

                (2, '🚀 PRO - 1 Month', 30, 299,
                 'Monthly access with priority support',
                 '✅ Channel Access\n✅ Priority Support\n✅ Daily Updates\n✅ HD Content'),

                (3, '🔥 PREMIUM - 3 Months', 90, 799,
                 '3 months access + bonus content',
                 '✅ Channel Access\n✅ Priority Support\n✅ All Updates\n✅ Bonus Content\n✅ 4K Quality'),

                (4, '👑 LIFETIME', 36500, 1999,
                 'Lifetime access + all future updates',
                 '✅ Lifetime Access\n✅ VIP Support\n✅ All Content\n✅ Future Updates\n✅ Special Badge\n✅ Early Access')
            ]
            for plan in plans:
                DatabaseManager.execute_query(
                    'INSERT OR IGNORE INTO plans (id, name, days, price, description, features) VALUES (?, ?, ?, ?, ?, ?)',
                    plan,
                    commit=True
                )

        logger.info("Database initialized")
    except Exception as e:
        logger.exception(f"init_db failed: {e}")

def has_active_subscription(user_id):
    """Check if user has active subscription."""
    try:
        result = DatabaseManager.execute_query(
            "SELECT expiry_date FROM users WHERE user_id = ?",
            (user_id,),
            fetchone=True
        )
        
        if result and result[0]:
            try:
                expiry = datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S')
            except Exception:
                expiry = datetime.fromisoformat(result[0])
            return expiry > datetime.now()
        return False
    except Exception as e:
        logger.error(f"has_active_subscription error for {user_id}: {e}")
        return False

def add_subscription(user_id, plan_id, days):
    """Add subscription to user."""
    try:
        # Get plan details
        result = DatabaseManager.execute_query(
            "SELECT name FROM plans WHERE id = ?",
            (plan_id,),
            fetchone=True
        )
        if not result:
            logger.error(f"Plan {plan_id} not found")
            return False
        
        plan_name = result[0]
        
        # Calculate expiry
        new_expiry = datetime.now() + timedelta(days=days)
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Check if user exists
        user_exists = DatabaseManager.execute_query(
            "SELECT user_id FROM users WHERE user_id = ?",
            (user_id,),
            fetchone=True
        )
        
        if user_exists:
            # Update existing user
            DatabaseManager.execute_query('''
            UPDATE users 
            SET plan = ?, expiry_date = ?, status = 'active', last_active = ?
            WHERE user_id = ?
            ''', (plan_name, new_expiry.strftime('%Y-%m-%d %H:%M:%S'), current_time, user_id),
            commit=True)
        else:
            # Insert new user
            DatabaseManager.execute_query('''
            INSERT INTO users (user_id, username, name, join_date, expiry_date, plan, status, last_active)
            VALUES (?, ?, ?, ?, ?, ?, 'active', ?)
            ''', (user_id, '', '', current_time, 
                  new_expiry.strftime('%Y-%m-%d %H:%M:%S'), plan_name, current_time),
            commit=True)
        
        logger.info(f"Subscription added for user {user_id}, plan {plan_name}, {days} days")
        return True
        
    except Exception as e:
        logger.exception(f"add_subscription failed for {user_id}: {e}")
        return False

# Initialize DB on startup
init_db()

# ==================== DB MIGRATION: ensure referral columns exist ====================
def ensure_user_columns():
    try:
        conn = DatabaseManager.get_connection()
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(users)")
        cols = [r[1] for r in cur.fetchall()]
        if "balance" not in cols:
            try:
                cur.execute("ALTER TABLE users ADD COLUMN balance INTEGER DEFAULT 0")
                logger.info("Added 'balance' column to users table.")
            except Exception as e:
                logger.warning(f"Could not add 'balance' column: {e}")
        if "withdraw_state" not in cols:
            try:
                cur.execute("ALTER TABLE users ADD COLUMN withdraw_state TEXT DEFAULT NULL")
                logger.info("Added 'withdraw_state' column to users table.")
            except Exception as e:
                logger.warning(f"Could not add 'withdraw_state' column: {e}")
        conn.commit()
        cur.close()
    except Exception as e:
        logger.exception(f"ensure_user_columns failed: {e}")

# call it once on startup
ensure_user_columns()

# ==================== KEYBOARDS ====================

def main_menu(user_id=None):
    keyboard = InlineKeyboardMarkup(row_width=2)

    buttons = [
        ("📋 View Plans", "view_plans"),
        ("🔍 My Subscription", "my_subscription"),
        ("💳 Payment Methods", "payment_methods"),
        ("📞 Contact Support", "contact_support"),
        ("❓ How to Pay", "how_to_pay"),
        ("🎁 Refer & Earn", "refer_earn"),
        ("🔗 Join Channel", "join_channel"),
        ("⭐ Rate Us", "rate_us")
    ]

    for i in range(0, len(buttons), 2):
        keyboard.row(
            InlineKeyboardButton(buttons[i][0], callback_data=buttons[i][1]),
            InlineKeyboardButton(buttons[i+1][0], callback_data=buttons[i+1][1])
        )

    if user_id == ADMIN_ID:
        keyboard.add(InlineKeyboardButton("👑 Admin Panel", callback_data="admin_panel"))

    return keyboard

def plans_keyboard():
    try:
        plans = DatabaseManager.execute_query(
            "SELECT id, name, price, days FROM plans ORDER BY price",
            fetchall=True
        )
    except Exception as e:
        logger.error(f"Error fetching plans: {e}")
        plans = []

    keyboard = InlineKeyboardMarkup(row_width=1)
    for plan in plans:
        button_text = f"{plan[1]} - ₹{plan[2]} ({plan[3]} days)"
        keyboard.add(InlineKeyboardButton(button_text, callback_data=f"plan_{plan[0]}"))

    keyboard.row(
        InlineKeyboardButton("🔙 Back", callback_data="main_menu"),
        InlineKeyboardButton("ℹ️ Compare", callback_data="compare_plans")
    )

    return keyboard

def plan_details_keyboard(plan_id):
    keyboard = InlineKeyboardMarkup(row_width=2)

    keyboard.row(
        InlineKeyboardButton("💳 Buy Now", callback_data=f"buy_{plan_id}"),
        InlineKeyboardButton("ℹ️ Features", callback_data=f"features_{plan_id}")
    )

    keyboard.row(
        InlineKeyboardButton("📋 All Plans", callback_data="view_plans"),
        InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
    )

    return keyboard

def payment_methods_keyboard(plan_id=None):
    keyboard = InlineKeyboardMarkup(row_width=2)

    methods = [
        ("📱 UPI Payment", "pay_upi"),
        ("🏦 Bank Transfer", "pay_bank"),
        ("📲 PhonePe", "pay_phonepe"),
        ("💳 Card", "pay_card"),
        ("💰 Crypto", "pay_crypto"),
        ("🤝 Manual", "pay_manual")
    ]

    for i in range(0, len(methods), 2):
        if i+1 < len(methods):
            callback1 = f"{methods[i][1]}_{plan_id}" if plan_id else methods[i][1]
            callback2 = f"{methods[i+1][1]}_{plan_id}" if plan_id else methods[i+1][1]
            keyboard.row(
                InlineKeyboardButton(methods[i][0], callback_data=callback1),
                InlineKeyboardButton(methods[i+1][0], callback_data=callback2)
            )

    if plan_id:
        keyboard.row(
            InlineKeyboardButton("🔙 Back", callback_data=f"plan_{plan_id}"),
            InlineKeyboardButton("🏠 Menu", callback_data="main_menu")
        )
    else:
        keyboard.add(InlineKeyboardButton("🔙 Back", callback_data="main_menu"))

    return keyboard

def confirm_payment_keyboard(plan_id, method):
    keyboard = InlineKeyboardMarkup(row_width=2)

    keyboard.row(
        InlineKeyboardButton("✅ I've Paid", callback_data=f"confirm_{method}_{plan_id}"),
        InlineKeyboardButton("❌ Cancel", callback_data=f"plan_{plan_id}")
    )

    keyboard.add(InlineKeyboardButton("📞 Need Help?", callback_data="contact_support"))
    keyboard.add(InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))

    return keyboard

def admin_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)

    buttons = [
        ("👥 All Users", "admin_users"),
        ("✅ Active Subs", "admin_active"),
        ("📊 Statistics", "admin_stats"),
        ("📢 Broadcast", "admin_broadcast"),
        ("➕ Add Sub", "admin_add_sub"),
        ("💳 Payments", "admin_payments"),
        ("⚙️ Settings", "admin_settings"),
        ("📋 Logs", "admin_logs")
    ]

    for i in range(0, len(buttons), 2):
        keyboard.row(
            InlineKeyboardButton(buttons[i][0], callback_data=buttons[i][1]),
            InlineKeyboardButton(buttons[i+1][0], callback_data=buttons[i+1][1])
        )

    keyboard.add(InlineKeyboardButton("🏠 User Menu", callback_data="main_menu"))
    return keyboard

# ==================== MESSAGE HANDLERS ====================

@bot.message_handler(commands=['start', 'menu', 'help'])
def start_command(message):
    user_id = message.from_user.id
    name = message.from_user.first_name or ""
    username = message.from_user.username or ""

    try:
        DatabaseManager.execute_query('''
        INSERT OR REPLACE INTO users (user_id, username, name, join_date, last_active)
        VALUES (?, ?, ?, ?, ?)
        ''', (user_id, username, name,
              datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
              datetime.now().strftime('%Y-%m-%d %H:%M:%S')) ,
        commit=True)
    except Exception as e:
        logger.error(f"Failed to insert/replace user on /start: {e}")

    welcome = f"""
🎉 Welcome {name}!

🤖 **STREAMX SUBSCRIPTION BOT**

🔐 Get exclusive access to premium content
✨ All features available through buttons

👇 **Use buttons below to navigate:**
    """

    bot.send_message(user_id, welcome, parse_mode='Markdown', reply_markup=main_menu(user_id))

@bot.message_handler(commands=['admin'])
def admin_command(message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        bot.reply_to(message, "❌ Unauthorized!")
        return

    text = """
👑 **ADMIN PANEL**

Select an option below:
    """

    bot.send_message(user_id, text, parse_mode='Markdown', reply_markup=admin_keyboard())

# ==================== CALLBACK HANDLERS ====================

# ===== Optimized unified callback router (REPLACE existing handle_callback) =====
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    # some callbacks arrive without message (inline queries etc.) - guard
    try:
        chat_id = call.message.chat.id
        msg_id = call.message.message_id
    except Exception:
        chat_id = None
        msg_id = None

    # Immediately stop spinner so user sees responsiveness
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass

    data = (call.data or "").strip()

    # update last_active (best-effort)
    try:
        DatabaseManager.execute_query(
            "UPDATE users SET last_active = ? WHERE user_id = ?",
            (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user_id),
            commit=True
        )
    except Exception as e:
        logger.debug(f"Could not update last_active for {user_id}: {e}")

    try:
        # ---------- MAIN MENU ----------
        if data == "main_menu":
            bot.edit_message_text(
                "📍 **MAIN MENU**\n\n*Select an option:*",
                chat_id, msg_id,
                parse_mode='Markdown',
                reply_markup=main_menu(user_id)
            )
            return

        # ---------- VIEW PLANS ----------
        if data == "view_plans":
            try:
                plans = DatabaseManager.execute_query(
                    "SELECT name, price, days, description FROM plans ORDER BY price",
                    fetchall=True
                ) or []
            except Exception as e:
                logger.error(f"Error fetching plans: {e}")
                plans = []

            text = "📋 **AVAILABLE SUBSCRIPTION PLANS**\n\n"
            for plan in plans:
                text += f"\n✨ **{plan[0]}**\n💰 Price: ₹{plan[1]}\n⏰ Duration: {plan[2]} days\n📝 {plan[3]}\n────────────────────\n"

            bot.edit_message_text(
                text,
                chat_id, msg_id,
                parse_mode='Markdown',
                reply_markup=plans_keyboard()
            )
            return

        # ---------- PLAN DETAILS / BUY ----------
        if data.startswith("plan_"):
            try:
                plan_id = int(data.split("_")[1])
            except Exception:
                bot.answer_callback_query(call.id, "Invalid plan.")
                return

            plan = DatabaseManager.execute_query(
                "SELECT name, price, days, description, features FROM plans WHERE id = ?",
                (plan_id,), fetchone=True
            )
            if not plan:
                bot.answer_callback_query(call.id, "Plan not found.")
                return

            text = f"""
🎯 **SELECTED PLAN**

✨ **{plan[0]}**
💰 **Price:** ₹{plan[1]}
⏰ **Duration:** {plan[2]} days
📝 **Description:** {plan[3]}

✅ **Features Included:**
{plan[4]}

👇 **Click below to proceed**
            """
            bot.edit_message_text(text, chat_id, msg_id, parse_mode='Markdown', reply_markup=plan_details_keyboard(plan_id))
            return

        if data.startswith("features_"):
            try:
                plan_id = int(data.split("_")[1])
            except Exception:
                bot.answer_callback_query(call.id, "Invalid plan.")
                return
            plan = DatabaseManager.execute_query(
                "SELECT name, features FROM plans WHERE id = ?",
                (plan_id,), fetchone=True
            )
            if not plan:
                bot.answer_callback_query(call.id, "Plan not found.")
                return
            text = f"""
✨ **{plan[0]} - FULL FEATURES**

✅ **Included Features:**
{plan[1]}

🎁 **Additional Benefits:**
• Instant access after payment
• 24/7 Support
• Regular content updates
• No hidden charges
            """
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("💳 Buy Now", callback_data=f"buy_{plan_id}"))
            keyboard.add(InlineKeyboardButton("🔙 Back", callback_data=f"plan_{plan_id}"))
            bot.edit_message_text(text, chat_id, msg_id, parse_mode='Markdown', reply_markup=keyboard)
            return

        if data.startswith("buy_"):
            try:
                plan_id = int(data.split("_")[1])
            except Exception:
                bot.answer_callback_query(call.id, "Invalid request.")
                return
            plan = DatabaseManager.execute_query(
                "SELECT name, price FROM plans WHERE id = ?",
                (plan_id,), fetchone=True
            )
            if not plan:
                bot.answer_callback_query(call.id, "Plan not found!")
                return
            text = f"""
💳 **PAYMENT FOR {plan[0]}**

💰 **Amount:** ₹{plan[1]}

**Select payment method:**
            """
            bot.edit_message_text(text, chat_id, msg_id, parse_mode='Markdown', reply_markup=payment_methods_keyboard(plan_id))
            return

        # ---------- PAYMENT METHODS ----------
        if data.startswith("pay_"):
            # handles pay_upi_<id>, pay_bank_<id>, pay_phonepe_<id> etc.
            parts = data.split("_")
            # form: pay, method, planid OR pay, method if no plan
            if len(parts) >= 3:
                method = parts[1]
                try:
                    plan_id = int(parts[2])
                except Exception:
                    bot.answer_callback_query(call.id, "Invalid plan id.")
                    return
            else:
                method = parts[1]
                plan_id = None

            plan = None
            if plan_id:
                plan = DatabaseManager.execute_query("SELECT name, price FROM plans WHERE id = ?", (plan_id,), fetchone=True)

            # UPI flow
            if method == "upi":
                if not plan:
                    bot.answer_callback_query(call.id, "Plan not found!")
                    return
                text = f"""
📱 **UPI PAYMENT INSTRUCTIONS**

**Plan:** {plan[0]}
**Amount:** ₹{plan[1]}

Send ₹{plan[1]} to UPI ID:
`{UPI_ID}`

Add `UserID: {user_id}` in note and click ✅ I've Paid.
                """
                bot.edit_message_text(text, chat_id, msg_id, parse_mode='Markdown', reply_markup=confirm_payment_keyboard(plan_id, "upi"))
                return
            else:
                # generic method info
                text = f"📝 Payment method: {method.upper()}\nContact support for instructions."
                keyboard = InlineKeyboardMarkup()
                keyboard.add(InlineKeyboardButton("📞 Contact Support", callback_data="contact_support"))
                if plan_id:
                    keyboard.add(InlineKeyboardButton("🔙 Back", callback_data=f"buy_{plan_id}"))
                bot.edit_message_text(text, chat_id, msg_id, parse_mode='Markdown', reply_markup=keyboard)
                return

        # CONFIRM PAYMENT
        if data.startswith("confirm_"):
            parts = data.split("_")
            if len(parts) < 3:
                bot.answer_callback_query(call.id, "Invalid confirm request.")
                return
            method = parts[1]
            try:
                plan_id = int(parts[2])
            except Exception:
                bot.answer_callback_query(call.id, "Invalid plan id.")
                return

            plan = DatabaseManager.execute_query("SELECT name, price, days FROM plans WHERE id = ?", (plan_id,), fetchone=True)
            if not plan:
                bot.answer_callback_query(call.id, "Plan not found!")
                return

            # create payment record
            try:
                DatabaseManager.execute_query('''
                    INSERT INTO payments (user_id, plan_id, amount, method, status, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_id, plan_id, plan[1], method, 'pending', datetime.now().strftime('%Y-%m-%d %H:%M:%S')), commit=True)

                result = DatabaseManager.execute_query("SELECT last_insert_rowid()", fetchone=True)
                payment_id = result[0] if result else "N/A"

                admin_msg = f"""
⚠️ NEW PAYMENT REQUEST
User: {call.from_user.first_name} (@{call.from_user.username})
User ID: `{user_id}`
Plan: {plan[0]}
Amount: ₹{plan[1]}
Method: {method}
Payment ID: `{payment_id}`
To approve: /approve {payment_id}
"""
                try:
                    bot.send_message(ADMIN_ID, admin_msg, parse_mode='Markdown')
                except Exception as e:
                    logger.error(f"Failed to notify admin: {e}")

                text = f"✅ Payment Request submitted. Payment ID: `{payment_id}`. Wait for verification."
                keyboard = InlineKeyboardMarkup()
                keyboard.add(InlineKeyboardButton("📞 Contact Support", callback_data="contact_support"))
                keyboard.add(InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))
                bot.edit_message_text(text, chat_id, msg_id, parse_mode='Markdown', reply_markup=keyboard)
                bot.answer_callback_query(call.id, "Payment request submitted!")
                return
            except Exception as e:
                logger.exception(f"Failed while confirming payment: {e}")
                bot.answer_callback_query(call.id, "❌ Failed to submit payment.")
                return

        # ---------- MY SUBSCRIPTION ----------
        if data == "my_subscription":
            user = DatabaseManager.execute_query("SELECT plan, expiry_date FROM users WHERE user_id = ?", (user_id,), fetchone=True)
            show_channel = False
            if user and user[1]:
                try:
                    expiry = datetime.strptime(user[1], '%Y-%m-%d %H:%M:%S')
                except Exception:
                    expiry = datetime.fromisoformat(user[1])
                days_left = (expiry - datetime.now()).days
                if days_left > 0:
                    status = "✅ ACTIVE"
                    status_desc = f"Expires in {days_left} days"
                    show_channel = True
                else:
                    status = "❌ EXPIRED"
                    status_desc = f"Expired {abs(days_left)} days ago"
                    show_channel = False
                text = f"""
🔍 **MY SUBSCRIPTION**

📅 **Plan:** {user[0]}
📆 **Expiry Date:** {expiry.strftime('%d %b %Y')}
⏳ **Status:** {status}
📝 **Note:** {status_desc}
                """
            else:
                text = "❌ **NO ACTIVE SUBSCRIPTION**\n\nYou don't have an active subscription."
                show_channel = False

            keyboard = InlineKeyboardMarkup(row_width=2)
            if show_channel:
                keyboard.row(InlineKeyboardButton("🔗 Join Channel", url=CHANNEL_INVITE_LINK), InlineKeyboardButton("🔄 Renew", callback_data="view_plans"))
            else:
                keyboard.row(InlineKeyboardButton("💳 Subscribe", callback_data="view_plans"), InlineKeyboardButton("📋 View Plans", callback_data="view_plans"))
            keyboard.add(InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))
            bot.edit_message_text(text, chat_id, msg_id, parse_mode='Markdown', reply_markup=keyboard)
            return

        # ---------- JOIN CHANNEL ----------
        if data == "join_channel":
            if has_active_subscription(user_id):
                keyboard = InlineKeyboardMarkup()
                keyboard.add(InlineKeyboardButton("🔗 Join Now", url=CHANNEL_INVITE_LINK))
                keyboard.add(InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))
                bot.edit_message_text("🔗 **JOIN PRIVATE CHANNEL**\n\nYou have active subscription!\n\nClick below to join:", chat_id, msg_id, parse_mode='Markdown', reply_markup=keyboard)
            else:
                keyboard = InlineKeyboardMarkup()
                keyboard.add(InlineKeyboardButton("💳 Subscribe Now", callback_data="view_plans"))
                keyboard.add(InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))
                bot.edit_message_text("❌ **ACCESS DENIED**\n\nYou need an active subscription to join the channel.", chat_id, msg_id, parse_mode='Markdown', reply_markup=keyboard)
            return

        # ---------- CONTACT SUPPORT ----------
        if data == "contact_support":
            text = f"""
📞 **CONTACT SUPPORT**

For payment or subscription help. Please provide your User ID: `{user_id}`
            """
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))
            bot.edit_message_text(text, chat_id, msg_id, parse_mode='Markdown', reply_markup=keyboard)
            return

        # ---------- HOW TO PAY ----------
        if data == "how_to_pay":
            keyboard = InlineKeyboardMarkup(row_width=2)
            keyboard.row(InlineKeyboardButton("📋 View Plans", callback_data="view_plans"), InlineKeyboardButton("📞 Contact Support", callback_data="contact_support"))
            keyboard.add(InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))
            bot.edit_message_text("❓ **HOW TO PAY - STEP BY STEP**\n\n1. Click View Plans\n2. Choose plan\n3. Click Buy Now\n4. Select payment method\n5. Make payment\n6. Click ✅ I've Paid", chat_id, msg_id, parse_mode='Markdown', reply_markup=keyboard)
            return

        # ---------- REFER & EARN (copy + withdraw) ----------
        if data == "refer_earn":
            # re-show refer screen (same as before)
            try:
                bot_info = bot.get_me()
                bot_username = bot_info.username
            except Exception:
                bot_username = CHANNEL_USERNAME.replace("@", "") or "streamXsub_bot"
            referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
            text = f"""
🎁 **REFER & EARN PROGRAM**

**Your Referral Link:**
`{referral_link}`

Earn 10% commission on referrals.
Current balance shown in your chat.
            """
            keyboard = InlineKeyboardMarkup(row_width=2)
            keyboard.row(InlineKeyboardButton("📋 Copy Link", callback_data="copy_ref_link"),
                         InlineKeyboardButton("💰 Withdraw", callback_data="withdraw_earnings"))
            keyboard.add(InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))
            bot.edit_message_text(text, chat_id, msg_id, parse_mode='Markdown', reply_markup=keyboard)
            return

        if data == "copy_ref_link":
            try:
                bot_info = bot.get_me()
                bot_username = bot_info.username
            except Exception:
                bot_username = CHANNEL_USERNAME.replace("@", "") or "streamXsub_bot"
            referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
            try:
                bot.send_message(user_id, f"📋 Your referral link:\n{referral_link}")
                bot.answer_callback_query(call.id, "Link sent to your chat.")
            except Exception:
                bot.answer_callback_query(call.id, "Unable to send link in chat.")
            return

        if data == "withdraw_earnings":
            # Check user's balance column (balanced added by migration)
            try:
                res = DatabaseManager.execute_query("SELECT balance FROM users WHERE user_id = ?", (user_id,), fetchone=True)
            except Exception as e:
                logger.debug(f"withdraw query failed: {e}")
                res = None
            balance = 0
            if res:
                try:
                    balance = int(res[0] or 0)
                except Exception:
                    balance = 0
            if balance <= 0:
                bot.answer_callback_query(call.id, "You have ₹0 balance.")
                return
            # Ask for UPI id via private message (simple flow)
            try:
                bot.send_message(user_id, f"💰 Your balance: ₹{balance}\nReply with your UPI ID to withdraw (or contact admin).")
                # set withdraw_state so next message can be handled (if you implement message handler)
                try:
                    DatabaseManager.execute_query("UPDATE users SET withdraw_state = ? WHERE user_id = ?", ("awaiting_upi", user_id), commit=True)
                except Exception:
                    pass
                bot.answer_callback_query(call.id, "Withdrawal started. Check your chat.")
            except Exception:
                bot.answer_callback_query(call.id, "Unable to start withdrawal.")
            return

        # ---------- ADMIN PANEL ----------
        if data == "admin_panel":
            if user_id != ADMIN_ID:
                bot.answer_callback_query(call.id, "❌ Unauthorized")
                return
            bot.edit_message_text("👑 **ADMIN PANEL**\n\nSelect an option below:", chat_id, msg_id, parse_mode='Markdown', reply_markup=admin_keyboard())
            return

        # admin actions
        if data == "admin_users":
            if user_id != ADMIN_ID:
                bot.answer_callback_query(call.id, "❌ Unauthorized")
                return
            rows = DatabaseManager.execute_query("SELECT user_id, username, plan, expiry_date FROM users ORDER BY join_date DESC LIMIT 20", fetchall=True) or []
            if not rows:
                bot.send_message(user_id, "No users found.")
            else:
                text = "👥 Latest Users (up to 20):\n\n"
                for r in rows:
                    text += f"• {r[0]} / @{r[1] or '-'} — {r[2] or 'free'} — exp:{r[3] or '-'}\n"
                bot.send_message(user_id, text)
            bot.answer_callback_query(call.id)
            return

        if data == "admin_active":
            if user_id != ADMIN_ID:
                return
            total_active = DatabaseManager.execute_query("SELECT COUNT(*) FROM users WHERE expiry_date > datetime('now')", fetchone=True) or (0,)
            bot.send_message(user_id, f"✅ Active subscriptions: {total_active[0] if total_active else 0}")
            bot.answer_callback_query(call.id)
            return

        if data == "admin_stats":
            if user_id != ADMIN_ID:
                return
            try:
                total_users = DatabaseManager.execute_query("SELECT COUNT(*) FROM users", fetchone=True)[0]
                active_subs = DatabaseManager.execute_query("SELECT COUNT(*) FROM users WHERE expiry_date > datetime('now')", fetchone=True)[0]
                pending_payments = DatabaseManager.execute_query("SELECT COUNT(*) FROM payments WHERE status = 'pending'", fetchone=True)[0]
                total_revenue = DatabaseManager.execute_query("SELECT SUM(amount) FROM payments WHERE status = 'completed'", fetchone=True)[0] or 0
            except Exception as e:
                logger.error(f"Error fetching admin stats: {e}")
                total_users = active_subs = pending_payments = total_revenue = 0
            text = f"""
📊 **ADMIN STATISTICS**

👥 Total Users: {total_users}
✅ Active Subscriptions: {active_subs}
💰 Total Revenue: ₹{total_revenue}
⏳ Pending Payments: {pending_payments}
            """
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("🔄 Refresh", callback_data="admin_stats"))
            keyboard.add(InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel"))
            bot.edit_message_text(text, chat_id, msg_id, parse_mode='Markdown', reply_markup=keyboard)
            return

        if data == "admin_payments":
            if user_id != ADMIN_ID:
                return
            pend = DatabaseManager.execute_query("SELECT id, user_id, plan_id, amount, timestamp FROM payments WHERE status = 'pending' ORDER BY id DESC LIMIT 20", fetchall=True) or []
            if not pend:
                bot.send_message(user_id, "No pending payments.")
            else:
                text = "⏳ Pending payments (up to 20):\n\n"
                for p in pend:
                    text += f"• ID:{p[0]} UID:{p[1]} Plan:{p[2]} ₹{p[3]} at {p[4]}\n"
                bot.send_message(user_id, text)
            bot.answer_callback_query(call.id)
            return

        if data == "admin_broadcast":
            if user_id != ADMIN_ID:
                return
            bot.send_message(user_id, "📢 To broadcast: use /broadcast_send <message> (this bot supports a separate /broadcast_send admin command).")
            bot.answer_callback_query(call.id)
            return

        if data == "admin_add_sub":
            if user_id != ADMIN_ID:
                return
            bot.send_message(user_id, "➕ Use /addsub <user_id> <days> to add subscription.")
            bot.answer_callback_query(call.id)
            return

        if data == "admin_settings":
            if user_id != ADMIN_ID:
                return
            bot.send_message(user_id, "⚙️ Admin settings: (not yet implemented in UI). Use commands.")
            bot.answer_callback_query(call.id)
            return

        if data == "admin_logs":
            if user_id != ADMIN_ID:
                return
            try:
                if os.path.exists("bot.log"):
                    with open("bot.log", "r", encoding="utf-8") as f:
                        lines = f.readlines()[-40:]
                    bot.send_message(user_id, "📄 Recent Logs:\n" + "".join(lines))
                else:
                    bot.send_message(user_id, "Log file not found.")
            except Exception as e:
                logger.exception(f"admin_logs error: {e}")
            bot.answer_callback_query(call.id)
            return

        # ---------- COMPARE / PAYMENT METHODS / RATE ----------
        if data == "compare_plans":
            plans = DatabaseManager.execute_query("SELECT name, price, days, features FROM plans ORDER BY price", fetchall=True) or []
            text = "📊 **PLAN COMPARISON**\n\n"
            for plan in plans:
                text += f"\n✨ **{plan[0]}**\n💰 ₹{plan[1]} | {plan[2]} days\n{plan[3]}\n────────────────────\n"
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("📋 View Plans", callback_data="view_plans"))
            kb.add(InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))
            bot.edit_message_text(text, chat_id, msg_id, parse_mode='Markdown', reply_markup=kb)
            return

        if data == "payment_methods":
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("📋 View Plans", callback_data="view_plans"))
            kb.add(InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))
            bot.edit_message_text("💳 **Payment Methods**\nSelect a plan first then a method.", chat_id, msg_id, parse_mode='Markdown', reply_markup=kb)
            return

        if data.startswith("rate_"):
            try:
                rating = int(data.split("_")[1])
                bot.answer_callback_query(call.id, f"Thanks for rating {rating}⭐")
            except Exception:
                bot.answer_callback_query(call.id, "Thanks for your feedback!")
            return

        # default fallback - stop spinner if nothing matched
        bot.answer_callback_query(call.id)
        return

    except Exception as e:
        logger.exception(f"Callback error: {e}")
        try:
            bot.answer_callback_query(call.id, "❌ Error occurred!")
        except Exception:
            pass
        return

# ==================== ADMIN COMMANDS ====================

@bot.message_handler(commands=['approve'])
def approve_payment(message):
    if message.from_user.id != ADMIN_ID:
        return

    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "Usage: /approve <payment_id>")
            return

        payment_id = int(parts[1])

        try:
            payment = DatabaseManager.execute_query('''
            SELECT p.user_id, p.plan_id, p.amount, pl.name, pl.days 
            FROM payments p 
            JOIN plans pl ON p.plan_id = pl.id 
            WHERE p.id = ? AND p.status = 'pending'
            ''', (payment_id,), fetchone=True)

            if not payment:
                bot.reply_to(message, "❌ Payment not found or already processed")
                return

            user_id, plan_id, amount, plan_name, days = payment

            # Update payment status
            DatabaseManager.execute_query(
                "UPDATE payments SET status = 'completed' WHERE id = ?",
                (payment_id,),
                commit=True
            )

            # Add subscription to user
            ok = add_subscription(user_id, plan_id, days)
            if not ok:
                bot.reply_to(message, "❌ Failed to update subscription in DB")
                return

        except Exception as e:
            logger.error(f"Database error in /approve: {e}")
            bot.reply_to(message, f"❌ Database error: {str(e)}")
            return

        # Notify user
        try:
            bot.send_message(
                user_id,
                f"""
✅ **PAYMENT APPROVED!**

Your payment of ₹{amount} has been verified.

**Plan:** {plan_name}
**Duration:** {days} days

🔗 **Channel Link:**
{CHANNEL_INVITE_LINK}

You now have access to the private channel!
                """,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to notify user: {e}")

        bot.reply_to(message, f"✅ Payment {payment_id} approved. User notified.")

    except Exception as e:
        logger.exception(f"/approve command failed: {e}")
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['addsub'])
def add_subscription_command(message):
    if message.from_user.id != ADMIN_ID:
        return

    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message, "Usage: /addsub <user_id> <days>")
            return

        target_user_id = int(parts[1])
        days = int(parts[2])

        ok = add_subscription(target_user_id, 2, days)
        if not ok:
            bot.reply_to(message, "❌ Failed to add subscription")
            return

        bot.reply_to(message, f"✅ Subscription added for user {target_user_id} for {days} days")

        # Notify user
        try:
            bot.send_message(
                target_user_id,
                f"""
🎉 **SUBSCRIPTION ACTIVATED**

Admin has activated your subscription for {days} days!

🔗 **Join Channel:**
{CHANNEL_INVITE_LINK}
                """,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to notify user: {e}")

    except Exception as e:
        logger.exception(f"/addsub failed: {e}")
        bot.reply_to(message, f"❌ Error: {str(e)}")

# ==================== BACKGROUND TASKS ====================

def check_expired_subscriptions():
    """Check for expired subscriptions periodically"""
    while True:
        try:
            try:
                expired_users = DatabaseManager.execute_query(
                    "SELECT user_id FROM users WHERE expiry_date <= datetime('now') AND status = 'active'",
                    fetchall=True
                )
            except Exception as e:
                logger.error(f"Error fetching expired users: {e}")
                expired_users = []

            for user in expired_users:
                try:
                    DatabaseManager.execute_query(
                        "UPDATE users SET status = 'expired' WHERE user_id = ?",
                        (user[0],),
                        commit=True
                    )
                    try:
                        bot.send_message(
                            user[0],
                            "⚠️ **SUBSCRIPTION EXPIRED**\n\nYour subscription has expired. Renew now to continue access!",
                            reply_markup=main_menu(user[0])
                        )
                    except Exception as e:
                        logger.error(f"Failed to notify user {user[0]}: {e}")
                except Exception as e:
                    logger.error(f"Failed to expire user {user[0]}: {e}")

            time.sleep(300)  # Check every 5 minutes

        except Exception as e:
            logger.exception(f"Background task error: {e}")
            time.sleep(60)

# ==================== START BOT ====================

if __name__ == "__main__":
    # Start background task
    import threading
    bg_thread = threading.Thread(target=check_expired_subscriptions, daemon=True)
    bg_thread.start()

    logger.info("=" * 50)
    logger.info("🤖 STREAMX SUBSCRIPTION BOT STARTED")
    logger.info("=" * 50)
    logger.info("✅ All features are now ACTIVE")
    logger.info("✅ Payment system ready")
    logger.info("✅ Subscription management ready")
    logger.info("=" * 50)

    try:
        bot_info = bot.get_me()
        print(f"✅ Bot connected: @{bot_info.username}")
        print(f"✅ Bot name: {bot_info.first_name}")
        print("✅ Bot is now running...")

        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        logger.exception(f"Bot connection error: {e}")
        print(f"❌ Bot failed to connect: {e}")
        print("Check your bot token in .env file")
