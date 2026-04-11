"""
Background price updater using APScheduler
This module handles periodic price updates from Amazon and Flipkart
"""
import sqlite3
import logging
from datetime import datetime
from scraper import get_amazon_price, get_flipkart_price

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('price_updater.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

DB_PATH = "laptop_dataset.db"


def update_all_prices():
    """
    Update prices for all products in the database
    This function is called by the scheduler every hour
    """
    logger.info("=" * 60)
    logger.info("Starting scheduled price update job")
    logger.info("=" * 60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Get all products with links
        cursor.execute("""
            SELECT rowid, Company, Product, amazon_link, flipkart_link 
            FROM laptops 
            WHERE (amazon_link IS NOT NULL AND amazon_link != '') 
               OR (flipkart_link IS NOT NULL AND flipkart_link != '')
        """)
        
        products = cursor.fetchall()
        total_products = len(products)
        logger.info(f"Found {total_products} products with marketplace links")
        
        if total_products == 0:
            logger.warning("No products with links found. Skipping update.")
            return
        
        updated_count = 0
        error_count = 0
        
        for idx, (rowid, company, product_name, amazon_link, flipkart_link) in enumerate(products, 1):
            logger.info(f"\n[{idx}/{total_products}] Processing: {company} - {product_name[:50]}...")
            
            # Fetch prices
            amazon_price = None
            flipkart_price = None
            
            if amazon_link and amazon_link.strip() != '':
                logger.info(f"  Fetching Amazon price...")
                try:
                    amazon_price = get_amazon_price(amazon_link)
                    if amazon_price:
                        logger.info(f"  ✓ Amazon: ₹{amazon_price:,.2f}")
                    else:
                        logger.warning(f"  ✗ Amazon: Price not found")
                except Exception as e:
                    logger.error(f"  ✗ Amazon error: {e}")
                    error_count += 1
            
            if flipkart_link and flipkart_link.strip() != '':
                logger.info(f"  Fetching Flipkart price...")
                try:
                    flipkart_price = get_flipkart_price(flipkart_link)
                    if flipkart_price:
                        logger.info(f"  ✓ Flipkart: ₹{flipkart_price:,.2f}")
                    else:
                        logger.warning(f"  ✗ Flipkart: Price not found")
                except Exception as e:
                    logger.error(f"  ✗ Flipkart error: {e}")
                    error_count += 1
            
            # Update database if at least one price was found
            if amazon_price or flipkart_price:
                try:
                    current_time = datetime.now().isoformat()
                    cursor.execute("""
                        UPDATE laptops 
                        SET amazon_price_cached = ?,
                            flipkart_price_cached = ?,
                            last_price_update = ?
                        WHERE rowid = ?
                    """, (amazon_price, flipkart_price, current_time, rowid))
                    
                    updated_count += 1
                    logger.info(f"  ✓ Database updated")
                except Exception as e:
                    logger.error(f"  ✗ Database update failed: {e}")
                    error_count += 1
            else:
                logger.warning(f"  ⚠ No prices found, skipping database update")
        
        # Commit all changes
        conn.commit()
        
        logger.info("\n" + "=" * 60)
        logger.info(f"Price update job completed!")
        logger.info(f"  Total products processed: {total_products}")
        logger.info(f"  Successfully updated: {updated_count}")
        logger.info(f"  Errors encountered: {error_count}")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Fatal error during price update: {e}")
        conn.rollback()
        raise
    
    finally:
        conn.close()


def update_single_product(product_id):
    """
    Update price for a single product (for manual refresh)
    
    Args:
        product_id (int): Product ID to update
        
    Returns:
        dict: Updated price data or None if failed
    """
    logger.info(f"Updating single product ID: {product_id}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Get product details
        cursor.execute("""
            SELECT Company, Product, amazon_link, flipkart_link 
            FROM laptops 
            WHERE rowid = ?
        """, (product_id,))
        
        result = cursor.fetchone()
        if not result:
            logger.error(f"Product ID {product_id} not found")
            return None
        
        company, product_name, amazon_link, flipkart_link = result
        logger.info(f"Product: {company} - {product_name}")
        
        # Fetch prices
        amazon_price = get_amazon_price(amazon_link) if amazon_link else None
        flipkart_price = get_flipkart_price(flipkart_link) if flipkart_link else None
        
        if amazon_price or flipkart_price:
            current_time = datetime.now().isoformat()
            cursor.execute("""
                UPDATE laptops 
                SET amazon_price_cached = ?,
                    flipkart_price_cached = ?,
                    last_price_update = ?
                WHERE rowid = ?
            """, (amazon_price, flipkart_price, current_time, product_id))
            
            conn.commit()
            logger.info(f"✓ Product {product_id} updated successfully")
            
            return {
                'amazon_price': amazon_price,
                'flipkart_price': flipkart_price,
                'last_updated': current_time
            }
        else:
            logger.warning(f"No prices found for product {product_id}")
            return None
    
    except Exception as e:
        logger.error(f"Error updating product {product_id}: {e}")
        conn.rollback()
        return None
    
    finally:
        conn.close()


if __name__ == "__main__":
    # Run price update when called directly
    logger.info("Running price updater manually...")
    update_all_prices()
