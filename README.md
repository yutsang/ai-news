# AI Market News Review System

A comprehensive system for scraping, analyzing, and summarizing Hong Kong real estate market news and transactions using AI.

## Features

- **Multi-source News Scraping**: Automatically scrapes market news from HKET, Wen Wei Po, and Sing Tao Daily
- **Transaction Data Extraction**: Identifies and extracts property transaction details from news articles
- **AI-Powered Analysis**: Uses DeepSeek AI to generate comprehensive market summaries and insights
- **Weekly Report Generation**: Creates detailed reports in HTML, Markdown, and JSON formats
- **Automated Scheduling**: Can run automatically on a weekly basis
- **Smart Date Logic**: Handles weekend vs weekday logic for report periods

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd ai-news
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your DeepSeek API key:
```bash
# Copy the example environment file
cp env_example.txt .env

# Edit .env and add your DeepSeek API key
# Get your API key from: https://platform.deepseek.com/
```

## Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

### Customizing Sources and Keywords

Edit `config.py` to customize:
- News sources and URLs
- Transaction and news keywords
- Report configuration
- Scraping settings

## Usage

### Running a One-time Report

```bash
# Run with API key from environment
python main.py

# Run with custom API key
python main.py --api-key your_api_key_here

# Run for a specific date range
python main.py --start-date 2024-01-01 --end-date 2024-01-07
```

### Setting up Automated Weekly Reports

```bash
# Run weekly reports every Monday at 9:00 AM
python scheduler.py --day monday --run-time 09:00

# Run daily reports at 9:00 AM
python scheduler.py --daily --run-time 09:00

# Run once immediately
python scheduler.py --once

# List scheduled jobs
python scheduler.py --list-jobs
```

### Command Line Options

#### Main Application (`main.py`)
- `--api-key`: DeepSeek API key
- `--start-date`: Start date for report period (YYYY-MM-DD)
- `--end-date`: End date for report period (YYYY-MM-DD)
- `--env-file`: Path to .env file

#### Scheduler (`scheduler.py`)
- `--api-key`: DeepSeek API key
- `--run-time`: Time to run reviews (HH:MM, default: 09:00)
- `--day`: Day of week for weekly reviews (default: monday)
- `--daily`: Run daily instead of weekly
- `--once`: Run once immediately and exit
- `--list-jobs`: List scheduled jobs and exit
- `--env-file`: Path to .env file

## Report Logic

The system uses intelligent date logic based on your requirements:

- **Weekend (Saturday/Sunday)**: Generates report for the current week (Monday to Sunday)
- **Weekday**: Generates report for the last full week (Monday to Sunday)

## Output

Reports are generated in multiple formats and saved in the `reports/` directory:

- **HTML**: Beautiful, formatted reports with styling
- **Markdown**: Plain text format for easy sharing
- **JSON**: Raw data for further processing

### Report Structure

Each report includes:

1. **Executive Summary**
   - Overall market performance
   - Key highlights
   - Market outlook
   - Recommendations

2. **Transaction Analysis**
   - Summary of market transactions
   - Key insights and trends
   - Notable deals
   - Market sentiment

3. **News Analysis**
   - Summary of market news
   - Key themes and trends
   - Policy impact analysis
   - Sector-specific analysis

4. **Statistics**
   - Total transactions and values
   - Number of news articles
   - Sources covered

## Data Sources

The system scrapes from three major Hong Kong news sources:

1. **HKET (Hong Kong Economic Times)**
   - URL: https://paper.hket.com/srap007/%E5%9C%B0%E7%94%A2
   - Focus: Property market news and transactions

2. **Wen Wei Po (文匯報)**
   - URL: https://www.wenweipo.com/business/real-estate
   - Focus: Business and real estate news

3. **Sing Tao Daily (星島頭條)**
   - URL: https://www.stheadline.com/daily-property/%E5%9C%B0%E7%94%A2
   - Focus: Property market analysis and transactions

## AI Integration

The system uses DeepSeek AI for:

- **Transaction Summarization**: Analyzing property deals and market activity
- **News Analysis**: Identifying trends and market sentiment
- **Executive Summaries**: Creating comprehensive market overviews
- **Insights Generation**: Extracting key insights and recommendations

## Logging

The system provides comprehensive logging:

- **Console Output**: Real-time progress and status
- **Log Files**: 
  - `market_news.log`: Main application logs
  - `scheduler.log`: Scheduler-specific logs

## Customization

### Adding New News Sources

1. Add source configuration to `config.py`
2. Implement scraping method in `scraper.py`
3. Update the scraping logic in `scrape_all_sources()`

### Modifying AI Prompts

Edit the prompt templates in `ai_summarizer.py` to customize:
- Analysis focus areas
- Output format
- Language preferences

### Customizing Report Templates

Modify templates in `templates/` directory:
- `report.html`: HTML report template
- `report.md`: Markdown report template

## Troubleshooting

### Common Issues

1. **API Key Issues**
   - Ensure your DeepSeek API key is valid
   - Check that the key has sufficient credits
   - Verify the API endpoint is accessible

2. **Scraping Issues**
   - Some websites may block automated requests
   - Check network connectivity
   - Verify website URLs are still valid

3. **Date Range Issues**
   - Ensure date format is YYYY-MM-DD
   - Check that start date is before end date

### Debug Mode

Enable debug logging by modifying the logging level in the respective files:

```python
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs for error messages
3. Open an issue on GitHub with detailed information
