import os

file_path = r'c:\Users\sachi\OneDrive\Documents\sachin\templates\product_detail.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add debugging after the fetch
target = """      fetch(`/api/get_price/${productId}`)
        .then(response => response.json())
        .then(data => {
          const formatter = new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: 'INR'
          });"""

replacement = """      fetch(`/api/get_price/${productId}`)
        .then(response => response.json())
        .then(data => {
          // DEBUG: Log complete API response
          console.log('=== FULL API RESPONSE ===');
          console.log('Amazon Price:', data.amazon_price, typeof data.amazon_price);
          console.log('Flipkart Price:', data.flipkart_price, typeof data.flipkart_price);
          console.log('Lowest Price:', data.lowest_price);
          console.log('Price Source:', data.price_source);
          console.log('Amazon Link:', data.amazon_link);
          console.log('Flipkart Link:', data.flipkart_link);
          console.log('========================');
          
          const formatter = new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: 'INR'
          });"""

if target in content:
    new_content = content.replace(target, replacement)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Successfully added debugging logs.")
else:
    print("Target not found. Trying alternative approach...")
    # Try to find where to insert
    idx = content.find("fetch(`/api/get_price/${productId}`)")
    if idx != -1:
        print(f"Found fetch at position {idx}")
        print("Context:")
        print(repr(content[idx:idx+300]))
    else:
        print("Could not find fetch call")
