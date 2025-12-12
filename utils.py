"""
utils.py - Database utilities with thread-local connection pooling
FIXED VERSION - No premature connection closing
Added: sqlite3.Row row_factory + channels functions
"""
import sqlite3
import threading
import logging
from datetime import datetime, timedelta
from contextlib import contextmanager
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

DB_PATH = "subscriptions.db"  # अगर आपके प्रोजेक्ट में अलग जगह है तो बदल दें

class DatabaseUtils:
    """Database utility class with thread-local connection pooling."""
    
    # Thread-local storage for database connections
    _local = threading.local()
    
    @staticmethod
    def get_connection():
        """
        Get a thread-local database connection.
        Connections are reused within the same thread.
        """
        if not hasattr(DatabaseUtils._local, 'connection') or DatabaseUtils._local.connection is None:
            try:
                # Create new connection with appropriate settings
                conn = sqlite3.connect(
                    DB_PATH,
                    check_same_thread=False,
                    timeout=30,
                    detect_types=sqlite3.PARSE_DECLTYPES
                )

                # allow row access by column name (so handlers can use row['name'])
                conn.row_factory = sqlite3.Row
                
                # Enable WAL mode for better concurrency
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA busy_timeout=5000")
                
                DatabaseUtils._local.connection = conn
                logger.debug(f"Created new database connection for thread {threading.current_thread().name}")
                
            except Exception as e:
                logger.error(f"Failed to create database connection: {e}")
                raise
        
        return DatabaseUtils._local.connection
    
    @staticmethod
    def close_connection():
        """Close the thread-local connection."""
        if hasattr(DatabaseUtils._local, 'connection') and DatabaseUtils._local.connection is not None:
            try:
                DatabaseUtils._local.connection.close()
                DatabaseUtils._local.connection = None
                logger.debug(f"Closed database connection for thread {threading.current_thread().name}")
            except Exception as e:
                logger.error(f"Failed to close database connection: {e}")
    
    @staticmethod
    @contextmanager
    def get_cursor():
        """
        Context manager for database operations.
        Usage:
        with DatabaseUtils.get_cursor() as cursor:
            cursor.execute("SELECT ...")
        """
        conn = DatabaseUtils.get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            # DO NOT close connection here - it's managed by thread-local
    
    @staticmethod
    def init_database():
        """Initialize database with correct schema (users, plans, payments, channels)."""
        with DatabaseUtils.get_cursor() as cursor:
            # Users table (matching bot.py schema)
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                name TEXT,
                join_date TEXT,
                expiry_date TEXT,
                plan TEXT DEFAULT 'free',
                status TEXT DEFAULT 'active',
                last_active TEXT,
                plan_type TEXT,
                subscription_end TEXT
            )
            ''')
            
            # Plans table (matching bot.py schema)
            # Note: include columns used by handlers: id, name, price, duration_days, description, is_active
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS plans (
                id INTEGER PRIMARY KEY,
                name TEXT,
                duration_days INTEGER,
                price INTEGER,
                description TEXT,
                features TEXT,
                is_active INTEGER DEFAULT 1,
                currency TEXT DEFAULT 'INR'
            )
            ''')
            
            # Payments table (matching bot.py schema)
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                plan_id INTEGER,
                amount INTEGER,
                currency TEXT,
                payment_method TEXT,
                status TEXT DEFAULT 'pending',
                timestamp TEXT,
                transaction_id TEXT
            )
            ''')
            
            # Channels table (new)
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT UNIQUE NOT NULL,   -- stores @username or numeric id as text
                title TEXT,
                added_by INTEGER,
                added_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Referrals table (used by handlers)
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referee_id INTEGER,
                commission INTEGER DEFAULT 0,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Insert default plans if not present
            cursor.execute("SELECT COUNT(*) FROM plans")
            if cursor.fetchone()[0] == 0:
                plans = [
                    (1, '⭐ BASIC - 1 Week', 7, 49,
                     'Weekly access to private channel',
                     '✅ Channel Access\n✅ Basic Support\n✅ Weekly Updates', 1, 'INR'),
                    
                    (2, '🚀 PRO - 1 Month', 30, 199,
                     'Monthly access with priority support',
                     '✅ Channel Access\n✅ Priority Support\n✅ Daily Updates\n✅ HD Content', 1, 'INR'),
                    
                    (3, '🔥 PREMIUM - 3 Months', 90, 399,
                     '3 months access + bonus content',
                     '✅ Channel Access\n✅ Priority Support\n✅ All Updates\n✅ Bonus Content\n✅ 4K Quality', 1, 'INR'),
                    
                    (4, '👑 LIFETIME', 36500, 1999,
                     'Lifetime access + all future updates',
                     '✅ Lifetime Access\n✅ VIP Support\n✅ All Content\n✅ Future Updates\n✅ Special Badge\n✅ Early Access', 1, 'INR')
                ]
                cursor.executemany('INSERT INTO plans (id, name, duration_days, price, description, features, is_active, currency) VALUES (?,?,?,?,?,?,?,?)', plans)
        
        logger.info("Database initialized successfully")

# ==================== CHANNELS: CRUD FUNCTIONS ====================

def add_channel(channel_id: str, title: Optional[str] = None, added_by: Optional[int] = None) -> bool:
    """
    Add a channel to channels table.
    channel_id: '@username' or string of numeric id
    title: optional human-friendly title
    added_by: user id of admin who added
    Returns True if inserted, False if already exists or error.
    """
    try:
        with DatabaseUtils.get_cursor() as cursor:
            cursor.execute(
                "INSERT INTO channels (channel_id, title, added_by) VALUES (?, ?, ?)",
                (channel_id, title, added_by)
            )
        logger.info(f"Channel {channel_id} added by {added_by}")
        return True
    except sqlite3.IntegrityError:
        # already exists (unique constraint)
        logger.debug(f"Attempted to add existing channel {channel_id}")
        return False
    except Exception as e:
        logger.error(f"Error adding channel {channel_id}: {e}")
        return False

def remove_channel(channel_id: str) -> bool:
    """
    Remove channel by exact channel_id. Returns True if deleted, False if not found or error.
    """
    try:
        with DatabaseUtils.get_cursor() as cursor:
            cursor.execute("DELETE FROM channels WHERE channel_id = ?", (channel_id,))
            deleted = cursor.rowcount > 0
        if deleted:
            logger.info(f"Channel {channel_id} removed")
        else:
            logger.debug(f"Channel {channel_id} not found for deletion")
        return deleted
    except Exception as e:
        logger.error(f"Error removing channel {channel_id}: {e}")
        return False

def list_channels() -> List[Tuple[int, str, Optional[str]]]:
    """
    Return list of channels as tuples (id, channel_id, title).
    """
    try:
        with DatabaseUtils.get_cursor() as cursor:
            cursor.execute("SELECT id, channel_id, title FROM channels ORDER BY id")
            rows = cursor.fetchall()
        # convert sqlite3.Row to plain tuples for callers
        return [(r['id'], r['channel_id'], r['title']) for r in rows]
    except Exception as e:
        logger.error(f"Error listing channels: {e}")
        return []

def get_channel(channel_id: str) -> Optional[Tuple[int, str, Optional[str]]]:
    """
    Return single channel row (id, channel_id, title) or None.
    """
    try:
        with DatabaseUtils.get_cursor() as cursor:
            cursor.execute("SELECT id, channel_id, title FROM channels WHERE channel_id = ?", (channel_id,))
            row = cursor.fetchone()
        if row:
            return (row['id'], row['channel_id'], row['title'])
        return None
    except Exception as e:
        logger.error(f"Error fetching channel {channel_id}: {e}")
        return None

# ==================== EXISTING FUNCTIONS (compat) ====================

def has_active_subscription(user_id):
    """Check if user has active subscription."""
    try:
        with DatabaseUtils.get_cursor() as cursor:
            cursor.execute("SELECT expiry_date FROM users WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            
            if result and result[0]:
                expiry = datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S')
                return expiry > datetime.now()
            return False
    except Exception as e:
        logger.error(f"Error checking subscription for user {user_id}: {e}")
        return False

def add_subscription(user_id, plan_id, days):
    """Add subscription to user."""
    try:
        with DatabaseUtils.get_cursor() as cursor:
            # Get plan details
            cursor.execute("SELECT name FROM plans WHERE id = ?", (plan_id,))
            result = cursor.fetchone()
            if not result:
                logger.error(f"Plan {plan_id} not found")
                return False
            
            plan_name = result['name'] if isinstance(result, sqlite3.Row) else result[0]
            
            # Calculate expiry
            new_expiry = datetime.now() + timedelta(days=days)
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Check if user exists
            cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            if cursor.fetchone():
                # Update existing user
                cursor.execute('''
                UPDATE users 
                SET plan = ?, expiry_date = ?, status = 'active', last_active = ?
                WHERE user_id = ?
                ''', (plan_name, new_expiry.strftime('%Y-%m-%d %H:%M:%S'), current_time, user_id))
            else:
                # Insert new user
                cursor.execute('''
                INSERT INTO users (user_id, username, name, join_date, expiry_date, plan, status, last_active)
                VALUES (?, ?, ?, ?, ?, ?, 'active', ?)
                ''', (user_id, '', '', current_time, 
                      new_expiry.strftime('%Y-%m-%d %H:%M:%S'), plan_name, current_time))
            
            logger.info(f"Subscription added for user {user_id}, plan {plan_name}, {days} days")
            return True
            
    except Exception as e:
        logger.error(f"Error adding subscription for user {user_id}: {e}")
        return False

# ==================== BOT.PY COMPATIBILITY ====================

def get_db():
    """
    Compatibility function for bot.py.
    Returns a database connection (do NOT close it).
    """
    return DatabaseUtils.get_connection()

# ==================== TEST FUNCTION ====================

def test_connection():
    """Test database connection."""
    print("🧪 Testing database connection...")
    
    try:
        # Initialize database
        DatabaseUtils.init_database()
        
        # Test with context manager
        with DatabaseUtils.get_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM plans")
            count = cursor.fetchone()[0]
            print(f"✅ Found {count} plans in database")
        
        # Test channels table
        with DatabaseUtils.get_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM channels")
            ccount = cursor.fetchone()[0]
            print(f"✅ Found {ccount} channels in database")
        
        # Test has_active_subscription
        print(f"✅ has_active_subscription(123): {has_active_subscription(123)}")
        
        print("✅ All tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    test_connection()
