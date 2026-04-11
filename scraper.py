"""
Web scraper module for fetching prices from Amazon and Flipkart
"""
import requests
from bs4 import BeautifulSoup
import re
import time
import random


def get_amazon_price(url):
    """
    Fetch price from Amazon product page
    
    Args:
        url (str): Amazon product URL
        
    Returns:
        float: Price in INR, or None if not found
    """
    if not url or url.strip() == "":
        return None
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # Reduced delay for faster performance
        time.sleep(random.uniform(0.2, 0.5))
        
        response = requests.get(url, headers=headers, timeout=10)  # Increased timeout
        
        if response.status_code != 200:
            print(f"❌ Amazon request failed with status code: {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try multiple selectors for Amazon price (updated for 2024)
        price_selectors = [
            'span.a-price-whole',
            'span.a-price span.a-offscreen',
            'span#priceblock_ourprice',
            'span#priceblock_dealprice',
            'span.a-color-price',
            'span.priceToPay span.a-price-whole',  # New design
        ]
        
        print(f"🔍 Attempting to scrape Amazon: {url[:60]}...")
        
        for selector in price_selectors:
            price_element = soup.select_one(selector)
            if price_element:
                price_text = price_element.get_text().strip()
                print(f"  → Found element with '{selector}': {price_text[:50]}")
                # Extract numbers from price text
                price_match = re.search(r'[\d,]+(?:\.\\d+)?', price_text.replace(',', ''))
                if price_match:
                    price = float(price_match.group(0))
                    print(f"✓ Amazon price found: ₹{price:,.0f}")
                    return price
        
        # Fallback: Search for any text containing ₹ followed by digits
        print("  → Trying fallback: searching for ₹ pattern in HTML...")
        price_pattern = re.compile(r'₹\s*([\d,]+(?:\.\d+)?)')
        all_text = soup.get_text()
        matches = price_pattern.findall(all_text)
        if matches:
            # Get the first large number (likely the product price)
            for match in matches:
                price_str = match.replace(',', '')
                try:
                    price = float(price_str)
                    if price > 1000:  # Filter out small amounts
                        print(f"✓ Amazon price found via fallback: ₹{price:,.0f}")
                        return price
                except ValueError:
                    continue
        
        print("❌ Amazon price not found with any method")
        return None
        
    except requests.exceptions.Timeout:
        print(f"⏱️ Amazon request timeout for URL: {url}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Amazon request error: {e}")
        return None
    except Exception as e:
        print(f"❌ Amazon parsing error: {e}")
        return None


def get_flipkart_price(url):
    """
    Fetch price from Flipkart product page
    
    Args:
        url (str): Flipkart product URL
        
    Returns:
        float: Price in INR, or None if not found
    """
    if not url or url.strip() == "":
        return None
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # Reduced delay for faster performance
        time.sleep(random.uniform(0.2, 0.5))
        
        response = requests.get(url, headers=headers, timeout=10)  # Increased timeout
        
        if response.status_code != 200:
            print(f"❌ Flipkart request failed with status code: {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Updated Flipkart price selectors (as of 2024)
        price_selectors = [
            'div.Nx9bqj.CxhGGd',  # New Flipkart design
            'div._30jeq3._16Jk6d',  # Legacy selector 1
            'div._30jeq3',  # Legacy selector 2
            'div._16Jk6d',  # Legacy selector 3
            'div.CEmiEU div._30jeq3',  # Legacy selector 4
            'div[class*="price"]',  # Generic price div
        ]
        
        print(f"🔍 Attempting to scrape Flipkart: {url[:60]}...")
        
        for selector in price_selectors:
            price_element = soup.select_one(selector)
            if price_element:
                price_text = price_element.get_text().strip()
                print(f"  → Found element with '{selector}': {price_text[:50]}")
                # Extract numbers from price text (remove ₹ and commas)
                price_match = re.search(r'[\d,]+', price_text.replace('₹', '').replace(',', ''))
                if price_match:
                    price = float(price_match.group(0))
                    print(f"✓ Flipkart price found: ₹{price:,.0f}")
                    return price
        
        # Fallback: Search for any text containing ₹ followed by digits
        print("  → Trying fallback: searching for ₹ pattern in HTML...")
        price_pattern = re.compile(r'₹\s*([\d,]+)')
        all_text = soup.get_text()
        matches = price_pattern.findall(all_text)
        if matches:
            # Get the first large number (likely the product price, not small amounts)
            for match in matches:
                price_str = match.replace(',', '')
                price = float(price_str)
                if price > 1000:  # Filter out small prices (ratings, etc.)
                    print(f"✓ Flipkart price found via fallback: ₹{price:,.0f}")
                    return price
        
        print("❌ Flipkart price not found with any method")
        return None
        
    except requests.exceptions.Timeout:
        print(f"⏱️ Flipkart request timeout for URL: {url}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Flipkart request error: {e}")
        return None
    except Exception as e:
        print(f"❌ Flipkart parsing error: {e}")
        return None


def get_lowest_price(amazon_url, flipkart_url, predicted_price):
    """
    Fetch prices from both Amazon and Flipkart and return the lowest
    Only compares Amazon and Flipkart prices - predicted price is used as fallback only
    
    Args:
        amazon_url (str): Amazon product URL
        flipkart_url (str): Flipkart product URL
        predicted_price (float): Fallback predicted price
        
    Returns:
        dict: {
            'amazon_price': float or None,
            'flipkart_price': float or None,
            'lowest_price': float,
            'price_source': str ('amazon', 'flipkart', or 'predicted')
        }
    """
    amazon_price = get_amazon_price(amazon_url) if amazon_url else None
    flipkart_price = get_flipkart_price(flipkart_url) if flipkart_url else None
    
    # Compare ONLY Amazon and Flipkart prices (exclude predicted from comparison)
    marketplace_prices = []
    if amazon_price:
        marketplace_prices.append(('amazon', amazon_price))
    if flipkart_price:
        marketplace_prices.append(('flipkart', flipkart_price))
    
    # Use marketplace lowest price if available, otherwise fallback to predicted
    if marketplace_prices:
        price_source, lowest_price = min(marketplace_prices, key=lambda x: x[1])
    else:
        lowest_price = predicted_price
        price_source = 'predicted'
    
    return {
        'amazon_price': amazon_price,
        'flipkart_price': flipkart_price,
        'lowest_price': lowest_price,
        'price_source': price_source
    }


if __name__ == "__main__":
    # Test the scraper
    print("Testing Amazon scraper...")
    test_amazon_url = "https://www.amazon.in/dp/B0CX23V2ZK"  # Example laptop
    amazon_result = get_amazon_price(test_amazon_url)
    print(f"Amazon Result: {amazon_result}")
    
    print("\nTesting Flipkart scraper...")
    test_flipkart_url = "https://www.flipkart.com/asus-vivobook-15-core-i3-12th-gen-1215u-8-gb-512-gb-ssd-windows-11-home-x1502za-ej322ws-thin-light-laptop/p/itm6bb10f87ae38f"
    flipkart_result = get_flipkart_price(test_flipkart_url)
    print(f"Flipkart Result: {flipkart_result}")
