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
from utils.consol_scraper import House852Scraper
from utils.ai_categorizer import DeepSeekCategorizer
from utils.transaction_filter import filter_transactions
from utils.detail_extractor import DetailExtractor
from utils.excel_formatter import ExcelFormatter
from utils.centaline_parser import CentalineParser
from utils.midland_parser import MidlandParser
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
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

# Disable httpx INFO logging (200 OK messages)
logging.getLogger('httpx').setLevel(logging.WARNING)


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
    parser.add_argument('--quick', action='store_true', default=False, help='Quick mode: process only first 15 articles with AI')
    
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
        print("\n[STEP 1/6] Scraping article list from primary source")
        print(f"  → Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        scraper = House852Scraper()
        
        html_pages = []
        page = 1
        found_before_start = False  # Track if we've seen dates before start_date
        consecutive_pages_without_in_range = 0  # Track consecutive pages without in-range items
        max_pages = 100  # Increased from 20 to 100 to get more historical data
        
        while page <= max_pages:
            html = scraper.fetch_page(page)
            if not html:
                break
            news_items = scraper.extract_news_items(html)
            if not news_items:
                break
            
            # Filter by date range
            page_has_in_range = False
            page_earliest_date = None
            
            for item in news_items:
                if item['date']:
                    item_date = scraper.parse_date(item['date'])
                    if item_date:
                        # Track earliest date on this page
                        if page_earliest_date is None or item_date < page_earliest_date:
                            page_earliest_date = item_date
                        
                        if start_date <= item_date <= end_date:
                            html_pages.append(item)
                            page_has_in_range = True
                        elif item_date < start_date:
                            found_before_start = True
            
            # If we found in-range items, reset the counter
            if page_has_in_range:
                consecutive_pages_without_in_range = 0
            else:
                consecutive_pages_without_in_range += 1
            
            # Show progress every 10 pages
            if page % 10 == 0:
                if page_earliest_date:
                    print(f"  → Page {page}: earliest date = {page_earliest_date.strftime('%Y-%m-%d')}, found {len(html_pages)} articles so far")
            
            # Stop if:
            # 1. We've seen dates before start_date AND
            # 2. The earliest date on this page is clearly before start_date (at least 1 day before) AND
            # 3. We've had 2 consecutive pages without in-range items
            if (found_before_start and 
                page_earliest_date and 
                page_earliest_date < start_date - timedelta(days=1) and
                consecutive_pages_without_in_range >= 2):
                print(f"  → Stopping at page {page}: earliest date {page_earliest_date.strftime('%Y-%m-%d')} is before start date")
                break
            
            page += 1
        
        if not html_pages:
            print("No articles found in date range")
            sys.exit(0)
        
        # Show date range of found articles for debugging
        dates_found = []
        for item in html_pages:
            if item.get('date'):
                item_date = scraper.parse_date(item['date'])
                if item_date:
                    dates_found.append(item_date)
        
        if dates_found:
            min_date = min(dates_found).strftime('%Y-%m-%d')
            max_date = max(dates_found).strftime('%Y-%m-%d')
            print(f"✓ Found {len(html_pages)} articles in date range")
            print(f"  → Actual dates found: {min_date} to {max_date} (expected: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})")
        else:
            print(f"✓ Found {len(html_pages)} articles in date range")
        
        # Step 1.5: Filter major transactions and keep all news
        print(f"\n  → Filtering for major transactions (>=20M HKD or >=2000 sqft)...")
        transaction_articles, total, filtered_count = filter_transactions(html_pages)
        
        # Also categorize to separate news from transactions early
        print(f"  → Pre-categorizing to identify news articles...")
        categorizer = DeepSeekCategorizer()
        
        # Quick categorization to identify news (using just title + tags)
        news_candidates = []
        for article in html_pages:
            title = article.get('title', '').lower()
            tags = ' '.join(article.get('tags', [])).lower()
            text = f"{title} {tags}"
            
            # If no transaction keywords, likely news
            trans_keywords = ['成交', '沽', '售', '租', '億', '萬', '呎']
            if not any(kw in text for kw in trans_keywords):
                news_candidates.append(article)
        
        print(f"  → Transactions: {filtered_count} (from {total} total)")
        print(f"  → News candidates: {len(news_candidates)}")
        print(f"  → API calls saved: ~{total - filtered_count - len(news_candidates)}")
        
        # Combine filtered transactions and news candidates
        articles = transaction_articles + news_candidates
        
        print(f"\n✓ Total to process: {len(articles)} articles ({len(transaction_articles)} transactions + {len(news_candidates)} news)")
        
        # Deduplicate news candidates by topic BEFORE AI categorization (to save API calls)
        if news_candidates:
            print(f"\n  → Deduplicating news by topic before AI categorization...")
            seen_topics = {}
            unique_news_candidates = []
            for article in news_candidates:
                title = article.get('title', '').strip()
                # Use title as topic key (normalized)
                topic_key = title.lower().strip()
                if topic_key and topic_key not in seen_topics:
                    seen_topics[topic_key] = article
                    unique_news_candidates.append(article)
            
            if len(unique_news_candidates) < len(news_candidates):
                print(f"  → Deduplicated: {len(unique_news_candidates)} unique news (removed {len(news_candidates) - len(unique_news_candidates)} duplicates)")
                # Replace news_candidates with deduplicated version
                news_candidates = unique_news_candidates
                # Rebuild articles list
                articles = transaction_articles + news_candidates
        
        # Quick mode: limit to first articles
        if args.quick:
            original_count = len(articles)
            articles = articles[:20]  # Take first 20 for quick testing
            print(f"  → Quick mode: Processing first {len(articles)} articles (out of {original_count})")
        
        print(f"\n[STEP 3/6] AI categorization using DeepSeek (parallel: 10 workers)")
        categorizer = DeepSeekCategorizer()
        categorized_articles = categorizer.categorize_batch(articles)
        
        # Separate articles by category
        transactions = [a for a in categorized_articles if a.get('category') == 'transactions']
        news_articles = [a for a in categorized_articles if a.get('category') == 'news']
        # Exclude new_property - don't process it
        excluded_articles = [a for a in categorized_articles if a.get('category') in ['exclude', 'new_property']]
        
        print(f"✓ Categorized: {len(transactions)} transactions + {len(news_articles)} news")
        if excluded_articles:
            new_prop_count = len([a for a in categorized_articles if a.get('category') == 'new_property'])
            exclude_count = len([a for a in categorized_articles if a.get('category') == 'exclude'])
            print(f"  → Excluded: {exclude_count} articles (non-valuation, quality issues, etc.) + {new_prop_count} new_property (not processed)")
        
        print(f"\n[STEP 4/6] Fetching full article content")
        # Only fetch content for articles that will be included (exclude already filtered by AI)
        all_to_fetch = transactions + news_articles
        for article in all_to_fetch:
            article_data = scraper.fetch_article_content(article['url'])
            article['full_content'] = article_data['content']
            article['source'] = article_data.get('source', 'Company C')
            article['fetch_success'] = article_data['success']
        print(f"✓ Fetched {len(all_to_fetch)} articles (excluded {len(excluded_articles)} articles skipped)")
        
        print(f"\n[STEP 5/6] AI detail extraction (parallel: 10 workers)")
        extractor = DetailExtractor()
        
        print(f"Extracting {len(transactions)} transaction details...")
        all_extracted_transactions = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_article = {executor.submit(extractor.extract_transaction_details, article): article 
                               for article in transactions}
            
            for future in tqdm(as_completed(future_to_article), total=len(transactions), 
                              desc="Transactions", unit="article"):
                try:
                    article = future_to_article[future]
                    details = future.result()
                    article['details'] = details
                    all_extracted_transactions.append(article)
                except Exception as e:
                    logger.error(f"Error extracting transaction: {e}")
        
        # Filter major transactions AFTER extraction (using actual extracted values)
        print(f"\n  → Filtering major transactions (price >= 20M HKD OR area >= 2000 sqft)...")
        major_transactions = []
        for article in all_extracted_transactions:
            details = article.get('details', {})
            price_str = str(details.get('price', 'N/A'))
            area_str = str(details.get('area', 'N/A'))
            
            # Convert to numeric values
            price_m = None
            area_sqft = None
            
            try:
                if price_str != 'N/A' and price_str:
                    price_num = float(str(price_str).replace(',', '').strip())
                    price_m = price_num / 1_000_000  # Convert to millions
            except (ValueError, AttributeError):
                pass
            
            try:
                if area_str != 'N/A' and area_str:
                    area_sqft = float(str(area_str).replace(',', '').strip())
            except (ValueError, AttributeError):
                pass
            
            # Check if meets criteria: price >= 20M OR area >= 2000 sqft
            if (price_m is not None and price_m >= 20.0) or (area_sqft is not None and area_sqft >= 2000.0):
                major_transactions.append(article)
        
        transactions = major_transactions
        print(f"  → Major transactions: {len(transactions)} (filtered from {len(all_extracted_transactions)})")
        
        if news_articles:
            print(f"\nExtracting {len(news_articles)} news summaries (will filter out General)...")
            filtered_news = []
            with ThreadPoolExecutor(max_workers=10) as executor:
                future_to_article = {executor.submit(extractor.extract_news_summary, article): article 
                                   for article in news_articles}
                
                for future in tqdm(as_completed(future_to_article), total=len(news_articles), 
                                  desc="News", unit="article"):
                    try:
                        article = future_to_article[future]
                        details = future.result()
                        article['details'] = details
                        # Only keep Residential and Commercial
                        asset_cat = details.get('asset_category', '')
                        if asset_cat in ['Residential', 'Commercial']:
                            filtered_news.append(article)
                    except Exception as e:
                        logger.error(f"Error extracting news: {e}")
            
            news_articles = filtered_news
            print(f"✓ Kept {len(news_articles)} market-related news (excluded {225 - len(news_articles)} General)")
        else:
            print(f"No news articles to process")
        
        print(f"✓ Detail extraction complete")
        
        print(f"\n[STEP 6/6] Loading additional data sources")
        print("Loading Company A residential transactions...")
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
                    print(f"✓ Company A: {len(centaline_transactions)} transactions")
                else:
                    print(f"ℹ️  centaline_data.txt is empty")
            except Exception as e:
                logger.error(f"Company A error: {e}")
                print(f"⚠️  Company A error: {e}")
        else:
            print(f"ℹ️  centaline_data.txt not found")
        
        print("Loading Company B commercial transactions...")
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
                    print(f"✓ Company B: {len(midland_transactions)} transactions")
                else:
                    print(f"ℹ️  midland_data.txt is empty")
            except Exception as e:
                logger.error(f"Company B error: {e}")
                print(f"⚠️  Company B error: {e}")
        else:
            print(f"ℹ️  midland_data.txt not found")
        
        print(f"\n[FINAL] Generating Excel report")
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


