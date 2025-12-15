#!/usr/bin/env python3
"""
Excel Formatter - Format Excel output with specific column requirements
"""

import pandas as pd
import yaml
import os
import re
from datetime import datetime, timedelta
from typing import List, Dict
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter


class ExcelFormatter:
    """Format and write Excel files with custom columns"""
    
    def __init__(self, config_path: str = "config.yml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.output_dir = self.config['excel']['output_dir']
        os.makedirs(self.output_dir, exist_ok=True)
    
    def get_next_monday_filename(self, end_date: datetime) -> str:
        """
        Get filename based on next Monday after period end
        Format: YYMMDD (e.g., 251215 for 15 Dec 2025)
        """
        # Find next Monday
        days_until_monday = (7 - end_date.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        next_monday = end_date + timedelta(days=days_until_monday)
        
        # Format as YYMMDD
        return next_monday.strftime('%y%m%d')
    
    def extract_source(self, article: Dict) -> str:
        """Extract source from article content"""
        # First check if source was extracted from article page
        if 'source' in article and article['source'] != '852.house':
            return article['source']
        
        # Check tags as fallback
        tags = article.get('tags', [])
        sources = self.config.get('sources', [])
        
        for tag in tags:
            for source in sources:
                if source in tag:
                    return source
        
        # Default to 852.house
        return "852.house"
    
    def deduplicate_transactions(self, articles: List[Dict]) -> List[Dict]:
        """
        Deduplicate transactions based on property + date
        Keep the one with most complete information
        Add dedup_flag for manual review
        """
        from collections import defaultdict
        
        # Group by property name + date
        groups = defaultdict(list)
        for article in articles:
            details = article.get('details', {})
            # Create key from property name + date
            property_name = details.get('property', '').strip()
            date = details.get('date', '')
            # Normalize property name (remove spaces, convert to lower)
            key = f"{property_name.replace(' ', '').lower()}_{date}"
            groups[key].append(article)
        
        # For each group, keep the most complete one
        deduped = []
        for key, group in groups.items():
            if len(group) == 1:
                # No duplicates
                group[0]['dedup_flag'] = ''
                deduped.append(group[0])
            else:
                # Multiple articles for same property+date
                # Score by completeness
                def completeness_score(article):
                    details = article.get('details', {})
                    score = 0
                    for field in ['district', 'floor', 'unit', 'price', 'area', 'unit_price', 
                                  'buyer', 'seller', 'yield_rate']:
                        if details.get(field) and details.get(field) != 'N/A':
                            score += 1
                    return score
                
                # Sort by completeness (highest first)
                sorted_group = sorted(group, key=completeness_score, reverse=True)
                
                # Keep the most complete one, mark for review
                best = sorted_group[0]
                best['dedup_flag'] = f'REVIEW: {len(group)} duplicates found'
                deduped.append(best)
        
        return deduped
    
    def format_transactions(self, articles: List[Dict], filename: str) -> pd.DataFrame:
        """Format transactions sheet"""
        # Deduplicate first
        deduped_articles = self.deduplicate_transactions(articles)
        
        data = []
        for idx, article in enumerate(deduped_articles, 1):
            details = article.get('details', {})
            
            row = {
                'No.': idx,
                'Date': details.get('date', 'N/A'),
                'District': details.get('district', 'N/A'),
                'Property': details.get('property', article.get('title', '')[:50]),
                'Asset type': details.get('asset_type', 'N/A'),
                'Floor': details.get('floor', 'N/A'),
                'Unit': details.get('unit', 'N/A'),
                'Nature': details.get('nature', 'N/A'),
                'Transaction price': details.get('price', 'N/A'),
                'Area': details.get('area', 'N/A'),
                'Unit basis': 'sqft',
                'Area/unit': details.get('area', 'N/A'),
                'Unit price': details.get('unit_price', 'N/A'),
                'Yield': details.get('yield_rate', 'N/A'),
                'Seller/Landlord': details.get('seller', 'N/A'),
                'Buyer/Tenant': details.get('buyer', 'N/A'),
                'Source': self.extract_source(article),
                'URL': article.get('url', ''),
                'Filename': filename,
                'Dedup Flag': article.get('dedup_flag', '')
            }
            data.append(row)
        
        return pd.DataFrame(data)
    
    def format_centaline(self, transactions: List[Dict], filename: str) -> pd.DataFrame:
        """Format Centaline transactions sheet"""
        data = []
        
        for idx, trans in enumerate(transactions, 1):
            row = {
                'No.': idx,
                'Date': trans.get('date', 'N/A'),
                'District': trans.get('district', 'N/A'),
                'Asset type': trans.get('asset_type', '住宅'),
                'Property': trans.get('property', 'N/A'),
                'Floor': trans.get('floor', 'N/A'),
                'Unit': trans.get('unit', 'N/A'),
                'Area basis': trans.get('area_basis', 'NFA'),
                'Unit basis': 'sqft',
                'Area/Unit': trans.get('area', trans.get('area_unit', 'N/A')),
                'Transaction Price': trans.get('price_numeric', trans.get('price', 'N/A')),
                'Unit Price': trans.get('unit_price', 'N/A'),
                'Nature': trans.get('nature', 'Sales'),
                'Category': 'Residential',
                'Source': 'Centaline',
                'Filename': filename
            }
            data.append(row)
        
        return pd.DataFrame(data)
    
    def format_news(self, articles: List[Dict], filename: str) -> pd.DataFrame:
        """Format news sheet"""
        data = []
        
        for idx, article in enumerate(articles, 1):
            details = article.get('details', {})
            
            row = {
                'No.': idx,
                'Date': details.get('date', article.get('date', 'N/A')),
                'Source': self.extract_source(article),
                'Asset type': details.get('asset_category', 'General'),
                'Topic': details.get('topic', article.get('title', '')),
                'Summary': details.get('summary', 'N/A'),
                'URL': article.get('url', ''),
                'Filename': filename
            }
            data.append(row)
        
        return pd.DataFrame(data)
    
    def format_worksheet(self, worksheet, is_transaction: bool = True):
        """Apply formatting to worksheet"""
        # Header style
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")
        
        for cell in worksheet[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # Column widths for transactions
        if is_transaction:
            widths = {
                'A': 6,   # No.
                'B': 12,  # Date
                'C': 12,  # District
                'D': 30,  # Property
                'E': 10,  # Asset type
                'F': 8,   # Floor
                'G': 8,   # Unit
                'H': 8,   # Nature
                'I': 15,  # Transaction price
                'J': 10,  # Area
                'K': 10,  # Unit basis
                'L': 10,  # Area/unit
                'M': 12,  # Unit price
                'N': 10,  # Yield
                'O': 20,  # Seller/Landlord
                'P': 20,  # Buyer/Tenant
                'Q': 12,  # Source
                'R': 15,  # URL
                'S': 10,  # Filename
                'T': 25   # Dedup Flag
            }
        else:
            # News columns
            widths = {
                'A': 6,   # No.
                'B': 12,  # Date
                'C': 12,  # Source
                'D': 12,  # Asset type
                'E': 40,  # Topic
                'F': 60,  # Summary
                'G': 15,  # URL
                'H': 10   # Filename
            }
        
        for col, width in widths.items():
            worksheet.column_dimensions[col].width = width
        
        # Text wrapping
        for row in worksheet.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = Alignment(wrap_text=True, vertical='top')
        
        # Freeze header
        worksheet.freeze_panes = 'A2'
    
    def _format_centaline_sheet(self, worksheet):
        """Format Centaline worksheet"""
        from openpyxl.styles import Font, Alignment, PatternFill
        
        # Header style
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")
        
        for cell in worksheet[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # Column widths
        widths = {
            'A': 6,   # No.
            'B': 12,  # Date
            'C': 12,  # District
            'D': 10,  # Asset type
            'E': 30,  # Property
            'F': 8,   # Floor
            'G': 8,   # Unit
            'H': 10,  # Area basis
            'I': 10,  # Unit basis
            'J': 10,  # Area/Unit
            'K': 15,  # Transaction Price
            'L': 12,  # Unit Price
            'M': 8,   # Nature
            'N': 12,  # Category
            'O': 12,  # Source
            'P': 10   # Filename
        }
        
        for col, width in widths.items():
            worksheet.column_dimensions[col].width = width
        
        # Text wrapping
        for row in worksheet.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = Alignment(wrap_text=True, vertical='top')
        
        worksheet.freeze_panes = 'A2'
    
    def write_excel(self, transactions: List[Dict], news: List[Dict], 
                   centaline: List[Dict], midland: List[Dict], 
                   start_date: datetime, end_date: datetime) -> str:
        """Write formatted Excel file"""
        # Get filename
        filename = self.get_next_monday_filename(end_date)
        filepath = os.path.join(self.output_dir, f"property_report_{filename}.xlsx")
        
        print(f"\n  → Creating Excel file: {filepath}")
        print(f"  → Filename code: {filename} (next Monday after period end)")
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # Transactions sheet (always create)
            df_trans = self.format_transactions(transactions, filename) if transactions else pd.DataFrame()
            if not df_trans.empty:
                df_trans.to_excel(writer, sheet_name='Transactions', index=False)
                self.format_worksheet(writer.book['Transactions'], is_transaction=True)
                print(f"  → Transactions: {len(df_trans)} rows")
            else:
                # Create empty sheet with headers
                df_trans = pd.DataFrame(columns=['No.', 'Date', 'District', 'Property', 'Asset type', 
                                                 'Floor', 'Unit', 'Nature', 'Transaction price', 'Area', 
                                                 'Unit basis', 'Area/unit', 'Unit price', 'Yield', 
                                                 'Seller/Landlord', 'Buyer/Tenant', 'Source', 'URL', 
                                                 'Filename', 'Dedup Flag'])
                df_trans.to_excel(writer, sheet_name='Transactions', index=False)
                self.format_worksheet(writer.book['Transactions'], is_transaction=True)
                print(f"  → Transactions: 0 rows (empty)")
            
            # News sheet (always create)
            df_news = self.format_news(news, filename) if news else pd.DataFrame()
            if not df_news.empty:
                df_news.to_excel(writer, sheet_name='News', index=False)
                self.format_worksheet(writer.book['News'], is_transaction=False)
                print(f"  → News: {len(df_news)} rows")
            else:
                # Create empty sheet with headers
                df_news = pd.DataFrame(columns=['No.', 'Date', 'Source', 'Asset type', 'Topic', 'Summary', 'URL', 'Filename'])
                df_news.to_excel(writer, sheet_name='News', index=False)
                self.format_worksheet(writer.book['News'], is_transaction=False)
                print(f"  → News: 0 rows (empty)")
            
            # Centaline sheet (always create)
            df_centaline = self.format_centaline(centaline, filename) if centaline else pd.DataFrame()
            if not df_centaline.empty:
                df_centaline.to_excel(writer, sheet_name='Centaline', index=False)
                self._format_centaline_sheet(writer.book['Centaline'])
                print(f"  → Centaline: {len(df_centaline)} rows")
            else:
                df_centaline = pd.DataFrame(columns=['No.', 'Date', 'District', 'Asset type', 'Property', 
                                                     'Floor', 'Unit', 'Area basis', 'Unit basis', 'Area/Unit', 
                                                     'Transaction Price', 'Unit Price', 'Nature', 'Category', 
                                                     'Source', 'Filename'])
                df_centaline.to_excel(writer, sheet_name='Centaline', index=False)
                self._format_centaline_sheet(writer.book['Centaline'])
                print(f"  → Centaline: 0 rows (empty)")
            
            # Midland ICI sheet (always create)
            df_midland = self.format_centaline(midland, filename) if midland else pd.DataFrame()
            if not df_midland.empty:
                df_midland.to_excel(writer, sheet_name='Midland ICI', index=False)
                self._format_centaline_sheet(writer.book['Midland ICI'])
                print(f"  → Midland ICI: {len(df_midland)} rows")
            else:
                df_midland = pd.DataFrame(columns=['No.', 'Date', 'District', 'Asset type', 'Property', 
                                                   'Floor', 'Unit', 'Area basis', 'Unit basis', 'Area/Unit', 
                                                   'Transaction Price', 'Unit Price', 'Nature', 'Category', 
                                                   'Source', 'Filename'])
                df_midland.to_excel(writer, sheet_name='Midland ICI', index=False)
                self._format_centaline_sheet(writer.book['Midland ICI'])
                print(f"  → Midland ICI: 0 rows (empty)")
        
        print(f"\n✅ Excel file created: {filepath}")
        return filepath

