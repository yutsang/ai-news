#!/usr/bin/env python3
"""
852.House News Scraper - Main Entry Point

This script scrapes Hong Kong real estate news from https://852.house/zh/newses
and categorizes them into Transactions, Real Estate News, and New Property using AI.

Usage:
    python main_852house.py

The script will prompt for start and end dates, then:
1. Scrape news articles within the date range
2. Use DeepSeek AI to categorize each article
3. Extract detailed information from each article
4. Save results to Excel with 3 tabs
"""

import sys
import logging
import argparse
from datetime import datetime, timedelta
from utils.house852_scraper import House852Scraper
from utils.ai_categorizer import DeepSeekCategorizer
from utils.transaction_filter import filter_transactions
from utils.detail_extractor import DetailExtractor
from utils.excel_formatter import ExcelFormatter
from utils.centaline_parser import CentalineParser
from utils.midland_parser import MidlandParser
import os


def get_smart_date_range():
    """
    Get smart date range based on current day:
    - Weekday (Mon-Fri): Last full week (previous Monday to Sunday)
    - Weekend (Sat-Sun): Current week (this Monday to today)
    
    Returns:
        tuple: (start_date, end_date) as datetime objects
    """
    today = datetime.now()
    weekday = today.weekday()  # Monday=0, Sunday=6
    
    if weekday <= 4:  # Monday to Friday (0-4)
        # Get last full week
        # Calculate days to go back to last Monday
        days_since_monday = weekday + 7  # Go back to previous week's Monday
        last_monday = today - timedelta(days=days_since_monday)
        last_sunday = last_monday + timedelta(days=6)
        
        logger.info(f"Running on weekday ({today.strftime('%A')}), using last full week")
        return last_monday.replace(hour=0, minute=0, second=0, microsecond=0), \
               last_sunday.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    else:  # Saturday or Sunday (5-6)
        # Get current week (this Monday to today)
        days_since_monday = weekday  # Days since this week's Monday
        this_monday = today - timedelta(days=days_since_monday)
        
        logger.info(f"Running on weekend ({today.strftime('%A')}), using current week")
        return this_monday.replace(hour=0, minute=0, second=0, microsecond=0), \
               today.replace(hour=23, minute=59, second=59, microsecond=999999)

# Set up logging - minimal output
logging.basicConfig(
    level=logging.WARNING,  # Only show warnings and errors
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


def get_date_input(prompt: str) -> datetime:
    """
    Get date input from user with validation
    
    Args:
        prompt: Prompt message to display
        
    Returns:
        datetime object
    """
    while True:
        try:
            date_str = input(prompt)
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            return date_obj
        except ValueError:
            print("Invalid date format. Please use YYYY-MM-DD format (e.g., 2025-12-13)")
        except KeyboardInterrupt:
            print("\nOperation cancelled by user")
            sys.exit(0)


def main():
    """Main function to run the 852.House news scraper"""
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='852.House Hong Kong Real Estate News Scraper')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD). Default: smart range based on day of week')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD). Default: smart range based on day of week')
    parser.add_argument('--interactive', action='store_true', help='Interactive mode with prompts')
    parser.add_argument('--quick', action='store_true', help='Quick mode: process only first 10-20 articles with AI')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("852.House Hong Kong Real Estate News Scraper")
    print("=" * 80)
    print("\nThis tool will scrape news from https://852.house/zh/newses")
    print("and categorize them using DeepSeek AI into:")
    print("  1. Transactions (Sales/Lease)")
    print("  2. Real Estate News")
    print("  3. New Property")
    print("\n" + "=" * 80)
    
    # Get date range
    if args.interactive:
        # Interactive mode - get dates from user
        print("\nPlease enter the date range for scraping:")
        start_date = get_date_input("Start date (YYYY-MM-DD): ")
        end_date = get_date_input("End date (YYYY-MM-DD): ")
    else:
        # Non-interactive mode - use command-line args or smart defaults
        if args.start_date and args.end_date:
            # Both dates provided
            try:
                start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
                end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
            except ValueError as e:
                print(f"Error: Invalid date format: {e}")
                print("Please use YYYY-MM-DD format")
                sys.exit(1)
        elif args.start_date or args.end_date:
            # Only one date provided - error
            print("Error: Please provide both --start-date and --end-date, or neither for smart range")
            sys.exit(1)
        else:
            # No dates provided - use smart range
            start_date, end_date = get_smart_date_range()
            print(f"\n📅 Smart date range selected:")
            print(f"   Today is {datetime.now().strftime('%A, %Y-%m-%d')}")
            if datetime.now().weekday() <= 4:
                print(f"   → Using LAST FULL WEEK (weekday mode)")
            else:
                print(f"   → Using CURRENT WEEK (weekend mode)")
    
    # Validate date range
    if start_date > end_date:
        print("\nError: Start date must be before or equal to end date")
        sys.exit(1)
    
    print(f"\nDate range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    # Confirm before proceeding (only in interactive mode)
    if args.interactive:
        confirm = input("\nProceed with scraping? (y/n): ").lower()
        if confirm != 'y':
            print("Operation cancelled")
            sys.exit(0)
    
    print("\n" + "=" * 80)
    print("Starting scraping process...")
    print("=" * 80)
    
    try:
        # Step 1: Scrape news articles (title + preview only, no full content yet)
        print("\n[STEP 1/3] Scraping news articles from 852.house...")
        scraper = House852Scraper()
        
        # Get articles without fetching full content first
        print("  → Fetching article list with previews...")
        html_pages = []
        page = 1
        while page <= 20:  # Max 20 pages
            html = scraper.fetch_page(page)
            if not html:
                break
            news_items = scraper.extract_news_items(html)
            if not news_items:
                break
            
            # Filter by date range
            for item in news_items:
                if item['date']:
                    item_date = scraper.parse_date(item['date'])
                    if item_date and start_date <= item_date <= end_date:
                        html_pages.append(item)
                    elif item_date and item_date < start_date:
                        break
            
            page += 1
        
        if not html_pages:
            print("\nNo articles found in the specified date range")
            sys.exit(0)
        
        print(f"  → Found {len(html_pages)} articles in date range")
        
        # Step 1.5: Filter high-value transactions BEFORE AI processing
        print(f"\n  → Filtering for major transactions (>20M HKD or >=2000 sqft)...")
        filtered_articles, total, filtered_count = filter_transactions(html_pages)
        
        print(f"  → Filtered to {filtered_count} high-value articles (from {total} total)")
        print(f"  → This saves ~{total - filtered_count} unnecessary API calls!")
        
        articles = filtered_articles
        
        if not articles:
            print("\nNo high-value transactions found in the specified date range")
            sys.exit(0)
        
        print(f"\n✓ Successfully filtered {len(articles)} major transaction articles")
        
        # Quick mode: limit to first 10-20 articles
        if args.quick:
            original_count = len(articles)
            articles = articles[:15]  # Take first 15 for quick testing
            print(f"  → Quick mode: Processing first {len(articles)} articles (out of {original_count})")
        
        # Step 2: Categorize and separate transactions from news
        print("\n[STEP 2/4] Categorizing articles using DeepSeek AI...")
        categorizer = DeepSeekCategorizer()
        categorized_articles = categorizer.categorize_batch(articles)
        
        # Separate by category
        transactions = [a for a in categorized_articles if a.get('category') == 'transactions']
        news_articles = [a for a in categorized_articles if a.get('category') in ['news', 'new_property']]
        
        print(f"\n✓ Categorized: {len(transactions)} transactions, {len(news_articles)} news")
        
        # Step 3: Fetch full content for detail extraction
        print("\n[STEP 3/4] Fetching full article content...")
        all_to_fetch = transactions + news_articles
        for article in all_to_fetch:
            article_data = scraper.fetch_article_content(article['url'])
            article['full_content'] = article_data['content']
            article['source'] = article_data.get('source', '852.house')
            article['fetch_success'] = article_data['success']
        print(f"  → Fetched content for {len(all_to_fetch)} articles")
        
        # Step 4: Extract detailed information using AI
        print("\n[STEP 4/4] Extracting detailed information using AI...")
        extractor = DetailExtractor()
        
        # Extract transaction details
        print(f"  → Extracting transaction details for {len(transactions)} articles...")
        for article in transactions:
            details = extractor.extract_transaction_details(article)
            article['details'] = details
        
        # Extract news summaries
        print(f"  → Extracting news summaries for {len(news_articles)} articles...")
        for article in news_articles:
            details = extractor.extract_news_summary(article)
            article['details'] = details
        
        print(f"\n✓ Completed detail extraction")
        
        # Step 5: Load Company A transactions from manual data file
        print("\n[STEP 5] Loading Company A residential transactions...")
        centaline_transactions = []
        if os.path.exists("centaline_data.txt"):
            try:
                with open("centaline_data.txt", 'r', encoding='utf-8') as f:
                    content = f.read()
                    data_lines = [l for l in content.split('\n') if l.strip() and not l.startswith('#')]
                
                if len(data_lines) > 5:
                    parser = CentalineParser()
                    all_company_a = parser.parse_transactions("centaline_data.txt")
                    
                    # Filter by date
                    centaline_transactions = [t for t in all_company_a 
                                            if t.get('date_obj') and start_date <= t['date_obj'] <= end_date]
                    print(f"  ✓ Loaded {len(centaline_transactions)} Company A transactions")
                else:
                    print(f"  ℹ️  No data in centaline_data.txt")
            except Exception as e:
                logger.error(f"Centaline error: {e}")
                print(f"  ⚠️  Centaline error: {e}")
        else:
            print(f"  ℹ️  centaline_data.txt not found")
        
        # Step 6: Load Company B transactions from manual data file
        print("\n[STEP 6] Loading Company B commercial transactions...")
        midland_transactions = []
        if os.path.exists("midland_data.txt"):
            try:
                with open("midland_data.txt", 'r', encoding='utf-8') as f:
                    content = f.read()
                    data_lines = [l for l in content.split('\n') if l.strip() and not l.startswith('#')]
                
                if len(data_lines) > 5:
                    parser = MidlandParser()
                    all_company_b = parser.parse_transactions("midland_data.txt")
                    
                    # Filter by date and area (>=3000 sqft)
                    midland_transactions = [t for t in all_company_b 
                                          if t.get('date_obj') and start_date <= t['date_obj'] <= end_date
                                          and float(t.get('area', 0)) >= 3000.0]
                    print(f"  ✓ Loaded {len(midland_transactions)} Company B transactions")
                else:
                    print(f"  ℹ️  No data in midland_data.txt")
            except Exception as e:
                logger.error(f"Midland error: {e}")
                print(f"  ⚠️  Midland error: {e}")
        else:
            print(f"  ℹ️  midland_data.txt not found")
        
        # Save to Excel with new format
        print("\n[FINAL STEP] Saving results to Excel...")
        formatter = ExcelFormatter()
        output_file = formatter.write_excel(transactions, news_articles, centaline_transactions,
                                           midland_transactions, start_date, end_date)
        
        print(f"\n✓ Successfully saved to: {output_file}")
        
        # Print summary
        print("\n" + "=" * 80)
        print("✅ SCRAPING COMPLETED SUCCESSFULLY")
        print("=" * 80)
        
        print(f"\n📊 Summary:")
        print(f"  Primary source: {len(transactions)} transactions + {len(news_articles)} news")
        print(f"  Trans_Commercial: {len(centaline_transactions)} + {len(midland_transactions)} = {len(centaline_transactions) + len(midland_transactions)}")
        print(f"    - Company A (Residential): {len(centaline_transactions)}")
        print(f"    - Company B (Commercial): {len(midland_transactions)}")
        print(f"  Total: {len(transactions) + len(centaline_transactions) + len(midland_transactions)} transactions")
        
        print(f"\n📁 Output: {output_file}")
        print("\n📋 3 Sheets: Transactions | News | Trans_Commercial")
        print("\n" + "=" * 80)
        
        return 0
        
    except FileNotFoundError as e:
        logger.error(f"Configuration file not found: {e}")
        print("\n❌ Error: config.yml not found or invalid")
        print("Please make sure config.yml exists and contains your DeepSeek API key")
        return 1
        
    except KeyError as e:
        logger.error(f"Missing configuration: {e}")
        print(f"\n❌ Error: Missing configuration key: {e}")
        print("Please check your config.yml file")
        return 1
        
    except Exception as e:
        logger.error(f"Error during scraping: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        print("Check 852house_scraper.log for details")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)


