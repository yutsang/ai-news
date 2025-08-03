#!/usr/bin/env python3
"""
Test HKET article extraction
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_hket_article():
    """Test extracting content from a specific HKET article."""
    
    # Test URL from the logs
    test_url = "https://ps.hket.com/article/3987686/%E7%9F%AD%E7%82%92%E7%8D%B2%E5%88%A9%EF%BD%9C%E7%82%92%E9%A2%A8%E8%94%93%E5%BB%B6%E8%87%B3%E8%B1%AA%E5%AE%85%20%E5%8C%97%E8%A7%92%E6%B5%B7%E7%92%8710%E5%80%8B%E6%9C%88%E7%82%92%E8%B2%B4263%E8%90%AC?mtc=80010"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            async with session.get(test_url, timeout=30) as response:
                print(f"Status: {response.status}")
                print(f"Headers: {dict(response.headers)}")
                
                if response.status == 200:
                    html = await response.text()
                    print(f"HTML length: {len(html)}")
                    print(f"First 500 chars: {html[:500]}")
                    
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Try to find title
                    title = soup.find('title')
                    if title:
                        print(f"Title: {title.get_text()}")
                    
                    # Try to find any content
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
                        '.entry-content',
                        'p',  # Just look for any paragraphs
                        'div'  # Look for any divs
                    ]
                    
                    for selector in content_selectors:
                        elements = soup.select(selector)
                        if elements:
                            print(f"Found {len(elements)} elements with selector: {selector}")
                            for i, elem in enumerate(elements[:3]):  # Show first 3
                                text = elem.get_text().strip()
                                if text and len(text) > 20:
                                    print(f"  Element {i+1}: {text[:100]}...")
                    
                    # Try to get all text
                    all_text = soup.get_text()
                    print(f"All text length: {len(all_text)}")
                    print(f"All text first 500 chars: {all_text[:500]}")
                    
                else:
                    print(f"Failed to get content: {response.status}")
                    
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_hket_article()) 