"""
Callback query handlers for the subscription bot
"""

import logging
from datetime import datetime, timedelta
from telebot.types import CallbackQuery
import sqlite3
from config import Config
from keyboards import Keyboards
import utils

logger = logging.getLogger(__name__)

class CallbackHandlers:
    def __init__(self, bot, db_connection):
        self.bot = bot
        self.db_conn = db_connection
        self.cursor = db_connection.cursor()
    
    def handle_callback(self, call: CallbackQuery):
        """Main callback handler - routes to specific handlers"""
        user_id = call.from_user.id
        chat_id = call.message.chat.id
        message_id = call.message.message_id
        callback_data = call.data
        
        try:
            # Update user activity
            self._update_user_activity(user_id)
            
            # Route callback based on data
            if callback_data == "main_menu":
                self._handle_main_menu(user_id, chat_id, message_id)
            
            elif callback_data == "view_plans":
                self._handle_view_plans(user_id, chat_id, message_id)
            
            elif callback_data.startswith("plan_"):
                plan_id = int(callback_data.split("_")[1])
                self._handle_plan_select(user_id, chat_id, message_id, plan_id)
            
            elif callback_data.startswith("buy_"):
                plan_id = int(callback_data.split("_")[1])
                self._handle_buy_plan(user_id, chat_id, message_id, plan_id)
            
            elif callback_data.startswith("pay_"):
                self._handle_payment_method(call)
            
            elif callback_data.startswith("confirm_"):
                self._handle_payment_confirmation(call)
            
            elif callback_data == "my_subscription":
                self._handle_my_subscription(user_id, chat_id, message_id)
            
            elif callback_data == "payment_methods":
                self._handle_payment_methods(user_id, chat_id, message_id)
            
            elif callback_data == "contact_support":
                self._handle_contact_support(user_id, chat_id, message_id)
            
            elif callback_data == "how_to_use":
                self._handle_how_to_use(user_id, chat_id, message_id)
            
            elif callback_data == "refer_earn":
                self._handle_refer_earn(user_id, chat_id, message_id)
            
            elif callback_data == "check_access":
                self._handle_check_access(user_id, chat_id, message_id)
            
            elif callback_data == "admin_panel":
                self._handle_admin_panel(user_id, chat_id, message_id)
            
            elif callback_data.startswith("admin_"):
                self._handle_admin_actions(call)
            
            elif callback_data == "join_channel":
                self._handle_join_channel(user_id, chat_id, message_id)
            
            elif callback_data == "get_invite":
                self._handle_get_invite(user_id, chat_id, message_id)
            
            else:
                # Unknown callback
                self.bot.answer_callback_query(call.id, "Unknown command")
            
        except Exception as e:
            logger.error(f"Error handling callback: {e}")
            self.bot.answer_callback_query(call.id, "❌ An error occurred!")
    
    # ==================== PRIVATE HANDLER METHODS ====================
    
    def _update_user_activity(self, user_id):
        """Update user's last active timestamp"""
        self.cursor.execute(
            "UPDATE users SET last_active = ? WHERE user_id = ?",
            (datetime.now(), user_id)
        )
        self.db_conn.commit()
    
    def _handle_main_menu(self, user_id, chat_id, message_id):
        """Show main menu"""
        text = "📍 *MAIN MENU*\n\n*Select an option:*"
        self.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=Keyboards.main_menu(user_id)
        )
    
    def _handle_view_plans(self, user_id, chat_id, message_id):
        """Show all subscription plans"""
        self.cursor.execute("SELECT * FROM plans WHERE is_active = 1 ORDER BY price")
        plans = self.cursor.fetchall()
        
        if not plans:
            text = "❌ No plans available at the moment."
            keyboard = Keyboards.back_to_menu()
        else:
            text = "📋 *AVAILABLE SUBSCRIPTION PLANS*\n\n"
            for plan in plans:
                text += f"✨ *{plan['name']}*\n"
                text += f"💰 Price: ₹{plan['price']}\n"
                text += f"⏰ Duration: {plan['duration_days']} days\n"
                text += f"📝 {plan['description']}\n"
                text += "────────────────────\n"
            
            keyboard = Keyboards.plans_list(plans)
        
        self.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    
    def _handle_plan_select(self, user_id, chat_id, message_id, plan_id):
        """Handle plan selection"""
        self.cursor.execute("SELECT * FROM plans WHERE id = ?", (plan_id,))
        plan = self.cursor.fetchone()
        
        if not plan:
            self.bot.answer_callback_query(call.id, "Plan not found!")
            return
        
        text = f"""
🎯 *SELECTED PLAN*

✨ *{plan['name']}*
💰 *Price:* ₹{plan['price']}
⏰ *Duration:* {plan['duration_days']} days
📝 *Description:* {plan['description']}

✅ *Benefits:*
• Access to private channel
• Premium content
• Priority support
• Regular updates

👇 *Click BUY NOW to proceed*
        """
        
        self.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=Keyboards.plan_details(plan_id)
        )
    
    def _handle_buy_plan(self, user_id, chat_id, message_id, plan_id):
        """Initiate purchase process"""
        self.cursor.execute("SELECT * FROM plans WHERE id = ?", (plan_id,))
        plan = self.cursor.fetchone()
        
        text = f"""
💳 *PAYMENT FOR {plan['name']}*

💰 *Amount:* ₹{plan['price']}
⏰ *Duration:* {plan['duration_days']} days

*Select payment method:*
        """
        
        self.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=Keyboards.payment_methods(plan_id)
        )
    
    def _handle_payment_method(self, call):
        """Handle payment method selection"""
        user_id = call.from_user.id
        chat_id = call.message.chat.id
        message_id = call.message.message_id
        
        parts = call.data.split("_")
        payment_method = parts[1]
        plan_id = int(parts[2]) if len(parts) > 2 else None
        
        if not plan_id:
            self.bot.answer_callback_query(call.id, "Please select a plan first!")
            return
        
        self.cursor.execute("SELECT * FROM plans WHERE id = ?", (plan_id,))
        plan = self.cursor.fetchone()
        
        if payment_method == "upi":
            text = Config.PAYMENT_INSTRUCTIONS["upi"].format(
                amount=plan['price'],
                upi_id=Config.UPI_ID,
                user_id=user_id
            )
        elif payment_method == "bank":
            text = Config.PAYMENT_INSTRUCTIONS["bank"].format(
                amount=plan['price'],
                user_id=user_id,
                **Config.BANK_DETAILS
            )
        else:
            text = f"""
📝 *{payment_method.upper()} PAYMENT*

**Plan:** {plan['name']}
**Amount:** ₹{plan['price']}
**Duration:** {plan['duration_days']} days

*Contact support for {payment_method} payment instructions.*
            """
        
        self.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=Keyboards.payment_confirmation(plan_id, payment_method)
        )
    
    def _handle_payment_confirmation(self, call):
        """Handle payment confirmation"""
        user_id = call.from_user.id
        chat_id = call.message.chat.id
        message_id = call.message.message_id
        
        parts = call.data.split("_")
        payment_method = parts[1]
        plan_id = int(parts[2])
        
        # Create payment record
        self.cursor.execute("SELECT * FROM plans WHERE id = ?", (plan_id,))
        plan = self.cursor.fetchone()
        
        payment_data = (
            user_id, plan_id, plan['price'], plan['currency'],
            payment_method, 'pending', datetime.now()
        )
        
        self.cursor.execute('''
        INSERT INTO payments (user_id, plan_id, amount, currency, payment_method, status, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', payment_data)
        
        payment_id = self.cursor.lastrowid
        self.db_conn.commit()
        
        # Notify admin
        self._notify_admin_payment(user_id, plan['name'], plan['price'], payment_method, payment_id)
        
        text = f"""
✅ *PAYMENT REQUEST RECEIVED*

**Payment ID:** `{payment_id}`
**Plan:** {plan['name']}
**Amount:** ₹{plan['price']}
**Method:** {payment_method}

⏳ *Status:* Pending Verification

Our team will verify your payment within {Config.PAYMENT_VERIFICATION_TIME} minutes.
You'll receive a notification once approved.
        """
        
        keyboard = Keyboards.back_to_menu()
        self.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
        self.bot.answer_callback_query(call.id, "Payment request submitted!")
    
    def _handle_my_subscription(self, user_id, chat_id, message_id):
        """Show user's subscription status"""
        self.cursor.execute(
            "SELECT plan_type, subscription_end, status FROM users WHERE user_id = ?",
            (user_id,)
        )
        user = self.cursor.fetchone()
        
        if user and user['subscription_end']:
            expiry_date = datetime.strptime(user['subscription_end'], '%Y-%m-%d %H:%M:%S')
            days_left = (expiry_date - datetime.now()).days
            
            if days_left > 0:
                status = "✅ ACTIVE"
                status_desc = f"Expires in {days_left} days"
            else:
                status = "❌ EXPIRED"
                status_desc = f"Expired {abs(days_left)} days ago"
            
            text = f"""
🔍 *MY SUBSCRIPTION*

📅 *Plan:* {user['plan_type']}
📆 *Expiry:* {expiry_date.strftime('%d %b %Y')}
⏳ *Status:* {status}
📝 *Note:* {status_desc}
            """
        else:
            text = """
❌ *NO ACTIVE SUBSCRIPTION*

You don't have an active subscription.

👇 *Click below to view plans and subscribe!*
            """
        
        has_access = user and user['subscription_end'] and days_left > 0
        keyboard = Keyboards.subscription_status(has_access)
        
        self.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    
    def _handle_payment_methods(self, user_id, chat_id, message_id):
        """Show payment methods info"""
        text = """
💳 *AVAILABLE PAYMENT METHODS*

1. *📱 UPI / QR Code* (Recommended)
   - Google Pay, PhonePe, Paytm
   - Instant payment
   - Automatic verification

2. *🏦 Bank Transfer*
   - NEFT/IMPS/RTGS
   - Manual verification (1-2 hours)
   - All Indian banks

3. *📲 PhonePe*
   - Direct PhonePe payment
   - Instant

4. *💳 Credit/Debit Card*
   - All cards accepted
   - Secure payment gateway

5. *💰 Crypto (USDT)*
   - TRC20 network
   - Binance/Other exchanges

*Select a plan first, then choose payment method.*
        """
        
        keyboard = Keyboards.back_to_menu()
        self.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    
    def _handle_contact_support(self, user_id, chat_id, message_id):
        """Show support contact info"""
        text = f"""
📞 *CONTACT SUPPORT*

For any queries regarding:
• Payment issues
• Subscription problems  
• Technical support
• General inquiries

*Contact:* {Config.SUPPORT_USERNAME}
*Group:* {Config.SUPPORT_GROUP}
*FAQ:* {Config.FAQ_LINK}

*Response Time:* 15-30 minutes

*Note:* Please have your User ID ready: `{user_id}`
        """
        
        keyboard = Keyboards.support_options()
        self.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    
    def _handle_how_to_use(self, user_id, chat_id, message_id):
        """Show how to use instructions"""
        text = """
❓ *HOW TO USE THIS BOT*

1. *📋 View Plans* - See available subscription options
2. *💳 Select Plan* - Choose your preferred plan
3. *💰 Make Payment* - Use any payment method
4. *✅ Get Verified* - Wait for payment verification
5. *🔓 Access Channel* - Get instant channel access

*Need help with any step?* Contact support!
        """
        
        keyboard = Keyboards.back_to_menu()
        self.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    
    def _handle_refer_earn(self, user_id, chat_id, message_id):
        """Show referral program"""
        # Get referral stats
        self.cursor.execute(
            "SELECT COUNT(*) as referrals, SUM(commission) as earnings FROM referrals WHERE referrer_id = ?",
            (user_id,)
        )
        stats = self.cursor.fetchone() or {'referrals': 0, 'earnings': 0}
        
        referral_link = f"https://t.me/{Config.BOT_USERNAME}?start=ref_{user_id}"
        
        text = f"""
🎁 *REFER & EARN PROGRAM*

*Earn {Config.REFERRAL_COMMISSION*100}% commission* on every referral!

*Your Stats:*
👥 Total Referrals: {stats['referrals']}
💰 Total Earnings: ₹{stats['earnings'] or 0}
📤 Available to withdraw: ₹{stats['earnings'] or 0}

*Your Referral Link:*
`{referral_link}`

*How it works:*
1. Share your referral link
2. When someone subscribes using your link
3. You get {Config.REFERRAL_COMMISSION*100}% of their payment
4. Earnings can be withdrawn or used for your subscription
        """
        
        keyboard = Keyboards.referral_actions()
        self.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    
    def _handle_check_access(self, user_id, chat_id, message_id):
        """Check and grant channel access"""
        has_access = utils.check_subscription_status(user_id, self.cursor)
        
        if has_access:
            text = """
✅ *ACCESS GRANTED*

You have active subscription!

🔗 *Channel Link:*
{link}
            """.format(link=Config.CHANNEL_INVITE_LINK)
            
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("🔗 Join Channel", url=Config.CHANNEL_INVITE_LINK))
            keyboard.add(InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))
        else:
            text = """
❌ *NO ACCESS*

You don't have an active subscription.

Subscribe now to get access to premium content!
            """
            
            keyboard = Keyboards.back_to_menu()
        
        self.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    
    def _handle_admin_panel(self, user_id, chat_id, message_id):
        """Show admin panel"""
        if not Config.is_admin(user_id):
            self.bot.answer_callback_query(call.id, "⛔ Unauthorized!")
            return
        
        # Get quick stats
        self.cursor.execute("SELECT COUNT(*) FROM users")
        total_users = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT COUNT(*) FROM users WHERE subscription_end > datetime('now')")
        active_subs = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT COUNT(*) FROM payments WHERE status = 'pending'")
        pending_payments = self.cursor.fetchone()[0]
        
        text = f"""
👑 *ADMIN PANEL*

📅 *Date:* {datetime.now().strftime('%d %b %Y %H:%M:%S')}

*Quick Stats:*
👥 Total Users: {total_users}
✅ Active Subs: {active_subs}
⏳ Pending Payments: {pending_payments}

*Select an option below:*
        """
        
        self.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=Keyboards.admin_panel()
        )
    
    def _handle_admin_actions(self, call):
        """Handle admin actions"""
        user_id = call.from_user.id
        
        if not Config.is_admin(user_id):
            self.bot.answer_callback_query(call.id, "⛔ Unauthorized!")
            return
        
        # Admin actions will be implemented based on specific requirements
        self.bot.answer_callback_query(call.id, "Admin feature under development")
    
    def _handle_join_channel(self, user_id, chat_id, message_id):
        """Provide channel join link"""
        text = f"""
🔗 *JOIN PRIVATE CHANNEL*

*Channel:* {Config.CHANNEL_NAME}
*Link:* {Config.CHANNEL_INVITE_LINK}

Click the button below to join:
        """
        
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🔗 Join Now", url=Config.CHANNEL_INVITE_LINK))
        keyboard.add(InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))
        
        self.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    
    def _handle_get_invite(self, user_id, chat_id, message_id):
        """Get personal invite link"""
        has_access = utils.check_subscription_status(user_id, self.cursor)
        
        if has_access:
            # Generate or get existing invite link
            # In production, you would create a real invite link
            invite_link = Config.CHANNEL_INVITE_LINK
            
            text = f"""
🔗 *YOUR INVITE LINK*

*Link:* {invite_link}

This link is valid for you to join the private channel.
            """
        else:
            text = """
❌ *NO ACCESS*

You need an active subscription to get the invite link.

Subscribe now to get access!
            """
        
        keyboard = Keyboards.back_to_menu()
        self.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    
    def _notify_admin_payment(self, user_id, plan_name, amount, method, payment_id):
        """Notify all admins about new payment"""
        for admin_id in Config.ADMIN_IDS:
            try:
                self.bot.send_message(
                    admin_id,
                    f"⚠️ *NEW PAYMENT REQUEST*\n\n"
                    f"*User ID:* `{user_id}`\n"
                    f"*Plan:* {plan_name}\n"
                    f"*Amount:* ₹{amount}\n"
                    f"*Method:* {method}\n"
                    f"*Payment ID:* `{payment_id}`\n\n"
                    f"*Verify with:* /verify {payment_id}",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {e}")

# Factory function to create handlers
def create_handlers(bot, db_connection):
    return CallbackHandlers(bot, db_connection)
