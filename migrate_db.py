"""
Database migration script to add price caching columns
Run this script once to update the database schema
"""
import sqlite3
from datetime import datetime

DB_PATH = "laptop_dataset.db"

def migrate_database():
    """Add price caching columns to laptops table"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        print("Starting database migration...")
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(laptops)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Add amazon_price_cached if it doesn't exist
        if 'amazon_price_cached' not in columns:
            print("Adding amazon_price_cached column...")
            cursor.execute("ALTER TABLE laptops ADD COLUMN amazon_price_cached REAL")
            print("✓ Added amazon_price_cached")
        else:
            print("✓ amazon_price_cached already exists")
        
        # Add flipkart_price_cached if it doesn't exist
        if 'flipkart_price_cached' not in columns:
            print("Adding flipkart_price_cached column...")
            cursor.execute("ALTER TABLE laptops ADD COLUMN flipkart_price_cached REAL")
            print("✓ Added flipkart_price_cached")
        else:
            print("✓ flipkart_price_cached already exists")
        
        # Add last_price_update if it doesn't exist
        if 'last_price_update' not in columns:
            print("Adding last_price_update column...")
            cursor.execute("ALTER TABLE laptops ADD COLUMN last_price_update TEXT")
            print("✓ Added last_price_update")
        else:
            print("✓ last_price_update already exists")
        
        conn.commit()
        print("\n✅ Database migration completed successfully!")
        
        # Show updated schema
        cursor.execute("PRAGMA table_info(laptops)")
        columns = cursor.fetchall()
        print(f"\nTotal columns in laptops table: {len(columns)}")
        print("\nNew columns added:")
        for col in columns:
            if col[1] in ['amazon_price_cached', 'flipkart_price_cached', 'last_price_update']:
                print(f"  - {col[1]}: {col[2]}")
        
    except sqlite3.Error as e:
        print(f"\n❌ Migration failed: {e}")
        conn.rollback()
        raise
    
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()
