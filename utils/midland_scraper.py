#!/usr/bin/env python3
"""
Midland ICI Transaction Scraper
Auto-scrapes commercial/industrial transactions from Midland ICI
Filter: Area >= 3000 sqft, within date range
"""

import time
import logging
import re
from datetime import datetime
from typing import List, Dict
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MidlandICIScraper:
    """Scraper for Midland ICI commercial transactions"""
    
    def __init__(self, headless: bool = True):
        self.base_url = "https://www.midlandici.com.hk/zh-hk/listing/transaction/ics/"
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
    
    def scrape_transactions(self, start_date: datetime, end_date: datetime, min_area_sqft: float = 3000.0) -> List[Dict]:
        """Scrape transactions from Midland ICI"""
        logger.info(f"Starting Midland ICI scrape from {start_date.date()} to {end_date.date()}")
        logger.info(f"Filter: Area >= {min_area_sqft} sqft")
        
        self.init_driver()
        transactions = []
        
        try:
            logger.info(f"Opening {self.base_url}")
            self.driver.get(self.base_url)
            time.sleep(8)  # Wait for page to load
            
            # Scroll to load content
            self.driver.execute_script("window.scrollTo(0, 1000);")
            time.sleep(2)
            
            # Get page text and parse it directly
            page_text = self.driver.find_element(By.TAG_NAME, 'body').text
            
            # Split into lines and look for transaction patterns
            lines = [line.strip() for line in page_text.split('\n') if line.strip()]
            
            logger.info(f"Parsing {len(lines)} lines of text...")
            
            i = 0
            while i < len(lines):
                line = lines[i]
                
                # Look for lines starting with district and containing property type
                if ('寫字樓' in line or '工商' in line or '商舖' in line) and len(line) > 10:
                    # This might be a transaction line
                    # Pattern: "香港仔 裕輝商業中心寫字樓寫字樓香港仔 裕輝商業中心..."
                    trans = self._extract_from_text(line, lines, i)
                    
                    if trans:
                        # Apply filters
                        trans_date = trans.get('date_obj')
                        area = float(trans.get('area', 0))
                        
                        date_ok = trans_date and start_date <= trans_date <= end_date
                        area_ok = area >= min_area_sqft
                        
                        if date_ok and area_ok:
                            transactions.append(trans)
                            logger.info(f"✓ {trans.get('property', '')} - {area} sqft on {trans_date.date()}")
                
                i += 1
            
            logger.info(f"Completed: Found {len(transactions)} Midland ICI transactions")
            
        except Exception as e:
            logger.error(f"Error scraping Midland ICI: {e}", exc_info=True)
        
        finally:
            if self.driver:
                self.driver.quit()
        
        return transactions
    
    def _extract_from_text(self, line: str, all_lines: list, idx: int) -> Dict:
        """Extract transaction from text line"""
        try:
            # Midland format: "District Property AssetAsset District Property Floor Unit Area Date Source Nature Price @UnitPrice"
            transaction = {
                'source': 'Midland ICI',
                'category': 'Commercial',
                'area_basis': 'GFA',
                'unit_basis': 'sqft',
                'floor': 'N/A',
                'unit': 'N/A'
            }
            
            # District - first word
            parts = line.split()
            if len(parts) > 0:
                transaction['district'] = parts[0]
            
            # Property - after district, before duplicate asset type
            prop_match = re.search(r'^[^\s]+\s+(.+?)(?:寫字樓寫字樓|工商工商|商舖商舖)', line)
            if prop_match:
                transaction['property'] = prop_match.group(1).strip()
            
            # Asset type
            if '寫字樓' in line:
                transaction['asset_type'] = '寫字樓'
            elif '商舖' in line:
                transaction['asset_type'] = '商舖'
            elif '工商' in line or '工廈' in line:
                transaction['asset_type'] = '工廈'
            else:
                transaction['asset_type'] = 'Commercial'
            
            # Floor
            floor_match = re.search(r'(高層|中層|低層|全層|地下|\d+樓)', line)
            if floor_match:
                transaction['floor'] = floor_match.group(1)
            
            # Unit
            unit_match = re.search(r'([A-Z0-9\-,&\(\)]+)室', line)
            if unit_match:
                transaction['unit'] = unit_match.group(1)
            
            # Area
            area_match = re.search(r'([\d,]+)\s*呎', line)
            if area_match:
                transaction['area'] = area_match.group(1).replace(',', '')
                transaction['area_unit'] = transaction['area']
            
            # Date
            date_match = re.search(r'(\d{4}/\d{1,2}/\d{1,2})', line)
            if date_match:
                date_str = date_match.group(1)
                try:
                    date_obj = datetime.strptime(date_str, '%Y/%m/%d')
                    transaction['date'] = date_obj.strftime('%d/%m/%Y')
                    transaction['date_obj'] = date_obj
                except:
                    pass
            
            # Nature
            if '租' in line:
                transaction['nature'] = 'Lease'
            elif '售' in line:
                transaction['nature'] = 'Sales'
            else:
                transaction['nature'] = 'N/A'
            
            # Price
            price_match = re.search(r'\$([\d,\.]+)(?:萬|億)', line)
            if price_match:
                price_str = price_match.group(0)
                transaction['price'] = price_str
                transaction['price_numeric'] = self._parse_price(price_str)
            
            # Unit price
            unit_price_match = re.search(r'@\$([\d,]+)', line)
            if unit_price_match:
                transaction['unit_price'] = unit_price_match.group(1).replace(',', '')
            
            # Only return if we have minimum required fields
            if transaction.get('property') and transaction.get('area') and transaction.get('date_obj'):
                return transaction
            
            return None
            
        except Exception as e:
            logger.debug(f"Error extracting from line: {e}")
            return None
    
    def _parse_price(self, price_str: str) -> str:
        """Parse price to numeric"""
        price_str = price_str.replace('$', '').replace(',', '').strip()
        
        if '億' in price_str:
            num = float(re.sub(r'[^\d.]', '', price_str))
            return str(int(num * 100000000))
        elif '萬' in price_str:
            num = float(re.sub(r'[^\d.]', '', price_str))
            return str(int(num * 10000))
        return price_str
    
    def _parse_area(self, area_str: str) -> float:
        """Parse area to numeric"""
        try:
            return float(area_str.replace(',', ''))
        except:
            return 0.0
