"""
Utility functions for the subscription bot
"""

import sqlite3
from datetime import datetime, timedelta
import logging
import json
import os
from typing import Dict, List, Optional, Tuple
from config import Config

logger = logging.getLogger(__name__)

class DatabaseUtils:
    """Database utility functions"""
    
    @staticmethod
    def init_database():
        """Initialize database with required tables"""
        conn = sqlite3.connect(Config.DATABASE_NAME)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            subscription_end TIMESTAMP,
            plan_type TEXT DEFAULT 'free',
            status TEXT DEFAULT 'active',
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            referred_by INTEGER,
            referral_code TEXT UNIQUE,
            total_spent REAL DEFAULT 0,
            notes TEXT
        )
        ''')
        
        # Plans table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            duration_days INTEGER,
            price REAL,
            currency TEXT DEFAULT 'INR',
            description TEXT,
            features TEXT,  -- JSON string of features list
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Payments table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            plan_id INTEGER,
            amount REAL,
            currency TEXT,
            payment_method TEXT,
            transaction_id TEXT UNIQUE,
            status TEXT DEFAULT 'pending',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            verified_by INTEGER,
            verified_at TIMESTAMP,
            notes TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (plan_id) REFERENCES plans (id)
        )
        ''')
        
        # Referrals table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER,
            referred_id INTEGER UNIQUE,
            commission REAL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (referrer_id) REFERENCES users (user_id),
            FOREIGN KEY (referred_id) REFERENCES users (user_id)
        )
        ''')
        
        # Logs table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Insert default plans
        cursor.execute("SELECT COUNT(*) FROM plans")
        if cursor.fetchone()[0] == 0:
            for plan_data in Config.DEFAULT_PLANS:
                features_json = json.dumps(plan_data.get('features', []))
                cursor.execute('''
                INSERT INTO plans (name, duration_days, price, currency, description, features)
                VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    plan_data['name'],
                    plan_data['duration_days'],
                    plan_data['price'],
                    plan_data['currency'],
                    plan_data['description'],
                    features_json
                ))
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    @staticmethod
    def get_connection():
        """Get database connection"""
        conn = sqlite3.connect(Config.DATABASE_NAME)
        conn.row_factory = sqlite3.Row
        return conn
    
    @staticmethod
    def add_user(user_id: int, username: str, first_name: str, referred_by: int = None):
        """Add new user to database"""
        conn = DatabaseUtils.get_connection()
        cursor = conn.cursor()
        
        # Generate referral code
        referral_code = f"REF{user_id}{int(datetime.now().timestamp()) % 10000}"
        
        cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, username, first_name, referred_by, referral_code, join_date)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, referred_by, referral_code, datetime.now()))
        
        # If user was referred, add to referrals table
        if referred_by:
            cursor.execute('''
            INSERT OR IGNORE INTO referrals (referrer_id, referred_id, status)
            VALUES (?, ?, 'pending')
            ''', (referred_by, user_id))
        
        conn.commit()
        conn.close()
        return referral_code
    
    @staticmethod
    def get_user(user_id: int):
        """Get user by ID"""
        conn = DatabaseUtils.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        return dict(user) if user else None
    
    @staticmethod
    def update_subscription(user_id: int, plan_id: int, duration_days: int):
        """Update user subscription"""
        conn = DatabaseUtils.get_connection()
        cursor = conn.cursor()
        
        # Get plan details
        cursor.execute("SELECT name, price FROM plans WHERE id = ?", (plan_id,))
        plan = cursor.fetchone()
        
        if not plan:
            conn.close()
            return False
        
        # Calculate new expiry
        cursor.execute("SELECT subscription_end FROM users WHERE user_id = ?", (user_id,))
        current = cursor.fetchone()
        
        if current and current['subscription_end']:
            current_end = datetime.strptime(current['subscription_end'], '%Y-%m-%d %H:%M:%S')
            if current_end > datetime.now():
                # Extend from current expiry
                new_end = current_end + timedelta(days=duration_days)
            else:
                # Start from now
                new_end = datetime.now() + timedelta(days=duration_days)
        else:
            # First subscription
            new_end = datetime.now() + timedelta(days=duration_days)
        
        # Update user
        cursor.execute('''
        UPDATE users 
        SET subscription_end = ?, plan_type = ?, status = 'active', total_spent = total_spent + ?
        WHERE user_id = ?
        ''', (new_end, plan['name'], plan['price'], user_id))
        
        # Log the subscription
        cursor.execute('''
        INSERT INTO logs (user_id, action, details)
        VALUES (?, ?, ?)
        ''', (user_id, 'subscription_update', 
              json.dumps({'plan_id': plan_id, 'duration': duration_days, 'new_end': new_end.isoformat()})))
        
        conn.commit()
        conn.close()
        return True
    
    @staticmethod
    def check_subscription_status(user_id: int):
        """Check if user has active subscription"""
        conn = DatabaseUtils.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT subscription_end, status 
        FROM users 
        WHERE user_id = ?
        ''', (user_id,))
        
        user = cursor.fetchone()
        conn.close()
        
        if not user or user['status'] != 'active':
            return False
        
        if not user['subscription_end']:
            return False
        
        expiry_date = datetime.strptime(user['subscription_end'], '%Y-%m-%d %H:%M:%S')
        return expiry_date > datetime.now()
    
    @staticmethod
    def get_active_users_count():
        """Get count of active subscribers"""
        conn = DatabaseUtils.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT COUNT(*) as count 
        FROM users 
        WHERE subscription_end > datetime('now') AND status = 'active'
        ''')
        
        result = cursor.fetchone()
        conn.close()
        return result['count'] if result else 0
    
    @staticmethod
    def get_pending_payments():
        """Get pending payments for admin review"""
        conn = DatabaseUtils.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT p.*, u.username, u.first_name, pl.name as plan_name
        FROM payments p
        LEFT JOIN users u ON p.user_id = u.user_id
        LEFT JOIN plans pl ON p.plan_id = pl.id
        WHERE p.status = 'pending'
        ORDER BY p.timestamp DESC
        LIMIT 50
        ''')
        
        payments = cursor.fetchall()
        conn.close()
        return [dict(p) for p in payments]
    
    @staticmethod
    def verify_payment(payment_id: int, admin_id: int, approve: bool = True):
        """Verify a payment"""
        conn = DatabaseUtils.get_connection()
        cursor = conn.cursor()
        
        # Get payment details
        cursor.execute('''
        SELECT p.*, pl.duration_days
        FROM payments p
        LEFT JOIN plans pl ON p.plan_id = pl.id
        WHERE p.id = ?
        ''', (payment_id,))
        
        payment = cursor.fetchone()
        
        if not payment:
            conn.close()
            return False, "Payment not found"
        
        if payment['status'] != 'pending':
            conn.close()
            return False, f"Payment already {payment['status']}"
        
        if approve:
            # Update payment status
            cursor.execute('''
            UPDATE payments 
            SET status = 'completed', verified_by = ?, verified_at = ?
            WHERE id = ?
            ''', (admin_id, datetime.now(), payment_id))
            
            # Update user subscription
            DatabaseUtils.update_subscription(
                payment['user_id'], 
                payment['plan_id'], 
                payment['duration_days']
            )
            
            # Handle referral commission
            cursor.execute('''
            SELECT referred_by FROM users WHERE user_id = ?
            ''', (payment['user_id'],))
            
            referred_by = cursor.fetchone()
            if referred_by and referred_by['referred_by']:
                commission = payment['amount'] * Config.REFERRAL_COMMISSION
                cursor.execute('''
                UPDATE referrals 
                SET commission = ?, status = 'completed', completed_at = ?
                WHERE referred_id = ?
                ''', (commission, datetime.now(), payment['user_id']))
            
            status_msg = "approved"
        else:
            # Reject payment
            cursor.execute('''
            UPDATE payments 
            SET status = 'rejected', verified_by = ?, verified_at = ?, notes = 'Rejected by admin'
            WHERE id = ?
            ''', (admin_id, datetime.now(), payment_id))
            status_msg = "rejected"
        
        # Log the action
        cursor.execute('''
        INSERT INTO logs (user_id, action, details)
        VALUES (?, ?, ?)
        ''', (admin_id, 'payment_verification', 
              json.dumps({'payment_id': payment_id, 'action': status_msg})))
        
        conn.commit()
        conn.close()
        return True, f"Payment {status_msg} successfully"

class PaymentUtils:
    """Payment related utilities"""
    
    @staticmethod
    def generate_payment_id(user_id: int, plan_id: int):
        """Generate unique payment ID"""
        timestamp = int(datetime.now().timestamp())
        return f"PAY{user_id:06d}{plan_id:03d}{timestamp % 1000000:06d}"
    
    @staticmethod
    def format_amount(amount: float):
        """Format amount with currency"""
        return Config.format_currency(amount)
    
    @staticmethod
    def get_payment_methods():
        """Get available payment methods"""
        return Config.PAYMENT_METHODS
    
    @staticmethod
    def get_payment_instructions(method: str, amount: float, user_id: int):
        """Get payment instructions for specific method"""
        if method == "upi":
            return Config.PAYMENT_INSTRUCTIONS["upi"].format(
                amount=amount,
                upi_id=Config.UPI_ID,
                user_id=user_id
            )
        elif method == "bank":
            return Config.PAYMENT_INSTRUCTIONS["bank"].format(
                amount=amount,
                user_id=user_id,
                **Config.BANK_DETAILS
            )
        else:
            return f"Contact support for {method} payment instructions."

class SubscriptionUtils:
    """Subscription related utilities"""
    
    @staticmethod
    def get_days_remaining(user_id: int):
        """Get days remaining in subscription"""
        user = DatabaseUtils.get_user(user_id)
        if not user or not user['subscription_end']:
            return 0
        
        expiry_date = datetime.strptime(user['subscription_end'], '%Y-%m-%d %H:%M:%S')
        days_left = (expiry_date - datetime.now()).days
        return max(0, days_left)
    
    @staticmethod
    def get_expiring_soon_users(days_threshold: int = 3):
        """Get users whose subscription expires soon"""
        conn = DatabaseUtils.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT user_id, first_name, username, subscription_end
        FROM users 
        WHERE subscription_end > datetime('now') 
        AND subscription_end <= datetime('now', ?)
        AND status = 'active'
        ''', (f'+{days_threshold} days',))
        
        users = cursor.fetchall()
        conn.close()
        return [dict(u) for u in users]
    
    @staticmethod
    def send_expiry_reminders():
        """Send reminders to users with expiring subscriptions"""
        users = SubscriptionUtils.get_expiring_soon_users(Config.REMINDER_DAYS_BEFORE_EXPIRE[0])
        
        from bot import bot  # Import here to avoid circular import
        
        for user in users:
            try:
                days_left = SubscriptionUtils.get_days_remaining(user['user_id'])
                bot.send_message(
                    user['user_id'],
                    f"⚠️ *SUBSCRIPTION REMINDER*\n\n"
                    f"Your subscription expires in {days_left} days.\n"
                    f"Renew now to avoid interruption in service.\n\n"
                    f"*Expiry Date:* {user['subscription_end'][:10]}",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to send reminder to {user['user_id']}: {e}")

class AdminUtils:
    """Admin utility functions"""
    
    @staticmethod
    def get_system_stats():
        """Get comprehensive system statistics"""
        conn = DatabaseUtils.get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # User stats
        cursor.execute("SELECT COUNT(*) as total FROM users")
        stats['total_users'] = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as active FROM users WHERE subscription_end > datetime('now')")
        stats['active_users'] = cursor.fetchone()['active']
        
        cursor.execute("SELECT COUNT(*) as today FROM users WHERE DATE(join_date) = DATE('now')")
        stats['new_today'] = cursor.fetchone()['today']
        
        # Payment stats
        cursor.execute("SELECT SUM(amount) as total FROM payments WHERE status = 'completed'")
        stats['total_revenue'] = cursor.fetchone()['total'] or 0
        
        cursor.execute("SELECT SUM(amount) as today FROM payments WHERE status = 'completed' AND DATE(timestamp) = DATE('now')")
        stats['today_revenue'] = cursor.fetchone()['today'] or 0
        
        cursor.execute("SELECT COUNT(*) as pending FROM payments WHERE status = 'pending'")
        stats['pending_payments'] = cursor.fetchone()['pending']
        
        # Plan stats
        cursor.execute("SELECT COUNT(*) as total FROM plans WHERE is_active = 1")
        stats['active_plans'] = cursor.fetchone()['total']
        
        conn.close()
        return stats
    
    @staticmethod
    def export_data(data_type: str = 'users'):
        """Export data as CSV"""
        conn = DatabaseUtils.get_connection()
        cursor = conn.cursor()
        
        if data_type == 'users':
            cursor.execute('''
            SELECT user_id, username, first_name, plan_type, subscription_end, 
                   status, total_spent, last_active
            FROM users
            ORDER BY join_date DESC
            ''')
            filename = f"users_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            headers = ['User ID', 'Username', 'First Name', 'Plan', 'Subscription End', 
                      'Status', 'Total Spent', 'Last Active']
        
        elif data_type == 'payments':
            cursor.execute('''
            SELECT p.id, p.user_id, u.username, p.amount, p.payment_method, 
                   p.status, p.timestamp, p.verified_by
            FROM payments p
            LEFT JOIN users u ON p.user_id = u.user_id
            ORDER BY p.timestamp DESC
            ''')
            filename = f"payments_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            headers = ['Payment ID', 'User ID', 'Username', 'Amount', 'Method', 
                      'Status', 'Timestamp', 'Verified By']
        
        else:
            conn.close()
            return None, "Invalid data type"
        
        data = cursor.fetchall()
        conn.close()
        
        # Create CSV content
        csv_lines = [','.join(headers)]
        for row in data:
            csv_lines.append(','.join([str(r) for r in row]))
        
        csv_content = '\n'.join(csv_lines)
        
        # Save to file
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(csv_content)
        
        return filename, csv_content
    
    @staticmethod
    def broadcast_message(message: str, user_ids: List[int] = None):
        """Broadcast message to users"""
        from bot import bot
        
        if not user_ids:
            # Get all active users
            conn = DatabaseUtils.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM users WHERE status = 'active'")
            user_ids = [row['user_id'] for row in cursor.fetchall()]
            conn.close()
        
        success = 0
        failed = 0
        
        for user_id in user_ids:
            try:
                bot.send_message(user_id, message, parse_mode='Markdown')
                success += 1
            except Exception as e:
                logger.error(f"Failed to send to {user_id}: {e}")
                failed += 1
        
        return success, failed

class BackupUtils:
    """Database backup utilities"""
    
    @staticmethod
    def create_backup():
        """Create database backup"""
        backup_file = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        
        try:
            # Simple copy for SQLite
            import shutil
            shutil.copy2(Config.DATABASE_NAME, backup_file)
            
            # Compress backup
            import gzip
            with open(Config.DATABASE_NAME, 'rb') as f_in:
                with gzip.open(f"{backup_file}.gz", 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            os.remove(backup_file)  # Remove uncompressed backup
            return f"{backup_file}.gz"
            
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return None
    
    @staticmethod
    def cleanup_old_backups(max_backups: int = 10):
        """Remove old backup files"""
        import glob
        
        backup_files = sorted(glob.glob("backup_*.db.gz"), key=os.path.getmtime)
        
        if len(backup_files) > max_backups:
            for old_backup in backup_files[:-max_backups]:
                try:
                    os.remove(old_backup)
                    logger.info(f"Removed old backup: {old_backup}")
                except Exception as e:
                    logger.error(f"Failed to remove {old_backup}: {e}")

# Shortcut functions
def check_subscription_status(user_id: int, cursor=None):
    """Check if user has active subscription (compatible with old code)"""
    if cursor:
        # Using provided cursor
        cursor.execute('''
        SELECT subscription_end, status 
        FROM users 
        WHERE user_id = ?
        ''', (user_id,))
        
        user = cursor.fetchone()
        
        if not user or user['status'] != 'active':
            return False
        
        if not user['subscription_end']:
            return False
        
        expiry_date = datetime.strptime(user['subscription_end'], '%Y-%m-%d %H:%M:%S')
        return expiry_date > datetime.now()
    else:
        # Use DatabaseUtils
        return DatabaseUtils.check_subscription_status(user_id)

def format_time_remaining(seconds: int):
    """Format time remaining in human readable format"""
    if seconds < 60:
        return f"{seconds} seconds"
    elif seconds < 3600:
        return f"{seconds//60} minutes"
    elif seconds < 86400:
        return f"{seconds//3600} hours"
    else:
        return f"{seconds//86400} days"

def generate_referral_code(user_id: int):
    """Generate referral code for user"""
    import random
    import string
    
    chars = string.ascii_uppercase + string.digits
    random_part = ''.join(random.choice(chars) for _ in range(6))
    return f"REF{user_id}{random_part}"

def validate_email(email: str):
    """Simple email validation"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def format_user_display(user):
    """Format user for display"""
    name = user.get('first_name', 'User')
    username = f" (@{user['username']})" if user.get('username') else ""
    return f"{name}{username}"
