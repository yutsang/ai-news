# Hong Kong Property Transaction Scraper

Automated scraper for Hong Kong property transactions and news with AI-powered analysis.

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure API Key
Edit `config.yml` and add your DeepSeek API key:
```yaml
deepseek:
  api_key: "sk-your-api-key-here"
```
Get API key from: https://platform.deepseek.com/

### 3. Prepare Centaline Data (Optional)
1. Visit: https://hk.centanet.com/findproperty/list/transaction
2. Filter: Price >= 2000萬, Date range = your report period
3. Copy all transaction text
4. Paste into `centaline_data.txt`

### 4. Run
```bash
# Full mode (3-4 minutes)
python main.py

# Quick mode (1.5 minutes, first 15 only)
python main.py --quick

# Custom dates
python main.py --start-date 2025-12-01 --end-date 2025-12-07
```

## Output

**File**: `output/property_report_YYMMDD.xlsx`

**3 Sheets**:
1. **Transactions** (852.house) - Major deals >20M or >=2000 sqft
2. **News** - Market news with AI summaries
3. **Centaline** - Residential from centaline_data.txt
4. **Midland ICI** - Commercial/Industrial >= 3000 sqft

## Date Logic

- **Weekday (Mon-Fri)**: Last full week (previous Mon-Sun)
- **Weekend (Sat-Sun)**: Current week (this Mon-today)

## Features

- ✅ Smart filtering (93% API reduction)
- ✅ Auto-deduplication with review flags
- ✅ AI detail extraction (19 fields)
- ✅ Multi-source data collection
- ✅ 30x faster processing

## Excel Columns

### Transactions Sheet (20 columns)
No. | Date | District | Property | Asset type | Floor | Unit | Nature | Transaction price | Area | Unit basis | Area/unit | Unit price | Yield | Seller/Landlord | Buyer/Tenant | Source | URL | Filename | Dedup Flag

### News Sheet (8 columns)
No. | Date | Source | Asset type | Topic | Summary | URL | Filename

### Centaline/Midland Sheets (16 columns)
No. | Date | District | Asset type | Property | Floor | Unit | Area basis | Unit basis | Area/Unit | Transaction Price | Unit Price | Nature | Category | Source | Filename

## Important Notes

- **Dedup Flag**: Review rows marked "REVIEW: X duplicates"
- **Yield**: Decimal format (0.07 = 7%)
- **Source**: Extracted from article pages
- **Filename**: YYMMDD of next Monday after period

## Files

- `main.py` - Main entry point
- `config.yml` - Configuration (API key, filters)
- `centaline_data.txt` - Manual Centaline data entry
- `utils/` - Helper scripts
- `output/` - Generated reports

## Support

Check logs: `852house_scraper.log`

---

**Quick Start**: `python main.py` → Check `output/` folder
