#!/usr/bin/env python3
"""
Improved ChromeDriver Hong Kong Real Estate Market Scraper
With DeepSeek content validation and better content extraction
"""

import asyncio
import aiohttp
import httpx
import json
import logging
import os
import re
import time
import subprocess
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from config import AI_CONFIG

# Set up simple logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

class ImprovedChromeDriverMarketScraper:
    def __init__(self):
        self.ai_client = None
        self.session = None
        self.driver = None
        
        # Load config
        with open('config.json', 'r', encoding='utf-8') as f:
            self.config = json.load(f)
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        self.ai_client = httpx.AsyncClient(
            base_url=AI_CONFIG['base_url'],
            headers={'Authorization': f"Bearer {AI_CONFIG['api_key']}"},
            timeout=30.0
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
        if self.ai_client:
            await self.ai_client.aclose()
        if self.driver:
            self.driver.quit()
    
    def setup_chromedriver(self):
        """Setup ChromeDriver with multiple fallback methods"""
        print("🔧 Setting up ChromeDriver...")
        
        # Method 1: Try system ChromeDriver
        try:
            result = subprocess.run(['which', 'chromedriver'], capture_output=True, text=True)
            if result.returncode == 0:
                chromedriver_path = result.stdout.strip()
                print(f"   Found system ChromeDriver: {chromedriver_path}")
                service = Service(chromedriver_path)
                self.driver = webdriver.Chrome(service=service, options=self._get_chrome_options())
                print("   ✅ System ChromeDriver setup completed!")
                return True
        except Exception as e:
            print(f"   System ChromeDriver failed: {e}")
        
        # Method 2: Try Homebrew ChromeDriver
        try:
            result = subprocess.run(['brew', 'list', 'chromedriver'], capture_output=True, text=True)
            if result.returncode == 0:
                result = subprocess.run(['brew', '--prefix', 'chromedriver'], capture_output=True, text=True)
                if result.returncode == 0:
                    brew_path = result.stdout.strip()
                    chromedriver_path = os.path.join(brew_path, 'bin', 'chromedriver')
                    if os.path.exists(chromedriver_path):
                        print(f"   Found Homebrew ChromeDriver: {chromedriver_path}")
                        service = Service(chromedriver_path)
                        self.driver = webdriver.Chrome(service=service, options=self._get_chrome_options())
                        print("   ✅ Homebrew ChromeDriver setup completed!")
                        return True
        except Exception as e:
            print(f"   Homebrew ChromeDriver failed: {e}")
        
        # Method 3: Try without specifying service
        try:
            print("   Trying default ChromeDriver...")
            self.driver = webdriver.Chrome(options=self._get_chrome_options())
            print("   ✅ Default ChromeDriver setup completed!")
            return True
        except Exception as e:
            print(f"   Default ChromeDriver failed: {e}")
        
        print("❌ All ChromeDriver setup methods failed")
        print("💡 Please install ChromeDriver: brew install chromedriver")
        return False
    
    def _get_chrome_options(self):
        """Get Chrome options from config"""
        chrome_options = Options()
        
        # Use headless setting from config
        if self.config['scraping_config']['headless']:
            chrome_options.add_argument('--headless')
        
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument(f'--user-agent={self.config["scraping_config"]["user_agent"]}')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Block ads and popups
        chrome_options.add_argument('--disable-popup-blocking')
        chrome_options.add_argument('--disable-notifications')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-plugins')
        chrome_options.add_argument('--disable-images')  # Speed up loading
        
        # Add ad blocking preferences
        prefs = {
            "profile.default_content_setting_values": {
                "notifications": 2,
                "popups": 2,
                "geolocation": 2,
                "media_stream": 2,
                "plugins": 2,
                "ppapi_broker": 2,
                "automatic_downloads": 2,
                "mixed_script": 2,
                "media_stream_mic": 2,
                "media_stream_camera": 2,
                "protocol_handlers": 2,
                "ppapi_broker": 2,
                "automatic_downloads": 2,
                "midi_sysex": 2,
                "push_messaging": 2,
                "ssl_cert_decisions": 2,
                "metro_switch_to_desktop": 2,
                "protected_media_identifier": 2,
                "app_banner": 2,
                "site_engagement": 2,
                "durable_storage": 2
            }
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        return chrome_options
    
    def handle_popups_and_ads(self):
        """Handle popups and ads that might appear during scraping"""
        try:
            # Try to close common popup elements
            popup_selectors = [
                'button[class*="close"]',
                'button[class*="dismiss"]',
                'button[class*="popup"]',
                'div[class*="close"]',
                'div[class*="dismiss"]',
                'div[class*="popup"]',
                'span[class*="close"]',
                'a[class*="close"]',
                'button[aria-label*="close"]',
                'button[aria-label*="dismiss"]',
                '.modal-close',
                '.popup-close',
                '.ad-close',
                '.banner-close'
            ]
            
            for selector in popup_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            element.click()
                            time.sleep(0.5)
                except:
                    continue
            
            # Try to handle alert dialogs
            try:
                alert = self.driver.switch_to.alert
                alert.dismiss()
                self.driver.switch_to.default_content()
            except:
                pass
                
        except Exception as e:
            print(f"   Popup handling error: {e}")
    
    async def validate_content_with_deepseek(self, content: str, title: str, url: str) -> dict:
        """Use DeepSeek to validate if content is related to real estate transactions or market news"""
        try:
            cleaned_content = ' '.join(content.split())
            if len(cleaned_content) < 100:
                return {'is_relevant': False, 'type': 'N/A', 'reason': 'Content too short'}
            
            prompt = f"""
            Analyze this Hong Kong real estate article and determine:
            1. Is this related to real estate transactions or market news?
            2. What type is it: 'transaction' (property deals, sales, purchases) or 'news' (market analysis, trends, policies)?
            3. If transaction: extract key details like property name, value, location
            4. If news: provide a 2-3 sentence summary
            
            Title: {title}
            URL: {url}
            Content: {cleaned_content[:4000]}
            
            Respond in JSON format:
            {{
                "is_relevant": true/false,
                "type": "transaction" or "news" or "N/A",
                "summary": "brief summary if news",
                "transaction_value": "extracted value if transaction",
                "property_name": "extracted property name if transaction",
                "reason": "why relevant or not"
            }}
            """
            
            response = await self.ai_client.post('/chat/completions', json={
                'model': AI_CONFIG['model'],
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 500,
                'temperature': 0.1
            }, timeout=30.0)
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result['choices'][0]['message']['content'].strip()
                
                # Try to parse JSON response
                try:
                    # Extract JSON from response (sometimes AI adds extra text)
                    json_start = ai_response.find('{')
                    json_end = ai_response.rfind('}') + 1
                    if json_start != -1 and json_end != 0:
                        json_str = ai_response[json_start:json_end]
                        parsed = json.loads(json_str)
                        return parsed
                except:
                    pass
                
                # Fallback: simple keyword-based validation
                return self._fallback_validation(content, title)
            else:
                return self._fallback_validation(content, title)
                
        except Exception as e:
            print(f"   DeepSeek validation error: {e}")
            return self._fallback_validation(content, title)
    
    def _fallback_validation(self, content: str, title: str) -> dict:
        """Fallback validation using keywords"""
        text = (title + " " + content).lower()
        
        # Check for transaction keywords
        transaction_keywords = self.config['transaction_keywords']
        if any(keyword in text for keyword in transaction_keywords):
            return {
                'is_relevant': True,
                'type': 'transaction',
                'summary': 'Transaction detected by keywords',
                'transaction_value': self.extract_transaction_value(content),
                'property_name': 'N/A',
                'reason': 'Contains transaction keywords'
            }
        
        # Check for news keywords
        news_keywords = self.config['news_keywords']
        if any(keyword in text for keyword in news_keywords):
            return {
                'is_relevant': True,
                'type': 'news',
                'summary': 'Market news detected by keywords',
                'transaction_value': 0,
                'property_name': 'N/A',
                'reason': 'Contains news keywords'
            }
        
        return {
            'is_relevant': False,
            'type': 'N/A',
            'summary': 'N/A',
            'transaction_value': 0,
            'property_name': 'N/A',
            'reason': 'No relevant keywords found'
        }
    
    def extract_transaction_value(self, text: str) -> int:
        """Extract transaction value from text"""
        patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:億|億港元|億港幣|billion|億)',
            r'(\d+(?:\.\d+)?)\s*(?:萬|萬港元|萬港幣|million|萬)',
            r'(\d+(?:,\d{3})*)\s*(?:港元|港幣|HKD)',
            r'(\d+(?:\.\d+)?)\s*(?:億|億港元|億港幣|billion|億)',
            r'(\d+(?:\.\d+)?)\s*(?:萬|萬港元|萬港幣|million|萬)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    value = float(match.group(1).replace(',', ''))
                    if '億' in pattern or 'billion' in pattern:
                        return int(value * 100000000)
                    elif '萬' in pattern or 'million' in pattern:
                        return int(value * 10000)
                    else:
                        return int(value)
                except (ValueError, TypeError):
                    continue
        return 0
    
    def extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract main content using multiple strategies"""
        # Strategy 1: Try specific content selectors
        content_selectors = [
            'div.article-content', 'div.content', 'article', 'div.article-body',
            'div.post-content', 'div.article-text', 'div.story-content',
            'div.article-detail', 'div.article-main', 'div.article-detail-content',
            'div.article-main-content', 'div.article-text-content',
            'div.text-content', 'div.main-content', 'div.entry-content',
            'div.post-body', 'div.article-content-text', 'div.article-body-text',
            'div.article', 'div.story', 'div.news-content', 'div.news-body',
            'div.article-wrapper', 'div.article-container', 'div.article-inner',
            'div.article-content-wrapper', 'div.article-text-wrapper'
        ]
        
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                content = content_elem.get_text().strip()
                if len(content) > 100:  # Lowered threshold for more content
                    return content
        
        # Strategy 2: Find the largest text block
        text_blocks = []
        for elem in soup.find_all(['p', 'div', 'section', 'article']):
            text = elem.get_text().strip()
            if len(text) > 30:  # Lowered threshold
                text_blocks.append((len(text), text))
        
        if text_blocks:
            # Sort by length and take the largest blocks
            text_blocks.sort(reverse=True)
            main_content = ' '.join([block[1] for block in text_blocks[:8]])  # More blocks
            return main_content
        
        # Strategy 3: Get all text and filter
        all_text = soup.get_text()
        lines = [line.strip() for line in all_text.split('\n') if line.strip()]
        content_lines = []
        
        for line in lines:
            if len(line) > 15 and not any(skip in line.lower() for skip in [
                'cookie', 'privacy', 'terms', 'advertisement', 'subscribe', 'login',
                'share', 'comment', 'related', 'recommended', 'footer', 'header',
                'navigation', 'menu', 'sidebar', 'banner', 'popup', 'ad', 'ads',
                'sponsored', 'promotion', 'newsletter', 'sign up', 'register'
            ]):
                content_lines.append(line)
        
        return ' '.join(content_lines)
    
    def extract_article_date(self, soup: BeautifulSoup, url: str) -> str:
        """Extract article date using multiple strategies"""
        # Strategy 1: Look for date in meta tags
        date_selectors = [
            'meta[property="article:published_time"]',
            'meta[name="publish_date"]',
            'meta[name="date"]',
            'meta[name="pubdate"]',
            'meta[property="og:updated_time"]',
            'meta[name="lastmod"]'
        ]
        
        for selector in date_selectors:
            date_elem = soup.select_one(selector)
            if date_elem and date_elem.get('content'):
                try:
                    date_str = date_elem['content']
                    # Try to parse and format the date
                    if 'T' in date_str:
                        date_str = date_str.split('T')[0]
                    return datetime.strptime(date_str, '%Y-%m-%d').strftime('%d/%m/%Y')
                except:
                    pass
        
        # Strategy 2: Look for date in article content
        date_patterns = [
            r'(\d{4})年(\d{1,2})月(\d{1,2})日',
            r'(\d{1,2})/(\d{1,2})/(\d{4})',
            r'(\d{4})-(\d{1,2})-(\d{1,2})',
            r'(\d{1,2})\.(\d{1,2})\.(\d{4})',
            r'(\d{1,2})-(\d{1,2})-(\d{4})'
        ]
        
        text = soup.get_text()
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    if len(match.group(1)) == 4:  # Year first
                        year, month, day = match.groups()
                    else:  # Day first
                        day, month, year = match.groups()
                    return f"{int(day):02d}/{int(month):02d}/{year}"
                except:
                    pass
        
        # Strategy 3: Extract from URL
        url_patterns = [
            r'/(\d{4})/(\d{1,2})/(\d{1,2})/',
            r'(\d{4})_(\d{1,2})_(\d{1,2})',
            r'(\d{4})-(\d{1,2})-(\d{1,2})'
        ]
        
        for pattern in url_patterns:
            match = re.search(pattern, url)
            if match:
                try:
                    year, month, day = match.groups()
                    return f"{int(day):02d}/{int(month):02d}/{year}"
                except:
                    pass
        
        # Fallback: Use current date
        return datetime.now().strftime('%d/%m/%Y')
    
    async def scrape_hket(self) -> tuple:
        """Scrape HKET using ChromeDriver with infinite scrolling"""
        print("🔍 Scraping HKET...")
        transactions = []
        news = []
        
        if not self.driver:
            if not self.setup_chromedriver():
                return transactions, news
        
        try:
            # Navigate to HKET real estate page
            self.driver.get("https://ps.hket.com/srae005/即時樓市")
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Get page source and extract links
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                if '/article/' in href and href.startswith('http'):
                    links.append(href)
            
            print(f"   Found {len(links)} articles")
            
            # Process articles
            for i, url in enumerate(links[:20]):  # Process articles from the page
                try:
                    print(f"   Processing article {i+1}/{min(20, len(links))}")
                    self.driver.get(url)
                    time.sleep(1)
                    
                    # Handle any popups or ads
                    self.handle_popups_and_ads()
                    
                    article_html = self.driver.page_source
                    article_soup = BeautifulSoup(article_html, 'html.parser')
                    
                    # Extract title
                    title = article_soup.find('h1')
                    title_text = title.get_text().strip() if title else "N/A"
                    
                    # Extract main content
                    content = self.extract_main_content(article_soup)
                    
                    if len(content) < 50:  # Lowered threshold for more content
                        continue
                    
                    # Extract article date
                    article_date = self.extract_article_date(article_soup, url)
                    
                    # Validate content with DeepSeek
                    validation = await self.validate_content_with_deepseek(content, title_text, url)
                    
                    if not validation['is_relevant']:
                        continue
                    
                    if validation['type'] == 'transaction':
                        transaction_value = validation.get('transaction_value', 0) or self.extract_transaction_value(content)
                        
                        # Ensure transaction_value is an integer
                        if isinstance(transaction_value, str):
                            try:
                                transaction_value = int(transaction_value)
                            except:
                                transaction_value = 0
                        
                        if transaction_value >= 50000000:  # 50M HKD minimum
                            transaction = {
                                'property': validation.get('property_name', 'N/A'),
                                'district': 'N/A',
                                'asset_type': 'N/A',
                                'floor': 'N/A',
                                'unit': 'N/A',
                                'transaction_type': 'sales',
                                'date': article_date,
                                'transaction_price': transaction_value,
                                'area_basis': 'N/A',
                                'unit_basis': 'N/A',
                                'area_unit': 'N/A',
                                'unit_price': 'N/A',
                                'yield': 'N/A',
                                'seller_landlord': 'N/A',
                                'buyer_tenant': 'N/A',
                                'source': 'HKET',
                                'url': url,
                                'validation_reason': validation.get('reason', 'N/A')
                            }
                            transactions.append(transaction)
                    
                    elif validation['type'] == 'news':
                        news_item = {
                            'source': 'HKET',
                            'asset_type': 'N/A',
                            'topic': title_text,
                            'summary': validation.get('summary', 'N/A'),
                            'website': url,
                            'date': article_date,
                            'validation_reason': validation.get('reason', 'N/A')
                        }
                        news.append(news_item)
                        
                except Exception as e:
                    print(f"   Error processing article: {e}")
                    continue
                    
        except Exception as e:
            print(f"   ❌ Error scraping HKET: {e}")
        
        print(f"   ✅ Found {len(transactions)} transactions, {len(news)} news articles")
        return transactions, news
    
    async def scrape_wenweipo(self) -> tuple:
        """Scrape Wenweipo using ChromeDriver"""
        print("🔍 Scraping Wenweipo...")
        transactions = []
        news = []
        
        if not self.driver:
            if not self.setup_chromedriver():
                return transactions, news
        
        try:
            # Navigate to Wenweipo real estate page
            self.driver.get("http://paper.wenweipo.com/007ME/")
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Get page source and extract links
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.startswith('http') and 'wenweipo.com' in href:
                    links.append(href)
            
            print(f"   Found {len(links)} articles")
            
            # Process articles
            for i, url in enumerate(links[:15]):  # Process articles from the page
                try:
                    print(f"   Processing article {i+1}/{min(15, len(links))}")
                    self.driver.get(url)
                    time.sleep(1)
                    
                    # Handle any popups or ads
                    self.handle_popups_and_ads()
                    
                    article_html = self.driver.page_source
                    article_soup = BeautifulSoup(article_html, 'html.parser')
                    
                    # Extract title
                    title = article_soup.find('title')
                    title_text = title.get_text().strip() if title else "N/A"
                    
                    # Extract main content
                    content = self.extract_main_content(article_soup)
                    
                    if len(content) < 50:  # Lowered threshold for more content
                        continue
                    
                    # Extract article date
                    article_date = self.extract_article_date(article_soup, url)
                    
                    # Validate content with DeepSeek
                    validation = await self.validate_content_with_deepseek(content, title_text, url)
                    
                    if not validation['is_relevant']:
                        continue
                    
                    if validation['type'] == 'transaction':
                        transaction_value = validation.get('transaction_value', 0) or self.extract_transaction_value(content)
                        
                        # Ensure transaction_value is an integer
                        if isinstance(transaction_value, str):
                            try:
                                transaction_value = int(transaction_value)
                            except:
                                transaction_value = 0
                        
                        if transaction_value >= 50000000:  # 50M HKD minimum
                            transaction = {
                                'property': validation.get('property_name', 'N/A'),
                                'district': 'N/A',
                                'asset_type': 'N/A',
                                'floor': 'N/A',
                                'unit': 'N/A',
                                'transaction_type': 'sales',
                                'date': article_date,
                                'transaction_price': transaction_value,
                                'area_basis': 'N/A',
                                'unit_basis': 'N/A',
                                'area_unit': 'N/A',
                                'unit_price': 'N/A',
                                'yield': 'N/A',
                                'seller_landlord': 'N/A',
                                'buyer_tenant': 'N/A',
                                'source': 'Wenweipo',
                                'url': url,
                                'validation_reason': validation.get('reason', 'N/A')
                            }
                            transactions.append(transaction)
                    
                    elif validation['type'] == 'news':
                        news_item = {
                            'source': 'Wenweipo',
                            'asset_type': 'N/A',
                            'topic': title_text,
                            'summary': validation.get('summary', 'N/A'),
                            'website': url,
                            'date': article_date,
                            'validation_reason': validation.get('reason', 'N/A')
                        }
                        news.append(news_item)
                        
                except Exception as e:
                    print(f"   Error processing article: {e}")
                    continue
                    
        except Exception as e:
            print(f"   ❌ Error scraping Wenweipo: {e}")
        
        print(f"   ✅ Found {len(transactions)} transactions, {len(news)} news articles")
        return transactions, news
    
    async def scrape_stheadline(self) -> tuple:
        """Scrape Sing Tao Headline using ChromeDriver"""
        print("🔍 Scraping Sing Tao Headline...")
        transactions = []
        news = []
        
        if not self.driver:
            if not self.setup_chromedriver():
                return transactions, news
        
        try:
            # Navigate to Sing Tao Headline daily property page
            self.driver.get("https://www.stheadline.com/daily-property/")
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Get page source and extract links
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.startswith('http') and 'stheadline.com' in href:
                    links.append(href)
            
            print(f"   Found {len(links)} articles")
            
            # Process articles
            for i, url in enumerate(links[:15]):  # Process articles from the page
                try:
                    print(f"   Processing article {i+1}/{min(15, len(links))}")
                    self.driver.get(url)
                    time.sleep(1)
                    
                    article_html = self.driver.page_source
                    article_soup = BeautifulSoup(article_html, 'html.parser')
                    
                    # Extract title
                    title = article_soup.find('title')
                    title_text = title.get_text().strip() if title else "N/A"
                    
                    # Extract main content
                    content = self.extract_main_content(article_soup)
                    
                    if len(content) < 50:  # Lowered threshold for more content
                        continue
                    
                    # Extract article date
                    article_date = self.extract_article_date(article_soup, url)
                    
                    # Validate content with DeepSeek
                    validation = await self.validate_content_with_deepseek(content, title_text, url)
                    
                    if not validation['is_relevant']:
                        continue
                    
                    if validation['type'] == 'transaction':
                        transaction_value = validation.get('transaction_value', 0) or self.extract_transaction_value(content)
                        
                        # Ensure transaction_value is an integer
                        if isinstance(transaction_value, str):
                            try:
                                transaction_value = int(transaction_value)
                            except:
                                transaction_value = 0
                        
                        if transaction_value >= 50000000:  # 50M HKD minimum
                            transaction = {
                                'property': validation.get('property_name', 'N/A'),
                                'district': 'N/A',
                                'asset_type': 'N/A',
                                'floor': 'N/A',
                                'unit': 'N/A',
                                'transaction_type': 'sales',
                                'date': article_date,
                                'transaction_price': transaction_value,
                                'area_basis': 'N/A',
                                'unit_basis': 'N/A',
                                'area_unit': 'N/A',
                                'unit_price': 'N/A',
                                'yield': 'N/A',
                                'seller_landlord': 'N/A',
                                'buyer_tenant': 'N/A',
                                'source': 'Sing Tao Headline',
                                'url': url,
                                'validation_reason': validation.get('reason', 'N/A')
                            }
                            transactions.append(transaction)
                    
                    elif validation['type'] == 'news':
                        news_item = {
                            'source': 'Sing Tao Headline',
                            'asset_type': 'N/A',
                            'topic': title_text,
                            'summary': validation.get('summary', 'N/A'),
                            'website': url,
                            'date': article_date,
                            'validation_reason': validation.get('reason', 'N/A')
                        }
                        news.append(news_item)
                        
                except Exception as e:
                    print(f"   Error processing article: {e}")
                    continue
                    
        except Exception as e:
            print(f"   ❌ Error scraping Sing Tao Headline: {e}")
        
        print(f"   ✅ Found {len(transactions)} transactions, {len(news)} news articles")
        return transactions, news
    
    async def scrape_all_sources(self) -> dict:
        """Scrape all sources and return combined results"""
        print("🚀 Starting Hong Kong Real Estate Market Scraping")
        print("=" * 50)
        
        all_transactions = []
        all_news = []
        
        # Scrape each source
        hket_transactions, hket_news = await self.scrape_hket()
        all_transactions.extend(hket_transactions)
        all_news.extend(hket_news)
        
        wenweipo_transactions, wenweipo_news = await self.scrape_wenweipo()
        all_transactions.extend(wenweipo_transactions)
        all_news.extend(wenweipo_news)
        
        stheadline_transactions, stheadline_news = await self.scrape_stheadline()
        all_transactions.extend(stheadline_transactions)
        all_news.extend(stheadline_news)
        
        results = {
            'transactions': all_transactions,
            'news': all_news,
            'timestamp': datetime.now().isoformat(),
            'config_used': {
                'headless': self.config['scraping_config']['headless'],
                'min_transaction_value': self.config['report_config']['min_transaction_value']
            }
        }
        
        print("=" * 50)
        print(f"📊 FINAL RESULTS:")
        print(f"   Transactions: {len(all_transactions)}")
        print(f"   News Articles: {len(all_news)}")
        print(f"   Headless Mode: {self.config['scraping_config']['headless']}")
        print("=" * 50)
        
        return results

async def main():
    """Main function"""
    os.makedirs('output', exist_ok=True)
    
    async with ImprovedChromeDriverMarketScraper() as scraper:
        results = await scraper.scrape_all_sources()
        
        # Save results with proper naming
        date_str = datetime.now().strftime("%Y%m%d")
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_filename = f"output/hong_kong_real_estate_market_data_{timestamp_str}.json"
        
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Results saved to: {json_filename}")
        print("✅ Scraping completed successfully!")

if __name__ == "__main__":
    asyncio.run(main()) 