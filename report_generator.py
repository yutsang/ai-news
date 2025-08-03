import os
import json
import logging
from datetime import datetime
from typing import Dict, List
from jinja2 import Template
import markdown

from config import REPORT_CONFIG

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReportGenerator:
    def __init__(self):
        self.output_dir = REPORT_CONFIG['output_dir']
        self.template_dir = REPORT_CONFIG['template_dir']
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.template_dir, exist_ok=True)
        
        # Create default templates
        self._create_default_templates()
    
    def _create_default_templates(self):
        """
        Create default HTML and Markdown templates if they don't exist.
        """
        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hong Kong Real Estate Market Report - {{ period.start_date }} to {{ period.end_date }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }
        .section { margin: 30px 0; padding: 20px; border-left: 4px solid #3498db; background: #f8f9fa; }
        .highlight { background: #fff3cd; padding: 15px; border-radius: 5px; margin: 10px 0; }
        .transaction { background: #d1ecf1; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .news-item { background: #e2e3e5; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }
        .stat-card { background: white; padding: 20px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }
        .stat-number { font-size: 2em; font-weight: bold; color: #2c3e50; }
        .stat-label { color: #7f8c8d; margin-top: 5px; }
        h1, h2, h3 { color: #2c3e50; }
        .insight { background: #d4edda; padding: 10px; margin: 5px 0; border-radius: 3px; }
        .recommendation { background: #f8d7da; padding: 10px; margin: 5px 0; border-radius: 3px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Hong Kong Real Estate Market Report</h1>
        <p>Period: {{ period.start_date }} to {{ period.end_date }}</p>
        <p>Generated: {{ generated_at }}</p>
    </div>

    <div class="section">
        <h2>Executive Summary</h2>
        <div class="highlight">
            {{ executive_summary.executive_summary }}
        </div>
        
        <h3>Key Highlights</h3>
        {% for highlight in executive_summary.key_highlights %}
        <div class="insight">{{ highlight }}</div>
        {% endfor %}
        
        <h3>Market Outlook</h3>
        <p>{{ executive_summary.market_outlook }}</p>
        
        <h3>Recommendations</h3>
        {% for rec in executive_summary.recommendations %}
        <div class="recommendation">{{ rec }}</div>
        {% endfor %}
    </div>

    <div class="stats">
        <div class="stat-card">
            <div class="stat-number">{{ statistics.total_transactions }}</div>
            <div class="stat-label">Total Transactions</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">${{ "{:,.0f}".format(statistics.total_transaction_value) }}</div>
            <div class="stat-label">Total Value (HKD)</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{{ statistics.total_news_articles }}</div>
            <div class="stat-label">News Articles</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{{ statistics.sources_covered|length }}</div>
            <div class="stat-label">Sources Covered</div>
        </div>
    </div>

    <div class="section">
        <h2>Transaction Analysis</h2>
        <div class="highlight">
            {{ transaction_analysis.summary }}
        </div>
        
        <h3>Key Insights</h3>
        {% for insight in transaction_analysis.key_insights %}
        <div class="insight">{{ insight }}</div>
        {% endfor %}
        
        <h3>Market Trends</h3>
        <p>{{ transaction_analysis.market_trends }}</p>
        
        <h3>Notable Deals</h3>
        <p>{{ transaction_analysis.notable_deals }}</p>
        
        <h3>Market Sentiment</h3>
        <p>{{ transaction_analysis.market_sentiment }}</p>
    </div>

    <div class="section">
        <h2>News Analysis</h2>
        <div class="highlight">
            {{ news_analysis.summary }}
        </div>
        
        <h3>Key Themes</h3>
        {% for theme in news_analysis.key_themes %}
        <div class="insight">{{ theme }}</div>
        {% endfor %}
        
        <h3>Market Analysis</h3>
        <p>{{ news_analysis.market_analysis }}</p>
        
        <h3>Sentiment</h3>
        <p>{{ news_analysis.sentiment }}</p>
        
        <h3>Policy Impact</h3>
        <p>{{ news_analysis.policy_impact }}</p>
        
        <h3>Sector Analysis</h3>
        <p>{{ news_analysis.sector_analysis }}</p>
    </div>
</body>
</html>
        """
        
        markdown_template = """
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
        """
        
        # Save templates
        with open(os.path.join(self.template_dir, 'report.html'), 'w', encoding='utf-8') as f:
            f.write(html_template)
        
        with open(os.path.join(self.template_dir, 'report.md'), 'w', encoding='utf-8') as f:
            f.write(markdown_template)
    
    def generate_html_report(self, report_data: Dict) -> str:
        """
        Generate an HTML report from the report data.
        """
        template_path = os.path.join(self.template_dir, 'report.html')
        
        if not os.path.exists(template_path):
            self._create_default_templates()
        
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        template = Template(template_content)
        html_content = template.render(**report_data)
        
        return html_content
    
    def generate_markdown_report(self, report_data: Dict) -> str:
        """
        Generate a Markdown report from the report data.
        """
        template_path = os.path.join(self.template_dir, 'report.md')
        
        if not os.path.exists(template_path):
            self._create_default_templates()
        
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        template = Template(template_content)
        markdown_content = template.render(**report_data)
        
        return markdown_content
    
    def save_report(self, report_data: Dict, filename_prefix: str = None) -> Dict[str, str]:
        """
        Save the report in multiple formats and return the file paths.
        """
        if filename_prefix is None:
            start_date = report_data['period']['start_date']
            end_date = report_data['period']['end_date']
            filename_prefix = f"market_report_{start_date}_to_{end_date}"
        
        saved_files = {}
        
        # Generate HTML report
        html_content = self.generate_html_report(report_data)
        html_filename = f"{filename_prefix}.html"
        html_path = os.path.join(self.output_dir, html_filename)
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        saved_files['html'] = html_path
        
        # Generate Markdown report
        markdown_content = self.generate_markdown_report(report_data)
        md_filename = f"{filename_prefix}.md"
        md_path = os.path.join(self.output_dir, md_filename)
        
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        saved_files['markdown'] = md_path
        
        # Save JSON data
        json_filename = f"{filename_prefix}.json"
        json_path = os.path.join(self.output_dir, json_filename)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)
        
        saved_files['json'] = json_path
        
        logger.info(f"Reports saved: {saved_files}")
        return saved_files
    
    def generate_summary_table(self, transactions: List[Dict]) -> str:
        """
        Generate a summary table of transactions in Markdown format.
        """
        if not transactions:
            return "No transactions found in this period."
        
        table = "| Source | Property | Location | Value (HKD) | Type | Date |\n"
        table += "|--------|----------|----------|-------------|------|------|\n"
        
        for transaction in transactions:
            transaction_data = transaction.get('transaction_data', {})
            source = transaction['source']
            property_name = transaction_data.get('property_name', 'N/A')
            location = transaction_data.get('location', 'N/A')
            value = transaction_data.get('transaction_value', 0)
            transaction_type = transaction_data.get('transaction_type', 'N/A')
            date = transaction['date'].strftime('%Y-%m-%d')
            
            table += f"| {source} | {property_name} | {location} | {value:,.0f} | {transaction_type} | {date} |\n"
        
        return table
    
    def generate_news_summary(self, news_articles: List[Dict]) -> str:
        """
        Generate a summary of news articles in Markdown format.
        """
        if not news_articles:
            return "No news articles found in this period."
        
        summary = ""
        for article in news_articles:
            summary += f"### {article['title']}\n"
            summary += f"**Source:** {article['source']} | **Date:** {article['date'].strftime('%Y-%m-%d')}\n\n"
            summary += f"{article['content'][:300]}...\n\n"
            summary += f"[Read more]({article['url']})\n\n"
            summary += "---\n\n"
        
        return summary 