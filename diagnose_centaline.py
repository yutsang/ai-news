#!/usr/bin/env python3
"""
Diagnostic script to check Centaline data quality
"""

import pandas as pd
import os
from glob import glob

# Find most recent Excel file
excel_files = glob('output/property_report_*.xlsx')
excel_files.sort(reverse=True)

if not excel_files:
    print("No Excel files found in output/")
    exit(1)

latest_file = excel_files[0]
print(f"Checking: {latest_file}")
print("=" * 80)

# Read Trans_Commercial sheet
try:
    df = pd.read_excel(latest_file, sheet_name='Trans_Commercial')
    
    print(f"\nTotal rows: {len(df)}")
    print(f"Columns: {list(df.columns)}")
    print()
    
    # Check data by source
    if 'Source' in df.columns:
        print("By Source:")
        print(df['Source'].value_counts())
        print()
    
    # Filter for Centaline only
    centaline_df = df[df['Source'] == 'Centaline']
    print(f"\nCentaline rows: {len(centaline_df)}")
    
    if len(centaline_df) > 0:
        print("\n" + "=" * 80)
        print("CENTALINE DATA QUALITY CHECK:")
        print("=" * 80)
        
        # Check for missing/N/A values
        for col in ['Date', 'District', 'Property', 'Floor', 'Unit', 'Area/Unit', 'Transaction Price', 'Unit Price']:
            if col in centaline_df.columns:
                na_count = centaline_df[col].isna().sum()
                na_value_count = (centaline_df[col] == 'N/A').sum()
                total_na = na_count + na_value_count
                print(f"\n{col}:")
                print(f"  - Missing (NaN): {na_count}")
                print(f"  - N/A: {na_value_count}")
                print(f"  - Total incomplete: {total_na} / {len(centaline_df)} ({total_na/len(centaline_df)*100:.1f}%)")
                
                # Show sample values
                valid_values = centaline_df[centaline_df[col] != 'N/A'][col].dropna()
                if len(valid_values) > 0:
                    print(f"  - Sample values: {list(valid_values.head(3))}")
        
        print("\n" + "=" * 80)
        print("SAMPLE CENTALINE RECORDS (first 3):")
        print("=" * 80)
        
        # Show first 3 records
        for idx, row in centaline_df.head(3).iterrows():
            print(f"\nRecord {idx+1}:")
            for col in ['Date', 'District', 'Property', 'Floor', 'Unit', 'Asset type', 
                       'Area/Unit', 'Transaction Price', 'Unit Price', 'Category']:
                if col in row:
                    print(f"  {col}: {row[col]}")
        
        # Check districts specifically
        print("\n" + "=" * 80)
        print("DISTRICT ANALYSIS:")
        print("=" * 80)
        
        districts = centaline_df['District'].value_counts()
        print(f"\nUnique districts: {len(districts)}")
        print(f"Top 10 districts:")
        print(districts.head(10))
        
        # Check if district has N/A or empty
        na_districts = centaline_df[(centaline_df['District'] == 'N/A') | (centaline_df['District'].isna())]
        if len(na_districts) > 0:
            print(f"\n⚠️  WARNING: {len(na_districts)} records with missing district!")
            print("\nSample records with missing district:")
            for idx, row in na_districts.head(3).iterrows():
                print(f"\n  Property: {row.get('Property', 'N/A')}")
                print(f"  Date: {row.get('Date', 'N/A')}")
                print(f"  District: {row.get('District', 'N/A')}")
    
    else:
        print("\n⚠️  No Centaline data found in Trans_Commercial sheet!")
        
except Exception as e:
    print(f"Error reading Excel file: {e}")
    import traceback
    traceback.print_exc()
