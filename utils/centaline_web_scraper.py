#!/usr/bin/env python3
"""
Centaline web scraper - fetches residential property transactions
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
import yaml
from .ai_helper import AIHelper
from .browser_utils import create_driver

logger = logging.getLogger(__name__)


class CentalineWebScraper:
    """Scraper for Centaline residential property transactions"""
    
    def __init__(self, headless: bool = True, config_path: str = "config.yml"):
        self.headless = headless
        self.driver = None
        
        # Initialize AI helper for district extraction
        try:
            self.ai_helper = AIHelper(config_path)
            self.ai_enabled = self.ai_helper.ai_enabled
        except Exception as e:
            logger.warning(f"Could not initialize AI helper: {e}")
            self.ai_helper = None
            self.ai_enabled = False
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.driver:
            self.driver.quit()
    
    def fetch_transactions(self, start_date: datetime, end_date: datetime, min_area: int = 2000) -> List[Dict]:
        """Fetch transactions from Centaline website - filter by area >2000 sqft only"""
        
        driver_args = [
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--window-size=1920,1080',
            '--disable-blink-features=AutomationControlled',
        ]
        if self.headless:
            driver_args.append('--headless')

        self.driver = create_driver(
            args=driver_args,
            experimental={
                'excludeSwitches': ['enable-automation'],
                'useAutomationExtension': False,
            },
        )
        
        try:
            url = "https://hk.centanet.com/findproperty/list/transaction"
            logger.info(f"Navigating to Centaline: {url}")
            self.driver.get(url)
            
            # Wait for page to load completely
            logger.info("Waiting for page to load...")
            time.sleep(8)
            
            # Set area filter using UI (server-side filtering is more efficient)
            logger.info(f"Setting area filter to >= {min_area} sqft...")
            
            try:
                # 1. Click "更多" (More) button
                more_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'btn-fiter') and contains(., '更多')]"))
                )
                more_btn.click()
                logger.info("✓ Clicked '更多' button")
                
                # Wait for popup to appear and settle
                time.sleep(4)
                
                # 2. Find the area input in #moreNSize section
                # Wait for the moreNSize section to be present
                area_section = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "moreNSize"))
                )
                logger.info("✓ Found #moreNSize section")
                
                # Find the first input in moreNSize section (this is the minimum area input)
                area_inputs = area_section.find_elements(By.CSS_SELECTOR, "input.el-input__inner[role='spinbutton']")
                
                if not area_inputs:
                    logger.warning("No spinbutton inputs found in #moreNSize")
                    raise Exception("No area inputs found")
                
                # The first input is the minimum area
                min_area_input = area_inputs[0]
                logger.info(f"✓ Found area input (max={min_area_input.get_attribute('max')})")
                
                # Wait for input to be interactable
                WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable(min_area_input)
                )
                logger.info("✓ Input is interactable")
                
                # 3. Clear and enter the minimum area
                min_area_input.click()  # Click first to focus
                time.sleep(0.5)
                min_area_input.clear()
                time.sleep(0.5)
                min_area_input.send_keys(str(min_area))
                time.sleep(1)
                logger.info(f"✓ Entered {min_area} in area filter")
                
                # 4. Click "搜尋" (Search) button
                # The search button is in the popup, find all search buttons
                logger.info("Looking for '搜尋' button...")
                search_btns = self.driver.find_elements(By.XPATH, "//button[contains(., '搜尋')]")
                logger.info(f"Found {len(search_btns)} buttons containing '搜尋'")
                
                # Find the visible one
                clicked = False
                for btn in search_btns:
                    try:
                        if btn.is_displayed() and btn.is_enabled():
                            btn.click()
                            logger.info("✓ Clicked '搜尋' button (regular click)")
                            clicked = True
                            break
                    except:
                        # Try JavaScript click
                        try:
                            self.driver.execute_script("arguments[0].click();", btn)
                            logger.info("✓ Clicked '搜尋' button (JavaScript)")
                            clicked = True
                            break
                        except:
                            continue
                
                if not clicked:
                    logger.warning("Could not click any '搜尋' button")
                    raise Exception("Search button not clickable")
                
                # Wait for filtered results to load
                logger.info("Waiting for filtered results...")
                time.sleep(8)
                    
            except Exception as e:
                logger.warning(f"Could not set area filter: {e}")
                logger.info("Continuing without filter...")
            
            # Scrape all pages (will filter by date and area client-side)
            transactions = self._scrape_all_pages(start_date, end_date)
            
            logger.info(f"Scraped {len(transactions)} Centaline transactions total (before area filter)")
            
            # Debug: show area distribution
            if transactions:
                areas = [int(t.get('area', 0)) for t in transactions if t.get('area') and t.get('area') != '0']
                if areas:
                    logger.info(f"Area range: {min(areas)} - {max(areas)} sqft")
            
            # Filter by minimum area (client-side filter)
            filtered = [t for t in transactions if int(t.get('area', 0)) >= min_area]
            
            logger.info(f"Retrieved {len(filtered)} Centaline transactions (>= {min_area} sqft, in date range)")
            
            # Fill districts using AI
            if filtered and self.ai_enabled:
                filtered = self._fill_districts_with_ai(filtered)
                
                # Print warning to user
                print("\n" + "⚠️ " * 40)
                print("⚠️  WARNING: AI-GENERATED DISTRICT DATA")
                print("⚠️ " * 40)
                print(f"\n⚠️  Centaline scraper retrieved {len(filtered)} transactions.")
                print(f"⚠️  Districts have been AUTOMATICALLY EXTRACTED using AI from property names.")
                print(f"⚠️  ")
                print(f"⚠️  ⚠️  PLEASE DOUBLE-CHECK DISTRICT DATA IN THE OUTPUT FILE!")
                print(f"⚠️  ")
                print(f"⚠️  All Centaline records in Trans_Commercial sheet have AI-generated districts.")
                print("⚠️ " * 40 + "\n")
            
            return filtered
            
        except Exception as e:
            logger.error(f"Error scraping Centaline: {e}")
            return []
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None
    
    def _scrape_all_pages(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Scrape all pages of results"""
        all_transactions = []
        page = 1
        max_pages = 10  # Limit to first 10 pages for residential (enough for recent data)
        pages_without_results = 0
        pages_with_old_data = 0  # Track consecutive pages with only old data
        
        while page <= max_pages:
            logger.info(f"Scraping Centaline page {page}...")
            page_transactions = self._scrape_current_page(start_date, end_date)
            
            if page_transactions:
                all_transactions.extend(page_transactions)
                pages_without_results = 0
                pages_with_old_data = 0
            else:
                pages_without_results += 1
                # If we get no results at all on 3 consecutive pages, stop
                if pages_without_results >= 3:
                    logger.info("No results on 3 consecutive pages, stopping")
                    break
            
            # Check if we're getting only old data (before start_date)
            if page_transactions:
                recent_count = sum(1 for t in page_transactions if t.get('date_obj') and t['date_obj'] >= start_date)
                if recent_count == 0:
                    pages_with_old_data += 1
                    if pages_with_old_data >= 2:
                        logger.info("2 consecutive pages with only old data, stopping")
                        break
            
            # Try to go to next page
            if not self._go_to_next_page():
                logger.info("Cannot go to next page, stopping")
                break
            
            page += 1
            time.sleep(3)  # Longer delay to avoid rate limiting
        
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
        
        # Cell[3] is floor plan icon (empty), skip it
        
        # Price (Cell[4])
        price_span = cells[4].find('span')
        price_str = price_span.get_text(strip=True) if price_span else '0'
        trans['price'] = self._parse_price(price_str)
        
        # Area (Cell[5])
        area_div = cells[5].find('div')
        area_str = area_div.get_text(strip=True) if area_div else ''
        area_match = re.search(r'([\d,]+)呎', area_str)
        if area_match:
            trans['area'] = area_match.group(1).replace(',', '')
            trans['area_unit'] = trans['area']
        else:
            trans['area'] = '0'
            trans['area_unit'] = '0'
        
        # Unit Price (Cell[6])
        unit_price_div = cells[6].find('div')
        unit_price_str = unit_price_div.get_text(strip=True) if unit_price_div else ''
        unit_price_match = re.search(r'@\$?([\d,]+)', unit_price_str)
        if unit_price_match:
            trans['unit_price'] = unit_price_match.group(1).replace(',', '')
        else:
            trans['unit_price'] = '0'
        
        # Source info (Cell[8] - internal source within Centaline)
        source_span = cells[8].find('span', class_='label') if len(cells) > 8 else None
        source_info = source_span.get_text(strip=True) if source_span else ''
        # Store as additional info, but main source remains 'Centaline'
        trans['source_info'] = source_info
        
        # District - Centaline website doesn't show district in table
        # We'll leave it as N/A for now - can be filled in later by AI or manual mapping
        # NOTE: The old fallback of using first word of property name was incorrect
        trans['district'] = 'N/A'
        
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
    
    def _extract_district_with_ai(self, property_name: str) -> str:
        """
        Use AI to extract district from property name
        
        Args:
            property_name: Full property name
            
        Returns:
            District name or 'N/A' if cannot determine
        """
        if not self.ai_enabled or not property_name or not self.ai_helper:
            return 'N/A'
        
        return self.ai_helper.extract_district(property_name)
    
    def _fill_districts_with_ai(self, transactions: List[Dict]) -> List[Dict]:
        """
        Fill missing districts using AI for all transactions
        
        Args:
            transactions: List of transactions with district='N/A'
            
        Returns:
            Transactions with AI-filled districts
        """
        if not self.ai_enabled:
            return transactions
        
        logger.info(f"Using AI to extract districts for {len(transactions)} transactions...")
        
        for trans in transactions:
            if trans.get('district') == 'N/A' or not trans.get('district'):
                property_name = trans.get('property', '')
                if property_name:
                    district = self._extract_district_with_ai(property_name)
                    trans['district'] = district
                    trans['district_ai_generated'] = True  # Flag for user to verify
        
        return transactions
    
    def _go_to_next_page(self) -> bool:
        """Navigate to next page"""
        try:
            # Try to find the next page button
            next_btn = self.driver.find_element(By.CSS_SELECTOR, "i.el-icon-arrow-right")
            parent_btn = next_btn.find_element(By.XPATH, "..")
            
            # Check if button is disabled
            parent_class = parent_btn.get_attribute('class') or ''
            if 'is-disabled' in parent_class or 'disabled' in parent_class:
                logger.info("Next button is disabled - no more pages")
                return False
            
            # Scroll button into view and use JavaScript to click (more reliable)
            self.driver.execute_script("arguments[0].scrollIntoView(true);", parent_btn)
            time.sleep(0.5)
            self.driver.execute_script("arguments[0].click();", parent_btn)
            logger.info("Clicked next page button (via JavaScript)")
            time.sleep(4)  # Wait longer for page to load
            return True
            
        except Exception as e:
            logger.warning(f"Could not find/click next page button: {type(e).__name__}")
            return False

