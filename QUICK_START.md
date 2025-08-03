# Quick Start Guide

## 🚀 Get Started in 5 Minutes

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Up Your API Key
```bash
# Copy the example environment file
cp env_example.txt .env

# Edit .env and add your DeepSeek API key
# Get your API key from: https://platform.deepseek.com/
```

### 3. Test the System
```bash
# Run the test to verify everything works
python test_system.py

# Run a one-time report (without API key for testing)
python main.py --once
```

### 4. Run with Your API Key
```bash
# Run with API key from environment
python main.py

# Or specify API key directly
python main.py --api-key your_api_key_here
```

### 5. Set Up Automated Reports
```bash
# Run weekly reports every Monday at 9:00 AM
python scheduler.py --day monday --run-time 09:00

# Run once immediately
python scheduler.py --once
```

## 📊 What You'll Get

The system generates comprehensive reports including:

- **Executive Summary**: Market overview and key insights
- **Transaction Analysis**: Property deals and market activity
- **News Analysis**: Market trends and policy impacts
- **Statistics**: Transaction values and source coverage

Reports are saved in multiple formats:
- `reports/market_report_YYYY-MM-DD_to_YYYY-MM-DD.html` (Beautiful HTML)
- `reports/market_report_YYYY-MM-DD_to_YYYY-MM-DD.md` (Markdown)
- `reports/market_report_YYYY-MM-DD_to_YYYY-MM-DD.json` (Raw data)

## 🎯 Key Features

- **Smart Date Logic**: Automatically handles weekend vs weekday reporting
- **Multi-source Scraping**: HKET, Wen Wei Po, and Sing Tao Daily
- **AI-Powered Analysis**: DeepSeek AI generates insights and summaries
- **Automated Scheduling**: Run reports on your preferred schedule
- **Multiple Formats**: HTML, Markdown, and JSON outputs

## 🔧 Configuration

Edit `config.py` to customize:
- News sources and URLs
- Transaction keywords
- Report settings
- Scraping parameters

## 📝 Example Usage

```bash
# Generate report for specific date range
python main.py --start-date 2024-01-01 --end-date 2024-01-07

# Run daily reports at 8:00 AM
python scheduler.py --daily --run-time 08:00

# Run weekly reports on Friday at 5:00 PM
python scheduler.py --day friday --run-time 17:00
```

## 🆘 Need Help?

1. Check the logs in `market_news.log` and `scheduler.log`
2. Run `python test_system.py` to verify system functionality
3. See the full documentation in `README.md`
4. Ensure your DeepSeek API key is valid and has sufficient credits

## 🎉 You're Ready!

Your AI-powered market news review system is now set up and ready to generate comprehensive Hong Kong real estate market reports! 