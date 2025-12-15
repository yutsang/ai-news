#!/usr/bin/env python3
"""
Centaline Transaction Scraper
Scrapes residential transactions from hk.centanet.com
"""

import time
import logging
import re
from datetime import datetime
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CentalineScraper:
    """Scraper for Centaline property transactions"""
    
    def __init__(self, headless: bool = True):
        self.base_url = "https://hk.centanet.com/findproperty/list/transaction"
        self.headless = headless
        self.driver = None
    
    def init_driver(self):
        """Initialize Chrome driver"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(10)
    
    def parse_price(self, price_str: str) -> Optional[float]:
        """Parse price to millions HKD"""
        try:
            # Remove $ and commas
            price_str = price_str.replace('$', '').replace(',', '').replace('萬', '').strip()
            
            if '億' in price_str:
                num = float(re.sub(r'[^\d.]', '', price_str))
                return num * 100  # 億 to millions
            elif 'M' in price_str.upper():
                return float(re.sub(r'[^\d.]', '', price_str))
            else:
                # Assume it's in 萬
                num = float(price_str)
                return num / 100  # 萬 to millions
        except:
            return None
    
    def scrape_transactions(self, start_date: datetime, end_date: datetime, min_price_m: float = 20.0) -> List[Dict]:
        """
        Scrape transactions from Centaline using Selenium/ChromeDriver
        
        Args:
            start_date: Start date for filtering
            end_date: End date for filtering
            min_price_m: Minimum price in millions HKD
            
        Returns:
            List of transaction dictionaries
        """
        logger.info(f"Starting Centaline scrape from {start_date.date()} to {end_date.date()}")
        
        self.init_driver()
        transactions = []
        
        try:
            # Navigate to transactions page
            logger.info(f"Opening {self.base_url}")
            self.driver.get(self.base_url)
            
            wait = WebDriverWait(self.driver, 30)
            
            # Wait for page to load
            logger.info("Waiting for page to load...")
            time.sleep(5)
            
            # Set price filter to minimum 20M (2000萬)
            logger.info("Setting price filter to >2000萬 (20M HKD)...")
            try:
                # Look for price filter input
                # Try to find the "from" price input field
                price_inputs = self.driver.find_elements(By.CSS_SELECTOR, 'input[type="text"], input[type="number"]')
                
                for input_elem in price_inputs:
                    placeholder = input_elem.get_attribute('placeholder') or ''
                    if '萬' in placeholder or 'price' in placeholder.lower():
                        # This might be the price input
                        input_elem.clear()
                        input_elem.send_keys('2000')  # 2000萬 = 20M
                        logger.info("Set minimum price filter to 2000萬")
                        time.sleep(1)
                        
                        # Try to find and click search/apply button
                        search_buttons = self.driver.find_elements(By.CSS_SELECTOR, 'button[class*="search"], button[class*="apply"], button[type="submit"]')
                        for btn in search_buttons:
                            if btn.is_displayed():
                                btn.click()
                                logger.info("Clicked search button")
                                time.sleep(3)
                                break
                        break
            except Exception as e:
                logger.warning(f"Could not set price filter: {e}")
            
            # Wait for results to load
            logger.info("Waiting for filtered results...")
            time.sleep(5)
            
            # Process multiple pages
            page = 1
            max_pages = 5  # Limit to first 5 pages
            
            while page <= max_pages:
                logger.info(f"Processing page {page}...")
                
                # Wait for content to load
                time.sleep(3)
                
                # Get all transaction rows
                logger.info("Searching for transaction records...")
                
                # Save HTML for debugging (first page only)
                if page == 1 and not self.headless:
                    with open('centaline_debug.html', 'w', encoding='utf-8') as f:
                        f.write(self.driver.page_source)
                    logger.info("Saved page HTML to centaline_debug.html")
                
                # Try to find transaction elements
                # Look for elements containing property info
                elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), '$')]/..")
                logger.info(f"Found {len(elements)} elements with price data")
                
                # Extract transactions from current page
                page_transactions = 0
                for idx, elem in enumerate(elements):
                    try:
                        transaction = self._extract_transaction_data(elem, idx)
                        
                        if transaction and transaction.get('price'):
                            trans_date = transaction.get('date_obj')
                            price_m = self.parse_price(transaction.get('price', '0'))
                            
                            # Apply filters
                            date_ok = trans_date and start_date <= trans_date <= end_date
                            price_ok = price_m and price_m >= min_price_m
                            
                            if date_ok and price_ok:
                                transaction['price_millions'] = price_m
                                transactions.append(transaction)
                                page_transactions += 1
                                logger.info(f"✓ Page {page}: {transaction.get('property', '')} - ${price_m:.1f}M")
                    
                    except Exception as e:
                        logger.debug(f"Error processing element {idx}: {e}")
                        continue
                
                logger.info(f"Page {page}: Added {page_transactions} transactions")
                
                # Try to go to next page
                try:
                    # Look for next page button
                    next_buttons = self.driver.find_elements(By.XPATH, 
                        "//button[contains(@class, 'next') or contains(text(), '下一頁') or contains(@aria-label, 'next')]")
                    
                    if not next_buttons:
                        # Try pagination numbers
                        next_buttons = self.driver.find_elements(By.XPATH, 
                            f"//a[contains(text(), '{page + 1}')]")
                    
                    if next_buttons and next_buttons[0].is_enabled():
                        logger.info(f"Going to page {page + 1}...")
                        next_buttons[0].click()
                        time.sleep(3)
                        page += 1
                    else:
                        logger.info("No more pages available")
                        break
                
                except Exception as e:
                    logger.info(f"Pagination ended: {e}")
                    break
            
            logger.info(f"Completed: Found {len(transactions)} total transactions (>={min_price_m}M HKD, dates {start_date.date()} to {end_date.date()})")
            
        except Exception as e:
            logger.error(f"Error scraping Centaline: {e}", exc_info=True)
        
        finally:
            if self.driver:
                self.driver.quit()
        
        return transactions
    
    def _extract_transaction_data(self, elem, idx: int) -> Optional[Dict]:
        """Extract data from a single transaction element"""
        try:
            # Get the element's HTML for inspection
            elem_html = elem.get_attribute('outerHTML')[:500]  # First 500 chars
            logger.debug(f"Element {idx} HTML: {elem_html}")
            
            # Extract all text from element
            all_text = elem.text.strip()
            if not all_text:
                return None
            
            logger.debug(f"Element {idx} text: {all_text[:200]}")
            
            # Try multiple selector strategies
            transaction = {
                'source': 'Centaline',
                'category': 'Residential',
                'asset_type': '住宅',
                'area_basis': 'NFA',
                'unit_basis': 'sqft',
                'nature': 'Sales'
            }
            
            # Property name - try multiple selectors
            property_name = 'N/A'
            try:
                selectors = [
                    'h3', 'h4', 'h5',
                    '[class*="name"]', '[class*="estate"]', '[class*="property"]',
                    'a[class*="title"]', 'div[class*="title"]'
                ]
                for selector in selectors:
                    try:
                        prop_elem = elem.find_element(By.CSS_SELECTOR, selector)
                        if prop_elem and prop_elem.text.strip():
                            property_name = prop_elem.text.strip()
                            break
                    except:
                        continue
            except:
                pass
            
            # District - <span data-v-* class="adress tag-adress">
            district = 'N/A'
            try:
                district_selectors = [
                    'span.adress.tag-adress',
                    'span[class*="adress"]',
                    'span.tag-adress',
                    '[class*="district"]',
                    '[class*="location"]'
                ]
                for selector in district_selectors:
                    try:
                        dist_elem = elem.find_element(By.CSS_SELECTOR, selector)
                        if dist_elem and dist_elem.text.strip():
                            district = dist_elem.text.strip()
                            break
                    except:
                        continue
            except:
                pass
            
            # Price - look for $ or 萬 or 億
            price = 'N/A'
            price_patterns = [
                r'\$[\d,]+(?:萬|億)?',
                r'[\d,]+萬',
                r'[\d,]+億',
                r'HK\$[\d,]+'
            ]
            for pattern in price_patterns:
                match = re.search(pattern, all_text)
                if match:
                    price = match.group(0)
                    break
            
            # Area - look for sqft or 呎
            area = 'N/A'
            area_patterns = [
                r'([\d,]+)\s*(?:呎|尺|sq\.?\s*ft)',
                r'([\d,]+)\s*平方呎'
            ]
            for pattern in area_patterns:
                match = re.search(pattern, all_text, re.IGNORECASE)
                if match:
                    area = match.group(1).replace(',', '')
                    break
            
            # Date - look for various date formats
            date_obj = None
            date_str = 'N/A'
            date_patterns = [
                r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',  # 2025-12-13
                r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})',  # 13/12/2025
            ]
            for pattern in date_patterns:
                match = re.search(pattern, all_text)
                if match:
                    date_str = match.group(1)
                    # Try to parse
                    for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y', '%d-%m-%Y']:
                        try:
                            date_obj = datetime.strptime(date_str, fmt)
                            date_str = date_obj.strftime('%d/%m/%Y')
                            break
                        except:
                            continue
                    if date_obj:
                        break
            
            # Unit price
            unit_price = 'N/A'
            unit_price_pattern = r'\$?([\d,]+)\s*[元/呎]'
            match = re.search(unit_price_pattern, all_text)
            if match:
                unit_price = match.group(1).replace(',', '')
            
            transaction.update({
                'property': property_name,
                'district': district,
                'price': price,
                'area': area,
                'unit_price': unit_price,
                'date': date_str,
                'date_obj': date_obj,
                'floor': 'N/A',
                'unit': 'N/A'
            })
            
            # Only return if we have at least property name and price
            if property_name != 'N/A' and price != 'N/A':
                return transaction
            
            return None
            
        except Exception as e:
            logger.debug(f"Could not extract transaction {idx}: {e}")
            return None


if __name__ == "__main__":
    # Test the scraper
    scraper = CentalineScraper(headless=False)
    
    # Test with date range
    start = datetime(2025, 12, 8)
    end = datetime(2025, 12, 14)
    
    transactions = scraper.scrape_transactions(start, end, min_price_m=20.0)
    
    print(f"\nFound {len(transactions)} transactions")
    for trans in transactions[:5]:
        print(f"\n{trans}")

