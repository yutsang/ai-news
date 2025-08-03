import os
import json
from datetime import datetime, timedelta
from typing import Dict, List

def load_config():
    """Load configuration from JSON file."""
    config_path = "config.json"
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        raise FileNotFoundError(f"Configuration file {config_path} not found")

# Load configuration
CONFIG = load_config()

# Extract configuration sections
NEWS_SOURCES = CONFIG['news_sources']
AI_CONFIG = CONFIG['ai_config']
TRANSACTION_KEYWORDS = CONFIG['transaction_keywords']
NEWS_KEYWORDS = CONFIG['news_keywords']
REPORT_CONFIG = CONFIG['report_config']
SCRAPING_CONFIG = CONFIG['scraping_config']
BIG_DEALS_BASELINE = CONFIG['big_deals_baseline']

def get_week_period(date: datetime = None) -> tuple:
    """
    Get the week period (Monday to Sunday) for the given date.
    If date is None, use current date.
    If current day is weekend, return last Monday to Sunday.
    If current day is weekday, return last full week.
    """
    if date is None:
        date = datetime.now()
    
    # If it's weekend (Saturday or Sunday), get last Monday to Sunday
    if date.weekday() >= 5:  # Saturday = 5, Sunday = 6
        # Go back to last Sunday
        days_to_subtract = date.weekday() - 5  # 0 for Saturday, 1 for Sunday
        date = date - timedelta(days=days_to_subtract + 1)
    
    # Get Monday of the week
    monday = date - timedelta(days=date.weekday())
    # Get Sunday of the week
    sunday = monday + timedelta(days=6)
    
    return monday, sunday

def get_last_full_week() -> tuple:
    """
    Get the last full week (Monday to Sunday).
    """
    today = datetime.now()
    # Go back to last Sunday
    days_to_subtract = (today.weekday() + 1) % 7
    last_sunday = today - timedelta(days=days_to_subtract)
    # Get Monday of that week
    last_monday = last_sunday - timedelta(days=6)
    
    return last_monday, last_sunday

def is_big_deal(transaction_data: Dict) -> bool:
    """
    Determine if a transaction is a big deal based on the baseline.
    """
    if not transaction_data or 'transaction_value' not in transaction_data:
        return False
    
    value = transaction_data.get('transaction_value', 0)
    property_type = transaction_data.get('property_type', 'commercial').lower()
    
    # Get baseline for property type
    baseline = BIG_DEALS_BASELINE.get(property_type, BIG_DEALS_BASELINE['commercial'])
    min_value = baseline['min_value']
    
    return value >= min_value

def get_property_type(text: str) -> str:
    """
    Determine property type from text.
    """
    text_lower = text.lower()
    
    if any(keyword in text_lower for keyword in ['住宅', 'residential', '樓盤', '新盤']):
        return 'residential'
    elif any(keyword in text_lower for keyword in ['寫字樓', 'office', '商廈']):
        return 'office'
    elif any(keyword in text_lower for keyword in ['商舖', 'shop', '零售']):
        return 'retail'
    elif any(keyword in text_lower for keyword in ['酒店', 'hotel']):
        return 'hotel'
    elif any(keyword in text_lower for keyword in ['地皮', 'land', '地塊']):
        return 'land'
    else:
        return 'commercial' 