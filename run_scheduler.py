"""
Background scheduler for periodic price updates
This runs as a separate process and updates prices in the database every hour
"""
from apscheduler.schedulers.blocking import BlockingScheduler
from price_updater import update_all_prices
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Main entry point for the price update scheduler"""
    scheduler = BlockingScheduler()
    
    # Schedule price updates every hour
    scheduler.add_job(
        update_all_prices,
        'interval',
        hours=1,
        id='price_updater',
        name='Update all laptop prices',
        replace_existing=True
    )
    
    logger.info("=" * 60)
    logger.info("Price Update Scheduler Started")
    logger.info("Prices will be updated every 1 hour")
    logger.info("=" * 60)
    
    # Run once immediately on startup
    logger.info("Running initial price update...")
    try:
        update_all_prices()
    except Exception as e:
        logger.error(f"Initial price update failed: {e}")
    
    # Start scheduler
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped by user")
    except Exception as e:
        logger.error(f"Scheduler error: {e}")

if __name__ == "__main__":
    main()
