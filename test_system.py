#!/usr/bin/env python3
"""
Test script for the AI Market News Review System

This script tests the core functionality without making actual API calls
or web scraping requests.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List

from config import get_week_period, get_last_full_week, REPORT_CONFIG
from ai_summarizer import DeepSeekSummarizer
from report_generator import ReportGenerator

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_mock_data():
    """
    Create mock data for testing the system.
    """
    # Mock transactions
    mock_transactions = [
        {
            'source': 'HKET',
            'title': '中環甲級寫字樓成交價創新高',
            'content': '中環一棟甲級寫字樓以15億港元成交，創下該區寫字樓成交價新高。該物業位於中環核心商業區，總樓面面積約20,000平方呎。',
            'url': 'https://example.com/article1',
            'date': datetime.now() - timedelta(days=2),
            'type': 'transaction',
            'transaction_data': {
                'property_name': '中環甲級寫字樓',
                'transaction_value': 1500000000,
                'transaction_type': 'sale',
                'location': '中環',
                'date': datetime.now() - timedelta(days=2),
                'area': 20000,
                'unit_price': 75000
            }
        },
        {
            'source': '文匯報',
            'title': '尖沙咀商舖租金回升',
            'content': '尖沙咀區商舖租金在過去一個月回升5%，顯示零售市場開始復甦。主要受惠於內地遊客回流和本地消費增加。',
            'url': 'https://example.com/article2',
            'date': datetime.now() - timedelta(days=3),
            'type': 'transaction',
            'transaction_data': {
                'property_name': '尖沙咀商舖',
                'transaction_value': 5000000,
                'transaction_type': 'lease',
                'location': '尖沙咀',
                'date': datetime.now() - timedelta(days=3),
                'area': 1000,
                'unit_price': 5000
            }
        }
    ]
    
    # Mock news articles
    mock_news = [
        {
            'source': '星島頭條',
            'title': '香港樓市展望：2024年市場趨勢分析',
            'content': '根據最新市場分析，香港樓市在2024年將面臨新的挑戰和機遇。利率環境、經濟復甦和政策調整將是影響市場的主要因素。',
            'url': 'https://example.com/news1',
            'date': datetime.now() - timedelta(days=1),
            'type': 'news'
        },
        {
            'source': 'HKET',
            'title': '政府推出新樓市政策',
            'content': '政府宣布推出新的樓市政策，旨在穩定市場並支持首次置業者。新政策包括調整印花稅和放寬按揭限制。',
            'url': 'https://example.com/news2',
            'date': datetime.now() - timedelta(days=4),
            'type': 'news'
        }
    ]
    
    return {
        'transactions': mock_transactions,
        'news': mock_news
    }

async def test_ai_summarizer():
    """
    Test the AI summarizer with mock data.
    """
    logger.info("Testing AI Summarizer...")
    
    # Create mock data
    mock_data = create_mock_data()
    
    # Initialize summarizer with API key from config
    from config import AI_CONFIG
    summarizer = DeepSeekSummarizer(AI_CONFIG['api_key'])
    
    # Test transaction summarization
    try:
        transaction_summary = await summarizer.summarize_transactions(mock_data['transactions'])
        logger.info("✓ Transaction summarization test completed")
        logger.info(f"  - Found {transaction_summary.get('transaction_count', 0)} transactions")
        logger.info(f"  - Total value: {transaction_summary.get('total_value', 0):,.0f} HKD")
    except Exception as e:
        logger.warning(f"⚠ Transaction summarization test failed (expected without API key): {e}")
    
    # Test news summarization
    try:
        news_summary = await summarizer.summarize_news(mock_data['news'])
        logger.info("✓ News summarization test completed")
        logger.info(f"  - Found {news_summary.get('article_count', 0)} articles")
    except Exception as e:
        logger.warning(f"⚠ News summarization test failed (expected without API key): {e}")
    
    # Test weekly report generation
    try:
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        report = await summarizer.generate_weekly_report(
            mock_data['transactions'], 
            mock_data['news'], 
            start_date, 
            end_date
        )
        logger.info("✓ Weekly report generation test completed")
        logger.info(f"  - Report period: {report['period']['start_date']} to {report['period']['end_date']}")
        logger.info(f"  - Statistics: {report['statistics']}")
    except Exception as e:
        logger.warning(f"⚠ Weekly report generation test failed (expected without API key): {e}")

def test_report_generator():
    """
    Test the report generator with mock data.
    """
    logger.info("Testing Report Generator...")
    
    # Create mock report data
    mock_report = {
        'period': {
            'start_date': '2024-01-01',
            'end_date': '2024-01-07'
        },
        'executive_summary': {
            'executive_summary': 'This is a test executive summary for the weekly market report.',
            'market_performance': 'Market performance analysis for the test period.',
            'key_highlights': ['Highlight 1', 'Highlight 2', 'Highlight 3'],
            'market_outlook': 'Positive outlook for the coming weeks.',
            'recommendations': ['Recommendation 1', 'Recommendation 2']
        },
        'transaction_analysis': {
            'summary': 'Test transaction analysis summary.',
            'key_insights': ['Insight 1', 'Insight 2'],
            'total_value': 1500000000,
            'transaction_count': 2
        },
        'news_analysis': {
            'summary': 'Test news analysis summary.',
            'key_themes': ['Theme 1', 'Theme 2'],
            'article_count': 2
        },
        'statistics': {
            'total_transactions': 2,
            'total_transaction_value': 1500000000,
            'total_news_articles': 2,
            'sources_covered': ['HKET', '文匯報', '星島頭條']
        },
        'generated_at': datetime.now().isoformat()
    }
    
    # Initialize report generator
    generator = ReportGenerator()
    
    # Test HTML report generation
    try:
        html_content = generator.generate_html_report(mock_report)
        logger.info("✓ HTML report generation test completed")
        logger.info(f"  - HTML content length: {len(html_content)} characters")
    except Exception as e:
        logger.error(f"✗ HTML report generation test failed: {e}")
    
    # Test Markdown report generation
    try:
        markdown_content = generator.generate_markdown_report(mock_report)
        logger.info("✓ Markdown report generation test completed")
        logger.info(f"  - Markdown content length: {len(markdown_content)} characters")
    except Exception as e:
        logger.error(f"✗ Markdown report generation test failed: {e}")
    
    # Test report saving
    try:
        saved_files = generator.save_report(mock_report, "test_report")
        logger.info("✓ Report saving test completed")
        for format_type, file_path in saved_files.items():
            logger.info(f"  - {format_type.upper()}: {file_path}")
    except Exception as e:
        logger.error(f"✗ Report saving test failed: {e}")

def test_config_functions():
    """
    Test the configuration functions.
    """
    logger.info("Testing Configuration Functions...")
    
    # Test get_week_period
    try:
        monday, sunday = get_week_period()
        logger.info("✓ get_week_period test completed")
        logger.info(f"  - Monday: {monday.strftime('%Y-%m-%d')}")
        logger.info(f"  - Sunday: {sunday.strftime('%Y-%m-%d')}")
    except Exception as e:
        logger.error(f"✗ get_week_period test failed: {e}")
    
    # Test get_last_full_week
    try:
        last_monday, last_sunday = get_last_full_week()
        logger.info("✓ get_last_full_week test completed")
        logger.info(f"  - Last Monday: {last_monday.strftime('%Y-%m-%d')}")
        logger.info(f"  - Last Sunday: {last_sunday.strftime('%Y-%m-%d')}")
    except Exception as e:
        logger.error(f"✗ get_last_full_week test failed: {e}")

async def run_all_tests():
    """
    Run all tests.
    """
    logger.info("=" * 60)
    logger.info("RUNNING SYSTEM TESTS")
    logger.info("=" * 60)
    
    # Test configuration functions
    test_config_functions()
    
    # Test report generator
    test_report_generator()
    
    # Test AI summarizer
    await test_ai_summarizer()
    
    logger.info("=" * 60)
    logger.info("ALL TESTS COMPLETED")
    logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_all_tests()) 