# Hong Kong Property Transaction Scraper

Automated property transaction scraper with AI-powered analysis and multi-source data collection.

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure API Key

Create `config.yml` from the example below and add your DeepSeek API key:

```yaml
# Configuration Example

# DeepSeek AI API Configuration
deepseek:
  api_key: "sk-your-api-key-here"  # Get from https://platform.deepseek.com/
  api_base: "https://api.deepseek.com"
  model: "deepseek-chat"
  temperature: 0.3
  max_tokens: 4000

# Scraping Configuration
scraping:
  max_retries: 3
  retry_delay: 2
  timeout: 30

# Asset Types
asset_types:
  - "寫字樓"    # Office
  - "商鋪"      # Shop
  - "住宅"      # Residential
  - "洋房"      # House
  - "工廈"      # Industrial
  - "酒店"      # Hotel
  - "停車位"    # Car park

# Data Source Mapping
data_sources:

# Excel Output
excel:
  output_dir: "output"
```

### 3. Prepare Data Files

**Company A Data**:
- Paste residential transaction data
- Filter: >= 20M HKD

**Company B Data**:
- Paste commercial transaction data  
- Filter: >= 3000 sqft

### 4. Run

```bash
# Full mode (3-4 minutes)
python main.py

# Quick mode (first 15 transactions)
python main.py --quick
```

## Output

**File**: `output/property_report_YYMMDD.xlsx`

**3 Sheets**:
1. **Transactions** - Major deals (>20M or >=2000 sqft)
2. **News** - Market news with AI summaries
3. **Trans_Commercial** - Combined residential + commercial data

## Date Logic

- **Weekday (Mon-Fri)**: Last full week (previous Mon-Sun)
- **Weekend (Sat-Sun)**: Current week (this Mon-today)

## Features

- ✅ Smart pre-filtering (93% API reduction)
- ✅ Auto-deduplication with review flags
- ✅ AI detail extraction (19 fields)
- ✅ Multi-source data (3 sources)
- ✅ 30x faster processing

## File Structure

```
├── main.py                 # Entry point
├── config.yml             # Configuration (excluded from git)
├── centaline_data.txt     # Company A data (excluded from git)
├── midland_data.txt       # Company B data (excluded from git)
├── utils/                 # Helper scripts
└── output/                # Generated reports (excluded from git)
```

## Weekly Workflow

1. Prepare Company A data → paste into `centaline_data.txt`
2. Prepare Company B data → paste into `midland_data.txt`
3. Run: `python main.py`
4. Review: `output/property_report_YYMMDD.xlsx`

## Excel Columns

### Transactions Sheet (20 columns)
No. | Date | District | Property | Asset type | Floor | Unit | Nature | Transaction price | Area | Unit basis | Area/unit | Unit price | Yield | Seller/Landlord | Buyer/Tenant | Source | URL | Filename | Dedup Flag

### News Sheet (8 columns)
No. | Date | Source | Asset type | Topic | Summary | URL | Filename

### Trans_Commercial Sheet (16 columns)
No. | Date | District | Asset type | Property | Floor | Unit | Area basis | Unit basis | Area/Unit | Transaction Price | Unit Price | Nature | Category | Source | Filename

---

**Time**: 3-4 minutes | **API Reduction**: 93% | **Speed**: 30x faster
