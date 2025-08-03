
# Hong Kong Real Estate Market Report

**Period:** {{ period.start_date }} to {{ period.end_date }}  
**Generated:** {{ generated_at }}

## Executive Summary

{{ executive_summary.executive_summary }}

### Key Highlights
{% for highlight in executive_summary.key_highlights %}
- {{ highlight }}
{% endfor %}

### Market Outlook
{{ executive_summary.market_outlook }}

### Recommendations
{% for rec in executive_summary.recommendations %}
- {{ rec }}
{% endfor %}

## Statistics

- **Total Transactions:** {{ statistics.total_transactions }}
- **Total Transaction Value:** ${{ "{:,.0f}".format(statistics.total_transaction_value) }} HKD
- **News Articles:** {{ statistics.total_news_articles }}
- **Sources Covered:** {{ statistics.sources_covered|join(', ') }}

## Transaction Analysis

{{ transaction_analysis.summary }}

### Key Insights
{% for insight in transaction_analysis.key_insights %}
- {{ insight }}
{% endfor %}

### Market Trends
{{ transaction_analysis.market_trends }}

### Notable Deals
{{ transaction_analysis.notable_deals }}

### Market Sentiment
{{ transaction_analysis.market_sentiment }}

## News Analysis

{{ news_analysis.summary }}

### Key Themes
{% for theme in news_analysis.key_themes %}
- {{ theme }}
{% endfor %}

### Market Analysis
{{ news_analysis.market_analysis }}

### Sentiment
{{ news_analysis.sentiment }}

### Policy Impact
{{ news_analysis.policy_impact }}

### Sector Analysis
{{ news_analysis.sector_analysis }}
        