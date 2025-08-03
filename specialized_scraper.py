#!/usr/bin/env python3
"""
Specialized scraper for Hong Kong real estate market data from specific sources
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import time
import re
import logging
from urllib.parse import urljoin, urlparse
import json
import httpx
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from config import AI_CONFIG

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SpecializedMarketScraper:
    def __init__(self):
        self.async_session = None
        self.ai_client = None
        
    async def __aenter__(self):
        self.async_session = aiohttp.ClientSession(
            headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        )
        self.ai_client = httpx.AsyncClient(
            base_url=AI_CONFIG['base_url'],
            headers={
                'Authorization': f'Bearer {AI_CONFIG["api_key"]}',
                'Content-Type': 'application/json'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.async_session:
            await self.async_session.close()
        if self.ai_client:
            await self.ai_client.aclose()
    
    async def get_ai_summary(self, content: str, article_type: str) -> str:
        """Get AI summary of content using DeepSeek"""
        try:
            # Clean the content - remove extra whitespace and ensure it's readable
            cleaned_content = ' '.join(content.split())
            
            # Only process if we have substantial content
            if len(cleaned_content) < 50:
                return "N/A"
            
            prompt = f"""
            Analyze this Hong Kong real estate {article_type} article and provide a concise summary in English.
            Focus on key market insights, transaction details, or significant developments.
            
            Article content:
            {cleaned_content[:3000]}
            
            Provide a 2-3 sentence summary focusing on the most important information:
            """
            
            response = await self.ai_client.post('/chat/completions', json={
                'model': AI_CONFIG['model'],
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 300,
                'temperature': 0.3
            })
            
            if response.status_code == 200:
                result = response.json()
                summary = result['choices'][0]['message']['content'].strip()
                # Ensure we get a meaningful summary
                if len(summary) > 10 and summary != "N/A":
                    return summary
                else:
                    return "N/A"
            else:
                logger.error(f"AI API error: {response.status_code}")
                return "N/A"
        except Exception as e:
            logger.error(f"AI summary error: {e}")
            return "N/A"
    
    def extract_date_from_text(self, text: str) -> Optional[str]:
        """Extract date from text in dd/mm/yyyy format"""
        date_patterns = [
            r'(\d{1,2})/(\d{1,2})/(\d{4})',  # dd/mm/yyyy
            r'(\d{4})-(\d{1,2})-(\d{1,2})',  # yyyy-mm-dd
            r'(\d{1,2})月(\d{1,2})日',  # Chinese date
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                if '月' in pattern:
                    month, day = match.groups()
                    year = datetime.now().year
                    return f"{day.zfill(2)}/{month.zfill(2)}/{year}"
                elif len(match.groups()) == 3:
                    if pattern.startswith(r'(\d{4})'):
                        year, month, day = match.groups()
                    else:
                        day, month, year = match.groups()
                    return f"{day.zfill(2)}/{month.zfill(2)}/{year}"
        return None
    
    def extract_transaction_value(self, text: str) -> Optional[float]:
        """Extract transaction value in HKD"""
        value_patterns = [
            r'(\d+(?:\.\d+)?)\s*億',  # 1.5億
            r'(\d+(?:\.\d+)?)\s*[Mm]illion',  # 1.5 million
            r'(\d+(?:,\d{3})*)\s*[Hh][Kk][Dd]',  # 1,500,000 HKD
            r'(\d+(?:,\d{3})*)\s*港幣',  # 1,500,000 港幣
            r'(\d+(?:,\d{3})*)\s*元',  # 1,500,000 元
            r'(\d+(?:,\d{3})*)\s*萬',  # 1,500,000 萬
            r'(\d+(?:\.\d+)?)\s*[Bb]illion',  # 1.5 billion
        ]
        
        for pattern in value_patterns:
            match = re.search(pattern, text)
            if match:
                value_str = match.group(1).replace(',', '')
                try:
                    if '億' in pattern:
                        return float(value_str) * 100000000
                    elif 'million' in pattern.lower():
                        return float(value_str) * 1000000
                    elif 'billion' in pattern.lower():
                        return float(value_str) * 1000000000
                    elif '萬' in pattern:
                        return float(value_str) * 10000
                    else:
                        return float(value_str)
                except ValueError:
                    continue
        return None
    
    def determine_asset_type(self, text: str) -> str:
        """Determine asset type from text"""
        text_lower = text.lower()
        
        if any(keyword in text_lower for keyword in ['寫字樓', 'office', '商廈', '商業大廈', '甲級寫字樓']):
            return 'office'
        elif any(keyword in text_lower for keyword in ['商舖', 'shop', '零售', '商場', '購物中心']):
            return 'retail'
        elif any(keyword in text_lower for keyword in ['住宅', 'residential', '樓盤', '新盤', '豪宅', '公寓']):
            return 'residential'
        elif any(keyword in text_lower for keyword in ['酒店', 'hotel', '賓館', '旅館']):
            return 'hotel'
        elif any(keyword in text_lower for keyword in ['地皮', 'land', '地塊', '土地']):
            return 'land'
        elif any(keyword in text_lower for keyword in ['車位', 'car park', 'parking', '停車位']):
            return 'cps'
        else:
            return 'N/A'
    
    def determine_transaction_type(self, text: str) -> str:
        """Determine transaction type"""
        text_lower = text.lower()
        
        if any(keyword in text_lower for keyword in ['成交', 'sale', 'purchase', '買賣', '售出']):
            return 'sales'
        elif any(keyword in text_lower for keyword in ['租', 'lease', 'rent', '出租', '承租']):
            return 'lease'
        else:
            return 'N/A'
    
    def extract_property_details(self, text: str) -> Dict:
        """Extract property details from text"""
        details = {
            'property_name': 'N/A',
            'district': 'N/A',
            'floor': 'N/A',
            'unit': 'N/A',
            'area_basis': 'N/A',
            'unit_basis': 'N/A',
            'area_unit': 'N/A',
            'unit_price': 'N/A',
            'yield': 'N/A',
            'seller_landlord': 'N/A',
            'buyer_tenant': 'N/A'
        }
        
        # Extract property name
        property_patterns = [
            r'([^，。\n]{2,15}(?:大廈|中心|廣場|花園|軒|苑|閣|樓|Building|Center|Plaza|Garden|Court))',
        ]
        
        for pattern in property_patterns:
            match = re.search(pattern, text)
            if match:
                details['property_name'] = match.group(1)
                break
        
        # Extract district
        district_patterns = [
            r'(中環|尖沙咀|銅鑼灣|旺角|北角|灣仔|金鐘|上環|西環|跑馬地|淺水灣|深水灣|赤柱|大潭|南區|東區|中西區|灣仔區|油尖旺區|深水埗區|九龍城區|黃大仙區|觀塘區|荃灣區|屯門區|元朗區|北區|大埔區|西貢區|沙田區|葵青區|離島區)',
        ]
        
        for pattern in district_patterns:
            match = re.search(pattern, text)
            if match:
                details['district'] = match.group(1)
                break
        
        # Extract floor and unit
        floor_unit_patterns = [
            r'(\d+)[樓層]?([A-Z]?\d+[A-Z]?號?)',
            r'(\d+)[樓層]?([A-Z]?\d+[A-Z]?室?)',
        ]
        
        for pattern in floor_unit_patterns:
            match = re.search(pattern, text)
            if match:
                details['floor'] = match.group(1)
                details['unit'] = match.group(2)
                break
        
        # Extract unit price
        unit_price_patterns = [
            r'每呎\s*(\d+(?:,\d{3})*)\s*元',
            r'呎價\s*(\d+(?:,\d{3})*)\s*元',
        ]
        
        for pattern in unit_price_patterns:
            match = re.search(pattern, text)
            if match:
                details['unit_price'] = match.group(1).replace(',', '')
                break
        
        return details
    
    async def scrape_hket(self) -> Tuple[List[Dict], List[Dict]]:
        """Scrape HKET website using ChromeDriver for JavaScript content"""
        transactions = []
        news = []
        
        try:
            # Set up Chrome options
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            
            # Initialize Chrome driver
            driver = webdriver.Chrome(options=chrome_options)
            
            try:
                # Navigate to HKET main page
                base_url = "https://ps.hket.com"
                logger.info(f"Scraping HKET with ChromeDriver: {base_url}")
                
                driver.get(base_url)
                
                # Wait for page to load
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # Get the page source after JavaScript execution
                html = driver.page_source
                soup = BeautifulSoup(html, 'html.parser')
                
                # Find article links
                article_links = []
                
                # Look for links with article patterns
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if any(pattern in href for pattern in ['/article/', '.html', '/property/', '/news/']):
                        if href.startswith('/'):
                            full_url = urljoin(base_url, href)
                        elif href.startswith('http'):
                            full_url = href
                        else:
                            full_url = urljoin(base_url, href)
                        if full_url not in article_links:
                            article_links.append(full_url)
                
                # Also look for links in specific containers
                for container in soup.find_all(['div', 'section'], class_=lambda x: x and any(word in x.lower() for word in ['article', 'news', 'content', 'item'])):
                    for link in container.find_all('a', href=True):
                        href = link['href']
                        if href.startswith('/'):
                            full_url = urljoin(base_url, href)
                        elif href.startswith('http'):
                            full_url = href
                        else:
                            full_url = urljoin(base_url, href)
                        if full_url not in article_links:
                            article_links.append(full_url)
                
                logger.info(f"Found {len(article_links)} articles on HKET")
                
                # Process each article
                for article_url in article_links[:20]:  # Limit to 20 articles
                    try:
                        logger.info(f"Processing HKET article: {article_url}")
                        
                        # Navigate to article page
                        driver.get(article_url)
                        
                        # Wait for page to load
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.TAG_NAME, "body"))
                        )
                        
                        # Get the page source
                        article_html = driver.page_source
                        article_soup = BeautifulSoup(article_html, 'html.parser')
                        
                        # Extract title and content
                        title_elem = article_soup.find('h1') or article_soup.find('title')
                        title = title_elem.get_text().strip() if title_elem else ""
                        
                        # Extract main content - try multiple selectors
                        content = ""
                        content_selectors = [
                            'div.article-content',
                            'div.content',
                            'article',
                            'div.article-body',
                            'div.post-content',
                            'div.entry-content',
                            'div.article-text',
                            'div.story-content',
                            'div.article-detail',
                            'div.article-main'
                        ]
                        
                        for selector in content_selectors:
                            content_elem = article_soup.select_one(selector)
                            if content_elem:
                                content = content_elem.get_text().strip()
                                break
                        
                        if not content:
                            # Try to get any text content
                            content = article_soup.get_text().strip()
                        
                        if len(content) < 50:  # Skip if too short
                            continue
                        
                        # Determine if it's a transaction or news
                        is_transaction = any(keyword in title + content for keyword in 
                                           ['成交', 'sale', 'purchase', '億', 'million', 'HKD', '港幣', '萬', 'billion'])
                        
                        if is_transaction:
                            # Extract transaction data
                            transaction_data = self.extract_property_details(content)
                            transaction_value = self.extract_transaction_value(content)
                            date = self.extract_date_from_text(content)
                            asset_type = self.determine_asset_type(content)
                            transaction_type = self.determine_transaction_type(content)
                            
                            if transaction_value and transaction_value >= 50000000:  # 50M HKD threshold
                                transaction = {
                                    'property': transaction_data['property_name'],
                                    'district': transaction_data['district'],
                                    'asset_type': asset_type,
                                    'floor': transaction_data['floor'],
                                    'unit': transaction_data['unit'],
                                    'transaction_type': transaction_type,
                                    'date': date or 'N/A',
                                    'transaction_price': int(transaction_value),
                                    'area_basis': transaction_data['area_basis'],
                                    'unit_basis': transaction_data['unit_basis'],
                                    'area_unit': transaction_data['area_unit'],
                                    'unit_price': transaction_data['unit_price'],
                                    'yield': transaction_data['yield'],
                                    'seller_landlord': transaction_data['seller_landlord'],
                                    'buyer_tenant': transaction_data['buyer_tenant'],
                                    'source': 'HKET',
                                    'url': article_url
                                }
                                transactions.append(transaction)
                        else:
                            # Market news - ensure we have proper content
                            if len(content) > 100:  # Only process if we have substantial content
                                summary = await self.get_ai_summary(content, 'news')
                                asset_type = self.determine_asset_type(content)
                                
                                news_item = {
                                    'source': 'HKET',
                                    'asset_type': asset_type,
                                    'topic': title,
                                    'summary': summary,
                                    'website': article_url
                                }
                                news.append(news_item)
                        
                        # Small delay between requests
                        time.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"Error processing HKET article {article_url}: {e}")
                        continue
                        
            finally:
                # Always close the driver
                driver.quit()
                            
        except Exception as e:
            logger.error(f"Error scraping HKET: {e}")
        
        return transactions, news
    
    async def scrape_wenweipo(self) -> Tuple[List[Dict], List[Dict]]:
        """Scrape Wenweipo website"""
        transactions = []
        news = []
        
        try:
            # Try multiple Wenweipo URLs
            urls_to_try = [
                "http://paper.wenweipo.com/007ME/",
                "https://paper.wenweipo.com/007ME/",
                "http://www.wenweipo.com",
                "https://www.wenweipo.com"
            ]
            
            for base_url in urls_to_try:
                try:
                    logger.info(f"Trying Wenweipo URL: {base_url}")
                    async with self.async_session.get(base_url, timeout=30) as response:
                        if response.status == 200:
                            # Try different encodings
                            try:
                                html = await response.text(encoding='utf-8')
                            except UnicodeDecodeError:
                                try:
                                    html = await response.text(encoding='big5')
                                except UnicodeDecodeError:
                                    try:
                                        html = await response.text(encoding='gbk')
                                    except UnicodeDecodeError:
                                        html = await response.text(encoding='latin-1')
                            
                            soup = BeautifulSoup(html, 'html.parser')
                            
                            # Find article links
                            article_links = []
                            for link in soup.find_all('a', href=True):
                                href = link['href']
                                if href.startswith('/') or href.startswith('http'):
                                    full_url = urljoin(base_url, href)
                                    if full_url not in article_links:
                                        article_links.append(full_url)
                            
                            logger.info(f"Found {len(article_links)} articles on Wenweipo from {base_url}")
                            
                            if len(article_links) > 0:
                                break  # Found articles, stop trying other URLs
                            
                except Exception as e:
                    logger.warning(f"Failed to scrape {base_url}: {e}")
                    continue
            
            # Process each article
            for article_url in article_links[:30]:  # Increased limit
                try:
                    async with self.async_session.get(article_url, timeout=30) as article_response:
                        if article_response.status == 200:
                            try:
                                article_html = await article_response.text(encoding='utf-8')
                            except UnicodeDecodeError:
                                try:
                                    article_html = await article_response.text(encoding='big5')
                                except UnicodeDecodeError:
                                    try:
                                        article_html = await article_response.text(encoding='gbk')
                                    except UnicodeDecodeError:
                                        article_html = await article_response.text(encoding='latin-1')
                            
                            article_soup = BeautifulSoup(article_html, 'html.parser')
                            
                            # Extract title and content
                            title_elem = article_soup.find('h1') or article_soup.find('title')
                            title = title_elem.get_text().strip() if title_elem else ""
                            
                            # Extract main content - try multiple selectors
                            content = ""
                            content_selectors = [
                                'div.content',
                                'div.article-content',
                                'article',
                                'div.article-body',
                                'div.post-content',
                                'div.article-text',
                                'div.story-content',
                                'div.article-detail',
                                'div.article-main',
                                'div.article',
                                'div.text-content',
                                'div.main-content'
                            ]
                            
                            for selector in content_selectors:
                                content_elem = article_soup.select_one(selector)
                                if content_elem:
                                    content = content_elem.get_text().strip()
                                    break
                            
                            if not content:
                                content = article_soup.get_text().strip()
                            
                            if len(content) < 50:  # Skip if too short
                                continue
                            
                            # Determine if it's a transaction or news
                            is_transaction = any(keyword in title + content for keyword in 
                                               ['成交', 'sale', 'purchase', '億', 'million', 'HKD', '港幣', '萬', 'billion'])
                            
                            if is_transaction:
                                # Extract transaction data
                                transaction_data = self.extract_property_details(content)
                                transaction_value = self.extract_transaction_value(content)
                                date = self.extract_date_from_text(content)
                                asset_type = self.determine_asset_type(content)
                                transaction_type = self.determine_transaction_type(content)
                                
                                if transaction_value and transaction_value >= 50000000:  # 50M HKD threshold
                                    transaction = {
                                        'property': transaction_data['property_name'],
                                        'district': transaction_data['district'],
                                        'asset_type': asset_type,
                                        'floor': transaction_data['floor'],
                                        'unit': transaction_data['unit'],
                                        'transaction_type': transaction_type,
                                        'date': date or 'N/A',
                                        'transaction_price': int(transaction_value),
                                        'area_basis': transaction_data['area_basis'],
                                        'unit_basis': transaction_data['unit_basis'],
                                        'area_unit': transaction_data['area_unit'],
                                        'unit_price': transaction_data['unit_price'],
                                        'yield': transaction_data['yield'],
                                        'seller_landlord': transaction_data['seller_landlord'],
                                        'buyer_tenant': transaction_data['buyer_tenant'],
                                        'source': 'Wenweipo',
                                        'url': article_url
                                    }
                                    transactions.append(transaction)
                            else:
                                # Market news - ensure we have proper content
                                if len(content) > 100:  # Only process if we have substantial content
                                    summary = await self.get_ai_summary(content, 'news')
                                    asset_type = self.determine_asset_type(content)
                                    
                                    news_item = {
                                        'source': 'Wenweipo',
                                        'asset_type': asset_type,
                                        'topic': title,
                                        'summary': summary,
                                        'website': article_url
                                    }
                                    news.append(news_item)
                            
                            await asyncio.sleep(0.5)  # Reduced delay
                            
                except Exception as e:
                    logger.error(f"Error processing Wenweipo article {article_url}: {e}")
                    continue
                            
        except Exception as e:
            logger.error(f"Error scraping Wenweipo: {e}")
        
        return transactions, news
    
    async def scrape_stheadline(self) -> Tuple[List[Dict], List[Dict]]:
        """Scrape Sing Tao Headline website"""
        transactions = []
        news = []
        
        try:
            # Get main page
            url = "https://www.stheadline.com/daily-property/"
            async with self.async_session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Find article links - try different approaches
                    article_links = []
                    
                    # Look for links with article patterns
                    for link in soup.find_all('a', href=True):
                        href = link['href']
                        if any(pattern in href for pattern in ['/article/', '/property/', '.html']):
                            if href.startswith('/'):
                                full_url = urljoin(url, href)
                            elif href.startswith('http'):
                                full_url = href
                            else:
                                full_url = urljoin(url, href)
                            article_links.append(full_url)
                    
                    # Also look for links in article containers
                    for container in soup.find_all(['div', 'section'], class_=lambda x: x and any(word in x.lower() for word in ['article', 'news', 'content', 'item'])):
                        for link in container.find_all('a', href=True):
                            href = link['href']
                            if href.startswith('/'):
                                full_url = urljoin(url, href)
                            elif href.startswith('http'):
                                full_url = href
                            else:
                                full_url = urljoin(url, href)
                            if full_url not in article_links:
                                article_links.append(full_url)
                    
                    logger.info(f"Found {len(article_links)} articles on Sing Tao Headline")
                    
                    # Process each article
                    for article_url in article_links[:20]:  # Limit to 20 articles
                        try:
                            async with self.async_session.get(article_url) as article_response:
                                if article_response.status == 200:
                                    article_html = await article_response.text()
                                    article_soup = BeautifulSoup(article_html, 'html.parser')
                                    
                                    # Extract title and content
                                    title_elem = article_soup.find('h1') or article_soup.find('title')
                                    title = title_elem.get_text().strip() if title_elem else ""
                                    
                                    # Extract main content - try multiple selectors
                                    content = ""
                                    content_selectors = [
                                        'div.article-content',
                                        'div.content',
                                        'article',
                                        'div.article-body',
                                        'div.post-content',
                                        'div.entry-content',
                                        'div.article-text',
                                        'div.story-content',
                                        'div.article-detail',
                                        'div.article-main'
                                    ]
                                    
                                    for selector in content_selectors:
                                        content_elem = article_soup.select_one(selector)
                                        if content_elem:
                                            content = content_elem.get_text().strip()
                                            break
                                    
                                    if not content:
                                        content = article_soup.get_text().strip()
                                    
                                    if len(content) < 50:  # Skip if too short
                                        continue
                                    
                                    # Determine if it's a transaction or news
                                    is_transaction = any(keyword in title + content for keyword in 
                                                       ['成交', 'sale', 'purchase', '億', 'million', 'HKD', '港幣', '萬', 'billion'])
                                    
                                    if is_transaction:
                                        # Extract transaction data
                                        transaction_data = self.extract_property_details(content)
                                        transaction_value = self.extract_transaction_value(content)
                                        date = self.extract_date_from_text(content)
                                        asset_type = self.determine_asset_type(content)
                                        transaction_type = self.determine_transaction_type(content)
                                        
                                        if transaction_value and transaction_value >= 50000000:  # 50M HKD threshold
                                            transaction = {
                                                'property': transaction_data['property_name'],
                                                'district': transaction_data['district'],
                                                'asset_type': asset_type,
                                                'floor': transaction_data['floor'],
                                                'unit': transaction_data['unit'],
                                                'transaction_type': transaction_type,
                                                'date': date or 'N/A',
                                                'transaction_price': int(transaction_value),
                                                'area_basis': transaction_data['area_basis'],
                                                'unit_basis': transaction_data['unit_basis'],
                                                'area_unit': transaction_data['area_unit'],
                                                'unit_price': transaction_data['unit_price'],
                                                'yield': transaction_data['yield'],
                                                'seller_landlord': transaction_data['seller_landlord'],
                                                'buyer_tenant': transaction_data['buyer_tenant'],
                                                'source': 'Sing Tao Headline',
                                                'url': article_url
                                            }
                                            transactions.append(transaction)
                                    else:
                                        # Market news - ensure we have proper content
                                        if len(content) > 100:  # Only process if we have substantial content
                                            summary = await self.get_ai_summary(content, 'news')
                                            asset_type = self.determine_asset_type(content)
                                            
                                            news_item = {
                                                'source': 'Sing Tao Headline',
                                                'asset_type': asset_type,
                                                'topic': title,
                                                'summary': summary,
                                                'website': article_url
                                            }
                                            news.append(news_item)
                                    
                                    await asyncio.sleep(1)  # Be respectful
                                    
                        except Exception as e:
                            logger.error(f"Error processing Sing Tao Headline article {article_url}: {e}")
                            continue
                            
        except Exception as e:
            logger.error(f"Error scraping Sing Tao Headline: {e}")
        
        return transactions, news
    
    async def scrape_all_sources(self) -> Dict[str, List[Dict]]:
        """Scrape all three sources"""
        logger.info("Starting specialized scraping of all sources...")
        
        all_transactions = []
        all_news = []
        
        # Scrape each source
        sources = [
            ('HKET', self.scrape_hket),
            ('Wenweipo', self.scrape_wenweipo),
            ('Sing Tao Headline', self.scrape_stheadline)
        ]
        
        for source_name, scraper_func in sources:
            logger.info(f"Scraping {source_name}...")
            try:
                transactions, news = await scraper_func()
                all_transactions.extend(transactions)
                all_news.extend(news)
                logger.info(f"{source_name}: Found {len(transactions)} transactions, {len(news)} news articles")
            except Exception as e:
                logger.error(f"Error scraping {source_name}: {e}")
        
        logger.info(f"Total results: {len(all_transactions)} transactions, {len(all_news)} news articles")
        
        return {
            'transactions': all_transactions,
            'news': all_news
        }

async def main():
    """Main function to run the specialized scraper"""
    async with SpecializedMarketScraper() as scraper:
        results = await scraper.scrape_all_sources()
        
        # Create output directory if it doesn't exist
        os.makedirs('output', exist_ok=True)
        
        # Generate date-based filename
        date_str = datetime.now().strftime("%Y%m%d")
        
        # Save results to output directory
        json_filename = f"output/market_data_{date_str}.json"
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\nScraping completed!")
        print(f"Transactions found: {len(results['transactions'])}")
        print(f"News articles found: {len(results['news'])}")
        print(f"Results saved to: {json_filename}")

if __name__ == "__main__":
    asyncio.run(main()) 