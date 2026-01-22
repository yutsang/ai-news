#!/usr/bin/env python3
"""
Midland ICI Web Scraper
Scrapes commercial property transactions directly from the Midland website HTML
More reliable than API approach
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import time
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class MidlandWebScraper:
    """Scraper for Midland ICI commercial transactions via website HTML"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.website_url = "https://www.midlandici.com.hk/transaction"
        self.driver = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.driver:
            self.driver.quit()
    
    def fetch_transactions(self, start_date: datetime, end_date: datetime, min_area: int = 2500) -> List[Dict]:
        """Fetch transactions by scraping the website HTML"""
        
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1400,1000')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        
        try:
            logger.info(f"Opening Midland ICI: {self.website_url}")
            print("  → Opening Midland ICI website...")
            self.driver.get(self.website_url)
            time.sleep(8)
            
            # Set date filters
            print("  → Setting date filters...")
            self._set_date_range(start_date, end_date)
            
            # Set minimum area filter
            print(f"  → Setting minimum area: {min_area} sqft...")
            self._set_min_area(min_area)
            
            # Apply filters / search
            print("  → Applying filters and searching...")
            self._click_search()
            
            # Scrape results
            print("  → Scraping results...")
            transactions = self._scrape_all_pages(start_date, end_date, min_area)
            
            logger.info(f"Retrieved {len(transactions)} Midland transactions")
            return transactions
            
        except Exception as e:
            logger.error(f"Error scraping Midland: {e}")
            return []
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None
    
    def _set_date_range(self, start_date: datetime, end_date: datetime):
        """Set date range filters on the website"""
        try:
            # Look for date input fields
            date_inputs = self.driver.find_elements(By.CSS_SELECTOR, 
                "input[type='text'][placeholder*='日期'], input[type='text'][placeholder*='Date'], input[class*='date']"
            )
            
            if len(date_inputs) >= 2:
                # First input: start date
                date_inputs[0].clear()
                date_inputs[0].send_keys(start_date.strftime('%Y-%m-%d'))
                time.sleep(0.5)
                
                # Second input: end date
                date_inputs[1].clear()
                date_inputs[1].send_keys(end_date.strftime('%Y-%m-%d'))
                time.sleep(0.5)
                
                logger.info(f"Set date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        except Exception as e:
            logger.warning(f"Could not set date range: {e}")
    
    def _set_min_area(self, min_area: int):
        """Set minimum area filter"""
        try:
            # Look for area input fields
            area_inputs = self.driver.find_elements(By.CSS_SELECTOR,
                "input[placeholder*='面積'], input[placeholder*='Area'], input[type='number']"
            )
            
            for input_elem in area_inputs:
                if input_elem.is_displayed():
                    input_elem.clear()
                    input_elem.send_keys(str(min_area))
                    time.sleep(0.5)
                    break
                    
            logger.info(f"Set minimum area: {min_area}")
        except Exception as e:
            logger.warning(f"Could not set area filter: {e}")
    
    def _click_search(self):
        """Click search/apply button"""
        try:
            # Look for search buttons
            search_btns = self.driver.find_elements(By.XPATH,
                "//button[contains(text(), '搜尋') or contains(text(), '搜索') or contains(text(), 'Search') or contains(@class, 'search')]"
            )
            
            for btn in search_btns:
                if btn.is_displayed() and btn.is_enabled():
                    btn.click()
                    time.sleep(5)  # Wait for results to load
                    logger.info("Clicked search button")
                    break
        except Exception as e:
            logger.warning(f"Could not click search: {e}")
    
    def _scrape_all_pages(self, start_date: datetime, end_date: datetime, min_area: int) -> List[Dict]:
        """Scrape all pages of results"""
        all_transactions = []
        page = 1
        max_pages = 20
        
        while page <= max_pages:
            logger.info(f"Scraping Midland page {page}...")
            page_transactions = self._scrape_current_page(start_date, end_date, min_area)
            
            if page_transactions:
                all_transactions.extend(page_transactions)
            else:
                # No results on this page
                if page == 1:
                    # No results at all
                    break
                # Try one more page
                if page > 1:
                    break
            
            # Try to go to next page
            if not self._go_to_next_page():
                break
            
            page += 1
            time.sleep(2)
        
        return all_transactions
    
    def _scrape_current_page(self, start_date: datetime, end_date: datetime, min_area: int) -> List[Dict]:
        """Scrape transactions from current page"""
        transactions = []
        
        try:
            time.sleep(3)
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Find transaction rows (this will vary based on actual HTML structure)
            # Common selectors for tables
            rows = soup.select('tr.transaction-row, tr.result-row, tbody tr, .transaction-item, .result-item')
            
            if not rows:
                # Try alternative selectors
                rows = soup.select('tr')
            
            logger.info(f"Found {len(rows)} potential transaction rows")
            
            for row in rows:
                try:
                    trans = self._parse_transaction_row(row, start_date, end_date, min_area)
                    if trans:
                        transactions.append(trans)
                except Exception as e:
                    continue
            
        except Exception as e:
            logger.error(f"Error scraping page: {e}")
        
        return transactions
    
    def _parse_transaction_row(self, row, start_date: datetime, end_date: datetime, min_area: int) -> Optional[Dict]:
        """Parse a single transaction row from HTML"""
        # This method needs to be customized based on actual Midland HTML structure
        # For now, return None - this is a placeholder
        return None
    
    def _go_to_next_page(self) -> bool:
        """Navigate to next page"""
        try:
            # Look for next page button
            next_btns = self.driver.find_elements(By.XPATH,
                "//button[contains(@class, 'next') or contains(text(), '下一頁') or contains(text(), 'Next')]"
            )
            
            for btn in next_btns:
                if btn.is_displayed() and btn.is_enabled():
                    if 'disabled' not in btn.get_attribute('class'):
                        btn.click()
                        time.sleep(3)
                        return True
        except:
            pass
        
        return False
