#!/usr/bin/env python3
"""
Enhanced ChromeDriver Hong Kong Real Estate Market Scraper
With two-stage validation and improved transaction filtering
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
from datetime import datetime, timedelta
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

class EnhancedChromeDriverMarketScraper:
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
    
    async def validate_topic_with_deepseek(self, title: str, url: str) -> dict:
        """Stage 1: Use DeepSeek to validate if topic is relevant to real estate"""
        try:
            prompt = f"""
            Analyze this Hong Kong real estate article title and determine if it's relevant to real estate transactions or market news.
            
            Title: {title}
            URL: {url}
            
            Respond in JSON format:
            {{
                "is_relevant": true/false,
                "type": "transaction" or "news" or "N/A",
                "reason": "brief reason why relevant or not"
            }}
            """
            
            response = await self.ai_client.post('/chat/completions', json={
                'model': AI_CONFIG['model'],
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 200,
                'temperature': 0.1
            }, timeout=15.0)
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result['choices'][0]['message']['content'].strip()
                
                # Try to parse JSON response
                try:
                    json_start = ai_response.find('{')
                    json_end = ai_response.rfind('}') + 1
                    if json_start != -1 and json_end != 0:
                        json_str = ai_response[json_start:json_end]
                        parsed = json.loads(json_str)
                        return parsed
                except:
                    pass
            
            # Fallback: simple keyword-based validation
            return self._fallback_topic_validation(title)
                
        except Exception as e:
            print(f"   DeepSeek topic validation error: {e}")
            return self._fallback_topic_validation(title)
    
    def _fallback_topic_validation(self, title: str) -> dict:
        """Fallback topic validation using keywords"""
        text = title.lower()
        
        # Check for transaction keywords
        transaction_keywords = self.config['transaction_keywords']
        if any(keyword in text for keyword in transaction_keywords):
            return {
                'is_relevant': True,
                'type': 'transaction',
                'reason': 'Contains transaction keywords'
            }
        
        # Check for news keywords
        news_keywords = self.config['news_keywords']
        if any(keyword in text for keyword in news_keywords):
            return {
                'is_relevant': True,
                'type': 'news',
                'reason': 'Contains news keywords'
            }
        
        return {
            'is_relevant': False,
            'type': 'N/A',
            'reason': 'No relevant keywords found'
        }
    
    async def validate_content_with_deepseek(self, content: str, title: str, url: str) -> dict:
        """Stage 2: Use DeepSeek to validate content and extract details"""
        try:
            cleaned_content = ' '.join(content.split())
            if len(cleaned_content) < 100:
                return {'is_relevant': False, 'type': 'N/A', 'reason': 'Content too short'}
            
            prompt = f"""
            Analyze this Hong Kong real estate article content and determine:
            1. Is this related to real estate transactions or market news?
            2. What type is it: 'transaction' (property deals, sales, purchases) or 'news' (market analysis, trends, policies)?
            3. If transaction: extract key details like property name, value, location, area
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
                "area_sqft": "extracted area in square feet if transaction",
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
            print(f"   DeepSeek content validation error: {e}")
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
                'area_sqft': self.extract_area_sqft(content),
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
                'area_sqft': 0,
                'reason': 'Contains news keywords'
            }
        
        return {
            'is_relevant': False,
            'type': 'N/A',
            'summary': 'N/A',
            'transaction_value': 0,
            'property_name': 'N/A',
            'area_sqft': 0,
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
    
    def extract_area_sqft(self, text: str) -> int:
        """Extract area in square feet from text"""
        patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:平方呎|sq ft|sqft|呎|ft²)',
            r'(\d+(?:,\d{3})*)\s*(?:平方呎|sq ft|sqft|呎|ft²)',
            r'(\d+(?:\.\d+)?)\s*(?:平方米|sq m|sqm|m²)',
            r'(\d+(?:,\d{3})*)\s*(?:平方米|sq m|sqm|m²)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    value = float(match.group(1).replace(',', ''))
                    # Convert square meters to square feet (1 sq m = 10.764 sq ft)
                    if '平方米' in pattern or 'sq m' in pattern or 'sqm' in pattern or 'm²' in pattern:
                        return int(value * 10.764)
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
    
    def get_last_week_dates(self) -> tuple:
        """Get last Monday to Friday dates"""
        today = datetime.now()
        
        # For testing: use a broader range to include recent articles
        # Start from 7 days ago to include more recent content
        start_date = today - timedelta(days=7)
        end_date = today
        
        return start_date, end_date
    
    def is_date_in_range(self, article_date: str, start_date: datetime, end_date: datetime) -> bool:
        """Check if article date is within the specified range"""
        try:
            # Parse article date (dd/mm/yyyy format)
            day, month, year = article_date.split('/')
            article_dt = datetime(int(year), int(month), int(day))
            
            # Check if date is within range (inclusive)
            return start_date <= article_dt <= end_date
        except:
            # If date parsing fails, assume it's recent and include it
            return True
    
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
    
    async def scrape_source(self, source_name: str, url: str = None) -> tuple:
        """Generic method to scrape any source using config URLs"""
        print(f"🔍 Scraping {source_name}...")
        transactions = []
        news = []
        
        if not self.driver:
            if not self.setup_chromedriver():
                return transactions, news
        
        # Get date range for filtering
        start_date, end_date = self.get_last_week_dates()
        print(f"   📅 Filtering for articles from {start_date.strftime('%d/%m/%Y')} to {end_date.strftime('%d/%m/%Y')}")
        
        try:
            # Get source config
            source_config = self.config['news_sources'][source_name.lower()]
            
            # Use provided URL or fall back to configured property_url
            if url is None:
                url = source_config['property_url']
            
            # Step 1: Navigate to property news list page
            print(f"   📄 Loading property news list: {url}")
            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Step 2: Scroll through the list to load more content
            print(f"   📜 Scrolling to load more articles...")
            scroll_count = 0
            max_scrolls = 50  # Reduced for faster processing
            
            while scroll_count < max_scrolls:
                # Scroll down
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                scroll_count += 1
                if scroll_count % 10 == 0:
                    print(f"   Scrolled {scroll_count} times...")
            
            # Step 3: Extract all article links and titles from the list
            print(f"   🔍 Extracting article links and titles from list...")
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract ALL links from the page - let AI filter them
            print(f"   🔍 Extracting ALL links from the page...")
            
            # Get all links from the page
            all_links = soup.find_all('a', href=True)
            print(f"   Found {len(all_links)} total links on the page")
            
            # Filter out common non-article links
            filtered_links = []
            for link in all_links:
                href = link.get('href', '').strip()
                if href and href != '#' and href != '/' and not href.startswith('javascript:'):
                    # Skip common navigation and utility links
                    skip_patterns = [
                        '/login', '/register', '/search', '/contact', '/about',
                        '/privacy', '/terms', '/cookie', '/sitemap', '/rss',
                        'facebook.com', 'twitter.com', 'instagram.com', 'youtube.com',
                        '.pdf', '.jpg', '.png', '.gif', '.css', '.js'
                    ]
                    
                    should_skip = any(pattern in href.lower() for pattern in skip_patterns)
                    if not should_skip:
                        filtered_links.append(link)
            
            print(f"   Filtered to {len(filtered_links)} potential article links")
            items = filtered_links
            
            # Extract links and titles
            article_items = []
            for item in items:
                try:
                    # Find link
                    link_elem = item.find('a', href=True) if item.name != 'a' else item
                    if not link_elem:
                        continue
                    
                    href = link_elem.get('href')
                    if not href:
                        continue
                    
                    # Convert relative URLs to absolute URLs
                    if not href.startswith('http'):
                        if href.startswith('/'):
                            # Absolute path on same domain
                            from urllib.parse import urljoin
                            href = urljoin(url, href)
                        else:
                            # Relative path
                            from urllib.parse import urljoin
                            href = urljoin(url, href)
                    
                    # Find title with multiple strategies
                    title_text = "N/A"
                    
                    # Strategy 1: Look for title in common elements
                    title_elem = item.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'span', 'div', 'a'])
                    if title_elem:
                        title_text = title_elem.get_text().strip()
                    
                    # Strategy 2: If title is too short or "N/A", try to extract from link text
                    if title_text == "N/A" or len(title_text) < 5:
                        if item.name == 'a':
                            title_text = item.get_text().strip()
                        else:
                            link_elem = item.find('a')
                            if link_elem:
                                title_text = link_elem.get_text().strip()
                    
                    # Strategy 3: If still no title, try to extract from URL
                    if title_text == "N/A" or len(title_text) < 5:
                        if href:
                            # Try to extract meaningful text from URL
                            url_parts = href.split('/')
                            if len(url_parts) > 1:
                                last_part = url_parts[-1]
                                if last_part and len(last_part) > 5:
                                    title_text = last_part.replace('-', ' ').replace('_', ' ')
                    
                    # Clean up title
                    if title_text and title_text != "N/A":
                        title_text = title_text.replace('\n', ' ').replace('\r', ' ').strip()
                        # Remove excessive whitespace
                        title_text = ' '.join(title_text.split())
                    
                    # Find date (if available in the list item)
                    date_elem = item.find(['time', 'span', 'div'], class_=lambda x: x and any(word in x.lower() for word in ['date', 'time', 'published']))
                    date_text = date_elem.get_text().strip() if date_elem else None
                    
                    article_items.append({
                        'url': href,
                        'title': title_text,
                        'date': date_text
                    })
                    
                except Exception as e:
                    continue
            
            # Remove duplicates
            seen_urls = set()
            unique_items = []
            for item in article_items:
                if item['url'] not in seen_urls:
                    seen_urls.add(item['url'])
                    unique_items.append(item)
            
            print(f"   📋 Found {len(unique_items)} unique articles in list")
            
            # Step 4: Use AI to filter relevant articles from the list
            print(f"   🤖 Using AI to filter relevant articles...")
            relevant_items = []
            
            for i, item in enumerate(unique_items[:100]):  # Limit to first 100 for efficiency
                try:
                    print(f"   Checking article {i+1}/{min(100, len(unique_items))}: {item['title'][:50]}...")
                    
                    # Use AI to check if this article is relevant
                    topic_validation = await self.validate_topic_with_deepseek(item['title'], item['url'])
                    
                    if topic_validation['is_relevant']:
                        relevant_items.append(item)
                        print(f"   ✅ Relevant: {topic_validation['reason']}")
                    else:
                        print(f"   ❌ Skipped: {topic_validation['reason']}")
                        
                except Exception as e:
                    print(f"   Error checking article: {e}")
                    continue
            
            print(f"   🎯 AI identified {len(relevant_items)} relevant articles")
            
            # Step 5: Visit only the relevant articles for detailed analysis
            print(f"   📖 Processing relevant articles for detailed analysis...")
            
            for i, item in enumerate(relevant_items):
                try:
                    print(f"   Processing relevant article {i+1}/{len(relevant_items)}: {item['title'][:50]}...")
                    
                    self.driver.get(item['url'])
                    time.sleep(1)
                    
                    # Handle any popups or ads
                    self.handle_popups_and_ads()
                    
                    article_html = self.driver.page_source
                    article_soup = BeautifulSoup(article_html, 'html.parser')
                    
                    # Extract main content
                    content = self.extract_main_content(article_soup)
                    
                    if len(content) < 50:
                        print(f"   ⚠️ Content too short, skipping...")
                        continue
                    
                    # Extract article date
                    article_date = self.extract_article_date(article_soup, item['url'])
                    
                    # Check if article is within date range
                    if not self.is_date_in_range(article_date, start_date, end_date):
                        print(f"   ⏰ Date {article_date} outside range, skipping...")
                        continue
                    
                    # Use AI to analyze content and extract details
                    validation = await self.validate_content_with_deepseek(content, item['title'], item['url'])
                    
                    if not validation['is_relevant']:
                        print(f"   ❌ Content not relevant: {validation['reason']}")
                        continue
                    
                    if validation['type'] == 'transaction':
                        transaction_value = validation.get('transaction_value', 0) or self.extract_transaction_value(content)
                        area_sqft = validation.get('area_sqft', 0) or self.extract_area_sqft(content)
                        
                        # Ensure transaction_value is an integer
                        if isinstance(transaction_value, str):
                            try:
                                transaction_value = int(transaction_value)
                            except:
                                transaction_value = 0
                        
                        # Ensure area_sqft is an integer
                        if isinstance(area_sqft, str):
                            try:
                                area_sqft = int(area_sqft)
                            except:
                                area_sqft = 0
                        
                        # Filter: 30M HKD or 3000 sq ft minimum
                        min_value = self.config['report_config']['min_transaction_value']  # 30M HKD
                        min_area = self.config['report_config']['min_area_for_ai_analysis']  # 3000 sq ft
                        
                        if transaction_value >= min_value or area_sqft >= min_area:
                            transaction = {
                                'property': validation.get('property_name', 'N/A'),
                                'district': 'N/A',
                                'asset_type': 'N/A',
                                'floor': 'N/A',
                                'unit': 'N/A',
                                'transaction_type': 'sales',
                                'date': article_date,
                                'transaction_price': transaction_value,
                                'area_sqft': area_sqft,
                                'area_basis': 'N/A',
                                'unit_basis': 'N/A',
                                'area_unit': 'N/A',
                                'unit_price': 'N/A',
                                'yield': 'N/A',
                                'seller_landlord': 'N/A',
                                'buyer_tenant': 'N/A',
                                'source': source_config['name'],
                                'url': item['url'],
                                'validation_reason': validation.get('reason', 'N/A')
                            }
                            transactions.append(transaction)
                            print(f"   💰 Transaction added: {transaction_value:,} HKD")
                    
                    elif validation['type'] == 'news':
                        news_item = {
                            'source': source_config['name'],
                            'asset_type': 'N/A',
                            'topic': item['title'],
                            'summary': validation.get('summary', 'N/A'),
                            'website': item['url'],
                            'date': article_date,
                            'validation_reason': validation.get('reason', 'N/A')
                        }
                        news.append(news_item)
                        print(f"   📰 News added: {validation.get('summary', 'N/A')[:50]}...")
                        
                except Exception as e:
                    print(f"   Error processing article: {e}")
                    continue
                    
        except Exception as e:
            print(f"   ❌ Error scraping {source_name}: {e}")
        
        print(f"   ✅ Found {len(transactions)} transactions, {len(news)} news articles")
        return transactions, news
    
    async def scrape_all_sources(self) -> dict:
        """Scrape all sources and return combined results"""
        print("🚀 Starting Hong Kong Real Estate Market Scraping")
        print("=" * 50)
        
        all_transactions = []
        all_news = []
        
        # Define sources with their URLs
        sources_config = {
            'hket': ['https://ps.hket.com/srae005/即時樓市'],
            'wenweipo': [
                'http://paper.wenweipo.com/007ME/',
                'https://www.wenweipo.com/business/real-estate'
            ],
            'stheadline': ['https://www.stheadline.com/daily-property/']
        }
        
        for source_name, urls in sources_config.items():
            print(f"🔍 Scraping {source_name}...")
            
            for url in urls:
                print(f"   📄 Processing URL: {url}")
                transactions, news = await self.scrape_source(source_name, url)
                all_transactions.extend(transactions)
                all_news.extend(news)
        
        results = {
            'transactions': all_transactions,
            'news': all_news,
            'timestamp': datetime.now().isoformat(),
            'config_used': {
                'headless': self.config['scraping_config']['headless'],
                'min_transaction_value': self.config['report_config']['min_transaction_value'],
                'min_area_sqft': self.config['report_config']['min_area_for_ai_analysis']
            }
        }
        
        print("=" * 50)
        print(f"📊 FINAL RESULTS:")
        print(f"   Transactions: {len(all_transactions)}")
        print(f"   News Articles: {len(all_news)}")
        print(f"   Headless Mode: {self.config['scraping_config']['headless']}")
        print(f"   Min Transaction Value: {self.config['report_config']['min_transaction_value']:,} HKD")
        print(f"   Min Area: {self.config['report_config']['min_area_for_ai_analysis']} sq ft")
        print("=" * 50)
        
        return results

async def main():
    """Main function"""
    os.makedirs('output', exist_ok=True)
    
    async with EnhancedChromeDriverMarketScraper() as scraper:
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