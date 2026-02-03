#!/usr/bin/env python3
"""
28hse.com New Property Scraper
Scrapes new property launches from https://www.28hse.com/new-properties/
"""

import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
from typing import List, Dict
import logging
import time

logger = logging.getLogger(__name__)


class NewPropertyScraper:
    """Scraper for new property launches from 28hse.com"""
    
    def __init__(self):
        self.base_url = "https://www.28hse.com/new-properties/"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    def fetch_new_properties(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """
        Fetch new properties launched within date range
        
        Args:
            start_date: Start date for filtering price list dates
            end_date: End date for filtering
            
        Returns:
            List of new property dictionaries
        """
        logger.info(f"Fetching new properties from {start_date.date()} to {end_date.date()}")
        
        properties = []
        
        try:
            # Fetch main listing page
            response = requests.get(self.base_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all property items
            property_items = soup.find_all('div', class_='newprop_items')
            logger.info(f"Found {len(property_items)} property listings on page 1")
            
            # Process each property
            for item in property_items:
                try:
                    prop_data = self._extract_property_summary(item)
                    if prop_data:
                        # Fetch detail page to check price list dates
                        detail_data = self._fetch_property_details(prop_data['url'], start_date, end_date)
                        
                        if detail_data:
                            # Merge summary and detail data
                            prop_data.update(detail_data)
                            properties.append(prop_data)
                            logger.info(f"✓ {prop_data['name']} - {prop_data['latest_price_list_date']}")
                
                except Exception as e:
                    logger.debug(f"Error processing property item: {e}")
                    continue
            
            logger.info(f"Retrieved {len(properties)} new properties with price lists in date range")
            
        except Exception as e:
            logger.error(f"Error fetching new properties: {e}")
        
        return properties
    
    def _extract_property_summary(self, item) -> Dict:
        """Extract summary data from property list item"""
        try:
            data = {}
            
            # Property name and URL
            header_link = item.find('a', class_='header')
            if header_link:
                data['name'] = header_link.text.strip()
                data['url'] = header_link.get('href', '')
            else:
                return None
            
            # District and address from meta div
            meta_div = item.find('div', class_='meta')
            if meta_div:
                meta_text = meta_div.get_text(strip=True)
                # Split by whitespace or newlines
                parts = [p.strip() for p in meta_text.split('\n') if p.strip()]
                if len(parts) >= 2:
                    data['district'] = parts[0].strip()
                    data['address'] = parts[1].strip()
                elif len(parts) == 1:
                    # Try splitting by comma or space
                    if ',' in parts[0]:
                        district, address = parts[0].split(',', 1)
                        data['district'] = district.strip()
                        data['address'] = address.strip()
                    else:
                        data['district'] = parts[0].strip()
                        data['address'] = ''
            
            # Status and units from description
            desc_div = item.find('div', class_='description')
            if desc_div:
                desc_text = desc_div.get_text(strip=True)
                # Extract status (開售中, 等待新價單, 已售罄)
                for status in ['開售中', '等待新價單', '已售罄']:
                    if status in desc_text:
                        data['status'] = status
                        break
                
                # Extract units (e.g., "775伙")
                units_match = re.search(r'(\d+)伙', desc_text)
                if units_match:
                    data['units'] = units_match.group(1)
            
            # Developer from extra labels
            extra_div = item.find('div', class_='extra')
            if extra_div:
                developer_labels = extra_div.find_all('div', class_='label')
                developers = []
                for label in developer_labels:
                    text = label.text.strip()
                    # Skip non-developer labels
                    if not any(skip in text for skip in ['年入伙', '張價單', '伙']):
                        developers.append(text)
                
                if developers:
                    data['developer'] = ', '.join(developers)
            
            # Price range from right floated description
            right_desc = item.find('div', class_='right floated description')
            if right_desc:
                value_div = right_desc.find('div', class_='value')
                if value_div:
                    price_text = value_div.get_text(strip=True)
                    # Extract price range (e.g., "10,018 - 12,476")
                    price_match = re.search(r'([\d,]+)\s*-\s*([\d,]+)', price_text)
                    if price_match:
                        data['price_min'] = price_match.group(1).replace(',', '')
                        data['price_max'] = price_match.group(2).replace(',', '')
            
            return data
            
        except Exception as e:
            logger.debug(f"Error extracting property summary: {e}")
            return None
    
    def _fetch_property_details(self, url: str, start_date: datetime, end_date: datetime) -> Dict:
        """
        Fetch property details page and extract price list dates
        
        Args:
            url: Property detail page URL
            start_date: Start date for filtering
            end_date: End date for filtering
            
        Returns:
            Dict with latest_price_list_date if in range, or None if out of range
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the price list table
            price_table = soup.find('table', class_='ui single line very basic selectable table')
            if not price_table:
                return None
            
            # Find all price list rows (價單 rows)
            rows = price_table.find_all('tr', class_='download_pricelist_pdf')
            
            if not rows:
                return None
            
            # Check dates in price lists
            latest_date = None
            for row in rows:
                # Find date column (second td)
                tds = row.find_all('td')
                if len(tds) >= 2:
                    date_text = tds[1].get_text(strip=True)
                    
                    # Parse date (format: YYYY-MM-DD)
                    try:
                        date_obj = datetime.strptime(date_text, '%Y-%m-%d')
                        
                        # Check if in range
                        if start_date <= date_obj <= end_date:
                            if latest_date is None or date_obj > latest_date:
                                latest_date = date_obj
                    except:
                        continue
            
            # Only return if we found a date in range
            if latest_date:
                return {
                    'latest_price_list_date': latest_date.strftime('%d/%m/%Y'),
                    'date_obj': latest_date
                }
            else:
                return None
                
        except Exception as e:
            logger.debug(f"Error fetching property details from {url}: {e}")
            return None


if __name__ == "__main__":
    # Test the scraper
    from datetime import timedelta
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    scraper = NewPropertyScraper()
    properties = scraper.fetch_new_properties(start_date, end_date)
    
    print(f"\nFound {len(properties)} new properties")
    for prop in properties[:5]:
        print(f"\n{prop}")
