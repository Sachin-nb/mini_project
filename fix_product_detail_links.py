# Quick Fix Script - Update product_detail.html JavaScript
# This script fixes the link display issue

import re

# Read the current file
with open('templates/product_detail.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the problematic JavaScript section
# The issue: Links only show when prices exist
# The fix: Show links independently of prices

old_amazon_section = '''if (amazonLink && data.amazon_link) {
              amazonLink.classList.remove('disabled');
              amazonLink.innerHTML = '🛒 View on Amazon';
              amazonLink.href = data.amazon_link;
            }'''

new_amazon_section = '''// Amazon link - handled separately below'''

old_flipkart_section = '''if (flipkartLink && data.flipkart_link) {
              flipkartLink.classList.remove('disabled');
              flipkartLink.innerHTML = '🛒 View on Flipkart';
              flipkartLink.href = data.flipkart_link;
            }'''

new_flipkart_section = '''// Flipkart link - handled separately below'''

# Add new sections after price updates
insert_after = '''amazonCard.classList.add('border-secondary');
          }'''

amazon_link_code = '''
          
          // Show Amazon link if it exists (regardless of price)
          if (data.amazon_link &&data.amazon_link.trim() !== '') {
            amazonLink.classList.remove('disabled');
            amazonLink.innerHTML = '🛒 View on Amazon';
            amazonLink.href = data.amazon_link;
          }'''

insert_after_flipkart = '''flipkartCard.classList.add('border-secondary');
          }'''

flipkart_link_code = '''
          
          // Show Flipkart link if it exists (regardless of price)
          if (data.flipkart_link && data.flipkart_link.trim() !== '') {
            flipkartLink.classList.remove('disabled');
            flipkartLink.innerHTML = '🛒 View on Flipkart';
            flipkartLink.href = data.flipkart_link;
          }'''

# Apply replacements
content = content.replace(old_amazon_section, new_amazon_section)
content = content.replace(old_flipkart_section, new_flipkart_section)
content = content.replace(insert_after, insert_after + amazon_link_code)
content = content.replace(insert_after_flipkart, insert_after_flipkart + flipkart_link_code)

# Write back
with open('templates/product_detail.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Fixed product_detail.html")
print("   - Amazon links now show even without cached price")
print("   - Flipkart links now show even without cached price")
print("\n🔄 Please restart your Flask app for changes to take effect")
