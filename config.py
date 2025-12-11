# config.py
import os

class Config:
    # Bot Configuration
    BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
    ADMIN_ID = 6764548697
    
    # Channel Configuration
    CHANNEL_USERNAME = "Streamx Player"
    CHANNEL_INVITE_LINK = "https://t.me/your_channel_link"
    
    # Payment Configuration
    UPI_ID = "your_upi@oksbi"  # Replace with your UPI
    BANK_DETAILS = {
        "account": "YOUR_NAME",
        "bank": "YOUR_BANK",
        "account_no": "1234567890",
        "ifsc": "ABCD0123456",
        "branch": "YOUR_CITY"
    }
    
    # Features Configuration
    ENABLE_PAYMENT = True
    ENABLE_REFERRAL = True
    ENABLE_ADMIN_PANEL = True
    
    @staticmethod
    def is_admin(user_id):
        return user_id == Config.ADMIN_ID
