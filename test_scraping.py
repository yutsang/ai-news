#!/usr/bin/env python3
"""
Test script to debug the scraper
"""

import asyncio
import logging
from datetime import datetime
from scraper import MarketNewsScraper

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_scraper():
    """Test the scraper with real data"""
    logger.info("Testing scraper...")
    
    async with MarketNewsScraper() as scraper:
        # Test with a recent date range
        start_date = datetime(2025, 7, 21)
        end_date = datetime(2025, 7, 27)
        
        logger.info(f"Testing date range: {start_date} to {end_date}")
        
        # Test HKET
        logger.info("Testing HKET...")
        hket_results = await scraper.scrape_hket(start_date, end_date)
        logger.info(f"HKET results: {len(hket_results)}")
        if hket_results:
            logger.info(f"Sample HKET result: {hket_results[0]}")
        
        # Test Wen Wei Po
        logger.info("Testing Wen Wei Po...")
        wenweipo_results = await scraper.scrape_wenweipo(start_date, end_date)
        logger.info(f"Wen Wei Po results: {len(wenweipo_results)}")
        if wenweipo_results:
            logger.info(f"Sample Wen Wei Po result: {wenweipo_results[0]}")
        
        # Test Sing Tao
        logger.info("Testing Sing Tao...")
        stheadline_results = await scraper.scrape_stheadline(start_date, end_date)
        logger.info(f"Sing Tao results: {len(stheadline_results)}")
        if stheadline_results:
            logger.info(f"Sample Sing Tao result: {stheadline_results[0]}")
        
        # Test all sources
        logger.info("Testing all sources...")
        all_results = await scraper.scrape_all_sources(start_date, end_date)
        logger.info(f"All sources results: {all_results}")

if __name__ == "__main__":
    asyncio.run(test_scraper()) 