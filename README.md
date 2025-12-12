# Telegram Subscription Bot

A complete button-based subscription bot for private Telegram channels.

## Features

- ✅ 100% Button-based interface
- ✅ Multiple payment methods (UPI, Bank, Crypto, etc.)
- ✅ Admin control panel
- ✅ Automatic subscription management
- ✅ Referral system with commissions
- ✅ Payment verification system
- ✅ Database backups
- ✅ Broadcast messages
- ✅ Expiry reminders

## Setup Instructions

### 1. Prerequisites
- Python 3.8 or higher
- Telegram account
- Private Telegram channel

### 2. Installation

```bash
# Clone or create project directory
mkdir telegram_vip_subscription
cd telegram_vip_subscription

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your details
# telegram-vip-subscription-bot

#delete database 
Get-ChildItem "D:\MY PROJECTS\telegram-vip-subscription-bot" -Filter "subscriptions.db.backup_*"
 Copy-Item .\subscriptions.db .\subscriptions.db.pre_restore_$(Get-Date -Format "yyyyMMdd_HHmmss") -Force
 python db_manager.py

 ===== SQLITE DATA MANAGER =====
📌 Backup created: subscriptions.db.backup

आप क्या करना चाहते हैं?

1️⃣  DELETE all USERS
2️⃣  DELETE all PAYMENTS
3️⃣  DELETE all EXPIRED users
4️⃣  DELETE all DATA (reset DB)
5️⃣  EXIT

👉 Enter choice number: 

#Subscription plan price update
cd "D:\MY PROJECTS\telegram-vip-subscription-bot"
1. Copy-Item .\subscriptions.db .\subscriptions.db.bak_$(Get-Date -Format "yyyyMMdd_HHmmss")

#install tabulate
2. pip install tabulate

#Run in Powershell
3. python update_prices.py show

#single plan price change
python update_prices.py update --plan 2 --price 499

#price percentage
python update_prices.py bulk --percentage 10
python update_prices.py bulk --percentage -15

#specific prices se
python update_prices.py set --plan1 99 --plan2 249 --plan3 699 --plan4 1999

#Quick Add Plan
1. python add_plan.py

Plan ID (must be unique): 5
Plan Name: ULTRA HD - 6 Months
Duration (days): 180
Price (₹): 999
Short Description: Best value 6 month plan
Features (use \n for new line): All features + 4K + VIP Support
