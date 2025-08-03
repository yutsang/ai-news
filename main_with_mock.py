#!/usr/bin/env python3
"""
AI Market News Review System with Enhanced Mock Data

This script runs the complete market news review system with realistic mock data
that demonstrates the full functionality including proper column structure.
"""

import asyncio
import argparse
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

from config import get_week_period, get_last_full_week, REPORT_CONFIG
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

def create_realistic_mock_data(start_date: datetime, end_date: datetime):
    """
    Create realistic mock data for the specified date range.
    Note: This is simulated data for demonstration purposes only.
    """
    # Calculate days in the period
    days_in_period = (end_date - start_date).days + 1
    
    # Mock transactions with realistic data - using real news source URLs
    mock_transactions = [
        {
            'source': 'HKET',
            'title': '中環甲級寫字樓成交價創新高 15億港元易手',
            'content': '中環一棟甲級寫字樓以15億港元成交，創下該區寫字樓成交價新高。該物業位於中環核心商業區，總樓面面積約20,000平方呎，每平方呎成交價達75,000港元。買家為本地投資基金，賣家為跨國企業。交易反映中環核心商業區寫字樓需求強勁，租金有望進一步上升。',
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
            'title': '尖沙咀商舖租金回升5% 零售市場復甦',
            'content': '尖沙咀區商舖租金在過去一個月回升5%，顯示零售市場開始復甦。主要受惠於內地遊客回流和本地消費增加。其中海港城附近商舖租金升幅最為明顯，平均租金達每平方呎500港元。',
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
            'title': '山頂豪宅2.5億成交 創今年新高',
            'content': '山頂一棟豪宅以2.5億港元成交，創下今年豪宅成交價新高。該物業位於山頂道，佔地約8,000平方呎，建築面積約6,000平方呎。買家為本地富豪，賣家為外資企業。豪宅市場持續升溫，反映高端買家對香港豪宅市場的信心。',
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
        },
        {
            'source': 'HKET',
            'title': '銅鑼灣地皮拍賣 成交價18億',
            'content': '銅鑼灣一宗地皮拍賣以18億港元成交，超出市場預期。該地皮面積約12,000平方呎，可建樓面面積約60,000平方呎。買家為本地發展商，計劃興建商業大廈。地皮成交價反映發展商對香港商業地產市場前景樂觀。',
            'url': 'https://www.hket.com/property',  # Real HKET property section
            'date': start_date + timedelta(days=4),
            'type': 'transaction',
            'transaction_data': {
                'property_name': '銅鑼灣地皮',
                'transaction_value': 1800000000,
                'transaction_type': 'sale',
                'location': '銅鑼灣',
                'date': start_date + timedelta(days=4),
                'area': 12000,
                'unit_price': 1500000,
                'property_type': 'land'
            }
        }
    ]
    
    # Mock news articles with realistic data - using real news source URLs
    mock_news = [
        {
            'source': '星島頭條',
            'title': '香港樓市展望：2024年市場趨勢分析',
            'content': '根據最新市場分析，香港樓市在2024年將面臨新的挑戰和機遇。利率環境、經濟復甦和政策調整將是影響市場的主要因素。專家預期住宅市場將保持穩定，商業物業市場則有望回升。政府政策支持首次置業者，預期將有助於提振市場信心。',
            'url': 'https://www.stheadline.com/property',  # Real Sing Tao property section
            'date': start_date + timedelta(days=1),
            'type': 'news'
        },
        {
            'source': 'HKET',
            'title': '政府推出新樓市政策 支持首次置業者',
            'content': '政府宣布推出新的樓市政策，旨在穩定市場並支持首次置業者。新政策包括調整印花稅和放寬按揭限制。市場預期這些措施將有助於提振樓市信心，特別是在住宅市場方面。政策將於下月正式實施。',
            'url': 'https://www.hket.com/property',  # Real HKET property section
            'date': start_date + timedelta(days=4),
            'type': 'news'
        },
        {
            'source': '文匯報',
            'title': '寫字樓空置率下降 租金有望回升',
            'content': '最新數據顯示，香港寫字樓空置率有所下降，租金有望回升。中環、金鐘等核心商業區的寫字樓需求增加，預期租金將在未來幾個月內逐步回升。企業擴張和經濟復甦是推動需求的主要因素。',
            'url': 'https://www.wenweipo.com/business/real-estate',  # Real Wen Wei Po business section
            'date': start_date + timedelta(days=2),
            'type': 'news'
        },
        {
            'source': '星島頭條',
            'title': '酒店業復甦 入住率回升至85%',
            'content': '香港酒店業復甦勢頭良好，整體入住率回升至85%。主要受惠於旅遊業復甦和商務活動增加。業界預期酒店業將在2024年繼續改善，租金收入有望進一步提升。',
            'url': 'https://www.stheadline.com/property',  # Real Sing Tao property section
            'date': start_date + timedelta(days=3),
            'type': 'news'
        }
    ]
    
    return {
        'transactions': mock_transactions,
        'news': mock_news
    }

class MockMarketNewsReviewSystem:
    def __init__(self, api_key: str = None):
        """
        Initialize the Mock Market News Review System.
        """
        self.api_key = api_key or os.getenv('DEEPSEEK_API_KEY')
        if not self.api_key:
            raise ValueError("DeepSeek API key is required. Set DEEPSEEK_API_KEY environment variable or pass as argument.")
        
        self.summarizer = DeepSeekSummarizer(self.api_key)
        self.report_generator = ReportGenerator()
        self.excel_generator = ExcelReportGenerator()
        
        logger.info("System initialized successfully.")
    
    async def get_mock_data(self, start_date: datetime, end_date: datetime):
        """
        Get mock data for the specified date range.
        """
        logger.info(f"Loading mock data for period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        mock_data = create_realistic_mock_data(start_date, end_date)
        
        logger.info(f"Loaded mock data: {len(mock_data['transactions'])} transactions, {len(mock_data['news'])} news articles")
        
        return mock_data
    
    async def generate_ai_summaries(self, transactions: list, news: list, start_date: datetime, end_date: datetime):
        """
        Generate AI summaries of the mock data.
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
        Run a complete weekly market review with mock data.
        """
        # Determine date range
        if start_date and end_date:
            period_start = start_date
            period_end = end_date
        else:
            period_start, period_end = get_last_full_week()
        
        logger.info(f"Running weekly review for period: {period_start.strftime('%Y-%m-%d')} to {period_end.strftime('%Y-%m-%d')}")
        
        try:
            # Step 1: Get mock data
            mock_data = await self.get_mock_data(period_start, period_end)
            transactions = mock_data['transactions']
            news = mock_data['news']
            
            # Step 2: Generate AI summaries
            report_data = await self.generate_ai_summaries(transactions, news, period_start, period_end)
            
            # Step 3: Save reports
            report_files, excel_file = await self.save_reports(report_data, transactions, news)
            
            logger.info("Weekly review completed successfully!")
            
            # Print summary
            print("\n" + "=" * 60)
            print("REPORT GENERATION COMPLETED (WITH MOCK DATA)")
            print("=" * 60)
            print("⚠️  IMPORTANT: This report contains SIMULATED DATA for demonstration purposes")
            print("   The transaction details and news articles are not real market data.")
            print("   URLs point to real news source sections but not specific articles.")
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
    """Main function to run the mock market news review system."""
    parser = argparse.ArgumentParser(description='AI Market News Review System (Mock Data)')
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
        system = MockMarketNewsReviewSystem(api_key=args.api_key)
        
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