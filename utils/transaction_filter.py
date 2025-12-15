#!/usr/bin/env python3
"""
Transaction Filter - Pre-filter articles before AI processing
Only process high-value transactions: >20M HKD and >=2000 sqft
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
    return has_high_price or has_large_area


def filter_transactions(articles: list, min_price_m: float = 20.0, min_area_sqft: float = 2000.0) -> tuple:
    """
    Filter articles to only include high-value transactions
    
    Args:
        articles: List of article dictionaries
        min_price_m: Minimum price in millions HKD
        min_area_sqft: Minimum area in square feet
        
    Returns:
        Tuple of (filtered_articles, total_count, filtered_count)
    """
    filtered = []
    
    for article in articles:
        if should_process_article(article, min_price_m, min_area_sqft):
            filtered.append(article)
    
    return filtered, len(articles), len(filtered)


def should_include_news_article(article: Dict) -> bool:
    """
    Filter news articles based on criteria:
    1. Not for specific properties only (general market news, not individual property listings)
    2. No "專欄作家" (columnist) articles
    3. Only related to valuation of real estate
    4. Only HK real estate news
    
    Args:
        article: Article dictionary with title, description, content, etc.
        
    Returns:
        True if article should be included, False otherwise
    """
    # Combine all text for analysis
    title = article.get('title', '')
    description = article.get('description', '')
    content = article.get('full_content', '')
    tags = ' '.join(article.get('tags', []))
    
    text = f"{title} {description} {content} {tags}".lower()
    
    # 1. Exclude columnist articles (專欄作家)
    columnist_keywords = ['專欄作家', '專欄', '專欄作者', '作者專欄', '專欄文章']
    if any(keyword in text for keyword in columnist_keywords):
        return False
    
    # 2. Exclude specific property-only articles (individual property listings/transactions)
    # These are usually about a single property transaction, not market trends
    specific_property_keywords = [
        '成交', '沽', '售', '租出', '易手',  # Transaction keywords
        '呎價', '成交價', '售價', '租金'  # Price keywords that suggest specific transaction
    ]
    
    # If it's about a specific property transaction (not market analysis), exclude
    # But we need to be careful - some market news might mention transactions as examples
    # So we check if it's ONLY about a specific property without market context
    has_specific_transaction = any(keyword in text for keyword in specific_property_keywords)
    
    # Market analysis keywords that indicate general market news
    market_keywords = [
        '市場', '趨勢', '走勢', '分析', '估值', '評估', '價格指數', 
        '樓價', '租金', '回報率', '空置率', '供應', '需求',
        '政策', '措施', '發展', '規劃', '前景', '展望'
    ]
    has_market_context = any(keyword in text for keyword in market_keywords)
    
    # If it's a specific transaction without market context, exclude
    if has_specific_transaction and not has_market_context:
        return False
    
    # 3. Exclude non-valuation related articles (building quality, complaints, etc.)
    non_valuation_keywords = [
        '質素', '差誤', '投訴', '驗收', '手工', '空鼓', '用料', '售樓書',  # Building quality issues
        '投訴機制', '品質', '缺陷', '問題', '維修', '保養',  # Quality/complaint keywords
        '業主會', '管理費', '物業管理', '法團'  # Property management (not valuation)
    ]
    # If article is primarily about quality/complaints without valuation context, exclude
    has_non_valuation = any(keyword in text for keyword in non_valuation_keywords)
    if has_non_valuation:
        # Check if it also has valuation context - if not, exclude
        valuation_keywords = [
            '估值', '評估', '估價', '價值', '價格', '樓價', '租金', '呎價',
            '市場', '趨勢', '走勢', '分析', '回報', '回報率', '空置率',
            '供應', '需求', '成交', '交易', '地產', '物業', '房地產'
        ]
        has_valuation_context = any(keyword in text for keyword in valuation_keywords)
        # If it's about quality/complaints but has no valuation context, exclude
        if not has_valuation_context:
            return False
    
    # 4. Only include real estate valuation-related news
    valuation_keywords = [
        '估值', '評估', '估價', '價值', '價格', '樓價', '租金', '呎價',
        '市場', '趨勢', '走勢', '分析', '回報', '回報率', '空置率',
        '供應', '需求', '成交', '交易', '地產', '物業', '房地產'
    ]
    has_valuation_context = any(keyword in text for keyword in valuation_keywords)
    
    if not has_valuation_context:
        return False
    
    # 5. Only HK real estate news
    hk_keywords = [
        '香港', 'hk', 'hong kong', '港', '本港', '本地',
        '中環', '金鐘', '銅鑼灣', '尖沙咀', '九龍', '新界', '港島'
    ]
    has_hk_context = any(keyword in text for keyword in hk_keywords)
    
    # If no HK context, might still be relevant if it's about HK real estate market
    # But be more strict - require some indication it's about HK
    if not has_hk_context:
        # Check if it's clearly about other regions
        other_regions = ['內地', '中國', '大陸', '台灣', '澳門', '新加坡', '日本', '美國', '英國']
        if any(region in text for region in other_regions):
            return False
    
    return True


def filter_news_articles(articles: list) -> tuple:
    """
    Filter news articles based on criteria
    
    Args:
        articles: List of article dictionaries
        
    Returns:
        Tuple of (filtered_articles, total_count, filtered_count)
    """
    filtered = []
    
    for article in articles:
        if should_include_news_article(article):
            filtered.append(article)
    
    return filtered, len(articles), len(filtered)


if __name__ == "__main__":
    # Test cases
    test_articles = [
        {
            'title': '御林皇府洋房3千萬沽 設計師20年蝕11%',
            'description': '實用面積2,500平方呎，成交價3000萬元'
        },
        {
            'title': '小型單位500萬易手',
            'description': '面積400呎'
        },
        {
            'title': '豪宅1.2億成交創新高',
            'description': '頂層複式單位'
        },
        {
            'title': '大型單位2500呎 售價1800萬',
            'description': '三房兩廳'
        }
    ]
    
    for article in test_articles:
        result = should_process_article(article)
        text = f"{article['title']} - {article['description']}"
        price = extract_price(text)
        area = extract_area(text)
        print(f"\nTitle: {article['title']}")
        print(f"  Price: {price}M HKD, Area: {area} sqft")
        print(f"  Should process: {result}")

