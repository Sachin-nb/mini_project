import sqlite3

conn = sqlite3.connect('laptop_dataset.db')
cur = conn.cursor()

# Check how many products have links
cur.execute('SELECT COUNT(*) FROM laptops WHERE amazon_link IS NOT NULL AND amazon_link != ""')
amazon_count = cur.fetchone()[0]
print(f'Products with Amazon links: {amazon_count}')

cur.execute('SELECT COUNT(*) FROM laptops WHERE flipkart_link IS NOT NULL AND flipkart_link != ""')
flipkart_count = cur.fetchone()[0]
print(f'Products with Flipkart links: {flipkart_count}')

# Get a sample product with links
cur.execute('''SELECT Company, Product, amazon_link, flipkart_link 
               FROM laptops 
               WHERE (amazon_link IS NOT NULL AND amazon_link != "") 
                  OR (flipkart_link IS NOT NULL AND flipkart_link != "")
               LIMIT 1''')
sample = cur.fetchone()
if sample:
    print(f'\nSample product: {sample[0]} - {sample[1][:50]}')
    print(f'Amazon link: {sample[2] if sample[2] else "None"}')
    print(f'Flipkart link: {sample[3] if sample[3] else "None"}')

conn.close()
