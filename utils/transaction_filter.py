#!/usr/bin/env python3
"""
Transaction filter — pre-screens articles by price/area before AI processing.
Only articles mentioning transactions >= 20M HKD or >= 2000 sqft pass through.
"""

import re
from typing import Dict, Optional


def extract_price(text: str) -> Optional[float]:
    """
    Extract price from text in millions HKD
    
    Args:
        text: Text containing price information
        
    Returns:
        Price in millions HKD, or None if not found
    """
    # Pattern for prices like: 2000萬, 2億, $20M, HK$2000萬, 20,000,000
    patterns = [
        r'(\d+\.?\d*)\s*億',  # X億
        r'(\d+,?\d*)\s*萬',   # X萬
        r'\$?\s*(\d+\.?\d*)\s*[Mm]',  # $XM or XM
        r'HK\$?\s*([\d,]+)',  # HK$X,XXX,XXX
        r'(\d{1,3}(?:,\d{3})+)',  # X,XXX,XXX format
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                # Remove commas
                value = match.replace(',', '')
                num = float(value)
                
                # Convert based on unit
                if '億' in text:
                    return num * 100  # 億 = 100M
                elif '萬' in text:
                    return num / 100  # 萬 = 0.01M
                elif 'M' in text.upper():
                    return num
                else:
                    # Assume it's in actual currency, convert to millions
                    return num / 1_000_000
            except ValueError:
                continue
    
    return None


def extract_area(text: str) -> Optional[float]:
    """
    Extract area from text in square feet
    
    Args:
        text: Text containing area information
        
    Returns:
        Area in square feet, or None if not found
    """
    # Patterns for area: 2000呎, 2,000平方呎, 2000 sq ft, 2000尺
    patterns = [
        r'(\d+,?\d*)\s*(?:平方呎|平方尺|呎|尺|sqft|sq\.?\s*ft)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                # Remove commas
                value = match.replace(',', '')
                return float(value)
            except ValueError:
                continue
    
    return None


def should_process_article(article: Dict, min_price_m: float = 20.0, min_area_sqft: float = 2000.0) -> bool:
    """
    Check if article should be processed based on price and area criteria
    Only include completed transactions, not listings
    
    Args:
        article: Article dictionary with title, description, etc.
        min_price_m: Minimum price in millions HKD (default: 20M)
        min_area_sqft: Minimum area in square feet (default: 2000)
        
    Returns:
        True if article meets criteria, False otherwise
    """
    # Combine all text for analysis
    text = f"{article.get('title', '')} {article.get('description', '')}"
    
    # Exclude listings (叫價, 放盤, 招租, 放售)
    listing_keywords = ['叫價', '放盤', '招租', '放售', '開價', '意向價']
    if any(keyword in text for keyword in listing_keywords):
        return False
    
    # Must have transaction keywords (成交, 沽, 售, 租出, 易手)
    transaction_keywords = ['成交', '沽', '售出', '租出', '易手', '賣', '買入']
    has_transaction = any(keyword in text for keyword in transaction_keywords)
    
    if not has_transaction:
        return False
    
    # Extract price and area
    price = extract_price(text)
    area = extract_area(text)
    
    # Check if meets criteria
    has_high_price = price is not None and price >= min_price_m
    has_large_area = area is not None and area >= min_area_sqft
    
    # Article should have either high price OR large area
    # (some articles mention only price, some only area)
    if has_high_price or has_large_area:
        return True
    
    # If we can't extract price/area but it's a transaction, include it
    # (some articles mention transactions without explicit numbers)
    # This helps capture more data
    if has_transaction:
        # Include if it mentions significant amounts (億, 千萬, etc.) even if we can't parse exact number
        significant_amount_keywords = ['億', '千萬', '百萬', '萬', 'million', 'M']
        if any(keyword in text for keyword in significant_amount_keywords):
            return True
        # Include if it mentions area (呎, sqft, etc.) even if we can't parse exact number
        area_keywords = ['呎', '尺', 'sqft', '平方']
        if any(keyword in text for keyword in area_keywords):
            return True
    
    return False


def filter_transactions(articles: list, min_price_m: float = 20.0, min_area_sqft: float = 2000.0) -> tuple:
    """
    Filter articles to only include significant transactions
    
    Args:
        articles: List of article dictionaries
        min_price_m: Minimum price in millions HKD (default: 10M)
        min_area_sqft: Minimum area in square feet (default: 1000)
        
    Returns:
        Tuple of (filtered_articles, total_count, filtered_count)
    """
    filtered = []
    
    for article in articles:
        if should_process_article(article, min_price_m, min_area_sqft):
            filtered.append(article)
    
    return filtered, len(articles), len(filtered)



