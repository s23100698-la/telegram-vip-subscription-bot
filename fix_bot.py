"""
Quick fix for STREAMX Bot - Fixes database and token issues
"""
import os
import sqlite3
import sys

print("=" * 50)
print("🤖 STREAMX BOT FIX SCRIPT")
print("=" * 50)

# 1. Clean old databases
print("\n1️⃣ Cleaning old databases...")
db_files = ['subscriptions.db', 'streamx_subscriptions.db', 'bot.db']
for db_file in db_files:
    if os.path.exists(db_file):
        os.remove(db_file)
        print(f"   Removed: {db_file}")
    else:
        print(f"   Not found: {db_file}")

# 2. Create fresh database with correct schema
print("\n2️⃣ Creating fresh database...")
conn = sqlite3.connect('subscriptions.db')
c = conn.cursor()

# Users table - CORRECTED
c.execute('''
CREATE TABLE users (
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
CREATE TABLE plans (
    id INTEGER PRIMARY KEY,
    name TEXT,
    days INTEGER,
    price REAL,
    currency TEXT DEFAULT 'INR',
    description TEXT,
    features TEXT
)
''')

# Payments table
c.execute('''
CREATE TABLE payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    plan_id INTEGER,
    amount REAL,
    method TEXT,
    status TEXT DEFAULT 'pending',
    timestamp TEXT,
    transaction_id TEXT,
    verified_by INTEGER,
    verified_at TEXT
)
''')

# Insert default plans
plans = [
    (1, '⭐ BASIC - 1 Week', 7, 99.00, 'INR', 
     'Weekly access to private channel',
     '✅ Channel Access\n✅ Basic Support\n✅ Weekly Updates'),
    
    (2, '🚀 PRO - 1 Month', 30, 299.00, 'INR',
     'Monthly access with priority support',
     '✅ Channel Access\n✅ Priority Support\n✅ Daily Updates\n✅ HD Quality'),
    
    (3, '🔥 PREMIUM - 3 Months', 90, 799.00, 'INR',
     '3 months access + bonus content',
     '✅ Channel Access\n✅ Priority Support\n✅ All Updates\n✅ 4K Quality\n✅ Bonus Content'),
    
    (4, '👑 LIFETIME', 36500, 1999.00, 'INR',
     'Lifetime access + all future updates',
     '✅ Lifetime Access\n✅ VIP Support\n✅ All Content\n✅ Future Updates\n✅ Special Badge')
]

c.executemany('INSERT INTO plans VALUES (?, ?, ?, ?, ?, ?, ?)', plans)
conn.commit()
conn.close()
print("   ✅ Database created with correct schema")

# 3. Check .env file
print("\n3️⃣ Checking .env file...")
if os.path.exists('.env'):
    with open('.env', 'r') as f:
        content = f.read()
        if 'BOT_TOKEN' in content:
            print("   ✅ .env file exists with BOT_TOKEN")
        else:
            print("   ⚠️ .env exists but no BOT_TOKEN found")
else:
    print("   ❌ .env file not found!")
    print("   Creating .env template...")
    with open('.env', 'w') as f:
        f.write('BOT_TOKEN=6764548697:AAHCHP5NQpM6JcFshdCtwLUM1sz2E93dCqE\n')
    print("   ✅ Created .env template")

# 4. Create SIMPLE WORKING BOT
print("\n4️⃣ Creating simple working bot...")
simple_bot_code = '''
"""
SIMPLE WORKING STREAMX BOT - No background task errors
"""
import telebot
import sqlite3
import logging
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# HARDCODED TOKEN - Replace with yours
BOT_TOKEN = "6764548697:AAHCHP5NQpM6JcFshdCtwLUM1sz2E93dCqE"

# Initialize bot
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    name = message.from_user.first_name
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📋 View Plans", callback_data="plans"),
        InlineKeyboardButton("🔍 My Status", callback_data="status"),
        InlineKeyboardButton("💳 Buy Now", callback_data="buy"),
        InlineKeyboardButton("📞 Support", callback_data="support")
    )
    
    bot.send_message(
        user_id,
        f"🎉 Welcome {name}!\\n\\n🤖 **STREAMX SUBSCRIPTION BOT**\\n\\nUse buttons below:",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if call.data == "plans":
        bot.send_message(call.message.chat.id, "📋 Plans:\\n1. Weekly - ₹99\\n2. Monthly - ₹299")
    elif call.data == "status":
        bot.send_message(call.message.chat.id, "✅ Check your subscription status")
    elif call.data == "buy":
        bot.send_message(call.message.chat.id, "💳 Select payment method")
    elif call.data == "support":
        bot.send_message(call.message.chat.id, "📞 Contact @StreamxSupport")

print("🤖 Simple bot started!")
print(f"Token: {BOT_TOKEN[:10]}...")
bot.infinity_polling()
'''

with open('simple_bot.py', 'w') as f:
    f.write(simple_bot_code)
print("   ✅ Created simple_bot.py")

print("\n" + "=" * 50)
print("✅ FIX COMPLETE!")
print("=" * 50)
print("\n📋 NEXT STEPS:")
print("1. Test your token:")
print("   python -c \"import telebot; bot = telebot.TeleBot('YOUR_TOKEN'); print(bot.get_me().username)\"")
print()
print("2. Run the simple bot:")
print("   python simple_bot.py")
print()
print("3. If simple bot works, we'll fix your main bot")
print()
print("4. Get new token if needed:")
print("   - Message @BotFather")
print("   - Send /mybots")
print("   - Select your bot")
print("   - Select API Token")
print("   - Generate new token")
