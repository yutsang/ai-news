#!/usr/bin/env python3
"""
Better diagnostic - handle inline strings
"""

import zipfile
import xml.etree.ElementTree as ET
from collections import Counter
import glob

# Find latest Excel file
excel_files = sorted(glob.glob('output/property_report_*.xlsx'), reverse=True)
if not excel_files:
    print("No Excel files found")
    exit(1)

file_path = excel_files[0]
print(f"Checking: {file_path}")
print("=" * 80)

def get_cell_value(cell, shared_strings):
    """Get value from cell (handles both shared strings and inline values)"""
    v = cell.find('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v')
    if v is None or v.text is None:
        # Check for inline string
        is_elem = cell.find('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}is')
        if is_elem is not None:
            t_elem = is_elem.find('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t')
            if t_elem is not None and t_elem.text:
                return t_elem.text
        return None
    
    # Check cell type
    if cell.get('t') == 's':
        # Shared string reference
        idx = int(v.text)
        if idx < len(shared_strings):
            return shared_strings[idx]
    
    # Return value directly
    return v.text

with zipfile.ZipFile(file_path, 'r') as zip_ref:
    # Read shared strings (may be empty)
    shared_strings = []
    try:
        with zip_ref.open('xl/sharedStrings.xml') as f:
            tree = ET.parse(f)
            root = tree.getroot()
            for si in root:
                t_elem = si.find('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t')
                if t_elem is not None and t_elem.text:
                    shared_strings.append(t_elem.text)
    except KeyError:
        pass
    
    # Read Trans_Commercial sheet
    with zip_ref.open('xl/worksheets/sheet3.xml') as ws_f:
        ws_tree = ET.parse(ws_f)
        ws_root = ws_tree.getroot()
        
        rows = ws_root.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row')
        print(f"Total rows: {len(rows)}")
        
        if len(rows) == 0:
            print("No data in Trans_Commercial sheet!")
            exit(1)
        
        # Get header row
        header_row = rows[0]
        cells = header_row.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c')
        
        headers = []
        for cell in cells:
            val = get_cell_value(cell, shared_strings)
            if val:
                headers.append(val)
        
        print(f"\nHeaders: {headers}")
        
        # Find column indices
        district_idx = headers.index('District') if 'District' in headers else None
        source_idx = headers.index('Source') if 'Source' in headers else None
        property_idx = headers.index('Property') if 'Property' in headers else None
        date_idx = headers.index('Date') if 'Date' in headers else None
        
        print(f"Column indices: District={district_idx}, Source={source_idx}, Property={property_idx}")
        
        # Parse all data rows
        all_rows = []
        for row in rows[1:]:
            cells = row.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c')
            row_data = [''] * len(headers)
            
            for cell in cells:
                # Get column index from cell reference (e.g., "A1" -> 0)
                cell_ref = cell.get('r')
                col_letter = ''.join([c for c in cell_ref if c.isalpha()])
                
                # Convert column letter to index
                col_idx = 0
                for c in col_letter:
                    col_idx = col_idx * 26 + (ord(c) - ord('A') + 1)
                col_idx -= 1
                
                val = get_cell_value(cell, shared_strings)
                if val and col_idx < len(row_data):
                    row_data[col_idx] = val
            
            all_rows.append(row_data)
        
        print(f"\nData rows: {len(all_rows)}")
        
        # Show first 3 rows
        print("\n" + "=" * 80)
        print("SAMPLE DATA (first 3 rows):")
        print("=" * 80)
        
        for i, row_data in enumerate(all_rows[:3], 1):
            print(f"\nRow {i}:")
            for j, header in enumerate(headers):
                if j < len(row_data) and row_data[j]:
                    print(f"  {header}: {row_data[j]}")
        
        # Statistics
        sources = [row[source_idx] for row in all_rows if source_idx is not None and source_idx < len(row)]
        districts = [row[district_idx] for row in all_rows if district_idx is not None and district_idx < len(row)]
        
        source_counts = Counter(sources)
        
        print("\n" + "=" * 80)
        print("STATISTICS:")
        print("=" * 80)
        
        print(f"\nBy Source:")
        for source, count in source_counts.most_common():
            print(f"  {source}: {count}")
        
        # Centaline-specific analysis
        centaline_count = source_counts.get('Centaline', 0)
        print(f"\n✓ Centaline records: {centaline_count}")
        
        if centaline_count > 0:
            # Get Centaline districts
            centaline_districts = []
            for row in all_rows:
                if source_idx < len(row) and row[source_idx] == 'Centaline':
                    if district_idx < len(row):
                        centaline_districts.append(row[district_idx])
            
            district_counts = Counter(centaline_districts)
            
            print(f"\nCentaline district distribution:")
            for dist, count in district_counts.most_common():
                print(f"  {dist}: {count}")
            
            # Check for missing districts
            na_count = sum(1 for d in centaline_districts if d == 'N/A' or d == '' or not d)
            if na_count > 0:
                print(f"\n⚠️  WARNING: {na_count} Centaline records with missing district ({na_count/centaline_count*100:.1f}%)")
                
                # Show examples
                print("\nExamples of records with missing district:")
                count = 0
                for row in all_rows:
                    if source_idx < len(row) and row[source_idx] == 'Centaline':
                        if district_idx < len(row) and (row[district_idx] == 'N/A' or row[district_idx] == '' or not row[district_idx]):
                            print(f"\n  Property: {row[property_idx] if property_idx < len(row) else 'N/A'}")
                            print(f"  Date: {row[date_idx] if date_idx < len(row) else 'N/A'}")
                            print(f"  District: '{row[district_idx] if district_idx < len(row) else ''}'")
                            count += 1
                            if count >= 3:
                                break
            else:
                print("\n✓ All Centaline records have district information")
