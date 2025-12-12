# config.py
import os
from typing import List, Dict, Any


class Config:
    """
    Central configuration for the bot.
    Reads settings from environment variables with sensible defaults.
    """

    # ========== BOT SETTINGS ==========
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "").strip()

    # Admin IDs (CSV in env, e.g. "12345,67890")
    _admin_env = os.getenv("ADMIN_IDS", "6764548697").strip()
    # parse to ints, ignore empties and invalid entries
    try:
        ADMIN_IDS: List[int] = [int(x) for x in (_admin_env.split(",") if _admin_env else []) if x.strip()]
    except Exception:
        # fallback to single default if parsing fails
        ADMIN_IDS = [6764548697]

    # ========== CHANNEL SETTINGS ==========
    CHANNEL_USERNAME: str = os.getenv("CHANNEL_USERNAME", "@StreamxPlayer").strip()
    CHANNEL_NAME: str = CHANNEL_USERNAME  # human-friendly name
    CHANNEL_INVITE_LINK: str = os.getenv(
        "CHANNEL_INVITE_LINK",
        "https://t.me/+wK-uZ4uhG3ozYjNl"
    ).strip()

    # ========== DATABASE SETTINGS ==========
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "subscriptions.db").strip()

    # ========== PAYMENT SETTINGS ==========
    UPI_ID: str = os.getenv("UPI_ID", "yourbusiness@oksbi").strip()

    BANK_DETAILS: Dict[str, str] = {
        "account": os.getenv("BANK_ACCOUNT_NAME", "YOUR BUSINESS NAME"),
        "bank": os.getenv("BANK_NAME", "HDFC BANK"),
        "account_no": os.getenv("BANK_ACCOUNT_NUMBER", "123456789012"),
        "ifsc": os.getenv("BANK_IFSC", "HDFC0001234"),
        "branch": os.getenv("BANK_BRANCH", "MAIN BRANCH"),
    }

    PAYMENT_VERIFICATION_TIME: int = int(os.getenv("PAYMENT_VERIFICATION_TIME", "30"))  # minutes
    REFERRAL_COMMISSION: float = float(os.getenv("REFERRAL_COMMISSION", "0.10"))  # e.g. 0.10 == 10%

    # ========== PAYMENT INSTRUCTIONS (templates) ==========
    PAYMENT_INSTRUCTIONS: Dict[str, str] = {
        "upi": (
            "📱 *UPI PAYMENT INSTRUCTIONS*\n\n"
            "Pay *{amount}* to UPI ID:\n"
            "`{upi_id}`\n\n"
            "*Payment Note:* UserID {user_id}\n\n"
            "After paying:\n"
            "1️⃣ Take Screenshot  \n"
            "2️⃣ Click *“I’ve Paid”*\n\n"
            "Your payment will be verified in {verification_time} mins."
        ),
        "bank": (
            "🏦 *BANK TRANSFER DETAILS*\n\n"
            "*Account Holder:* {account}  \n"
            "*Bank:* {bank}  \n"
            "*Account No:* {account_no}  \n"
            "*IFSC:* {ifsc}  \n"
            "*Amount:* {amount}\n\n"
            "*Note:* Add UserID {user_id} in remarks.\n\n"
            "After paying:\n"
            "1️⃣ Save transaction ID  \n"
            "2️⃣ Click *“I’ve Paid”*"
        ),
        # generic fallback
        "default": (
            "📝 *{method} PAYMENT*\n\n"
            "**Amount:** {amount}\n"
            "**Note:** Use UserID {user_id} in payment reference\n\n"
            "Contact support after payment."
        )
    }

    # ========== SUPPORT SETTINGS ==========
    SUPPORT_USERNAME: str = os.getenv("SUPPORT_USERNAME", "@your_support_username").strip()
    SUPPORT_GROUP: str = os.getenv("SUPPORT_GROUP", "https://t.me/your_support_group").strip()
    FAQ_LINK: str = os.getenv("FAQ_LINK", "https://t.me/your_faq_page").strip()

    # ========== PLAN SETTINGS ==========
    DEFAULT_PLANS: List[Dict[str, Any]] = [
        {
            "name": "BASIC (1 Week)",
            "duration_days": 7,
            "price": 49,
            "description": "1-week access to private channel",
            "features": ["Channel Access", "Basic Support"],
        },
        {
            "name": "PRO (1 Month)",
            "duration_days": 30,
            "price": 199,
            "description": "Full monthly access",
            "features": ["Priority Access", "Premium Content", "Daily Uploads"],
        },
        {
            "name": "PREMIUM (3 Months)",
            "duration_days": 90,
            "price": 399,
            "description": "3-month access + VIP perks",
            "features": ["VIP Support", "4K Content", "Early Access"],
        },
    ]

    # ========== HELPERS ==========

    @staticmethod
    def is_admin(user_id: int) -> bool:
        """Return True if user_id is in ADMIN_IDS."""
        try:
            return int(user_id) in Config.ADMIN_IDS
        except Exception:
            return False

    @staticmethod
    def format_currency(amount: float) -> str:
        """Format numeric amount as currency string."""
        try:
            # integer rupee values are common; preserve decimals if present
            if float(amount).is_integer():
                return f"₹{int(amount)}"
            return f"₹{amount:.2f}"
        except Exception:
            return f"₹{amount}"

    @staticmethod
    def payment_instruction(method: str, amount: Any, user_id: Any) -> str:
        """
        Return a formatted payment instruction string for the given method.
        method: 'upi' | 'bank' | other
        """
        method_key = method.lower() if method else "default"
        tpl = Config.PAYMENT_INSTRUCTIONS.get(method_key, Config.PAYMENT_INSTRUCTIONS["default"])

        # common placeholders
        ctx = {
            "amount": Config.format_currency(amount),
            "upi_id": Config.UPI_ID,
            "user_id": user_id,
            "verification_time": Config.PAYMENT_VERIFICATION_TIME,
            **Config.BANK_DETAILS
        }

        try:
            return tpl.format(**ctx)
        except Exception:
            # fallback: return minimal instruction
            return Config.PAYMENT_INSTRUCTIONS["default"].format(method=method.upper(), amount=Config.format_currency(amount), user_id=user_id)

    @staticmethod
    def admins_list() -> List[int]:
        """Return list of admin ids."""
        return Config.ADMIN_IDS.copy()

    @staticmethod
    def get_bank_details() -> Dict[str, str]:
        return Config.BANK_DETAILS.copy()
