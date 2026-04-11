import sqlite3

conn = sqlite3.connect('laptop_dataset.db')
cursor = conn.cursor()

# Check cached prices
cursor.execute('SELECT COUNT(*) FROM laptops WHERE amazon_price_cached IS NOT NULL OR flipkart_price_cached IS NOT NULL')
print(f'Products with cached prices: {cursor.fetchone()[0]}')

# Check links
cursor.execute('SELECT COUNT(*) FROM laptops WHERE amazon_link IS NOT NULL AND amazon_link != ""')
print(f'Products with Amazon links: {cursor.fetchone()[0]}')

cursor.execute('SELECT COUNT(*) FROM laptops WHERE flipkart_link IS NOT NULL AND flipkart_link != ""')
print(f'Products with Flipkart links: {cursor.fetchone()[0]}')

# Check sample product
cursor.execute('''
    SELECT rowid, Company, Product, amazon_link, flipkart_link, 
           amazon_price_cached, flipkart_price_cached, last_price_update
    FROM laptops 
    LIMIT 5
''')
print('\nSample products:')
for row in cursor.fetchall():
    print(f"ID {row[0]}: {row[1]} {row[2][:30]}...")
    print(f"  Amazon: {row[3][:50] if row[3] else 'None'}... Price: {row[5]}")
    print(f"  Flipkart: {row[4][:50] if row[4] else 'None'}... Price: {row[6]}")
    print()

conn.close()
