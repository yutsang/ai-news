#!/usr/bin/env python3
"""
Hybrid Market News Review System

This system attempts to scrape real data first, and if that fails,
provides clearly labeled simulated data for demonstration purposes.
"""

import asyncio
import argparse
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

from config import get_week_period, get_last_full_week, REPORT_CONFIG
from enhanced_scraper import EnhancedMarketScraper
from ai_summarizer import DeepSeekSummarizer
from report_generator import ReportGenerator
from excel_generator import ExcelReportGenerator

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('market_news.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def create_simulated_data(start_date: datetime, end_date: datetime):
    """
    Create simulated data with clear labeling.
    """
    logger.info("Creating simulated data for demonstration purposes...")
    
    # Simulated transactions with real news source URLs
    simulated_transactions = [
        {
            'source': 'HKET',
            'title': '[SIMULATED] 中環甲級寫字樓成交價創新高 15億港元易手',
            'content': '[SIMULATED DATA] 中環一棟甲級寫字樓以15億港元成交，創下該區寫字樓成交價新高。該物業位於中環核心商業區，總樓面面積約20,000平方呎，每平方呎成交價達75,000港元。買家為本地投資基金，賣家為跨國企業。',
            'url': 'https://www.hket.com/property',  # Real HKET property section
            'date': start_date + timedelta(days=2),
            'type': 'transaction',
            'transaction_data': {
                'property_name': '中環甲級寫字樓',
                'transaction_value': 1500000000,
                'transaction_type': 'sale',
                'location': '中環',
                'date': start_date + timedelta(days=2),
                'area': 20000,
                'unit_price': 75000,
                'property_type': 'office'
            }
        },
        {
            'source': '文匯報',
            'title': '[SIMULATED] 尖沙咀商舖租金回升5% 零售市場復甦',
            'content': '[SIMULATED DATA] 尖沙咀區商舖租金在過去一個月回升5%，顯示零售市場開始復甦。主要受惠於內地遊客回流和本地消費增加。',
            'url': 'https://www.wenweipo.com/business/real-estate',  # Real Wen Wei Po business section
            'date': start_date + timedelta(days=3),
            'type': 'transaction',
            'transaction_data': {
                'property_name': '尖沙咀商舖',
                'transaction_value': 5000000,
                'transaction_type': 'lease',
                'location': '尖沙咀',
                'date': start_date + timedelta(days=3),
                'area': 1000,
                'unit_price': 5000,
                'property_type': 'retail'
            }
        },
        {
            'source': '星島頭條',
            'title': '[SIMULATED] 山頂豪宅2.5億成交 創今年新高',
            'content': '[SIMULATED DATA] 山頂一棟豪宅以2.5億港元成交，創下今年豪宅成交價新高。該物業位於山頂道，佔地約8,000平方呎，建築面積約6,000平方呎。',
            'url': 'https://www.stheadline.com/property',  # Real Sing Tao property section
            'date': start_date + timedelta(days=1),
            'type': 'transaction',
            'transaction_data': {
                'property_name': '山頂豪宅',
                'transaction_value': 250000000,
                'transaction_type': 'sale',
                'location': '山頂',
                'date': start_date + timedelta(days=1),
                'area': 6000,
                'unit_price': 41667,
                'property_type': 'residential'
            }
        }
    ]
    
    # Simulated news articles
    simulated_news = [
        {
            'source': '星島頭條',
            'title': '[SIMULATED] 香港樓市展望：2024年市場趨勢分析',
            'content': '[SIMULATED DATA] 根據最新市場分析，香港樓市在2024年將面臨新的挑戰和機遇。利率環境、經濟復甦和政策調整將是影響市場的主要因素。',
            'url': 'https://www.stheadline.com/property',  # Real Sing Tao property section
            'date': start_date + timedelta(days=1),
            'type': 'news'
        },
        {
            'source': 'HKET',
            'title': '[SIMULATED] 政府推出新樓市政策 支持首次置業者',
            'content': '[SIMULATED DATA] 政府宣布推出新的樓市政策，旨在穩定市場並支持首次置業者。新政策包括調整印花稅和放寬按揭限制。',
            'url': 'https://www.hket.com/property',  # Real HKET property section
            'date': start_date + timedelta(days=4),
            'type': 'news'
        }
    ]
    
    return {
        'transactions': simulated_transactions,
        'news': simulated_news
    }

class HybridMarketNewsReviewSystem:
    def __init__(self, api_key: str = None):
        """
        Initialize the Hybrid Market News Review System.
        """
        self.api_key = api_key or os.getenv('DEEPSEEK_API_KEY')
        if not self.api_key:
            raise ValueError("DeepSeek API key is required. Set DEEPSEEK_API_KEY environment variable or pass as argument.")
        
        self.summarizer = DeepSeekSummarizer(self.api_key)
        self.report_generator = ReportGenerator()
        self.excel_generator = ExcelReportGenerator()
        
        logger.info("Hybrid system initialized successfully.")
    
    async def try_real_scraping(self, start_date: datetime, end_date: datetime):
        """
        Attempt to scrape real data from news sources.
        """
        logger.info("Attempting to scrape real market data...")
        
        try:
            async with EnhancedMarketScraper() as scraper:
                results = await scraper.scrape_all_sources_enhanced(start_date, end_date)
                
                transactions = results.get('transactions', [])
                news = results.get('news', [])
                
                if transactions or news:
                    logger.info(f"✅ Real data found: {len(transactions)} transactions, {len(news)} news articles")
                    return {
                        'transactions': transactions,
                        'news': news,
                        'is_real': True
                    }
                else:
                    logger.warning("❌ No real data found from scraping")
                    return {
                        'transactions': [],
                        'news': [],
                        'is_real': False
                    }
                    
        except Exception as e:
            logger.error(f"Error during real scraping: {e}")
            return {
                'transactions': [],
                'news': [],
                'is_real': False
            }
    
    async def get_market_data(self, start_date: datetime, end_date: datetime):
        """
        Get market data - try real scraping first, fall back to simulated data.
        """
        # Try real scraping first
        real_data = await self.try_real_scraping(start_date, end_date)
        
        if real_data['is_real'] and (real_data['transactions'] or real_data['news']):
            logger.info("Using real market data")
            return real_data
        else:
            logger.info("Real data not available, using simulated data for demonstration")
            simulated_data = create_simulated_data(start_date, end_date)
            return {
                'transactions': simulated_data['transactions'],
                'news': simulated_data['news'],
                'is_real': False
            }
    
    async def generate_ai_summaries(self, transactions: list, news: list, start_date: datetime, end_date: datetime, is_real: bool = False):
        """
        Generate AI summaries of the data.
        """
        logger.info("Generating AI summaries...")
        
        try:
            # Add context about data source
            if not is_real:
                logger.info("Adding simulated data disclaimer to AI analysis")
            
            report = await self.summarizer.generate_weekly_report(
                transactions, news, start_date, end_date
            )
            
            # Add data source information
            if not is_real:
                report['data_source'] = 'simulated'
                report['disclaimer'] = 'This report contains simulated data for demonstration purposes only.'
            else:
                report['data_source'] = 'real'
                report['disclaimer'] = 'This report contains real market data scraped from news sources.'
            
            logger.info("AI summaries generated successfully.")
            return report
            
        except Exception as e:
            logger.error(f"Error generating AI summaries: {e}")
            # Return a basic report structure
            return {
                'period': {
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d')
                },
                'executive_summary': {
                    'executive_summary': f'Weekly market report for {start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}',
                    'market_performance': 'Analysis not available due to technical issues',
                    'key_highlights': ['Report generated successfully'],
                    'market_outlook': 'Outlook analysis not available',
                    'recommendations': ['Monitor market developments closely']
                },
                'transaction_analysis': {
                    'summary': f'Found {len(transactions)} transactions.',
                    'key_insights': ['Analysis not available'],
                    'total_value': sum(t.get('transaction_data', {}).get('transaction_value', 0) for t in transactions),
                    'transaction_count': len(transactions)
                },
                'news_analysis': {
                    'summary': f'Found {len(news)} news articles.',
                    'key_themes': ['Analysis not available'],
                    'article_count': len(news)
                },
                'statistics': {
                    'total_transactions': len(transactions),
                    'total_transaction_value': sum(t.get('transaction_data', {}).get('transaction_value', 0) for t in transactions),
                    'total_news_articles': len(news),
                    'sources_covered': list(set([t['source'] for t in transactions] + [n['source'] for n in news]))
                },
                'generated_at': datetime.now().isoformat(),
                'data_source': 'simulated' if not is_real else 'real',
                'disclaimer': 'This report contains simulated data for demonstration purposes only.' if not is_real else 'This report contains real market data.'
            }
    
    async def save_reports(self, report_data: dict, transactions: list, news: list):
        """
        Save reports in all formats.
        """
        logger.info("Saving reports...")
        
        try:
            # Generate reports
            report_files = self.report_generator.save_report(report_data)
            
            # Generate Excel report
            excel_file = self.excel_generator.create_excel_report(
                report_data, transactions, news
            )
            
            logger.info("Reports saved successfully:")
            for format_type, filepath in report_files.items():
                logger.info(f"  {format_type.upper()}: {filepath}")
            logger.info(f"  EXCEL: {excel_file}")
            
            return report_files, excel_file
            
        except Exception as e:
            logger.error(f"Error saving reports: {e}")
            return {}, None
    
    async def run_weekly_review(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None):
        """
        Run a complete weekly market review.
        """
        # Determine date range
        if start_date and end_date:
            period_start = start_date
            period_end = end_date
        else:
            period_start, period_end = get_last_full_week()
        
        logger.info(f"Running weekly review for period: {period_start.strftime('%Y-%m-%d')} to {period_end.strftime('%Y-%m-%d')}")
        
        try:
            # Step 1: Get market data (real or simulated)
            market_data = await self.get_market_data(period_start, period_end)
            transactions = market_data['transactions']
            news = market_data['news']
            is_real = market_data.get('is_real', False)
            
            # Step 2: Generate AI summaries
            report_data = await self.generate_ai_summaries(transactions, news, period_start, period_end, is_real)
            
            # Step 3: Save reports
            report_files, excel_file = await self.save_reports(report_data, transactions, news)
            
            logger.info("Weekly review completed successfully!")
            
            # Print summary with data source information
            print("\n" + "=" * 60)
            if is_real:
                print("REPORT GENERATION COMPLETED (REAL DATA)")
                print("✅ This report contains REAL market data from news sources")
            else:
                print("REPORT GENERATION COMPLETED (SIMULATED DATA)")
                print("⚠️  This report contains SIMULATED DATA for demonstration purposes")
                print("   URLs point to real news source sections but not specific articles")
            print("=" * 60)
            print(f"Reports saved in: {REPORT_CONFIG['output_dir']}")
            for format_type, filepath in report_files.items():
                print(f"  {format_type.upper()}: {filepath}")
            if excel_file:
                print(f"  EXCEL: {excel_file}")
            print("=" * 60)
            
            return True
            
        except Exception as e:
            logger.error(f"Error running weekly review: {e}")
            return False

async def main():
    """Main function to run the hybrid market news review system."""
    parser = argparse.ArgumentParser(description='Hybrid AI Market News Review System')
    parser.add_argument('--api-key', help='DeepSeek API key')
    parser.add_argument('--start-date', help='Start date for report period (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date for report period (YYYY-MM-DD)')
    parser.add_argument('--env-file', help='Path to .env file')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--force-simulated', action='store_true', help='Force use of simulated data')
    
    args = parser.parse_args()
    
    # Load environment variables if env file is specified
    if args.env_file:
        from dotenv import load_dotenv
        load_dotenv(args.env_file)
    
    try:
        # Initialize system
        system = HybridMarketNewsReviewSystem(api_key=args.api_key)
        
        # Parse dates if provided
        start_date = None
        end_date = None
        if args.start_date and args.end_date:
            start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
            end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
        
        # Run review
        success = await system.run_weekly_review(start_date, end_date)
        
        if args.once:
            return 0 if success else 1
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code) 