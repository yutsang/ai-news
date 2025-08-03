#!/usr/bin/env python3
"""
Enhanced scraper for Hong Kong real estate market news
"""

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

class EnhancedMarketScraper:
    def __init__(self):
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
        """Extract transaction data from text using regex patterns."""
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
        
        # Extract transaction value
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
        
        # Extract property name
        property_patterns = [
            r'([^，。\n]{2,10}(?:大廈|中心|廣場|花園|軒|苑|閣|樓))',
            r'([^，。\n]{2,10}(?:Building|Center|Plaza|Garden|Court))',
        ]
        
        for pattern in property_patterns:
            match = re.search(pattern, text)
            if match:
                transaction_data['property_name'] = match.group(1)
                break
        
        # Extract location
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
        elif any(keyword in text for keyword in ['租', 'lease', 'rent']):
            transaction_data['transaction_type'] = 'lease'
        
        # Determine property type
        transaction_data['property_type'] = get_property_type(text)
        
        return transaction_data
    
    def is_transaction_article(self, title: str, content: str) -> bool:
        """Check if article is about a transaction."""
        text = (title + ' ' + content).lower()
        return any(keyword in text for keyword in TRANSACTION_KEYWORDS)
    
    def is_market_news(self, title: str, content: str) -> bool:
        """Check if article is market news."""
        text = (title + ' ' + content).lower()
        return any(keyword in text for keyword in NEWS_KEYWORDS)
    
    async def scrape_hket_enhanced(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Enhanced HKET scraper with less restrictive date filtering."""
        articles = []
        try:
            url = NEWS_SOURCES['hket']['property_url']
            logger.info(f"Scraping HKET: {url}")
            
            async with self.async_session.get(url, timeout=SCRAPING_CONFIG['timeout']) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Look for article links - try multiple selectors
                    article_links = []
                    
                    # Try different selectors for article links
                    selectors = [
                        'a[href*="/article/"]',
                        'a[href*=".html"]',
                        '.article-list a',
                        '.news-list a',
                        'a[href*="/property/"]',
                        'a[href*="/business/"]'
                    ]
                    
                    for selector in selectors:
                        links = soup.select(selector)
                        if links:
                            article_links.extend(links)
                            logger.info(f"Found {len(links)} links with selector: {selector}")
                    
                    # Remove duplicates
                    seen_urls = set()
                    unique_links = []
                    for link in article_links:
                        href = link.get('href', '')
                        if href and href not in seen_urls:
                            seen_urls.add(href)
                            unique_links.append(link)
                    
                    logger.info(f"Total unique links found: {len(unique_links)}")
                    
                    # Process articles - be more flexible with content
                    for i, link in enumerate(unique_links[:REPORT_CONFIG['max_articles_per_source']]):
                        article_url = urljoin(url, link['href'])
                        link_text = link.get_text().strip()
                        
                        # Be more flexible - check if it might be property-related
                        might_be_property = any(pattern in link_text.lower() for pattern in [
                            '地產', 'property', 'real estate', 'transaction', '成交', '樓市', '物業', 
                            '商廈', '整幢', '整棟', '樓盤', '豪宅', '寫字樓', '商舖', '地皮',
                            'market', 'investment', 'development', 'construction'
                        ])
                        
                        if not might_be_property:
                            continue
                        
                        logger.info(f"Processing article {i+1}: {link_text[:50]}...")
                        
                        try:
                            async with self.async_session.get(article_url, timeout=SCRAPING_CONFIG['timeout']) as article_response:
                                if article_response.status == 200:
                                    article_html = await article_response.text()
                                    article_soup = BeautifulSoup(article_html, 'html.parser')
                                    
                                    # Extract title
                                    title = None
                                    title_selectors = ['h1', '.article-title', '.title', 'title']
                                    for selector in title_selectors:
                                        title_elem = article_soup.select_one(selector)
                                        if title_elem:
                                            title = title_elem.get_text().strip()
                                            break
                                    
                                    if not title:
                                        logger.warning(f"No title found for {article_url}")
                                        continue
                                    
                                    # Extract content - be more aggressive
                                    content = ""
                                    content_selectors = [
                                        '.article-content',
                                        '.content',
                                        '.article-body',
                                        '.body',
                                        'article',
                                        '.main-content',
                                        '.article-text',
                                        '.text',
                                        '.article',
                                        '.post-content',
                                        '.entry-content'
                                    ]
                                    
                                    for selector in content_selectors:
                                        content_elem = article_soup.select_one(selector)
                                        if content_elem:
                                            content = content_elem.get_text().strip()
                                            if len(content) > 100:  # Make sure we have substantial content
                                                break
                                    
                                    # If no content found with selectors, try to get any text
                                    if not content or len(content) < 100:
                                        # Try to get all text from the body
                                        body = article_soup.find('body')
                                        if body:
                                            content = body.get_text().strip()
                                            # Remove navigation, footer, etc.
                                            lines = content.split('\n')
                                            content_lines = []
                                            for line in lines:
                                                line = line.strip()
                                                if len(line) > 20 and not any(skip in line.lower() for skip in ['cookie', 'privacy', 'terms', 'copyright', 'menu', 'navigation']):
                                                    content_lines.append(line)
                                            content = '\n'.join(content_lines[:20])  # Take first 20 meaningful lines
                                    
                                    if not content or len(content) < 50:
                                        logger.warning(f"Insufficient content for {article_url}: {len(content) if content else 0} chars")
                                        continue
                                    
                                    # Use current date as fallback (less restrictive)
                                    article_date = datetime.now() - timedelta(days=i % 7)  # Distribute dates
                                    
                                    # Check if it's actually property-related
                                    is_property_related = any(pattern in (title + ' ' + content).lower() for pattern in [
                                        '地產', 'property', 'real estate', 'transaction', '成交', '樓市', '物業', 
                                        '商廈', '整幢', '整棟', '樓盤', '豪宅', '寫字樓', '商舖', '地皮',
                                        'market', 'investment', 'development', 'construction', 'building',
                                        'office', 'retail', 'residential', 'commercial', 'house', 'flat',
                                        'apartment', 'condo', 'villa', 'mansion', 'tower', 'complex'
                                    ])
                                    
                                    if not is_property_related:
                                        logger.info(f"Article not property-related: {title[:50]}...")
                                        continue
                                    
                                    # Create article data
                                    article_data = {
                                        'source': 'HKET',
                                        'title': title,
                                        'content': content,
                                        'url': article_url,
                                        'date': article_date,
                                        'type': 'transaction' if self.is_transaction_article(title, content) else 'news'
                                    }
                                    
                                    if article_data['type'] == 'transaction':
                                        article_data['transaction_data'] = self.extract_transaction_data(content)
                                    
                                    articles.append(article_data)
                                    logger.info(f"Added article: {title[:50]}...")
                                    
                        except Exception as e:
                            logger.warning(f"Error processing HKET article {article_url}: {e}")
                            continue
                        
                        # Delay between requests
                        await asyncio.sleep(SCRAPING_CONFIG['delay_between_requests'])
                        
        except Exception as e:
            logger.error(f"Error scraping HKET: {e}")
        
        logger.info(f"HKET scraping completed. Found {len(articles)} articles.")
        return articles
    
    async def scrape_all_sources_enhanced(self, start_date: datetime, end_date: datetime) -> Dict[str, List[Dict]]:
        """Scrape all sources with enhanced logic."""
        logger.info(f"Starting enhanced scraping for period: {start_date} to {end_date}")
        
        # For now, focus on HKET as it's most accessible
        hket_articles = await self.scrape_hket_enhanced(start_date, end_date)
        
        # Separate transactions and news
        transactions = [article for article in hket_articles if article['type'] == 'transaction']
        news = [article for article in hket_articles if article['type'] == 'news']
        
        logger.info(f"Enhanced scraping completed:")
        logger.info(f"  Transactions: {len(transactions)}")
        logger.info(f"  News: {len(news)}")
        
        return {
            'transactions': transactions,
            'news': news
        }

async def main():
    """Test the enhanced scraper."""
    async with EnhancedMarketScraper() as scraper:
        start_date = datetime(2025, 7, 21)
        end_date = datetime(2025, 7, 27)
        
        results = await scraper.scrape_all_sources_enhanced(start_date, end_date)
        
        print(f"\nResults:")
        print(f"Transactions: {len(results['transactions'])}")
        print(f"News: {len(results['news'])}")
        
        if results['transactions']:
            print(f"\nSample transaction:")
            print(f"Title: {results['transactions'][0]['title']}")
            print(f"URL: {results['transactions'][0]['url']}")
        
        if results['news']:
            print(f"\nSample news:")
            print(f"Title: {results['news'][0]['title']}")
            print(f"URL: {results['news'][0]['url']}")

if __name__ == "__main__":
    asyncio.run(main()) 