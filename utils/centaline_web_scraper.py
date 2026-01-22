#!/usr/bin/env python3
"""
Centaline web scraper - fetches residential property transactions
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class CentalineWebScraper:
    """Scraper for Centaline residential property transactions"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.driver:
            self.driver.quit()
    
    def fetch_transactions(self, start_date: datetime, end_date: datetime, min_area: int = 2000) -> List[Dict]:
        """Fetch transactions from Centaline website - filter by area >2000 sqft only"""
        
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=600,800')  # Narrower window to trigger mobile UI with district
        
        self.driver = webdriver.Chrome(options=chrome_options)
        
        try:
            url = "https://hk.centanet.com/findproperty/list/transaction"
            logger.info(f"Navigating to Centaline: {url}")
            self.driver.get(url)
            time.sleep(10)  # Wait longer for mobile UI to fully load and render
            
            # Set filters on the website (using tested working approach)
            # 1. Click "30日" to get recent transactions
            try:
                date_btn = self.driver.find_element(By.XPATH, "//button[contains(@class, 'btn-fiter') and contains(@class, 'active')]")
                date_btn.click()
                time.sleep(1)
                option_30 = self.driver.find_element(By.XPATH, "//li//span[text()='30日']")
                option_30.click()
                time.sleep(2)
                logger.info("Selected 30-day filter")
            except Exception as e:
                logger.warning(f"Could not set date filter: {e}")
            
            # 2. Set minimum area filter
            try:
                # Open "更多" popup
                more_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'btn-fiter') and contains(., '更多')]"))
                )
                more_btn.click()
                time.sleep(2)
                logger.info("Opened 更多 popup")
                
                # Find area inputs using working selector
                area_section = self.driver.find_element(By.ID, "moreNSize")
                inputs = area_section.find_elements(By.CSS_SELECTOR, "input.el-input__inner")
                
                if len(inputs) >= 2:
                    # Set minimum area
                    min_input = inputs[0]
                    min_input.clear()
                    min_input.send_keys(str(min_area))
                    time.sleep(1)
                    logger.info(f"Set minimum area to {min_area} sqft")
                    
                    # Click search to apply filters
                    search_btns = self.driver.find_elements(By.XPATH, "//button[contains(@class, 'el-button--text') and contains(., '搜尋')]")
                    for btn in search_btns:
                        if btn.is_displayed():
                            btn.click()
                            logger.info("Applied filters")
                            break
                    
                    time.sleep(5)
            except Exception as e:
                logger.warning(f"Could not set area filter: {e}")
            
            # Scrape all pages (will filter by date and area client-side)
            transactions = self._scrape_all_pages(start_date, end_date)
            
            logger.info(f"Scraped {len(transactions)} Centaline transactions total (before area filter)")
            
            # Debug: show area distribution
            if transactions:
                areas = [int(t.get('area', 0)) for t in transactions]
                logger.info(f"Area range: {min(areas)} - {max(areas)} sqft")
            
            # Filter by minimum area (client-side filter as backup)
            filtered = [t for t in transactions if int(t.get('area', 0)) > min_area]
            
            logger.info(f"Retrieved {len(filtered)} Centaline transactions (> {min_area} sqft, in date range)")
            return filtered
            
        except Exception as e:
            logger.error(f"Error scraping Centaline: {e}")
            return []
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None
    
    def _set_date_range(self, start_date: datetime, end_date: datetime):
        """Set date range to last 30 days"""
        try:
            # Click on the date filter button (3年 -> 30日)
            date_btns = self.driver.find_elements(By.XPATH, "//button[contains(@class, 'btn-fiter')]//span[contains(text(), '30日')]")
            for btn in date_btns:
                if btn.is_displayed():
                    btn.click()
                    time.sleep(1)
                    break
        except:
            pass
    
    def _set_min_area(self, min_area: int):
        """Set minimum area filter"""
        try:
            # Open "更多" popup
            more_btn = self.driver.find_element(By.XPATH, "//button[contains(., '更多')]")
            more_btn.click()
            time.sleep(1)
            
            # Find area inputs
            area_inputs = self.driver.find_elements(By.XPATH, "//div[@id='moreNSize']//input[@type='text']")
            if area_inputs:
                area_inputs[0].clear()
                area_inputs[0].send_keys(str(min_area))
                time.sleep(0.5)
        except:
            pass
    
    def _click_search(self):
        """Click search button"""
        try:
            search_btns = self.driver.find_elements(By.XPATH, "//button[contains(., '搜尋')]")
            for btn in search_btns:
                if btn.is_displayed() and btn.is_enabled():
                    btn.click()
                    time.sleep(3)
                    break
        except:
            pass
    
    def _scrape_all_pages(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Scrape all pages of results"""
        all_transactions = []
        page = 1
        max_pages = 50
        pages_without_results = 0
        
        while page <= max_pages:
            logger.info(f"Scraping Centaline page {page}...")
            page_transactions = self._scrape_current_page(start_date, end_date)
            
            if page_transactions:
                all_transactions.extend(page_transactions)
                pages_without_results = 0
            else:
                pages_without_results += 1
                # Continue for a few more pages even if no results (might have older data)
                if pages_without_results >= 3:
                    logger.info("No results on 3 consecutive pages, stopping")
                    break
            
            # Try to go to next page
            if not self._go_to_next_page():
                break
            
            page += 1
            time.sleep(2)
        
        return all_transactions
    
    def _scrape_current_page(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Scrape transactions from current page"""
        transactions = []
        
        try:
            time.sleep(3)
            page_source = self.driver.page_source
            
            # Save page for debugging (first page only)
            if not hasattr(self, '_page_saved'):
                with open('centaline_debug.html', 'w', encoding='utf-8') as f:
                    f.write(page_source)
                self._page_saved = True
                logger.info("Saved page to centaline_debug.html")
            
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Find transaction rows
            rows = soup.select('tr.cv-structured-list-item')
            
            logger.info(f"Found {len(rows)} transaction rows on page")
            
            # Parse all rows
            for row in rows:
                try:
                    trans = self._parse_transaction_row(row, start_date, end_date)
                    if trans:
                        transactions.append(trans)
                except Exception as e:
                    continue
            
            logger.info(f"Parsed {len(transactions)} valid transactions from {len(rows)} rows")
            
        except Exception as e:
            logger.error(f"Error scraping page: {e}")
        
        return transactions
    
    def _parse_transaction_row(self, row, start_date: datetime, end_date: datetime) -> Optional[Dict]:
        """Parse a single transaction row"""
        cells = row.find_all('td', class_='cv-structured-list-data')
        if len(cells) < 7:
            return None
        
        trans = {
            'source': 'Centaline',  # Main source is Centaline
            'category': 'Residential',
            'nature': 'Sales',  # Default to Sales in English
            'area_unit': '',
            'unit_price': ''
        }
        
        # Date - convert from YYYY-MM-DD to DD/MM/YYYY
        date_span = cells[0].find('span')
        date_str = date_span.get_text(strip=True) if date_span else ''
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            # Allow some flexibility - include up to 1 day after end_date
            # (in case page shows today's data when running on Monday)
            flexible_end = end_date + timedelta(days=1)
            if not (start_date <= date_obj <= flexible_end):
                return None
            trans['date'] = date_obj.strftime('%d/%m/%Y')  # Convert to DD/MM/YYYY
            trans['date_obj'] = date_obj
        except:
            return None
        
        # Property
        property_div = cells[1].find('div', class_='addr')
        property_full = property_div.get('title', property_div.get_text(strip=True)) if property_div else ''
        property_name, floor, unit = self._parse_property_details(property_full)
        trans['property'] = property_name
        trans['floor'] = floor
        trans['unit'] = unit
        
        # Layout (for reference, not used in output)
        layout_div = cells[2].find('div')
        layout = layout_div.get_text(strip=True) if layout_div else ''
        
        # Price
        price_span = cells[3].find('span')
        price_str = price_span.get_text(strip=True) if price_span else '0'
        trans['price'] = self._parse_price(price_str)
        
        # Area
        area_div = cells[4].find('div')
        area_str = area_div.get_text(strip=True) if area_div else ''
        area_match = re.search(r'([\d,]+)呎', area_str)
        if area_match:
            trans['area'] = area_match.group(1).replace(',', '')
            trans['area_unit'] = trans['area']
        else:
            trans['area'] = '0'
            trans['area_unit'] = '0'
        
        # Unit Price
        unit_price_div = cells[5].find('div')
        unit_price_str = unit_price_div.get_text(strip=True) if unit_price_div else ''
        unit_price_match = re.search(r'@\$?([\d,]+)', unit_price_str)
        if unit_price_match:
            trans['unit_price'] = unit_price_match.group(1).replace(',', '')
        else:
            trans['unit_price'] = '0'
        
        # Source info (internal source within Centaline)
        source_span = cells[6].find('span', class_='label')
        source_info = source_span.get_text(strip=True) if source_span else ''
        # Store as additional info, but main source remains 'Centaline'
        trans['source_info'] = source_info
        
        # District - try to extract from district tag in mobile UI
        district = ''
        # Look for district span with various possible selectors
        district_selectors = [
            'span.adress',
            'span.tag-adress', 
            'span[class*="district"]',
            'span[class*="location"]',
            'span[class*="adress"]'
        ]
        
        # Try to find district in the property cell (cells[1])
        for selector in district_selectors:
            district_elem = cells[1].select_one(selector)
            if district_elem:
                district = district_elem.get_text(strip=True)
                logger.info(f"Found district from selector '{selector}': {district}")
                break
        
        # Fallback: extract from property name (first word)
        if not district:
            words = property_name.split()
            district = words[0] if words else ''
        
        trans['district'] = district
        
        # Asset type
        if '洋房' in property_full:
            trans['asset_type'] = '洋房'
        elif '座' in property_full:
            trans['asset_type'] = '住宅'
        else:
            trans['asset_type'] = '住宅'
        
        return trans
    
    def _parse_property_details(self, property_full: str) -> tuple:
        """
        Parse property string into name, floor, unit
        Handles 洋房 (house) cases properly
        """
        property_name = property_full
        floor = ''
        unit = ''
        
        # Check for 洋房 pattern first (e.g., "海灣園 9座 9號 9號洋房", "新德園 57座 1號 57號洋房")
        house_match = re.search(r'(\d+號?)\s*洋房', property_full)
        if house_match:
            floor = '洋房'
            unit = house_match.group(1).replace('號', '')  # Extract number before 洋房
            # Property name is everything before the 洋房 part
            property_name = property_full[:house_match.start()].strip()
            # Remove trailing unit numbers like "9號", "57號"
            property_name = re.sub(r'\s+\d+號$', '', property_name)
            return property_name, floor, unit
        
        # Look for standard floor keywords (for apartments)
        floor_keywords = ['高層', '中層', '低層', '地下', '頂層']
        for keyword in floor_keywords:
            if keyword in property_full:
                idx = property_full.find(keyword)
                property_name = property_full[:idx].strip()
                rest = property_full[idx:].strip()
                
                # Extract floor and unit
                rest_parts = rest.split()
                if rest_parts:
                    floor = rest_parts[0]
                    if len(rest_parts) > 1:
                        unit_part = rest_parts[1]
                        # Extract just the letter/number from unit (remove 室)
                        unit = unit_part.replace('室', '')
                break
        
        # Look for explicit floor numbers (e.g., "20樓")
        if not floor:
            floor_match = re.search(r'(\d+樓)', property_full)
            if floor_match:
                floor = floor_match.group(1)
                property_name = property_full[:floor_match.start()].strip()
                
                # Look for unit after floor
                unit_match = re.search(r'(\d+樓)\s*([A-Z]\d*|[A-Z]室)', property_full)
                if unit_match:
                    unit = unit_match.group(2).replace('室', '')
        
        return property_name, floor, unit
    
    def _parse_price(self, price_str: str) -> str:
        """Parse price string to integer"""
        # Remove $ and commas
        price_str = price_str.replace('$', '').replace(',', '')
        
        # Handle 萬 (10,000) and 億 (100,000,000)
        if '億' in price_str:
            num = float(re.sub(r'[^0-9.]', '', price_str))
            return str(int(num * 100000000))
        elif '萬' in price_str:
            num = float(re.sub(r'[^0-9.]', '', price_str))
            return str(int(num * 10000))
        else:
            return price_str
    
    def _go_to_next_page(self) -> bool:
        """Navigate to next page"""
        try:
            next_btn = self.driver.find_element(By.CSS_SELECTOR, "i.el-icon-arrow-right")
            parent_btn = next_btn.find_element(By.XPATH, "..")
            
            if 'is-disabled' not in parent_btn.get_attribute('class'):
                parent_btn.click()
                time.sleep(2)
                return True
        except:
            pass
        
        return False

