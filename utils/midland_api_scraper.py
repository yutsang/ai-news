#!/usr/bin/env python3
"""
Midland ICI API scraper - fetches commercial property transactions
"""

import requests
import time
from datetime import datetime
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class MidlandAPIScraper:
    """Scraper for Midland ICI commercial transactions using their API"""
    
    def __init__(self):
        self.base_url = "https://data.midlandici.com.hk/search/v1/transaction"
        # Authorization token from the user's browser session
        self.auth_token = "Bearer eyJhbGciOiJSUzI1NiJ9.eyJndWlkIjoiaWNpLUVGZjdZMGxYb1o4czRPYV9GaCIsImlhdCI6MTc2NzU3Nzk4NywiZXhwIjoxODAyMTM3OTg3LCJpc3MiOiJ3d3cubWlkbGFuZGljaS5jb20uaGsifQ.T3vbFMw9uA0xbd5f7XpDXalq1VaxBQ5-POqDTy_-ubFttiMx-h7AmWQ1X8wTYmhSmhmaUvBzo3ksyR2G6RL8Dt2I8SXxGJvIsZoNWbr2o1ks1guIt9im6lu_Mg1NA3igfe4wm6fSJzViocT_l5WH5w34AN-1FmGlNfQ-KQgNC_o"
    
    def fetch_transactions(self, start_date: datetime, end_date: datetime, min_area: int = 2500) -> List[Dict]:
        """Fetch transactions from Midland API"""
        
        all_transactions = []
        page = 1
        max_pages = 100
        
        date_from = start_date.strftime('%Y-%m-%d')
        date_to = end_date.strftime('%Y-%m-%d')
        
        logger.info(f"Fetching Midland transactions: {date_from} to {date_to}, min area: {min_area} sqft")
        
        while page <= max_pages:
            params = {
                'areaFrom': min_area,
                'areaTo': 999999999,
                'currency': 'HKD',
                'dateFrom': date_from,
                'dateTo': date_to,
                'hash': 'true',
                'lang': 'zh-hk',
                'limit': 100,
                'noResultRecomm': 'true',
                'page': page,
                'q': 'WtBkLzAWkvE',
                'sort': 'txDate-desc',
                'txType': 'SL',
                'unit': 'feet'
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
        
        logger.info(f"Retrieved {len(all_transactions)} Midland transactions")
        return all_transactions
    
    def parse_transaction(self, tx: Dict) -> Dict:
        """Parse a transaction from API response"""
        
        # Parse date
        date_str = tx.get('txDate', '')
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        except:
            date_obj = None
        
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
            'date': date_str,
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

