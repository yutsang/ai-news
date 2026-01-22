#!/usr/bin/env python3
"""
Midland ICI API scraper - fetches commercial property transactions
Automatically retrieves authorization token using ChromeDriver
"""

import requests
import time
from datetime import datetime
from typing import List, Dict, Optional
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json

logger = logging.getLogger(__name__)


class MidlandAPIScraper:
    """Scraper for Midland ICI commercial transactions using their API"""
    
    def __init__(self):
        self.base_url = "https://data.midlandici.com.hk/search/v1/transaction"
        self.auth_token = None
    
    def _get_auth_token_from_browser(self) -> Optional[str]:
        """
        Automatically retrieve authorization token using Selenium
        Opens Midland website and extracts token from browser session
        """
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Enable performance logging to capture network requests
        chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
        
        driver = None
        try:
            driver = webdriver.Chrome(options=chrome_options)
            logger.info("Opening Midland ICI website to retrieve auth token...")
            
            # Navigate to Midland ICI
            driver.get("https://www.midlandici.com.hk/")
            time.sleep(5)  # Wait for page load
            
            # Try to get token from localStorage or sessionStorage
            try:
                token = driver.execute_script("""
                    // Try to find token in various storage locations
                    return localStorage.getItem('auth_token') || 
                           localStorage.getItem('token') ||
                           sessionStorage.getItem('auth_token') ||
                           sessionStorage.getItem('token');
                """)
                if token:
                    logger.info("Found token in browser storage")
                    return f"Bearer {token}" if not token.startswith('Bearer') else token
            except:
                pass
            
            # If not in storage, trigger a search to generate API call
            try:
                # Click on transaction search or any action that triggers the API
                search_btn = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'transaction') or contains(text(), '成交')]"))
                )
                driver.execute_script("arguments[0].click();", search_btn)
                time.sleep(3)
            except:
                logger.warning("Could not trigger search, attempting to extract from network logs")
            
            # Extract token from network logs
            logs = driver.get_log('performance')
            for entry in logs:
                try:
                    log = json.loads(entry['message'])['message']
                    if log.get('method') == 'Network.requestWillBeSent':
                        request = log.get('params', {}).get('request', {})
                        headers = request.get('headers', {})
                        
                        # Check if this is a Midland API request
                        url = request.get('url', '')
                        if 'midlandici.com.hk' in url and 'transaction' in url:
                            auth_header = headers.get('Authorization') or headers.get('authorization')
                            if auth_header and 'Bearer' in auth_header:
                                logger.info("Extracted auth token from network request")
                                return auth_header
                except:
                    continue
            
            logger.warning("Could not extract auth token from browser")
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving auth token: {e}")
            return None
        finally:
            if driver:
                driver.quit()
    
    def fetch_transactions(self, start_date: datetime, end_date: datetime, min_area: int = 2500) -> List[Dict]:
        """Fetch transactions from Midland API"""
        
        # Get fresh authorization token
        if not self.auth_token:
            print("  → Retrieving Midland API authorization token...")
            self.auth_token = self._get_auth_token_from_browser()
            
            if not self.auth_token:
                logger.error("Failed to retrieve Midland auth token")
                print("  ⚠️  Could not retrieve Midland authorization token")
                print("  → Skipping Midland API data")
                return []
            else:
                print("  ✓ Authorization token retrieved successfully")
        
        all_transactions = []
        page = 1
        max_pages = 100
        
        # Try multiple date formats to see which one works
        # Format 1: YYYY-MM-DD (standard ISO)
        date_from_iso = start_date.strftime('%Y-%m-%d')
        date_to_iso = end_date.strftime('%Y-%m-%d')
        
        # Format 2: Unix timestamp
        date_from_ts = int(start_date.timestamp() * 1000)  # Milliseconds
        date_to_ts = int(end_date.timestamp() * 1000)
        
        logger.info(f"Fetching Midland transactions: {date_from_iso} to {date_to_iso}, min area: {min_area} sqft")
        print(f"  → Requesting Midland API: dateFrom={date_from_iso}, dateTo={date_to_iso}")
        
        while page <= max_pages:
            # Simplified parameters - only essentials
            params = {
                'areaFrom': min_area,
                'dateFrom': date_from_iso,
                'dateTo': date_to_iso,
                'limit': 100,
                'page': page,
                'sort': 'txDate-desc',
                'txType': 'SL',
                'unit': 'feet',
                'lang': 'zh-hk'
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
                'Authorization': self.auth_token,
                'Referer': 'https://www.midlandici.com.hk/',
                'Origin': 'https://www.midlandici.com.hk'
            }
            
            try:
                # Debug: Show actual request URL on first page
                if page == 1:
                    from urllib.parse import urlencode
                    query_str = urlencode(params)
                    full_url = f"{self.base_url}?{query_str}"
                    print(f"  → API URL: {full_url[:120]}...")
                
                response = requests.get(self.base_url, params=params, headers=headers, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                # Handle list response with wrapper
                if isinstance(data, list) and data:
                    first_item = data[0]
                    if isinstance(first_item, dict) and 'results' in first_item:
                        results = first_item['results']
                        total_count = first_item.get('count', 0)
                        
                        if page == 1:
                            logger.info(f"Found {total_count} Midland transactions")
                        
                        if results:
                            all_transactions.extend(results)
                            
                            if len(all_transactions) >= total_count:
                                break
                        else:
                            break
                    else:
                        break
                else:
                    break
                    
                page += 1
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error fetching Midland page {page}: {e}")
                break
        
        logger.info(f"Retrieved {len(all_transactions)} Midland transactions from API")
        
        # Debug: Show actual date range returned by API
        if all_transactions:
            dates = []
            for tx in all_transactions[:10]:  # Check first 10
                dates.append(tx.get('txDate', 'N/A'))
            print(f"  → API returned dates (first 10): {', '.join(dates[:5])}...")
        
        # Client-side date filtering (API doesn't always respect date params)
        filtered_transactions = []
        out_of_range_count = 0
        
        for tx in all_transactions:
            tx_date_str = tx.get('txDate', '')
            try:
                tx_date = datetime.strptime(tx_date_str, '%Y-%m-%d')
                # Only keep transactions within the requested date range
                if start_date <= tx_date <= end_date:
                    filtered_transactions.append(tx)
                else:
                    out_of_range_count += 1
            except:
                # If date parsing fails, skip this transaction
                out_of_range_count += 1
                continue
        
        if out_of_range_count > 0:
            print(f"  ⚠️  WARNING: API returned {out_of_range_count} transactions OUTSIDE requested range!")
            print(f"  → Kept {len(filtered_transactions)} transactions within {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # If API returns NO data in the requested range, it might be an API issue
        if len(filtered_transactions) == 0 and len(all_transactions) > 0:
            print(f"  ⚠️  API returned {len(all_transactions)} transactions but NONE in your date range!")
            print(f"  → This suggests the Midland API is not respecting date parameters")
            print(f"  → Keeping all transactions from API as fallback")
            return all_transactions  # Return all data as fallback
        
        return filtered_transactions
    
    def parse_transaction(self, tx: Dict) -> Dict:
        """Parse a transaction from API response"""
        
        # Parse date - convert to dd/mm/yyyy format
        date_str = tx.get('txDate', '')
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%d/%m/%Y')
        except:
            date_obj = None
            formatted_date = date_str
        
        # Property name
        property_name = tx.get('name', '')
        if not property_name:
            building = tx.get('building', {})
            property_name = building.get('name', '') if isinstance(building, dict) else ''
        
        # District
        district_data = tx.get('district', {})
        district = district_data.get('name', '') if isinstance(district_data, dict) else ''
        
        # Floor
        floor = tx.get('floor', '')
        if floor == '**MID**':
            floor = '中層'
        elif floor == '**HIGH**':
            floor = '高層'
        elif floor == '**LOW**':
            floor = '低層'
        elif not floor or floor == 'null':
            floor = ''
        
        # Unit
        unit = tx.get('flat', '') or ''
        
        # Asset type
        sbu_owner = tx.get('sbuOwner', 'COMMERCIAL')
        if sbu_owner == 'INDUSTRIAL':
            asset_type = '工商'
        elif sbu_owner == 'OFFICE':
            asset_type = '寫字樓'
        elif sbu_owner == 'SHOP':
            asset_type = '舖位'
        else:
            asset_type = '工商'
        
        # Area
        area_data = tx.get('area', {})
        area = area_data.get('value', 0) if isinstance(area_data, dict) else (area_data or 0)
        
        # Price
        tx_type = tx.get('txType', 'S')
        if tx_type == 'L':  # Lease
            price = tx.get('rent', 0) or 0
            unit_price = tx.get('ftRent', 0) or 0
            nature = '租'
        else:  # Sales
            price = tx.get('price', 0) or 0
            unit_price = tx.get('ftPrice', 0) or 0
            nature = '售'
        
        # Source info (where the data came from)
        upload_source = tx.get('uploadSource', 'N/A')
        if upload_source == 'MARKET_INFO':
            source_info = '市場資訊'
        elif upload_source == 'LAND_REGISTRY':
            source_info = '土地註冊處'
        else:
            source_info = 'N/A'
        
        return {
            'date': formatted_date,
            'date_obj': date_obj,
            'district': district,
            'property': property_name,
            'floor': floor,
            'unit': unit,
            'asset_type': asset_type,
            'area': str(int(area)) if area else '0',
            'area_unit': str(int(area)) if area else '0',
            'price': str(int(price)) if price else '0',
            'unit_price': str(int(unit_price)) if unit_price else '0',
            'nature': nature,
            'source': 'Midland',  # Main source is Midland
            'source_info': source_info,  # Additional info about data origin
            'category': 'Commercial'
        }

