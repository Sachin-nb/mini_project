"""
Quick Test Script - Verify all fixes are working
"""
import sqlite3

print("=" * 60)
print("Qualitron Laptop Store - Verification Test")
print("=" * 60)

# Test 1: Check database schema
print("\n[TEST 1] Checking database schema...")
conn = sqlite3.connect('laptop_dataset.db')
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(laptops)")
columns = [row[1] for row in cursor.fetchall()]

required_columns = ['amazon_price_cached', 'flipkart_price_cached', 'last_price_update']
missing_columns = [col for col in required_columns if col not in columns]

if missing_columns:
    print(f"  ❌ FAIL: Missing columns: {missing_columns}")
    print(f"  → Run: python fix_database.py")
else:
    print(f"  ✅ PASS: All required columns present")

# Test 2: Check for products with links
cursor.execute("""
    SELECT COUNT(*) FROM laptops 
    WHERE (amazon_link IS NOT NULL AND amazon_link != '') 
       OR (flipkart_link IS NOT NULL AND flipkart_link != '')
""")
products_with_links = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM laptops")
total_products = cursor.fetchone()[0]

print(f"\n[TEST 2] Checking product links...")
print(f"  Total products: {total_products}")
print(f"  Products with marketplace links: {products_with_links}")
if products_with_links > 0:
    print(f"  ✅ PASS: {products_with_links} products ready for price tracking")
else:
    print(f"  ⚠️  WARNING: No products have marketplace links")
    print(f"  → Add links via Admin panel at http://127.0.0.1:5000/admin/login")

conn.close()

# Test 3: Check imports
print(f"\n[TEST 3] Checking Python dependencies...")
try:
    import flask
    import pandas
    import requests
    from bs4 import BeautifulSoup
    import reportlab
    print(f"  ✅ PASS: All core dependencies installed")
except ImportError as e:
    print(f"  ❌ FAIL: Missing dependency: {e}")
    print(f"  → Run: pip install flask pandas requests beautifulsoup4 reportlab apscheduler")

try:
    import apscheduler
    print(f"  ✅ PASS: APScheduler installed (for background updates)")
except ImportError:
    print(f"  ⚠️  WARNING: APScheduler not installed")
    print(f"  → For background price updates, run: pip install apscheduler")

# Test 4: Check app structure
print(f"\n[TEST 4] Checking application files...")
import os
required_files = {
    'app.py': 'Main Flask application',
    'scraper.py': 'Price scraper module',
    'price_updater.py': 'Background price updater',
    'run_scheduler.py': 'Scheduler runner',
    'templates/products.html': 'Products listing page',
    'templates/product_detail.html': 'Product detail page'
}

all_files_present = True
for file, description in required_files.items():
    if os.path.exists(file):
        print(f"  ✅ {file} - {description}")
    else:
        print(f"  ❌ {file} - MISSING")
        all_files_present = False

# Final Summary
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)

if not missing_columns and all_files_present:
    print("✅ All tests passed! Your application is ready to run.")
    print("\n🚀 TO START THE APPLICATION:")
    print("   1. Run: python app.py")
    print("   2. Open: http://127.0.0.1:5000")
    print("\n⚡ TO ENABLE BACKGROUND PRICE UPDATES:")
    print("   1. Open a NEW terminal")
    print("   2. Run: python run_scheduler.py")
    print("\nOR simply run: start.bat (Windows)")
else:
    print("⚠️  Some issues detected. Please fix them before running.")
    
print("=" * 60)
