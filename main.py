#!/usr/bin/env python3
"""
AI Market News Review System - Main Application

This script runs the complete market news review system, including:
- Scraping market data from multiple sources
- AI-powered analysis and summarization
- Report generation in multiple formats
"""

import asyncio
import argparse
import logging
import os
from datetime import datetime
from typing import Optional

from config import get_week_period, get_last_full_week, REPORT_CONFIG, AI_CONFIG
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

class MarketNewsReviewSystem:
    def __init__(self, api_key: str = None):
        """
        Initialize the Market News Review System.
        
        Args:
            api_key: DeepSeek API key. If None, will try to load from config or environment.
        """
        self.api_key = api_key or os.getenv('DEEPSEEK_API_KEY') or AI_CONFIG.get('api_key')
        if not self.api_key:
            raise ValueError("DeepSeek API key is required. Set DEEPSEEK_API_KEY environment variable, pass as argument, or configure in config.json.")
        
        self.summarizer = DeepSeekSummarizer(self.api_key)
        self.report_generator = ReportGenerator()
        self.excel_generator = ExcelReportGenerator()
        
        logger.info("System initialized successfully.")
    
    async def scrape_market_data(self, start_date: datetime, end_date: datetime):
        """
        Scrape market data from all sources.
        """
        logger.info(f"Scraping market data from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        try:
            async with EnhancedMarketScraper() as scraper:
                results = await scraper.scrape_all_sources_enhanced(start_date, end_date)
                
                transactions = results.get('transactions', [])
                news = results.get('news', [])
                
                logger.info(f"Scraped {len(transactions)} transactions and {len(news)} news articles")
                
                return {
                    'transactions': transactions,
                    'news': news
                }
                
        except Exception as e:
            logger.error(f"Error scraping market data: {e}")
            return {'transactions': [], 'news': []}
    
    async def generate_ai_summaries(self, transactions: list, news: list, start_date: datetime, end_date: datetime):
        """
        Generate AI summaries of the scraped data.
        """
        logger.info("Generating AI summaries...")
        
        try:
            report = await self.summarizer.generate_weekly_report(
                transactions, news, start_date, end_date
            )
            
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
                'generated_at': datetime.now().isoformat()
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
            # Step 1: Scrape market data
            market_data = await self.scrape_market_data(period_start, period_end)
            transactions = market_data['transactions']
            news = market_data['news']
            
            # Step 2: Generate AI summaries
            report_data = await self.generate_ai_summaries(transactions, news, period_start, period_end)
            
            # Step 3: Save reports
            report_files, excel_file = await self.save_reports(report_data, transactions, news)
            
            logger.info("Weekly review completed successfully!")
            
            # Print summary
            print("\n" + "=" * 60)
            print("REPORT GENERATION COMPLETED")
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
    """Main function to run the market news review system."""
    parser = argparse.ArgumentParser(description='AI Market News Review System')
    parser.add_argument('--api-key', help='DeepSeek API key')
    parser.add_argument('--start-date', help='Start date for report period (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date for report period (YYYY-MM-DD)')
    parser.add_argument('--env-file', help='Path to .env file')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    
    args = parser.parse_args()
    
    # Load environment variables if env file is specified
    if args.env_file:
        from dotenv import load_dotenv
        load_dotenv(args.env_file)
    
    try:
        # Initialize system
        system = MarketNewsReviewSystem(api_key=args.api_key)
        
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