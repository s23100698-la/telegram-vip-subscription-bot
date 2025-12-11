"""
All inline keyboard templates for the subscription bot
"""

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import Config

class Keyboards:
    
    @staticmethod
    def main_menu(user_id=None):
        """Main menu keyboard"""
        keyboard = InlineKeyboardMarkup(row_width=Config.BUTTONS_PER_ROW)
        
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
        for i in range(0, len(buttons), Config.BUTTONS_PER_ROW):
            row_buttons = []
            for j in range(Config.BUTTONS_PER_ROW):
                if i + j < len(buttons):
                    text, callback = buttons[i + j]
                    row_buttons.append(InlineKeyboardButton(text, callback_data=callback))
            keyboard.add(*row_buttons)
        
        # Add admin button if user is admin
        if user_id and Config.is_admin(user_id):
            keyboard.add(InlineKeyboardButton("👑 Admin Panel", callback_data="admin_panel"))
        
        return keyboard
    
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
        
        # Create buttons
        row = []
        for i, (text, method) in enumerate(methods):
            callback = f"{method}_{plan_id}" if plan_id else method
            row.append(InlineKeyboardButton(text, callback_data=callback))
            
            if len(row) == 2:
                keyboard.row(*row)
                row = []
        
        if row:  # Add remaining button if odd number
            keyboard.add(*row)
        
        # Navigation buttons
        nav_buttons = []
        if plan_id:
            nav_buttons.append(InlineKeyboardButton("🔙 Back", callback_data=f"plan_{plan_id}"))
        nav_buttons.append(InlineKeyboardButton("🏠 Menu", callback_data="main_menu"))
        
        keyboard.row(*nav_buttons)
        
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
    
    @staticmethod
    def subscription_status(has_access, is_expired_soon=False):
        """Keyboard based on subscription status"""
        keyboard = InlineKeyboardMarkup(row_width=2)
        
        if has_access:
            buttons = [
                ("🔗 Join Channel", "join_channel"),
                ("🔄 Renew", "view_plans"),
                ("📅 Extend", "view_plans"),
                ("🎁 Gift", "gift_subscription")
            ]
        else:
            buttons = [
                ("💳 Subscribe", "view_plans"),
                ("📋 View Plans", "view_plans"),
                ("❓ Why Subscribe", "why_subscribe"),
                ("🎁 Free Trial", "free_trial")
            ]
        
        # Add status-specific buttons
        for i in range(0, len(buttons), 2):
            keyboard.row(
                InlineKeyboardButton(buttons[i][0], callback_data=buttons[i][1]),
                InlineKeyboardButton(buttons[i+1][0], callback_data=buttons[i+1][1])
            )
        
        if is_expired_soon:
            keyboard.add(InlineKeyboardButton("⚠️ Expiring Soon - Renew Now!", callback_data="view_plans"))
        
        keyboard.add(InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))
        
        return keyboard
    
    @staticmethod
    def admin_panel():
        """Admin control panel"""
        keyboard = InlineKeyboardMarkup(row_width=2)
        
        admin_buttons = [
            ("👥 Users", "admin_users"),
            ("✅ Active", "admin_active"),
            ("📊 Stats", "admin_stats"),
            ("📢 Broadcast", "admin_broadcast"),
            ("➕ Add Sub", "admin_add"),
            ("➖ Remove", "admin_remove"),
            ("⚙️ Plans", "admin_plans"),
            ("💳 Payments", "admin_payments"),
            ("📤 Export", "admin_export"),
            ("🔄 Refresh", "admin_refresh"),
            ("🔧 Settings", "admin_settings"),
            ("📋 Logs", "admin_logs")
        ]
        
        # Add in grid format
        for i in range(0, len(admin_buttons), 2):
            if i+1 < len(admin_buttons):
                keyboard.row(
                    InlineKeyboardButton(admin_buttons[i][0], callback_data=admin_buttons[i][1]),
                    InlineKeyboardButton(admin_buttons[i+1][0], callback_data=admin_buttons[i+1][1])
                )
            else:
                keyboard.add(InlineKeyboardButton(admin_buttons[i][0], callback_data=admin_buttons[i][1]))
        
        keyboard.add(InlineKeyboardButton("🏠 User Menu", callback_data="main_menu"))
        
        return keyboard
    
    @staticmethod
    def admin_users_action(user_id):
        """Actions for specific user in admin panel"""
        keyboard = InlineKeyboardMarkup(row_width=2)
        
        actions = [
            ("➕ Add 7 Days", f"admin_add_days_{user_id}_7"),
            ("➕ Add 30 Days", f"admin_add_days_{user_id}_30"),
            ("➕ Add 90 Days", f"admin_add_days_{user_id}_90"),
            ("➖ Remove Access", f"admin_remove_{user_id}"),
            ("📝 Message", f"admin_message_{user_id}"),
            ("📋 Info", f"admin_info_{user_id}")
        ]
        
        for i in range(0, len(actions), 2):
            keyboard.row(
                InlineKeyboardButton(actions[i][0], callback_data=actions[i][1]),
                InlineKeyboardButton(actions[i+1][0], callback_data=actions[i+1][1])
            )
        
        keyboard.add(InlineKeyboardButton("🔙 Back", callback_data="admin_users"))
        
        return keyboard
    
    @staticmethod
    def admin_payments_action(payment_id):
        """Actions for payment verification"""
        keyboard = InlineKeyboardMarkup(row_width=2)
        
        keyboard.row(
            InlineKeyboardButton("✅ Approve", callback_data=f"admin_approve_{payment_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject_{payment_id}")
        )
        
        keyboard.row(
            InlineKeyboardButton("👀 View Details", callback_data=f"admin_view_payment_{payment_id}"),
            InlineKeyboardButton("📞 Contact User", callback_data=f"admin_contact_{payment_id}")
        )
        
        keyboard.add(InlineKeyboardButton("🔙 Back", callback_data="admin_payments"))
        
        return keyboard
    
    @staticmethod
    def yes_no_cancel():
        """Simple Yes/No/Cancel keyboard"""
        keyboard = InlineKeyboardMarkup(row_width=2)
        
        keyboard.row(
            InlineKeyboardButton("✅ Yes", callback_data="yes"),
            InlineKeyboardButton("❌ No", callback_data="no")
        )
        
        keyboard.add(InlineKeyboardButton("🚫 Cancel", callback_data="cancel"))
        
        return keyboard
    
    @staticmethod
    def back_button(back_to="main_menu"):
        """Single back button"""
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🔙 Back", callback_data=back_to))
        return keyboard
    
    @staticmethod
    def back_to_menu():
        """Back to main menu"""
        return Keyboards.back_button("main_menu")
    
    @staticmethod
    def referral_actions():
        """Referral program actions"""
        keyboard = InlineKeyboardMarkup(row_width=2)
        
        keyboard.row(
            InlineKeyboardButton("📋 My Referrals", callback_data="my_referrals"),
            InlineKeyboardButton("💰 Earnings", callback_data="referral_earnings")
        )
        
        keyboard.row(
            InlineKeyboardButton("📤 Withdraw", callback_data="withdraw_earnings"),
            InlineKeyboardButton("📢 Share Link", callback_data="share_referral")
        )
        
        keyboard.add(InlineKeyboardButton("❓ How it Works", callback_data="referral_how"))
        keyboard.add(InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))
        
        return keyboard
    
    @staticmethod
    def broadcast_options():
        """Broadcast message options"""
        keyboard = InlineKeyboardMarkup(row_width=2)
        
        options = [
            ("👥 All Users", "broadcast_all"),
            ("✅ Active Only", "broadcast_active"),
            ("❌ Inactive Only", "broadcast_inactive"),
            ("📅 Scheduled", "broadcast_schedule")
        ]
        
        for i in range(0, len(options), 2):
            keyboard.row(
                InlineKeyboardButton(options[i][0], callback_data=options[i][1]),
                InlineKeyboardButton(options[i+1][0], callback_data=options[i+1][1])
            )
        
        keyboard.add(InlineKeyboardButton("🔙 Back", callback_data="admin_panel"))
        
        return keyboard
    
    @staticmethod
    def plan_management():
        """Manage subscription plans"""
        keyboard = InlineKeyboardMarkup(row_width=2)
        
        actions = [
            ("➕ Add Plan", "plan_add"),
            ("✏️ Edit Plan", "plan_edit"),
            ("🚫 Disable Plan", "plan_disable"),
            ("✅ Enable Plan", "plan_enable"),
            ("📊 Plan Stats", "plan_stats"),
            ("🔄 Reset Plans", "plan_reset")
        ]
        
        for i in range(0, len(actions), 2):
            keyboard.row(
                InlineKeyboardButton(actions[i][0], callback_data=actions[i][1]),
                InlineKeyboardButton(actions[i+1][0], callback_data=actions[i+1][1])
            )
        
        keyboard.add(InlineKeyboardButton("🔙 Back", callback_data="admin_panel"))
        
        return keyboard
    
    @staticmethod
    def support_options():
        """Support contact options"""
        keyboard = InlineKeyboardMarkup(row_width=2)
        
        keyboard.row(
            InlineKeyboardButton("💳 Payment Issue", callback_data="support_payment"),
            InlineKeyboardButton("🔐 Access Issue", callback_data="support_access")
        )
        
        keyboard.row(
            InlineKeyboardButton("📱 Technical", callback_data="support_technical"),
            InlineKeyboardButton("📋 General", callback_data="support_general")
        )
        
        keyboard.add(InlineKeyboardButton("📞 Direct Contact", url=f"https://t.me/{Config.SUPPORT_USERNAME.replace('@', '')}"))
        keyboard.add(InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))
        
        return keyboard
    
    @staticmethod
    def user_actions_menu():
        """Quick actions menu for users"""
        keyboard = InlineKeyboardMarkup(row_width=2)
        
        quick_actions = [
            ("🔍 Check Status", "my_subscription"),
            ("💳 Quick Renew", "view_plans"),
            ("🔗 Get Link", "get_invite"),
            ("📞 Quick Support", "quick_support"),
            ("⭐ Rate", "rate_us"),
            ("🔄 Refresh", "refresh_status")
        ]
        
        for i in range(0, len(quick_actions), 2):
            keyboard.row(
                InlineKeyboardButton(quick_actions[i][0], callback_data=quick_actions[i][1]),
                InlineKeyboardButton(quick_actions[i+1][0], callback_data=quick_actions[i+1][1])
            )
        
        keyboard.add(InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))
        
        return keyboard

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
