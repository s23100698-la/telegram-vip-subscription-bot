"""
Complete Subscription Bot with All Features
"""

import telebot
import sqlite3
import logging
import time
import os
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
ADMIN_ID = 6764548697  # Your Telegram ID
CHANNEL_USERNAME = "@your_private_channel"  # Your channel
CHANNEL_INVITE_LINK = "https://t.me/your_private_channel/123"

# Payment Details
UPI_ID = "your_upi_id@oksbi"  # Replace with your UPI
BANK_DETAILS = {
    "account": "YOUR_NAME",
    "bank": "YOUR_BANK",
    "account_no": "1234567890",
    "ifsc": "ABCD0123456"
}

# Initialize bot
bot = telebot.TeleBot(BOT_TOKEN)

# Initialize database
def init_db():
    conn = sqlite3.connect('subscriptions.db', check_same_thread=False)
    c = conn.cursor()
    
    # Users table
    c.execute('''
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
    ''')
    
    # Plans table
    c.execute('''
    CREATE TABLE IF NOT EXISTS plans (
        id INTEGER PRIMARY KEY,
        name TEXT,
        days INTEGER,
        price INTEGER,
        description TEXT,
        features TEXT
    )
    ''')
    
    # Payments table
    c.execute('''
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
    ''')
    
    # Insert default plans
    c.execute("SELECT COUNT(*) FROM plans")
    if c.fetchone()[0] == 0:
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
        c.executemany('INSERT INTO plans VALUES (?,?,?,?,?,?)', plans)
    
    conn.commit()
    conn.close()
    logger.info("Database initialized")

init_db()

# Database helper
def get_db():
    return sqlite3.connect('subscriptions.db', check_same_thread=False, timeout=10)

# Check if user has active subscription
def has_active_subscription(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT expiry_date FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    
    if result and result[0]:
        expiry = datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S')
        return expiry > datetime.now()
    return False

# Add subscription to user
def add_subscription(user_id, plan_id, days):
    conn = get_db()
    c = conn.cursor()
    
    # Get plan details
    c.execute("SELECT name FROM plans WHERE id = ?", (plan_id,))
    plan_name = c.fetchone()[0]
    
    # Calculate expiry
    new_expiry = datetime.now() + timedelta(days=days)
    
    # Update user
    c.execute('''
    UPDATE users 
    SET plan = ?, expiry_date = ?, status = 'active'
    WHERE user_id = ?
    ''', (plan_name, new_expiry.strftime('%Y-%m-%d %H:%M:%S'), user_id))
    
    conn.commit()
    conn.close()
    return True

# ==================== KEYBOARD FUNCTIONS ====================

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
    
    # Add buttons in grid
    for i in range(0, len(buttons), 2):
        keyboard.row(
            InlineKeyboardButton(buttons[i][0], callback_data=buttons[i][1]),
            InlineKeyboardButton(buttons[i+1][0], callback_data=buttons[i+1][1])
        )
    
    if user_id == ADMIN_ID:
        keyboard.add(InlineKeyboardButton("👑 Admin Panel", callback_data="admin_panel"))
    
    return keyboard

def plans_keyboard():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, name, price, days FROM plans ORDER BY price")
    plans = c.fetchall()
    conn.close()
    
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
    
    # Add payment methods
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
    name = message.from_user.first_name
    username = message.from_user.username or ""
    
    # Save user to database
    conn = get_db()
    c = conn.cursor()
    c.execute('''
    INSERT OR REPLACE INTO users (user_id, username, name, join_date, last_active)
    VALUES (?, ?, ?, ?, ?)
    ''', (user_id, username, name, 
          datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
          datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()
    
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

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    msg_id = call.message.message_id
    
    try:
        # Update last active
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE users SET last_active = ? WHERE user_id = ?",
                 (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user_id))
        conn.commit()
        conn.close()
        
        # Main menu
        if call.data == "main_menu":
            bot.edit_message_text(
                "📍 **MAIN MENU**\n\n*Select an option:*",
                chat_id, msg_id,
                parse_mode='Markdown',
                reply_markup=main_menu(user_id)
            )
        
        # View plans
        elif call.data == "view_plans":
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT name, price, days, description FROM plans ORDER BY price")
            plans = c.fetchall()
            conn.close()
            
            text = "📋 **AVAILABLE SUBSCRIPTION PLANS**\n\n"
            for plan in plans:
                text += f"""
✨ **{plan[0]}**
💰 Price: ₹{plan[1]}
⏰ Duration: {plan[2]} days
📝 {plan[3]}
────────────────────
"""
            
            bot.edit_message_text(
                text,
                chat_id, msg_id,
                parse_mode='Markdown',
                reply_markup=plans_keyboard()
            )
        
        # Plan selected
        elif call.data.startswith("plan_"):
            plan_id = int(call.data.split("_")[1])
            
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT name, price, days, description, features FROM plans WHERE id = ?", (plan_id,))
            plan = c.fetchone()
            conn.close()
            
            if plan:
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
                
                bot.edit_message_text(
                    text,
                    chat_id, msg_id,
                    parse_mode='Markdown',
                    reply_markup=plan_details_keyboard(plan_id)
                )
        
        # Show features
        elif call.data.startswith("features_"):
            plan_id = int(call.data.split("_")[1])
            
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT name, features FROM plans WHERE id = ?", (plan_id,))
            plan = c.fetchone()
            conn.close()
            
            if plan:
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
                
                bot.edit_message_text(
                    text,
                    chat_id, msg_id,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
        
        # Buy plan
        elif call.data.startswith("buy_"):
            plan_id = int(call.data.split("_")[1])
            
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT name, price FROM plans WHERE id = ?", (plan_id,))
            plan = c.fetchone()
            conn.close()
            
            text = f"""
💳 **PAYMENT FOR {plan[0]}**

💰 **Amount:** ₹{plan[1]}

**Select payment method:**
            """
            
            bot.edit_message_text(
                text,
                chat_id, msg_id,
                parse_mode='Markdown',
                reply_markup=payment_methods_keyboard(plan_id)
            )
        
        # UPI Payment
        elif call.data.startswith("pay_upi_"):
            plan_id = int(call.data.split("_")[2])
            
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT name, price FROM plans WHERE id = ?", (plan_id,))
            plan = c.fetchone()
            conn.close()
            
            text = f"""
📱 **UPI PAYMENT INSTRUCTIONS**

**Plan:** {plan[0]}
**Amount:** ₹{plan[1]}

**Steps to Pay:**
1. Open any UPI app (GPay/PhonePe/Paytm)
2. Send ₹{plan[1]} to UPI ID:
   `{UPI_ID}`
3. In payment note, add:
   `UserID: {user_id}`
4. Take screenshot of payment
5. Click "✅ I've Paid" below

**After payment:**
• Click "✅ I've Paid"
• Wait for verification (15-30 minutes)
• Get instant channel access

⚠️ **Important:** Payment verification is manual
            """
            
            bot.edit_message_text(
                text,
                chat_id, msg_id,
                parse_mode='Markdown',
                reply_markup=confirm_payment_keyboard(plan_id, "upi")
            )
        
        # Bank Transfer
        elif call.data.startswith("pay_bank_"):
            plan_id = int(call.data.split("_")[2])
            
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT name, price FROM plans WHERE id = ?", (plan_id,))
            plan = c.fetchone()
            conn.close()
            
            text = f"""
🏦 **BANK TRANSFER DETAILS**

**Plan:** {plan[0]}
**Amount:** ₹{plan[1]}

**Bank Details:**
📛 Account Name: {BANK_DETAILS['account']}
🏦 Bank: {BANK_DETAILS['bank']}
🔢 Account Number: {BANK_DETAILS['account_no']}
🔄 IFSC Code: {BANK_DETAILS['ifsc']}

**Instructions:**
1. Transfer ₹{plan[1]} to above account
2. Keep transaction ID/UTR number
3. Take screenshot
4. Click "✅ I've Paid" below

**Note:** Add User ID `{user_id}` in transaction remarks.
            """
            
            bot.edit_message_text(
                text,
                chat_id, msg_id,
                parse_mode='Markdown',
                reply_markup=confirm_payment_keyboard(plan_id, "bank")
            )
        
        # Confirm payment
        elif call.data.startswith("confirm_"):
            parts = call.data.split("_")
            method = parts[1]
            plan_id = int(parts[2])
            
            conn = get_db()
            c = conn.cursor()
            
            # Get plan details
            c.execute("SELECT name, price, days FROM plans WHERE id = ?", (plan_id,))
            plan = c.fetchone()
            
            # Create payment record
            c.execute('''
            INSERT INTO payments (user_id, plan_id, amount, method, status, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, plan_id, plan[1], method, 'pending',
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
            payment_id = c.lastrowid
            
            # Notify admin
            admin_msg = f"""
⚠️ **NEW PAYMENT REQUEST**

**User:** {call.from_user.first_name} (@{call.from_user.username})
**User ID:** `{user_id}`
**Plan:** {plan[0]}
**Amount:** ₹{plan[1]}
**Method:** {method}
**Payment ID:** `{payment_id}`

**To approve:**
/approve {payment_id}
"""
            
            try:
                bot.send_message(ADMIN_ID, admin_msg, parse_mode='Markdown')
            except:
                pass
            
            conn.commit()
            conn.close()
            
            text = f"""
✅ **PAYMENT REQUEST SUBMITTED**

**Payment ID:** `{payment_id}`
**Plan:** {plan[0]}
**Amount:** ₹{plan[1]}
**Method:** {method}

⏳ **Status:** Pending Verification

Our team will verify your payment within 15-30 minutes.
You'll receive a notification once approved.

📞 **Need help?** Contact support.
            """
            
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("📞 Contact Support", callback_data="contact_support"))
            keyboard.add(InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))
            
            bot.edit_message_text(
                text,
                chat_id, msg_id,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
            bot.answer_callback_query(call.id, "Payment request submitted!")
        
        # My Subscription
        elif call.data == "my_subscription":
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT plan, expiry_date FROM users WHERE user_id = ?", (user_id,))
            user = c.fetchone()
            conn.close()
            
            if user and user[1]:
                expiry = datetime.strptime(user[1], '%Y-%m-%d %H:%M:%S')
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
                text = """
❌ **NO ACTIVE SUBSCRIPTION**

You don't have an active subscription.

👇 **Click below to view plans and subscribe!**
                """
                show_channel = False
            
            keyboard = InlineKeyboardMarkup(row_width=2)
            
            if show_channel:
                keyboard.row(
                    InlineKeyboardButton("🔗 Join Channel", url=CHANNEL_INVITE_LINK),
                    InlineKeyboardButton("🔄 Renew", callback_data="view_plans")
                )
            else:
                keyboard.row(
                    InlineKeyboardButton("💳 Subscribe", callback_data="view_plans"),
                    InlineKeyboardButton("📋 View Plans", callback_data="view_plans")
                )
            
            keyboard.add(InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))
            
            bot.edit_message_text(
                text,
                chat_id, msg_id,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        
        # Join channel
        elif call.data == "join_channel":
            if has_active_subscription(user_id):
                text = f"""
🔗 **JOIN PRIVATE CHANNEL**

You have active subscription!

**Channel Link:**
{CHANNEL_INVITE_LINK}

Click button below to join:
                """
                
                keyboard = InlineKeyboardMarkup()
                keyboard.add(InlineKeyboardButton("🔗 Join Now", url=CHANNEL_INVITE_LINK))
                keyboard.add(InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))
            else:
                text = """
❌ **ACCESS DENIED**

You need an active subscription to join the channel.

Subscribe now to get access!
                """
                
                keyboard = InlineKeyboardMarkup()
                keyboard.add(InlineKeyboardButton("💳 Subscribe Now", callback_data="view_plans"))
                keyboard.add(InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))
            
            bot.edit_message_text(
                text,
                chat_id, msg_id,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        
        # Contact Support
        elif call.data == "contact_support":
            text = f"""
📞 **CONTACT SUPPORT**

For any queries regarding:
• Payment issues
• Subscription problems
• Technical support
• General inquiries

**Response Time:** 15-30 minutes

**Note:** Please have your User ID ready: `{user_id}`
            """
            
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))
            
            bot.edit_message_text(
                text,
                chat_id, msg_id,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        
        # How to Pay
        elif call.data == "how_to_pay":
            text = """
❓ **HOW TO PAY - STEP BY STEP**

1. **Click** → "📋 View Plans"
2. **Choose** your preferred plan
3. **Click** → "💳 Buy Now"
4. **Select** payment method
5. **Make payment** using instructions
6. **Click** → "✅ I've Paid"
7. **Wait** for verification (15-30 mins)
8. **Receive** channel access automatically

**Need help?** Contact support!
            """
            
            keyboard = InlineKeyboardMarkup(row_width=2)
            keyboard.row(
                InlineKeyboardButton("📋 View Plans", callback_data="view_plans"),
                InlineKeyboardButton("📞 Contact Support", callback_data="contact_support")
            )
            keyboard.add(InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))
            
            bot.edit_message_text(
                text,
                chat_id, msg_id,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        
        # Refer & Earn
        elif call.data == "refer_earn":
            referral_link = f"https://t.me/{(bot.get_me()).username}?start=ref_{user_id}"
            
            text = f"""
🎁 **REFER & EARN PROGRAM**

**Earn 10% commission** on every referral!

**Your Referral Link:**
`{referral_link}`

**How it works:**
1. Share your referral link
2. When someone subscribes using your link
3. You get 10% of their payment
4. Earnings can be withdrawn or used for your own subscription

**Current Balance:** ₹0
**Total Earnings:** ₹0
**Total Referrals:** 0
            """
            
            keyboard = InlineKeyboardMarkup(row_width=2)
            keyboard.row(
                InlineKeyboardButton("📋 Copy Link", callback_data="copy_ref_link"),
                InlineKeyboardButton("💰 Withdraw", callback_data="withdraw_earnings")
            )
            keyboard.add(InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))
            
            bot.edit_message_text(
                text,
                chat_id, msg_id,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        
        # Admin Panel
        elif call.data == "admin_panel":
            if user_id != ADMIN_ID:
                bot.answer_callback_query(call.id, "❌ Unauthorized!")
                return
            
            text = """
👑 **ADMIN PANEL**

Select an option below:
            """
            
            bot.edit_message_text(
                text,
                chat_id, msg_id,
                parse_mode='Markdown',
                reply_markup=admin_keyboard()
            )
        
        # Admin Statistics
        elif call.data == "admin_stats":
            if user_id != ADMIN_ID:
                return
            
            conn = get_db()
            c = conn.cursor()
            
            c.execute("SELECT COUNT(*) FROM users")
            total_users = c.fetchone()[0]
            
            c.execute("SELECT COUNT(*) FROM users WHERE expiry_date > datetime('now')")
            active_subs = c.fetchone()[0]
            
            c.execute("SELECT COUNT(*) FROM payments WHERE status = 'pending'")
            pending_payments = c.fetchone()[0]
            
            c.execute("SELECT SUM(amount) FROM payments WHERE status = 'completed'")
            total_revenue = c.fetchone()[0] or 0
            
            conn.close()
            
            text = f"""
📊 **ADMIN STATISTICS**

**Users:**
👥 Total Users: {total_users}
✅ Active Subscriptions: {active_subs}
❌ Inactive Users: {total_users - active_subs}

**Payments:**
💰 Total Revenue: ₹{total_revenue}
⏳ Pending Payments: {pending_payments}

**System:**
📅 Last Updated: {datetime.now().strftime('%H:%M:%S')}
🤖 Bot Status: ✅ Running
            """
            
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("🔄 Refresh", callback_data="admin_stats"))
            keyboard.add(InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel"))
            
            bot.edit_message_text(
                text,
                chat_id, msg_id,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        
        # Compare Plans
        elif call.data == "compare_plans":
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT name, price, days, features FROM plans ORDER BY price")
            plans = c.fetchall()
            conn.close()
            
            text = "📊 **PLAN COMPARISON**\n\n"
            
            for plan in plans:
                text += f"""
✨ **{plan[0]}**
💰 ₹{plan[1]} | {plan[2]} days
{plan[3]}
────────────────────
"""
            
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("📋 View Plans", callback_data="view_plans"))
            keyboard.add(InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))
            
            bot.edit_message_text(
                text,
                chat_id, msg_id,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        
        # Payment Methods Info
        elif call.data == "payment_methods":
            text = """
💳 **AVAILABLE PAYMENT METHODS**

1. **📱 UPI / QR Code** (Recommended)
   - Google Pay, PhonePe, Paytm
   - Fastest verification

2. **🏦 Bank Transfer**
   - NEFT/IMPS/RTGS
   - Manual verification (1-2 hours)

3. **📲 PhonePe**
   - Direct PhonePe payment

4. **💳 Credit/Debit Card**
   - All cards accepted

5. **💰 Crypto (USDT)**
   - TRC20 network

6. **🤝 Manual Payment**
   - Contact admin directly

*Select a plan first, then choose payment method.*
            """
            
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("📋 View Plans", callback_data="view_plans"))
            keyboard.add(InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))
            
            bot.edit_message_text(
                text,
                chat_id, msg_id,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        
        # Rate Us
        elif call.data == "rate_us":
            text = """
⭐ **RATE OUR SERVICE**

We value your feedback!

**Please rate your experience:**
            """
            
            keyboard = InlineKeyboardMarkup(row_width=5)
            keyboard.row(
                InlineKeyboardButton("1 ⭐", callback_data="rate_1"),
                InlineKeyboardButton("2 ⭐", callback_data="rate_2"),
                InlineKeyboardButton("3 ⭐", callback_data="rate_3"),
                InlineKeyboardButton("4 ⭐", callback_data="rate_4"),
                InlineKeyboardButton("5 ⭐", callback_data="rate_5")
            )
            keyboard.add(InlineKeyboardButton("🔙 Back", callback_data="main_menu"))
            
            bot.edit_message_text(
                text,
                chat_id, msg_id,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        
        # Other payment methods
        elif call.data.startswith("pay_phonepe_") or call.data.startswith("pay_card_") or call.data.startswith("pay_crypto_") or call.data.startswith("pay_manual_"):
            parts = call.data.split("_")
            method = parts[1]
            plan_id = int(parts[2])
            
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT name, price FROM plans WHERE id = ?", (plan_id,))
            plan = c.fetchone()
            conn.close()
            
            text = f"""
📝 **{method.upper()} PAYMENT**

**Plan:** {plan[0]}
**Amount:** ₹{plan[1]}

*Contact support for {method} payment instructions.*

**Support:** @your_support_bot
            """
            
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("📞 Contact Support", callback_data="contact_support"))
            keyboard.add(InlineKeyboardButton("🔙 Back", callback_data=f"buy_{plan_id}"))
            
            bot.edit_message_text(
                text,
                chat_id, msg_id,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        logger.error(f"Callback error: {e}")
        bot.answer_callback_query(call.id, "❌ Error occurred!")

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
        
        conn = get_db()
        c = conn.cursor()
        
        # Get payment details
        c.execute('''
        SELECT p.user_id, p.plan_id, p.amount, pl.name, pl.days 
        FROM payments p 
        JOIN plans pl ON p.plan_id = pl.id 
        WHERE p.id = ? AND p.status = 'pending'
        ''', (payment_id,))
        
        payment = c.fetchone()
        
        if not payment:
            bot.reply_to(message, "❌ Payment not found or already processed")
            conn.close()
            return
        
        user_id, plan_id, amount, plan_name, days = payment
        
        # Update payment status
        c.execute("UPDATE payments SET status = 'completed' WHERE id = ?", (payment_id,))
        
        # Add subscription to user
        add_subscription(user_id, plan_id, days)
        
        conn.commit()
        
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
        except:
            pass
        
        bot.reply_to(message, f"✅ Payment {payment_id} approved. User notified.")
        
        conn.close()
        
    except Exception as e:
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
        
        # Use plan ID 2 (PRO) as default for manual additions
        add_subscription(target_user_id, 2, days)
        
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
        except:
            pass
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

# ==================== BACKGROUND TASKS ====================

def check_expired_subscriptions():
    """Check for expired subscriptions"""
    while True:
        try:
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT user_id FROM users WHERE expiry_date <= datetime('now') AND status = 'active'")
            expired_users = c.fetchall()
            
            for user in expired_users:
                c.execute("UPDATE users SET status = 'expired' WHERE user_id = ?", (user[0],))
                
                try:
                    bot.send_message(
                        user[0],
                        "⚠️ **SUBSCRIPTION EXPIRED**\n\nYour subscription has expired. Renew now to continue access!",
                        reply_markup=main_menu(user[0])
                    )
                except:
                    pass
            
            conn.commit()
            conn.close()
            
            time.sleep(300)  # Check every 5 minutes
            
        except Exception as e:
            logger.error(f"Background task error: {e}")
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
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}")
