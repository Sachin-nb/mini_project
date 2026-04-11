import sqlite3
import json

DB_PATH = "laptop_dataset.db"

def check_product_prices(product_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT rowid, Company, Product, 
               amazon_link, flipkart_link, 
               amazon_price_cached, flipkart_price_cached, 
               last_price_update 
        FROM laptops 
        WHERE rowid = ?
    """, (product_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        print(f"\n=== Product ID: {row['rowid']} ===")
        print(f"Company: {row['Company']}")
        print(f"Product: {row['Product']}")
        print(f"\nAmazon Link: {row['amazon_link'][:50] if row['amazon_link'] else 'None'}...")
        print(f"Amazon Price Cached: {row['amazon_price_cached']} (Type: {type(row['amazon_price_cached'])})")
        print(f"\nFlipkart Link: {row['flipkart_link'][:50] if row['flipkart_link'] else 'None'}...")
        print(f"Flipkart Price Cached: {row['flipkart_price_cached']} (Type: {type(row['flipkart_price_cached'])})")
        print(f"\nLast Update: {row['last_price_update']}")
        
        # Simulate what the API would return
        print(f"\n=== Simulated API Response ===")
        api_response = {
            'amazon_price': row['amazon_price_cached'],
            'flipkart_price': row['flipkart_price_cached'],
            'amazon_link': row['amazon_link'],
            'flipkart_link': row['flipkart_link']
        }
        print(json.dumps(api_response, indent=2))
    else:
        print("Product not found")

if __name__ == "__main__":
    # Test with a few product IDs
    for pid in [26, 248, 196]:
        check_product_prices(pid)
        print("\n" + "="*60 + "\n")
