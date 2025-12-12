import sqlite3
import shutil
from datetime import datetime

DB = "subscriptions.db"

print("===== SQLITE DATA MANAGER =====")

# --- AUTO BACKUP ---
backup = f"{DB}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
shutil.copyfile(DB, backup)
print(f"📌 Backup created: {backup}\n")

# --- CONNECT DB ---
conn = sqlite3.connect(DB)
cur = conn.cursor()

print("आप क्या करना चाहते हैं?\n")
print("1️⃣  DELETE all USERS")
print("2️⃣  DELETE all PAYMENTS")
print("3️⃣  DELETE all EXPIRED users")
print("4️⃣  DELETE all DATA (reset DB)")
print("5️⃣  EXIT\n")

choice = input("👉 Enter choice number: ")

try:
    if choice == "1":
        cur.execute("DELETE FROM users")
        print("🧹 All USERS deleted!")

    elif choice == "2":
        cur.execute("DELETE FROM payments")
        print("🧹 All PAYMENTS deleted!")

    elif choice == "3":
        cur.execute("DELETE FROM users WHERE expiry_date <= datetime('now')")
        print("🧹 All EXPIRED users deleted!")

    elif choice == "4":
        cur.execute("DELETE FROM users")
        cur.execute("DELETE FROM payments")
        cur.execute("DELETE FROM plans")
        print("🧹 Full database reset (tables cleared)!")

    elif choice == "5":
        print("❌ Exit without changes.")
        cur.close()
        conn.close()
        exit()

    else:
        print("⚠ Invalid choice!")
        cur.close()
        conn.close()
        exit()

    conn.commit()
    cur.execute("VACUUM")   # clean + compact DB
    conn.commit()

    print("\n✅ Operation completed successfully!")

except Exception as e:
    print("❌ Error:", e)

finally:
    cur.close()
    conn.close()
