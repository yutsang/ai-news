# Hong Kong Property News Scraper

Automated scraper for Hong Kong property news, transactions, and market data. Generates professional Excel reports with AI-categorized content.

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure API key
cp config.sample.yml config.yml
# Edit config.yml and add your DeepSeek API key (optional - AI features will be disabled if not provided)

# Run the scraper
python main.py
```

**Note**: AI features are optional. If you don't provide an API key, the scraper will still work but without AI categorization and filtering.

## 📊 What It Does

Automatically collects and processes:

1. **Property Transactions** (3 sources)
   - Centaline: Residential transactions (> 2000 sqft)
   - Midland ICI: Commercial transactions (> 2500 sqft)  
   - 852.house: Major transactions (>= $20M or >= 2000 sqft)

2. **Real Estate News** (852.house)
   - AI-categorized and filtered
   - Top 15-20 market-relevant articles
   - Duplicates removed

## 📋 Output

Generates Excel file: `output/property_report_YYMMDD_HHMMSS.xlsx`

### 4 Sheets:

| Sheet | Content | Typical Count |
|-------|---------|---------------|
| **major_trans** | High-value transactions from 852.house | 20-30 |
| **news** | Top market-relevant news articles | 15-20 |
| **Trans_Commercial** | All property transactions (Centaline + Midland) | 50-70 |
| **new_property** | New property launches | 0-10 |

## 🎯 Expected Results (Per Week)

- **Residential** (Centaline): 10-15 transactions
- **Commercial** (Midland ICI): 40-50 transactions
- **News** (852.house): 15-20 articles
- **Major Transactions** (852.house): 20-30

## 📅 Date Range Logic

**Automatic (Smart Date Range)**:
- **Weekday (Mon-Fri)**: Last full week (previous Monday to Sunday)
- **Weekend (Sat-Sun)**: Current week (this Monday to today)

**Manual Override**:
```bash
python main.py --start-date 2025-12-29 --end-date 2026-01-04
```

## 🔧 Configuration

1. Copy sample config: `cp config.sample.yml config.yml`
2. Edit `config.yml` and choose your AI setup:

### Option 1: Cloud DeepSeek (Recommended)
```yaml
deepseek:
  api_key: "sk-your-deepseek-api-key"
  api_base: "https://api.deepseek.com"
  model: "deepseek-chat"
```

### Option 2: Local AI (LM Studio, Ollama, etc.)
```yaml
deepseek:
  api_key: "local-key"  # Any value works for local
  api_base: "http://localhost:1234/v1"  # LM Studio default
  model: "qwen2.5-32b-instruct"  # Your local model name
```

### Option 3: No AI (Basic Scraping Only)
```yaml
deepseek:
  api_key: ""  # Leave empty to disable AI
```

**AI Features**:
- **With AI**: Categorization, filtering, deduplication, district extraction
- **Without AI**: Basic scraping only, no AI processing
- **Cross-computer compatible**: Run on different machines with or without API keys

## 📦 Requirements

- Python 3.8+
- Chrome/Chromium browser (for Centaline scraping)
- Internet connection
- DeepSeek AI API key

## ⚠️ Notes

### Midland ICI Authorization
- Automatically retrieves fresh authorization token using ChromeDriver
- Creates new session every time to avoid tracking
- No manual token configuration needed

### Filters Applied
- **Centaline**: Area > 2000 sqft, Date range
- **Midland**: Area >= 2500 sqft, Date range, Fresh session every time to avoid tracking
- **News**: AI-filtered for HK market relevance (score >= 6/10)
  - **Excludes**: Greater Bay Area, Mainland China, quality issues, property management
  - **Focuses on**: Hong Kong real estate valuation, market trends, price analysis

## 📖 Usage Examples

### Default (Smart Date Range)
```bash
python main.py
```

### Custom Date Range
```bash
python main.py --start-date 2025-12-01 --end-date 2025-12-31
```

### Expected Runtime
- Data collection: 2-3 minutes
- AI processing: 3-5 minutes
- **Total**: 5-10 minutes

## 📊 Sample Output

```
✅ SCRAPING COMPLETED SUCCESSFULLY

📊 Summary:
  Primary source: 21 transactions + 59 news
  Trans_Commercial: 12 + 44 = 56
    - Centaline (Residential): 12
    - Midland ICI (Commercial): 44
  Total: 77 transactions

📁 Output: output/property_report_260105_131447.xlsx
```

## 🆘 Troubleshooting

**No Centaline results**:
- Check Chrome is installed
- Website filters may need adjustment
- May be no large properties (>2000 sqft) in date range

**Midland 401 error**:
- Authorization token expired
- Update token in `utils/midland_api_scraper.py`

**AI errors**:
- Check DeepSeek API key in `config.yml`
- Verify API quota/credits

## 📝 License

See LICENSE file for details.
