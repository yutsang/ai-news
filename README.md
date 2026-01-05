# Hong Kong Property News Scraper

Automated scraper for Hong Kong property news, transactions, and market data. Generates professional Excel reports with AI-categorized content.

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure API keys in config.yml
# - DeepSeek AI API key (for categorization)

# Run the scraper
python main.py
```

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

Edit `config.yml`:

```yaml
deepseek:
  api_key: "YOUR_API_KEY_HERE"
  api_base: "https://api.deepseek.com"
  model: "deepseek-chat"
```

## 📦 Requirements

- Python 3.8+
- Chrome/Chromium browser (for Centaline scraping)
- Internet connection
- DeepSeek AI API key

## ⚠️ Notes

### Midland ICI Authorization
- Uses API with authorization token
- Token valid until 2034
- If expired, update in `utils/midland_api_scraper.py`

### Filters Applied
- **Centaline**: Area > 2000 sqft, Date range
- **Midland**: Area >= 2500 sqft, Date range  
- **News**: AI-filtered for market relevance (score >= 6/10)

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
