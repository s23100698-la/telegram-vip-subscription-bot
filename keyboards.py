"""
All inline keyboard templates for the subscription bot
"""

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import Config

class Keyboards:
    
    @staticmethod
    def main_menu(user_id=None):
        """Main menu keyboard"""
        keyboard = InlineKeyboardMarkup(row_width=getattr(Config, "BUTTONS_PER_ROW", 2))
        
        buttons = [
            ("📋 View Plans", "view_plans"),
            ("🔍 My Subscription", "my_subscription"),
            ("💳 Payment Methods", "payment_methods"),
            ("📞 Contact Support", "contact_support"),
            ("❓ How to Use", "how_to_use"),
            ("🎁 Refer & Earn", "refer_earn"),
            ("⭐ Rate Us", "rate_us"),
            ("🔄 Check Access", "check_access")
        ]
        
        # Add buttons in rows
        for i in range(0, len(buttons), 2):
            row_buttons = []
            for j in range(2):
                if i + j < len(buttons):
                    text, callback = buttons[i + j]
                    row_buttons.append(InlineKeyboardButton(text, callback_data=callback))
            keyboard.add(*row_buttons)
        
        # Add admin button if user is admin
        if user_id and Config.is_admin(user_id):
            keyboard.add(InlineKeyboardButton("👑 Admin Panel", callback_data="admin_panel"))
        
        return keyboard
    

    # ================== PLANS & PAYMENTS ==================

    @staticmethod
    def plans_list(plans_data):
        """Keyboard showing all subscription plans"""
        keyboard = InlineKeyboardMarkup(row_width=1)
        
        for plan in plans_data:
            plan_id = plan['id']
            name = plan['name']
            price = plan['price']
            duration = plan['duration_days']
            
            button_text = f"{name} - ₹{price} ({duration} days)"
            keyboard.add(InlineKeyboardButton(button_text, callback_data=f"plan_{plan_id}"))
        
        keyboard.row(
            InlineKeyboardButton("🔙 Back", callback_data="main_menu"),
            InlineKeyboardButton("ℹ️ Compare", callback_data="compare_plans")
        )
        
        return keyboard
    

    @staticmethod
    def plan_details(plan_id):
        """After selecting a plan"""
        keyboard = InlineKeyboardMarkup(row_width=2)
        
        keyboard.row(
            InlineKeyboardButton("💳 Buy Now", callback_data=f"buy_{plan_id}"),
            InlineKeyboardButton("ℹ️ Details", callback_data=f"details_{plan_id}")
        )
        
        keyboard.row(
            InlineKeyboardButton("📋 All Plans", callback_data="view_plans"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
        )
        
        return keyboard
    

    @staticmethod
    def payment_methods(plan_id=None):
        """Payment methods selection"""
        keyboard = InlineKeyboardMarkup(row_width=2)
        
        methods = [
            ("📱 UPI", "pay_upi"),
            ("🏦 Bank", "pay_bank"),
            ("📲 PhonePe", "pay_phonepe"),
            ("💳 Card", "pay_card"),
            ("💰 Crypto", "pay_crypto"),
            ("📞 Manual", "pay_manual")
        ]
        
        for text, method in methods:
            callback = f"{method}_{plan_id}" if plan_id else method
            keyboard.add(InlineKeyboardButton(text, callback_data=callback))
        
        # Navigation
        if plan_id:
            keyboard.add(InlineKeyboardButton("🔙 Back", callback_data=f"plan_{plan_id}"))
        keyboard.add(InlineKeyboardButton("🏠 Menu", callback_data="main_menu"))
        
        return keyboard
    

    @staticmethod
    def payment_confirmation(plan_id, payment_method):
        """Confirm payment made"""
        keyboard = InlineKeyboardMarkup(row_width=2)
        
        keyboard.row(
            InlineKeyboardButton("✅ I've Paid", callback_data=f"confirm_{payment_method}_{plan_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"plan_{plan_id}")
        )
        
        keyboard.add(InlineKeyboardButton("📞 Need Help?", callback_data="contact_support"))
        keyboard.add(InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))
        
        return keyboard
    

    # ================== SUBSCRIPTION STATUS ==================

    @staticmethod
    def subscription_status(has_access):
        keyboard = InlineKeyboardMarkup(row_width=2)

        if has_access:
            keyboard.row(
                InlineKeyboardButton("🔗 Join Channel", callback_data="join_channel"),
                InlineKeyboardButton("🔄 Renew", callback_data="view_plans")
            )
            keyboard.add(InlineKeyboardButton("📤 Get Invite", callback_data="get_invite"))
        else:
            keyboard.row(
                InlineKeyboardButton("💳 Subscribe", callback_data="view_plans"),
                InlineKeyboardButton("📋 View Plans", callback_data="view_plans")
            )

        keyboard.add(InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))
        return keyboard
    

    # ================== ADMIN PANEL ==================

    @staticmethod
    def admin_panel():
        """Admin control panel"""
        keyboard = InlineKeyboardMarkup(row_width=2)
        
        admin_buttons = [
            ("👥 Users", "admin_users"),
            ("📊 Stats", "admin_stats"),
            ("💳 Payments", "admin_payments"),
            ("📢 Broadcast", "admin_broadcast"),
            ("➕ Add Sub", "admin_add"),
            ("➖ Remove Sub", "admin_remove"),
            ("⚙️ Plans", "admin_plans"),

            # ⭐ NEW BUTTONS ⭐
            ("📺 Manage Channels", "admin_list_channels"),  # 👈 IMPORTANT
        ]
        
        for i in range(0, len(admin_buttons), 2):
            row = []
            for j in range(2):
                if i + j < len(admin_buttons):
                    text, callback = admin_buttons[i + j]
                    row.append(InlineKeyboardButton(text, callback_data=callback))
            keyboard.add(*row)
        
        keyboard.add(InlineKeyboardButton("🏠 User Menu", callback_data="main_menu"))
        
        return keyboard
    

    # ================== CHANNEL MANAGEMENT ==================

    @staticmethod
    def channel_list_keyboard(channels):
        """
        Used in handlers for showing a list of channels.
        Each button deletes its channel.
        """
        keyboard = InlineKeyboardMarkup(row_width=1)

        for ch in channels:
            cid = ch[1]
            title = ch[2] or ""
            text = f"{cid} — {title}" if title else cid

            keyboard.add(
                InlineKeyboardButton(
                    f"❌ {text}",
                    callback_data=f"delchan:{cid}"
                )
            )

        # Add-channel button
        keyboard.add(InlineKeyboardButton("➕ Add Channel", callback_data="admin_add_channel"))
        keyboard.add(InlineKeyboardButton("🔙 Back", callback_data="admin_panel"))

        return keyboard
    

    # ================== MISC ==================

    @staticmethod
    def back_button(back_to="main_menu"):
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🔙 Back", callback_data=back_to))
        return keyboard

    @staticmethod
    def back_to_menu():
        return Keyboards.back_button("main_menu")


# Shortcut functions
def main_menu(user_id=None):
    return Keyboards.main_menu(user_id)

def plans_list(plans):
    return Keyboards.plans_list(plans)

def payment_methods(plan_id=None):
    return Keyboards.payment_methods(plan_id)

def admin_panel():
    return Keyboards.admin_panel()

def back_to_menu():
    return Keyboards.back_to_menu()
