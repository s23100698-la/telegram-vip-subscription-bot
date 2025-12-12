#!/usr/bin/env python3
"""
update_prices.py - Command line tool to update plan prices
Usage: python update_prices.py [command] [arguments]
"""

import sqlite3
import sys
import argparse
from tabulate import tabulate

def get_connection():
    """Get database connection"""
    conn = sqlite3.connect('subscriptions.db')
    conn.row_factory = sqlite3.Row
    return conn

def show_current_prices():
    """Display current plan prices"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM plans ORDER BY id")
    plans = cursor.fetchall()
    
    print("\n" + "="*60)
    print("📊 CURRENT PLAN PRICES")
    print("="*60)
    
    table_data = []
    for plan in plans:
        table_data.append([
            plan['id'],
            plan['name'],
            f"{plan['days']} days",
            f"₹{plan['price']}",
            plan['description'][:50] + "..." if len(plan['description']) > 50 else plan['description']
        ])
    
    headers = ["ID", "Plan Name", "Duration", "Price", "Description"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    conn.close()

def update_single_price(plan_id, new_price):
    """Update price of a single plan"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if plan exists
    cursor.execute("SELECT name FROM plans WHERE id = ?", (plan_id,))
    plan = cursor.fetchone()
    
    if not plan:
        print(f"❌ Error: Plan ID {plan_id} not found!")
        return False
    
    # Get old price
    cursor.execute("SELECT price FROM plans WHERE id = ?", (plan_id,))
    old_price = cursor.fetchone()['price']
    
    # Update price
    cursor.execute("UPDATE plans SET price = ? WHERE id = ?", (new_price, plan_id))
    conn.commit()
    
    print(f"✅ Price updated successfully!")
    print(f"   Plan: {plan['name']}")
    print(f"   Old Price: ₹{old_price}")
    print(f"   New Price: ₹{new_price}")
    print(f"   Change: ₹{new_price - old_price} ({((new_price - old_price)/old_price*100):.1f}%)")
    
    conn.close()
    return True

def update_all_prices(percentage):
    """Update all plan prices by percentage"""
    conn = get_connection()
    cursor = conn.cursor()
    
    multiplier = 1 + (percentage / 100)
    
    # Get current prices
    cursor.execute("SELECT id, name, price FROM plans ORDER BY id")
    plans = cursor.fetchall()
    
    print(f"\n📈 Updating all prices by {percentage}%")
    print("-" * 50)
    
    # Show changes before applying
    for plan in plans:
        new_price = round(plan['price'] * multiplier)
        change = new_price - plan['price']
        change_percent = (change / plan['price']) * 100
        print(f"  {plan['id']}. {plan['name']}: ₹{plan['price']} → ₹{new_price} ({change_percent:+.1f}%)")
    
    # Ask for confirmation
    confirm = input("\n❓ Confirm update? (yes/no): ").lower()
    if confirm not in ['yes', 'y', '1']:
        print("❌ Update cancelled!")
        return False
    
    # Apply changes
    cursor.execute("UPDATE plans SET price = ROUND(price * ?)", (multiplier,))
    conn.commit()
    
    print("✅ All prices updated successfully!")
    conn.close()
    return True

def set_all_prices(prices_dict):
    """Set specific prices for multiple plans"""
    conn = get_connection()
    cursor = conn.cursor()
    
    print("\n🎯 Setting specific prices:")
    print("-" * 50)
    
    for plan_id, new_price in prices_dict.items():
        cursor.execute("SELECT name, price FROM plans WHERE id = ?", (plan_id,))
        plan = cursor.fetchone()
        
        if plan:
            cursor.execute("UPDATE plans SET price = ? WHERE id = ?", (new_price, plan_id))
            print(f"  Plan {plan_id} ({plan['name']}): ₹{plan['price']} → ₹{new_price}")
    
    conn.commit()
    conn.close()
    print("✅ Prices set successfully!")
    return True

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Manage subscription plan prices',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python update_prices.py show
  python update_prices.py update --plan 2 --price 499
  python update_prices.py bulk --percentage 10
  python update_prices.py bulk --percentage -15
  python update_prices.py set --plan1 99 --plan2 299 --plan3 799 --plan4 1999
        '''
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Show command
    subparsers.add_parser('show', help='Show current prices')
    
    # Update single plan
    update_parser = subparsers.add_parser('update', help='Update single plan price')
    update_parser.add_argument('--plan', type=int, required=True, help='Plan ID (1-4)')
    update_parser.add_argument('--price', type=int, required=True, help='New price')
    
    # Bulk update
    bulk_parser = subparsers.add_parser('bulk', help='Update all prices by percentage')
    bulk_parser.add_argument('--percentage', type=float, required=True, help='Percentage change (+10 or -15)')
    
    # Set all prices
    set_parser = subparsers.add_parser('set', help='Set prices for all plans')
    set_parser.add_argument('--plan1', type=int, help='Price for Plan 1 (BASIC)')
    set_parser.add_argument('--plan2', type=int, help='Price for Plan 2 (PRO)')
    set_parser.add_argument('--plan3', type=int, help='Price for Plan 3 (PREMIUM)')
    set_parser.add_argument('--plan4', type=int, help='Price for Plan 4 (LIFETIME)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'show':
        show_current_prices()
    
    elif args.command == 'update':
        update_single_price(args.plan, args.price)
    
    elif args.command == 'bulk':
        update_all_prices(args.percentage)
    
    elif args.command == 'set':
        prices = {}
        if args.plan1: prices[1] = args.plan1
        if args.plan2: prices[2] = args.plan2
        if args.plan3: prices[3] = args.plan3
        if args.plan4: prices[4] = args.plan4
        
        if prices:
            set_all_prices(prices)
        else:
            print("❌ Error: No prices provided!")

if __name__ == "__main__":
    main()