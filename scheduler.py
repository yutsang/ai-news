#!/usr/bin/env python3
"""
Scheduler for the Hong Kong Real Estate Market News Review System

This module provides functionality to run the market news review system
automatically on a weekly basis.
"""

import schedule
import time
import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Optional

from main import MarketNewsReviewSystem

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class MarketNewsScheduler:
    def __init__(self, api_key: str = None, run_time: str = "09:00"):
        """
        Initialize the scheduler.
        
        Args:
            api_key: DeepSeek API key
            run_time: Time to run the weekly review (format: "HH:MM")
        """
        self.api_key = api_key
        self.run_time = run_time
        self.system = None
        self.is_running = False
    
    async def run_weekly_review(self):
        """
        Run the weekly market review.
        """
        if self.is_running:
            logger.warning("Weekly review is already running. Skipping this execution.")
            return
        
        self.is_running = True
        logger.info("Starting scheduled weekly market review...")
        
        try:
            # Initialize system if not already done
            if not self.system:
                self.system = MarketNewsReviewSystem(self.api_key)
                await self.system.initialize()
            
            # Run the weekly review
            saved_files = await self.system.run_weekly_review()
            
            if saved_files:
                logger.info("Scheduled weekly review completed successfully!")
                logger.info(f"Reports saved: {list(saved_files.keys())}")
            else:
                logger.error("Scheduled weekly review failed!")
                
        except Exception as e:
            logger.error(f"Error during scheduled weekly review: {e}")
        finally:
            self.is_running = False
    
    def schedule_weekly_review(self, day_of_week: str = "monday"):
        """
        Schedule the weekly review to run on a specific day of the week.
        
        Args:
            day_of_week: Day of the week to run the review ("monday", "tuesday", etc.)
        """
        day_mapping = {
            "monday": schedule.every().monday,
            "tuesday": schedule.every().tuesday,
            "wednesday": schedule.every().wednesday,
            "thursday": schedule.every().thursday,
            "friday": schedule.every().friday,
            "saturday": schedule.every().saturday,
            "sunday": schedule.every().sunday
        }
        
        if day_of_week.lower() not in day_mapping:
            logger.error(f"Invalid day of week: {day_of_week}")
            return
        
        # Schedule the job
        day_mapping[day_of_week.lower()].at(self.run_time).do(
            lambda: asyncio.run(self.run_weekly_review())
        )
        
        logger.info(f"Weekly review scheduled for every {day_of_week} at {self.run_time}")
    
    def schedule_daily_review(self):
        """
        Schedule the review to run daily at the specified time.
        """
        schedule.every().day.at(self.run_time).do(
            lambda: asyncio.run(self.run_weekly_review())
        )
        
        logger.info(f"Daily review scheduled at {self.run_time}")
    
    def run_once(self):
        """
        Run the review once immediately.
        """
        logger.info("Running one-time market review...")
        asyncio.run(self.run_weekly_review())
    
    def start_scheduler(self):
        """
        Start the scheduler and keep it running.
        """
        logger.info("Starting market news scheduler...")
        logger.info(f"Next scheduled run: {schedule.next_run()}")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
                
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
    
    def list_jobs(self):
        """
        List all scheduled jobs.
        """
        jobs = schedule.get_jobs()
        if not jobs:
            logger.info("No jobs scheduled")
            return
        
        logger.info("Scheduled jobs:")
        for job in jobs:
            logger.info(f"  - {job}")

def main():
    """
    Main entry point for the scheduler.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Market News Review Scheduler')
    parser.add_argument('--api-key', help='DeepSeek API key')
    parser.add_argument('--run-time', default='09:00', help='Time to run reviews (HH:MM)')
    parser.add_argument('--day', default='monday', help='Day of week to run weekly reviews')
    parser.add_argument('--daily', action='store_true', help='Run daily instead of weekly')
    parser.add_argument('--once', action='store_true', help='Run once immediately and exit')
    parser.add_argument('--list-jobs', action='store_true', help='List scheduled jobs and exit')
    parser.add_argument('--env-file', help='Path to .env file containing API key')
    
    args = parser.parse_args()
    
    # Load API key from environment or arguments
    api_key = args.api_key
    
    if not api_key and args.env_file:
        from dotenv import load_dotenv
        load_dotenv(args.env_file)
        api_key = os.getenv('DEEPSEEK_API_KEY')
    
    if not api_key:
        api_key = os.getenv('DEEPSEEK_API_KEY')
    
    # Create scheduler
    scheduler = MarketNewsScheduler(api_key, args.run_time)
    
    if args.list_jobs:
        scheduler.list_jobs()
        return
    
    if args.once:
        scheduler.run_once()
        return
    
    # Schedule jobs
    if args.daily:
        scheduler.schedule_daily_review()
    else:
        scheduler.schedule_weekly_review(args.day)
    
    # Start the scheduler
    scheduler.start_scheduler()

if __name__ == "__main__":
    main() 