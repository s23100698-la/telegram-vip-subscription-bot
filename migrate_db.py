# migrate_db.py
import sqlite3
import shutil
import os
from datetime import datetime

DB = "subscriptions.db"

def backup_db(db_path):
    if not os.path.exists(db_path):
        print("DB not found:", db_path)
        return None
    bak_name = f"{db_path}.bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(db_path, bak_name)
    print("Backup created:", bak_name)
    return bak_name

def column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cursor.fetchall()]  # name is at index 1
    return column in cols

def table_exists(cursor, table):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",(table,))
    return cursor.fetchone() is not None

def safe_execute(cursor, sql, params=None):
    try:
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
    except Exception as e:
        print("SQL failed:", sql, "->", e)

def migrate():
    if not os.path.exists(DB):
        print("Database file does not exist:", DB)
        return

    backup_db(DB)

    conn = sqlite3.connect(DB, timeout=30)
    cursor = conn.cursor()

    # 1) Ensure users table exists (if not, create new users table compatible with advanced schema)
    if not table_exists(cursor, "users"):
        print("users table missing — creating advanced users table.")
        cursor.execute('''
        CREATE TABLE users (
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
        conn.commit()
    else:
        print("users table exists — checking columns...")
        # add missing columns to users
        needed_users_cols = {
            "subscription_end": "TEXT",
            "plan_type": "TEXT DEFAULT 'free'",
            "last_active": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "referred_by": "INTEGER",
            "referral_code": "TEXT UNIQUE",
            "total_spent": "REAL DEFAULT 0",
            "notes": "TEXT"
        }
        for col, col_def in needed_users_cols.items():
            if not column_exists(cursor, "users", col):
                print(f"Adding column users.{col}")
                safe_execute(cursor, f"ALTER TABLE users ADD COLUMN {col} {col_def}")
        conn.commit()

    # 2) Ensure plans table has duration_days (some old schema uses 'days' column)
    if not table_exists(cursor, "plans"):
        print("plans table missing — creating plans table.")
        cursor.execute('''
        CREATE TABLE plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            duration_days INTEGER,
            price REAL,
            currency TEXT DEFAULT 'INR',
            description TEXT,
            features TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        conn.commit()
    else:
        print("plans table exists — checking columns...")
        # if old column 'days' exists and 'duration_days' missing -> add and copy
        has_days = column_exists(cursor, "plans", "days")
        has_duration = column_exists(cursor, "plans", "duration_days")
        if not has_duration:
            print("Adding plans.duration_days column")
            safe_execute(cursor, "ALTER TABLE plans ADD COLUMN duration_days INTEGER")
            # Copy from days if available
            if has_days:
                print("Copying plans.days -> plans.duration_days")
                safe_execute(cursor, "UPDATE plans SET duration_days = days WHERE duration_days IS NULL")
        # ensure price column exists (some schemas had price as integer)
        if not column_exists(cursor, "plans", "price"):
            print("Adding plans.price column")
            safe_execute(cursor, "ALTER TABLE plans ADD COLUMN price REAL DEFAULT 0")
        conn.commit()

    # 3) Ensure payments table exists with advanced schema
    if not table_exists(cursor, "payments"):
        print("Creating payments table")
        cursor.execute('''
        CREATE TABLE payments (
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
        conn.commit()
    else:
        print("payments table exists")

    # 4) Ensure referrals table exists
    if not table_exists(cursor, "referrals"):
        print("Creating referrals table")
        cursor.execute('''
        CREATE TABLE referrals (
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
        conn.commit()
    else:
        print("referrals table exists")

    # 5) Ensure logs table exists
    if not table_exists(cursor, "logs"):
        print("Creating logs table")
        cursor.execute('''
        CREATE TABLE logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        conn.commit()
    else:
        print("logs table exists")

    # 6) Fix common column naming differences:
    # If users has 'expiry_date' but not 'subscription_end', copy values
    if column_exists(cursor, "users", "expiry_date") and not column_exists(cursor, "users", "subscription_end"):
        print("Copying users.expiry_date -> users.subscription_end")
        safe_execute(cursor, "ALTER TABLE users ADD COLUMN subscription_end TEXT")
        safe_execute(cursor, "UPDATE users SET subscription_end = expiry_date WHERE subscription_end IS NULL")
        conn.commit()

    # If plans has 'days' and duration_days is empty, copy already handled above.

    print("Migration complete. Please restart the bot.")
    conn.close()

if __name__ == "__main__":
    migrate()
