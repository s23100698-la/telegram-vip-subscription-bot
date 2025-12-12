#!/usr/bin/env python3
import sqlite3

def add_plan(plan_id, name, days, price, description, features):
    conn = sqlite3.connect('subscriptions.db')
    cur = conn.cursor()

    # Check if already exists
    cur.execute("SELECT id FROM plans WHERE id = ?", (plan_id,))
    if cur.fetchone():
        print(f"❌ Plan ID {plan_id} already exists!")
        conn.close()
        return

    cur.execute("""
        INSERT INTO plans (id, name, days, price, description, features)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (plan_id, name, days, price, description, features))

    conn.commit()
    conn.close()
    print(f"✅ New plan added successfully! (ID: {plan_id})")

if __name__ == "__main__":
    print("⭐ ADD NEW PLAN")
    pid = int(input("Plan ID (must be unique): "))
    name = input("Plan Name: ")
    days = int(input("Duration (days): "))
    price = int(input("Price (₹): "))
    desc = input("Short Description: ")
    feats = input("Features (use \\n for new line): ")

    add_plan(pid, name, days, price, desc, feats)
