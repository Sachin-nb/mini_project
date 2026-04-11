"""
Quick Test - Fetch Amazon Price for a Product
This will test if price fetching is working
"""
import sqlite3
from scraper import get_amazon_price, get_flipkart_price

# Get a product with an Amazon link
conn = sqlite3.connect('laptop_dataset.db')
cursor = conn.cursor()

cursor.execute("""
    SELECT rowid, Company, Product, amazon_link, flipkart_link
    FROM laptops 
    WHERE amazon_link IS NOT NULL AND amazon_link != ''
    LIMIT 1
""")

result = cursor.fetchone()

if not result:
    print("❌ No products with Amazon links found in database")
    print("   Add Amazon links via Admin panel: http://127.0.0.1:5000/admin/login")
else:
    product_id, company, product, amazon_link, flipkart_link = result
    print(f"Testing price fetch for:")
    print(f"  Product ID: {product_id}")
    print(f"  Name: {company} {product[:50]}...")
    print(f"  Amazon Link: {amazon_link[:60]}...")
    print()
    
    print("Fetching Amazon price... (this may take 5-10 seconds)")
    amazon_price = get_amazon_price(amazon_link)
    
    if amazon_price:
        print(f"✅ Success! Amazon price: ₹{amazon_price:,.2f}")
        
        # Update cache
        from datetime import datetime
        current_time = datetime.now().isoformat()
        cursor.execute("""
            UPDATE laptops 
            SET amazon_price_cached = ?,
                last_price_update = ?
            WHERE rowid = ?
        """, (amazon_price, current_time, product_id))
        conn.commit()
        print(f"✓ Price cached in database")
        print()
        print(f"Now visit: http://127.0.0.1:5000/product/{product_id}")
        print(f"You should see the Amazon price!")
    else:
        print(f"❌ Could not fetch Amazon price")
        print(f"   This could mean:")
        print(f"   - Amazon is blocking the request")
        print(f"   - The URL is invalid")
        print(f"   - The page structure changed")

conn.close()
