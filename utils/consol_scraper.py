#!/usr/bin/env python3
"""
Primary news source scraper — fetches articles with date filtering.
"""

import requests
import urllib3
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Optional
import time
import logging
import re
from .utils import load_config

logger = logging.getLogger(__name__)


class House852Scraper:
    """Scraper for the primary news source."""

    def __init__(self, config_path: str = "config.yml"):
        self.config = load_config(config_path)
        
        scraping = self.config['scraping']
        self.base_url = scraping['base_url']
        self.max_retries = scraping['max_retries']
        self.retry_delay = scraping['retry_delay']
        self.timeout = scraping['timeout']
        self.verify_ssl = scraping.get('verify_ssl', True)

        if not self.verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            logger.warning("SSL verification disabled — corporate proxy mode active")

        self.session = requests.Session()
        self.session.verify = self.verify_ssl
        self.session.headers.update({
            'User-Agent': scraping['user_agent'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-HK,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })
    
    def fetch_page(self, page: int) -> Optional[str]:
        """
        Fetch a single page from the website
        
        Args:
            page: Page number to fetch
            
        Returns:
            HTML content or None if failed
        """
        url = f"{self.base_url}?page={page}"

        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                return response.text
            except requests.exceptions.SSLError as e:
                # Corporate SSL inspection — retry once without verification
                if self.verify_ssl:
                    logger.warning(
                        "SSL certificate error detected (corporate proxy?). "
                        "Retrying without SSL verification. "
                        "Set verify_ssl: false in config.yml to silence this warning."
                    )
                    try:
                        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                        response = self.session.get(url, timeout=self.timeout, verify=False)
                        response.raise_for_status()
                        return response.text
                    except Exception as inner_e:
                        logger.error(f"Still failed after SSL bypass: {inner_e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"Failed to fetch page {page} after {self.max_retries} attempts (SSL error)")
                    print(f"  ✗ Cannot reach {url} — SSL error. If on a corporate network, set verify_ssl: false in config.yml")
                    return None
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"Attempt {attempt + 1}/{self.max_retries} — connection error for page {page}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"Failed to fetch page {page} — host unreachable")
                    print(f"  ✗ Cannot reach {url} — check your internet/VPN connection")
                    return None
            except requests.RequestException as e:
                logger.warning(f"Attempt {attempt + 1}/{self.max_retries} failed for page {page}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"Failed to fetch page {page} after {self.max_retries} attempts")
                    return None
    
    def parse_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse date string from the website
        
        Args:
            date_str: Date string (e.g., "2025-12-13")
            
        Returns:
            datetime object or None if parsing failed
        """
        try:
            return datetime.strptime(date_str.strip(), "%Y-%m-%d")
        except ValueError:
            logger.warning(f"Failed to parse date: {date_str}")
            return None
    
    def extract_news_items(self, html: str) -> List[Dict]:
        """
        Extract news items from a page HTML
        
        Args:
            html: HTML content of the page
            
        Returns:
            List of news items with title, link, date, and tags
        """
        soup = BeautifulSoup(html, 'html.parser')
        news_items = []
        
        # Find all news articles
        # Based on the structure, news items are in the main content area
        articles = soup.find_all('div', class_='news-item') or soup.find_all('article')
        
        # If the above doesn't work, try to find by heading tags
        if not articles:
            # Look for h5 tags with news titles
            headings = soup.find_all('h5')
            for heading in headings:
                # Get the link
                link_tag = heading.find('a')
                if not link_tag:
                    continue
                
                title = link_tag.get_text(strip=True)
                href = link_tag.get('href', '')
                
                # Make absolute URL
                if href and not href.startswith('http'):
                    full_url = f"https://852.house{href}" if href.startswith('/') else f"https://852.house/{href}"
                else:
                    full_url = href
                
                # Find date - look in parent row for small.text-muted element
                date_str = None
                # First find the parent row
                parent_row = heading.find_parent('div', class_='row')
                if parent_row:
                    # Look for small with text-muted class (contains date)
                    date_elem = parent_row.find('small', class_='text-muted')
                    if date_elem:
                        date_str = date_elem.get_text(strip=True)
                
                # Fallback to looking in immediate parent
                if not date_str:
                    parent = heading.find_parent()
                    if parent:
                        # Look for date in previous siblings or within parent
                        date_elem = parent.find('small', class_='text-muted')
                        if date_elem:
                            date_str = date_elem.get_text(strip=True)
                
                # Extract tags - look in the parent row or nearest container
                tags = []
                search_container = parent_row if parent_row else heading.find_parent()
                if search_container:
                    tag_elements = search_container.find_all('a', href=lambda x: x and 'tag=' in str(x))
                    for tag_elem in tag_elements:
                        tag_text = tag_elem.get_text(strip=True)
                        if tag_text:
                            tags.append(tag_text)
                
                # Get description/preview text - look for paragraph in the container
                description = ""
                if search_container:
                    # Look for paragraph or div with text
                    desc_elem = search_container.find('p') or search_container.find('div', class_='description')
                    if desc_elem:
                        description = desc_elem.get_text(strip=True)
                
                news_items.append({
                    'title': title,
                    'url': full_url,
                    'date': date_str,
                    'tags': tags,
                    'description': description
                })
        
        return news_items
    
    def fetch_article_content(self, url: str) -> Dict:
        """
        Fetch full content of a single article
        
        Args:
            url: URL of the article
            
        Returns:
            Dictionary with article details including source
        """
        for attempt in range(self.max_retries):
            try:
                try:
                    response = self.session.get(url, timeout=self.timeout)
                except requests.exceptions.SSLError:
                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                    response = self.session.get(url, timeout=self.timeout, verify=False)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract source from: <div class="px-md-1 px-2"><small><span class="mr-1">...</span><span class="mr-1">經濟日報</span></small></div>
                source = "Company C"  # Default
                try:
                    # First, try to find the div with class "px-md-1 px-2" which contains both date and source
                    metadata_div = soup.find('div', class_='px-md-1 px-2')
                    if metadata_div:
                        # Find all spans with mr-1 class within this div
                        span_tags = metadata_div.find_all('span', class_='mr-1')
                        for span in span_tags:
                            # Check if it contains an <i> tag with newspaper icon
                            icon = span.find('i')
                            if icon:
                                svg = icon.find('svg')
                                if svg:
                                    # Check SVG class for "newspaper" or "calendar"
                                    svg_class = svg.get('class', [])
                                    if isinstance(svg_class, list):
                                        svg_class_str = ' '.join(svg_class)
                                    else:
                                        svg_class_str = str(svg_class)
                                    
                                    # Check if it's a newspaper icon
                                    data_icon = svg.get('data-icon', '')
                                    path = svg.find('path')
                                    path_d = ''
                                    if path:
                                        path_d = path.get('d', '')
                                    
                                    # Newspaper icon indicators
                                    is_newspaper_icon = (
                                        'newspaper' in svg_class_str.lower() or 
                                        'M552 64H88' in path_d or 
                                        data_icon == 'newspaper'
                                    )
                                    # Calendar icon indicators
                                    is_calendar_icon = (
                                        'calendar' in svg_class_str.lower() or 
                                        'M400 64h-48V12' in path_d or 
                                        data_icon == 'calendar'
                                    )
                                    
                                    if is_newspaper_icon and not is_calendar_icon:
                                        # This is the newspaper icon span, extract source name directly
                                        # Get text after the icon (not including icon text)
                                        # Find all text nodes in the span and get the one after the icon
                                        icon_text = icon.get_text(strip=True)
                                        full_text = span.get_text(strip=True)
                                        # Remove the icon text if it's in the full text
                                        if icon_text in full_text:
                                            full_text = full_text.replace(icon_text, '').strip()
                                        
                                        # Remove any date-like patterns (YYYY-MM-DD)
                                        full_text = re.sub(r'\d{4}-\d{2}-\d{2}', '', full_text).strip()
                                        # Remove percentage patterns (like "51%")
                                        full_text = re.sub(r'\d+%', '', full_text).strip()
                                        # Remove any whitespace/formatting
                                        full_text = ' '.join(full_text.split())
                                        
                                        # Only use if it looks like a source name (not a number or percentage)
                                        if full_text and len(full_text) > 0 and not re.match(r'^[\d%\.]+$', full_text):
                                            # Use the extracted text as source directly (no matching needed)
                                            source = full_text
                                            break
                    
                    # Fallback: if we didn't find via the div, try finding all spans with mr-1 class
                    if source == "Company C":
                        span_tags = soup.find_all('span', class_='mr-1')
                        for span in span_tags:
                            icon = span.find('i')
                            if icon:
                                svg = icon.find('svg')
                                if svg:
                                    svg_class = svg.get('class', [])
                                    if isinstance(svg_class, list):
                                        svg_class_str = ' '.join(svg_class)
                                    else:
                                        svg_class_str = str(svg_class)
                                    
                                    data_icon = svg.get('data-icon', '')
                                    path = svg.find('path')
                                    path_d = ''
                                    if path:
                                        path_d = path.get('d', '')
                                    
                                    is_newspaper_icon = (
                                        'newspaper' in svg_class_str.lower() or 
                                        'M552 64H88' in path_d or 
                                        data_icon == 'newspaper'
                                    )
                                    is_calendar_icon = (
                                        'calendar' in svg_class_str.lower() or 
                                        'M400 64h-48V12' in path_d or 
                                        data_icon == 'calendar'
                                    )
                                    
                                    if is_newspaper_icon and not is_calendar_icon:
                                        # Get text after the icon
                                        icon_text = icon.get_text(strip=True)
                                        full_text = span.get_text(strip=True)
                                        if icon_text in full_text:
                                            full_text = full_text.replace(icon_text, '').strip()
                                        
                                        full_text = re.sub(r'\d{4}-\d{2}-\d{2}', '', full_text).strip()
                                        full_text = re.sub(r'\d+%', '', full_text).strip()
                                        full_text = ' '.join(full_text.split())
                                        
                                        # Only use if it looks like a source name (not a number or percentage)
                                        if full_text and len(full_text) > 0 and not re.match(r'^[\d%\.]+$', full_text):
                                            source = full_text
                                            break
                    
                    # Final fallback: try to find source in any span text (excluding dates and percentages)
                    if source == "Company C":
                        span_tags = soup.find_all('span', class_='mr-1')
                        for span in span_tags:
                            span_text = span.get_text(strip=True)
                            # Skip if it looks like a date
                            if re.match(r'^\d{4}-\d{2}-\d{2}', span_text):
                                continue
                            # Skip if it's just a number or percentage
                            if re.match(r'^[\d%\.]+$', span_text):
                                continue
                            # Use the text as source directly (if it's not empty and not a date/percentage)
                            if span_text and len(span_text) > 0:
                                source = span_text
                                break
                    
                    # Log if we still couldn't find source (for debugging)
                    if source == "Company C":
                        logger.debug(f"Could not extract source from URL: {url}")
                except Exception as e:
                    logger.debug(f"Could not extract source: {e}")
                
                # Extract article content
                content = ""
                
                # Try to find main content area
                article_body = soup.find('article') or soup.find('div', class_='article-content') or soup.find('div', class_='content')
                
                if article_body:
                    # Get all paragraphs
                    paragraphs = article_body.find_all('p')
                    content = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
                
                # If still no content, try to get all text from body
                if not content:
                    body = soup.find('body')
                    if body:
                        # Remove script and style elements
                        for script in body(["script", "style"]):
                            script.decompose()
                        content = body.get_text(strip=True)
                
                return {
                    'url': url,
                    'content': content,
                    'source': source,
                    'success': True
                }
                
            except requests.RequestException as e:
                logger.warning(f"Attempt {attempt + 1}/{self.max_retries} failed for article {url}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"Failed to fetch article {url} after {self.max_retries} attempts")
                    return {
                        'url': url,
                        'content': '',
                        'source': '852.house',
                        'success': False
                    }
    


