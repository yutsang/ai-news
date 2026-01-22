#!/usr/bin/env python3
"""
Midland ICI Web API Scraper
Opens the Midland website with Selenium, captures the actual API call,
and replicates it to get correct data
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
import json
import requests
from datetime import datetime
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class MidlandWebAPIScraper:
    """
    Scraper for Midland ICI that captures the actual API call from the website
    This ensures we use the exact parameters that work
    """
    
    def __init__(self):
        self.base_url = "https://data.midlandici.com.hk/search/v1/transaction"
        self.website_url = "https://www.midlandici.com.hk/transaction"
        self.auth_token = None
        self.api_params = None
    
    def _capture_api_call_from_website(self, start_date: datetime, end_date: datetime) -> bool:
        """
        Open Midland website and capture the actual API call it makes
        Returns True if successful
        """
        chrome_options = Options()
        # Run in visible mode for better reliability
        # chrome_options.add_argument('--headless')  # Disabled for better capture
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1280,1024')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        
        # Enable performance logging to capture network requests
        chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL', 'browser': 'ALL'})
        
        driver = None
        try:
            driver = webdriver.Chrome(options=chrome_options)
            logger.info("Opening Midland website to capture API call...")
            print("  → Opening Midland ICI website...")
            
            # Navigate to transaction search page
            driver.get(self.website_url)
            print("  → Waiting for page to load...")
            time.sleep(8)  # Wait longer for initial load
            
            # Wait for page to fully load by checking for specific elements
            try:
                WebDriverWait(driver, 15).until(
                    lambda d: d.execute_script('return document.readyState') == 'complete'
                )
                print("  → Page loaded, waiting for API calls...")
                time.sleep(5)  # Wait for API calls to complete
            except:
                pass
            
            # The page should have made API calls by now
            # Try to trigger a refresh/new search to generate more API calls
            try:
                # Try to find and interact with search or filter elements
                # Look for common search/filter buttons
                search_elements = driver.find_elements(By.XPATH, 
                    "//button[contains(@class, 'search') or contains(@class, 'btn') or contains(text(), '搜')]"
                )
                
                if search_elements:
                    for elem in search_elements:
                        try:
                            if elem.is_displayed():
                                print("  → Triggering search to capture API call...")
                                driver.execute_script("arguments[0].click();", elem)
                                time.sleep(4)
                                break
                        except:
                            continue
            except Exception as e:
                logger.debug(f"Could not trigger search: {e}")
            
            # Give it more time to capture requests
            time.sleep(2)
            
            # Extract API call from performance logs
            print("  → Analyzing network requests...")
            logs = driver.get_log('performance')
            
            transaction_requests = []
            
            for entry in logs:
                try:
                    log = json.loads(entry['message'])['message']
                    
                    # Look for API request
                    if log.get('method') == 'Network.requestWillBeSent':
                        request = log.get('params', {}).get('request', {})
                        url = request.get('url', '')
                        
                        # Check if this is the transaction API
                        if 'midlandici.com.hk' in url and 'transaction' in url:
                            transaction_requests.append((url, request))
                
                except Exception as e:
                    continue
            
            print(f"  → Found {len(transaction_requests)} transaction API calls")
            
            # Process the most recent transaction API call
            if transaction_requests:
                url, request = transaction_requests[-1]  # Use last one (most recent)
                headers = request.get('headers', {})
                
                # Extract authorization token
                auth = headers.get('Authorization') or headers.get('authorization')
                if auth and 'Bearer' in auth:
                    self.auth_token = auth
                    logger.info("✓ Captured authorization token from website")
                    print("  ✓ Authorization token captured")
                
                # Extract query parameters from URL
                if '?' in url:
                    query_string = url.split('?')[1]
                    # Handle URL-encoded parameters
                    from urllib.parse import parse_qs, unquote
                    params_dict = parse_qs(query_string)
                    
                    # Convert from lists to single values
                    params = {k: v[0] if isinstance(v, list) else v for k, v in params_dict.items()}
                    
                    self.api_params = params
                    logger.info(f"✓ Captured API parameters: {len(params)} params")
                    print(f"  ✓ Captured {len(params)} API parameters from website")
                    
                    # Show key parameters for debugging
                    for key in ['dateFrom', 'dateTo', 'areaFrom', 'sort', 'limit']:
                        if key in params:
                            print(f"    - {key}: {params[key]}")
                    
                    return True
                else:
                    # No query string, check if params in request body
                    post_data = request.get('postData', '')
                    if post_data:
                        try:
                            params = json.loads(post_data)
                            self.api_params = params
                            print(f"  ✓ Captured {len(params)} API parameters from POST body")
                            return True
                        except:
                            pass
            
            logger.warning("Could not capture API call details from website")
            print("  ✗ Could not capture complete API parameters")
            return False
            
        except Exception as e:
            logger.error(f"Error capturing API call: {e}")
            return False
        finally:
            if driver:
                driver.quit()
    
    def fetch_transactions(self, start_date: datetime, end_date: datetime, min_area: int = 2500) -> List[Dict]:
        """Fetch transactions using captured API parameters from website"""
        
        print("  → Capturing API call from Midland website...")
        
        # First, capture the actual API call the website makes
        success = self._capture_api_call_from_website(start_date, end_date)
        
        if not success or not self.auth_token:
            logger.error("Failed to capture API call from website")
            print("  ✗ Could not capture API parameters")
            return []
        
        # Use captured parameters, but override date range to ensure correctness
        date_from = start_date.strftime('%Y-%m-%d')
        date_to = end_date.strftime('%Y-%m-%d')
        
        # Build params - use captured params as base, then override key ones
        params = self.api_params.copy() if self.api_params else {}
        
        # Override/ensure critical parameters
        params.update({
            'areaFrom': str(min_area),
            'areaTo': '999999999',
            'dateFrom': date_from,
            'dateTo': date_to,
            'limit': '100',
            'page': '1',
            'sort': 'txDate-desc',
            'txType': 'SL',
            'unit': 'feet'
        })
        
        all_transactions = []
        page = 1
        max_pages = 100
        
        logger.info(f"Fetching with captured parameters: {date_from} to {date_to}")
        print(f"  → Fetching transactions with website's API format...")
        
        while page <= max_pages:
            params['page'] = str(page)
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
                'Authorization': self.auth_token,
                'Referer': 'https://www.midlandici.com.hk/',
                'Origin': 'https://www.midlandici.com.hk'
            }
            
            try:
                response = requests.get(self.base_url, params=params, headers=headers, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                # Handle response
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
        
        # Debug: Show actual date range
        if all_transactions:
            dates = []
            for tx in all_transactions[:10]:
                dates.append(tx.get('txDate', 'N/A'))
            print(f"  → API returned dates (sample): {', '.join(dates[:5])}...")
        
        # Client-side date filtering
        filtered_transactions = []
        out_of_range_count = 0
        
        for tx in all_transactions:
            tx_date_str = tx.get('txDate', '')
            try:
                tx_date = datetime.strptime(tx_date_str, '%Y-%m-%d')
                if start_date <= tx_date <= end_date:
                    filtered_transactions.append(tx)
                else:
                    out_of_range_count += 1
            except:
                out_of_range_count += 1
                continue
        
        if out_of_range_count > 0:
            print(f"  ⚠️  API returned {out_of_range_count} transactions outside range")
            print(f"  → Kept {len(filtered_transactions)} within {date_from} to {date_to}")
        else:
            print(f"  ✓ All {len(filtered_transactions)} transactions within requested range")
        
        # Fallback if nothing in range
        if len(filtered_transactions) == 0 and len(all_transactions) > 0:
            print(f"  ⚠️  No transactions in requested range - using all {len(all_transactions)} from API")
            return all_transactions
        
        return filtered_transactions
    
    def parse_transaction(self, tx: Dict) -> Dict:
        """Parse a transaction from API response (same as original)"""
        
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
        
        # Source info
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
            'source': 'Midland',
            'source_info': source_info,
            'category': 'Commercial'
        }


if __name__ == "__main__":
    # Test
    from datetime import datetime, timedelta
    
    scraper = MidlandWebAPIScraper()
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    transactions = scraper.fetch_transactions(start_date, end_date, min_area=2500)
    
    print(f"\nFound {len(transactions)} transactions")
    if transactions:
        # Parse and show first few
        for i, tx in enumerate(transactions[:3]):
            parsed = scraper.parse_transaction(tx)
            print(f"\n{i+1}. {parsed['property']}")
            print(f"   Date: {parsed['date']}, Area: {parsed['area']} sqft")
