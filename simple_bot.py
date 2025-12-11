
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
        f"🎉 Welcome {name}!\n\n🤖 **STREAMX SUBSCRIPTION BOT**\n\nUse buttons below:",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if call.data == "plans":
        bot.send_message(call.message.chat.id, "📋 Plans:\n1. Weekly - ₹99\n2. Monthly - ₹299")
    elif call.data == "status":
        bot.send_message(call.message.chat.id, "✅ Check your subscription status")
    elif call.data == "buy":
        bot.send_message(call.message.chat.id, "💳 Select payment method")
    elif call.data == "support":
        bot.send_message(call.message.chat.id, "📞 Contact @StreamxSupport")

print("🤖 Simple bot started!")
print(f"Token: {BOT_TOKEN[:10]}...")
bot.infinity_polling()
