# HK Property News Scraper

Automated scraper for Hong Kong property transactions and market news.
Generates a multi-sheet Excel report, AI-categorised and filtered for market relevance.

## Quick Start

```bash
pip install -r requirements.txt
cp config.yml.example config.yml   # then fill in your AI API key
python main.py
```

> **config.yml is not committed to the repository.** Create it from the template and keep it local.

## What It Produces

An Excel workbook with four sheets, written to `output/`:

| Sheet | Content |
|-------|---------|
| `major_trans` | High-value transactions (≥ $20M or ≥ 2 000 sqft) from the news source |
| `news` | Top 15-20 market-relevant news articles, AI-ranked and deduplicated |
| `Trans_Commercial` | Residential + commercial property transactions from data providers |
| `new_property` | New project launches with price-list dates in the selected week |

## Usage

```bash
# Smart date range (auto-selects last full week on weekdays, current week on weekends)
python main.py

# Custom date range
python main.py --start-date 2026-01-01 --end-date 2026-01-07

# Interactive mode (prompted input)
python main.py --interactive

# Quick mode (first 20 articles only — useful for testing)
python main.py --quick
```

## Configuration (`config.yml`)

```yaml
deepseek:
  api_key: "sk-..."           # AI API key (leave empty to disable AI)
  api_base: "https://api.deepseek.com"
  model: "deepseek-chat"

scraping:
  verify_ssl: true            # set false on corporate networks with SSL inspection
```

### AI options

| Setup | `api_key` | `api_base` |
|-------|-----------|------------|
| Cloud AI | your key | `https://api.deepseek.com` |
| Local AI (LM Studio / Ollama) | any value | `http://localhost:1234/v1` |
| No AI | *(empty)* | *(any)* |

Without an AI key the scraper still runs but skips categorisation, deduplication, and district extraction.

## Requirements

- Python 3.8+
- Google Chrome (used for browser-based data collection)
- Internet connection
- AI API key (optional)

## Date Range Logic

- **Weekday (Mon–Fri):** previous Monday → Sunday (last full week)
- **Weekend (Sat–Sun):** this Monday → today (current week)

Override with `--start-date` / `--end-date` at any time.

## Filters Applied

| Source | Filter |
|--------|--------|
| Residential | Area > 2 000 sqft, within date range |
| Commercial | Area ≥ 2 500 sqft, within date range |
| News | AI relevance score ≥ 6/10; excludes Greater Bay Area, Mainland, quality complaints |
| Major transactions | Price ≥ $20M HKD **or** area ≥ 2 000 sqft |

## Troubleshooting

**SSL / network errors on corporate networks**
Set `verify_ssl: false` in `config.yml`.

**No residential results**
Chrome must be installed. The site's filter UI may have changed.

**Auth token not retrieved for commercial data**
The commercial data provider's website may have updated its auth flow.
Check the logs — the scraper tries three strategies before giving up.

**AI errors**
Verify your `api_key` and API quota in `config.yml`.
