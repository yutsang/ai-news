import requests
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time
import re
import logging
from urllib.parse import urljoin, urlparse
import json

from config import NEWS_SOURCES, SCRAPING_CONFIG, TRANSACTION_KEYWORDS, NEWS_KEYWORDS, is_big_deal, get_property_type, REPORT_CONFIG

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MarketNewsScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': SCRAPING_CONFIG['user_agent']
        })
        self.async_session = None
    
    async def __aenter__(self):
        self.async_session = aiohttp.ClientSession(
            headers={'User-Agent': SCRAPING_CONFIG['user_agent']}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.async_session:
            await self.async_session.close()
    
    def extract_transaction_data(self, text: str) -> Dict:
        """
        Extract transaction data from text using regex patterns.
        """
        transaction_data = {
            'property_name': None,
            'transaction_value': None,
            'transaction_type': None,
            'location': None,
            'date': None,
            'area': None,
            'unit_price': None,
            'property_type': None
        }
        
        # Extract transaction value (look for patterns like "億", "million", "HKD")
        value_patterns = [
            r'(\d+(?:\.\d+)?)\s*億',  # 1.5億
            r'(\d+(?:\.\d+)?)\s*[Mm]illion',  # 1.5 million
            r'(\d+(?:,\d{3})*)\s*[Hh][Kk][Dd]',  # 1,500,000 HKD
            r'(\d+(?:,\d{3})*)\s*港幣',  # 1,500,000 港幣
        ]
        
        for pattern in value_patterns:
            match = re.search(pattern, text)
            if match:
                value_str = match.group(1).replace(',', '')
                try:
                    if '億' in pattern:
                        transaction_data['transaction_value'] = float(value_str) * 100000000
                    elif 'million' in pattern.lower():
                        transaction_data['transaction_value'] = float(value_str) * 1000000
                    else:
                        transaction_data['transaction_value'] = float(value_str)
                    break
                except ValueError:
                    continue
        
        # Extract property name (look for patterns like "大廈", "中心", "廣場")
        property_patterns = [
            r'([^，。\n]{2,10}(?:大廈|中心|廣場|花園|軒|苑|閣|樓))',
            r'([^，。\n]{2,10}(?:Building|Center|Plaza|Garden|Court))',
        ]
        
        for pattern in property_patterns:
            match = re.search(pattern, text)
            if match:
                transaction_data['property_name'] = match.group(1)
                break
        
        # Extract location (look for district names)
        location_patterns = [
            r'(中環|尖沙咀|銅鑼灣|旺角|北角|灣仔|金鐘|上環|西環|跑馬地|淺水灣|深水灣|赤柱|大潭|南區|東區|中西區|灣仔區|油尖旺區|深水埗區|九龍城區|黃大仙區|觀塘區|荃灣區|屯門區|元朗區|北區|大埔區|西貢區|沙田區|葵青區|離島區)',
            r'(Central|Tsim Sha Tsui|Causeway Bay|Mong Kok|North Point|Wan Chai|Admiralty|Sheung Wan|Sai Ying Pun|Happy Valley|Repulse Bay|Deep Water Bay|Stanley|Tai Tam|Southern District|Eastern District|Central and Western District|Wan Chai District|Yau Tsim Mong District|Sham Shui Po District|Kowloon City District|Wong Tai Sin District|Kwun Tong District|Tsuen Wan District|Tuen Mun District|Yuen Long District|North District|Tai Po District|Sai Kung District|Sha Tin District|Kwai Tsing District|Islands District)',
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, text)
            if match:
                transaction_data['location'] = match.group(1)
                break
        
        # Extract transaction type
        if any(keyword in text for keyword in ['成交', 'sale', 'purchase']):
            transaction_data['transaction_type'] = 'sale'
        elif any(keyword in text for keyword in ['租賃', 'lease', 'rent']):
            transaction_data['transaction_type'] = 'lease'
        
        # Determine property type
        transaction_data['property_type'] = get_property_type(text)
        
        return transaction_data
    
    def is_transaction_article(self, title: str, content: str) -> bool:
        """
        Determine if an article is about market transactions.
        """
        combined_text = f"{title} {content}".lower()
        return any(keyword in combined_text for keyword in TRANSACTION_KEYWORDS)
    
    def is_market_news(self, title: str, content: str) -> bool:
        """
        Determine if an article is about market news/analysis.
        """
        combined_text = f"{title} {content}".lower()
        return any(keyword in combined_text for keyword in NEWS_KEYWORDS)
    
    async def scrape_hket(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """
        Scrape HKET for market news and transactions.
        """
        articles = []
        try:
            url = NEWS_SOURCES['hket']['property_url']
            async with self.async_session.get(url, timeout=SCRAPING_CONFIG['timeout']) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Look for article links
                    article_links = soup.find_all('a', href=True)
                    
                    for link in article_links[:REPORT_CONFIG['max_articles_per_source']]:
                        article_url = urljoin(url, link['href'])
                        
                        # Skip if not a property-related article
                        if not any(pattern in link.get_text() for pattern in NEWS_SOURCES['hket']['search_patterns']):
                            continue
                        
                        try:
                            # Get article content
                            async with self.async_session.get(article_url, timeout=SCRAPING_CONFIG['timeout']) as article_response:
                                if article_response.status == 200:
                                    article_html = await article_response.text()
                                    article_soup = BeautifulSoup(article_html, 'html.parser')
                                    
                                    title = article_soup.find('h1')
                                    title_text = title.get_text().strip() if title else ''
                                    
                                    content = article_soup.find('div', class_='article-content')
                                    content_text = content.get_text().strip() if content else ''
                                    
                                    # Extract date from article
                                    date_elem = article_soup.find('time') or article_soup.find('span', class_='date')
                                    article_date = None
                                    if date_elem:
                                        date_text = date_elem.get_text().strip()
                                        try:
                                            article_date = datetime.strptime(date_text, '%Y-%m-%d')
                                        except ValueError:
                                            try:
                                                article_date = datetime.strptime(date_text, '%d/%m/%Y')
                                            except ValueError:
                                                pass
                                    
                                    # Check if article is within date range
                                    if article_date and start_date <= article_date <= end_date:
                                        article_data = {
                                            'source': 'HKET',
                                            'title': title_text,
                                            'content': content_text,
                                            'url': article_url,
                                            'date': article_date,
                                            'type': 'transaction' if self.is_transaction_article(title_text, content_text) else 'news'
                                        }
                                        
                                        if article_data['type'] == 'transaction':
                                            article_data['transaction_data'] = self.extract_transaction_data(content_text)
                                        
                                        articles.append(article_data)
                                        
                        except Exception as e:
                            logger.warning(f"Error scraping HKET article {article_url}: {e}")
                            continue
                        
                        # Delay between requests
                        await asyncio.sleep(SCRAPING_CONFIG['delay_between_requests'])
                        
        except Exception as e:
            logger.error(f"Error scraping HKET: {e}")
        
        return articles
    
    async def scrape_wenweipo(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """
        Scrape Wen Wei Po for market news and transactions.
        """
        articles = []
        try:
            url = NEWS_SOURCES['wenweipo']['property_url']
            async with self.async_session.get(url, timeout=SCRAPING_CONFIG['timeout']) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Look for article links
                    article_links = soup.find_all('a', href=True)
                    
                    for link in article_links[:REPORT_CONFIG['max_articles_per_source']]:
                        article_url = urljoin(url, link['href'])
                        
                        # Skip if not a property-related article
                        if not any(pattern in link.get_text() for pattern in NEWS_SOURCES['wenweipo']['search_patterns']):
                            continue
                        
                        try:
                            # Get article content
                            async with self.async_session.get(article_url, timeout=SCRAPING_CONFIG['timeout']) as article_response:
                                if article_response.status == 200:
                                    article_html = await article_response.text()
                                    article_soup = BeautifulSoup(article_html, 'html.parser')
                                    
                                    title = article_soup.find('h1')
                                    title_text = title.get_text().strip() if title else ''
                                    
                                    content = article_soup.find('div', class_='article-content')
                                    content_text = content.get_text().strip() if content else ''
                                    
                                    # Extract date from article
                                    date_elem = article_soup.find('time') or article_soup.find('span', class_='date')
                                    article_date = None
                                    if date_elem:
                                        date_text = date_elem.get_text().strip()
                                        try:
                                            article_date = datetime.strptime(date_text, '%Y-%m-%d')
                                        except ValueError:
                                            try:
                                                article_date = datetime.strptime(date_text, '%d/%m/%Y')
                                            except ValueError:
                                                pass
                                    
                                    # Check if article is within date range
                                    if article_date and start_date <= article_date <= end_date:
                                        article_data = {
                                            'source': '文匯報',
                                            'title': title_text,
                                            'content': content_text,
                                            'url': article_url,
                                            'date': article_date,
                                            'type': 'transaction' if self.is_transaction_article(title_text, content_text) else 'news'
                                        }
                                        
                                        if article_data['type'] == 'transaction':
                                            article_data['transaction_data'] = self.extract_transaction_data(content_text)
                                        
                                        articles.append(article_data)
                                        
                        except Exception as e:
                            logger.warning(f"Error scraping Wen Wei Po article {article_url}: {e}")
                            continue
                        
                        # Delay between requests
                        await asyncio.sleep(SCRAPING_CONFIG['delay_between_requests'])
                        
        except Exception as e:
            logger.error(f"Error scraping Wen Wei Po: {e}")
        
        return articles
    
    async def scrape_stheadline(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """
        Scrape Sing Tao Daily for market news and transactions.
        """
        articles = []
        try:
            url = NEWS_SOURCES['stheadline']['property_url']
            async with self.async_session.get(url, timeout=SCRAPING_CONFIG['timeout']) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Look for article links
                    article_links = soup.find_all('a', href=True)
                    
                    for link in article_links[:REPORT_CONFIG['max_articles_per_source']]:
                        article_url = urljoin(url, link['href'])
                        
                        # Skip if not a property-related article
                        if not any(pattern in link.get_text() for pattern in NEWS_SOURCES['stheadline']['search_patterns']):
                            continue
                        
                        try:
                            # Get article content
                            async with self.async_session.get(article_url, timeout=SCRAPING_CONFIG['timeout']) as article_response:
                                if article_response.status == 200:
                                    article_html = await article_response.text()
                                    article_soup = BeautifulSoup(article_html, 'html.parser')
                                    
                                    title = article_soup.find('h1')
                                    title_text = title.get_text().strip() if title else ''
                                    
                                    content = article_soup.find('div', class_='article-content')
                                    content_text = content.get_text().strip() if content else ''
                                    
                                    # Extract date from article
                                    date_elem = article_soup.find('time') or article_soup.find('span', class_='date')
                                    article_date = None
                                    if date_elem:
                                        date_text = date_elem.get_text().strip()
                                        try:
                                            article_date = datetime.strptime(date_text, '%Y-%m-%d')
                                        except ValueError:
                                            try:
                                                article_date = datetime.strptime(date_text, '%d/%m/%Y')
                                            except ValueError:
                                                pass
                                    
                                    # Check if article is within date range
                                    if article_date and start_date <= article_date <= end_date:
                                        article_data = {
                                            'source': '星島頭條',
                                            'title': title_text,
                                            'content': content_text,
                                            'url': article_url,
                                            'date': article_date,
                                            'type': 'transaction' if self.is_transaction_article(title_text, content_text) else 'news'
                                        }
                                        
                                        if article_data['type'] == 'transaction':
                                            article_data['transaction_data'] = self.extract_transaction_data(content_text)
                                        
                                        articles.append(article_data)
                                        
                        except Exception as e:
                            logger.warning(f"Error scraping Sing Tao Daily article {article_url}: {e}")
                            continue
                        
                        # Delay between requests
                        await asyncio.sleep(SCRAPING_CONFIG['delay_between_requests'])
                        
        except Exception as e:
            logger.error(f"Error scraping Sing Tao Daily: {e}")
        
        return articles
    
    async def scrape_all_sources(self, start_date: datetime, end_date: datetime) -> Dict[str, List[Dict]]:
        """
        Scrape all news sources concurrently.
        """
        tasks = [
            self.scrape_hket(start_date, end_date),
            self.scrape_wenweipo(start_date, end_date),
            self.scrape_stheadline(start_date, end_date)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_articles = {
            'transactions': [],
            'news': []
        }
        
        for result in results:
            if isinstance(result, list):
                for article in result:
                    if article['type'] == 'transaction':
                        all_articles['transactions'].append(article)
                    else:
                        all_articles['news'].append(article)
        
        return all_articles 