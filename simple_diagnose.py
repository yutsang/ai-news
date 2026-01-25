#!/usr/bin/env python3
"""
Simple diagnostic using only standard library
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

with zipfile.ZipFile(file_path, 'r') as zip_ref:
    # Read shared strings
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
        print("No shared strings found")
    
    print(f"\nTotal shared strings: {len(shared_strings)}")
    
    # Find Trans_Commercial sheet
    with zip_ref.open('xl/workbook.xml') as f:
        tree = ET.parse(f)
        root = tree.getroot()
        sheets = root.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheet')
        
        trans_comm_id = None
        for sheet in sheets:
            if sheet.get('name') == 'Trans_Commercial':
                trans_comm_id = sheet.get('sheetId')
                rel_id = sheet.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
                print(f"\nFound Trans_Commercial sheet (ID: {trans_comm_id}, RelID: {rel_id})")
                
                # Find worksheet file
                with zip_ref.open('xl/_rels/workbook.xml.rels') as rels_f:
                    rels_tree = ET.parse(rels_f)
                    rels_root = rels_tree.getroot()
                    for rel in rels_root:
                        if rel.get('Id') == rel_id:
                            target = rel.get('Target')
                            # Target may start with /, remove it
                            if target.startswith('/'):
                                worksheet_path = target[1:]
                            else:
                                worksheet_path = 'xl/' + target
                            print(f"Worksheet path: {worksheet_path}")
                            
                            # Read worksheet
                            with zip_ref.open(worksheet_path) as ws_f:
                                ws_tree = ET.parse(ws_f)
                                ws_root = ws_tree.getroot()
                                
                                rows = ws_root.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row')
                                print(f"Total rows: {len(rows)}")
                                
                                # Get header row (row 1)
                                header_row = rows[0] if rows else None
                                if header_row:
                                    cells = header_row.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c')
                                    headers = []
                                    for cell in cells:
                                        v = cell.find('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v')
                                        if v is not None and v.text:
                                            # Check if it's a shared string reference
                                            if cell.get('t') == 's':
                                                idx = int(v.text)
                                                if idx < len(shared_strings):
                                                    headers.append(shared_strings[idx])
                                            else:
                                                headers.append(v.text)
                                    
                                    print(f"\nHeaders: {headers}")
                                    
                                    # Try to find District and Source columns
                                    district_col_idx = None
                                    source_col_idx = None
                                    property_col_idx = None
                                    
                                    for i, h in enumerate(headers):
                                        if h == 'District':
                                            district_col_idx = i
                                        elif h == 'Source':
                                            source_col_idx = i
                                        elif h == 'Property':
                                            property_col_idx = i
                                    
                                    print(f"\nColumn indices: District={district_col_idx}, Source={source_col_idx}, Property={property_col_idx}")
                                    
                                    # Check first 5 data rows
                                    print("\n" + "=" * 80)
                                    print("SAMPLE DATA (first 5 rows):")
                                    print("=" * 80)
                                    
                                    sources = []
                                    districts = []
                                    centaline_count = 0
                                    
                                    for row_idx, row in enumerate(rows[1:6], 2):  # Skip header
                                        cells = row.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c')
                                        row_data = {}
                                        
                                        for cell in cells:
                                            # Get column reference (e.g., "A", "B", "C")
                                            cell_ref = cell.get('r')
                                            col_letter = ''.join([c for c in cell_ref if c.isalpha()])
                                            col_idx = ord(col_letter) - ord('A') if len(col_letter) == 1 else (ord(col_letter[0]) - ord('A') + 1) * 26 + (ord(col_letter[1]) - ord('A'))
                                            
                                            v = cell.find('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v')
                                            if v is not None and v.text:
                                                if cell.get('t') == 's':
                                                    idx = int(v.text)
                                                    if idx < len(shared_strings):
                                                        value = shared_strings[idx]
                                                    else:
                                                        value = v.text
                                                else:
                                                    value = v.text
                                                
                                                if col_idx < len(headers):
                                                    row_data[headers[col_idx]] = value
                                        
                                        print(f"\nRow {row_idx}:")
                                        for h in ['Source', 'District', 'Property', 'Date']:
                                            if h in row_data:
                                                print(f"  {h}: {row_data[h]}")
                                        
                                        # Collect stats
                                        if 'Source' in row_data:
                                            sources.append(row_data['Source'])
                                            if row_data['Source'] == 'Centaline':
                                                centaline_count += 1
                                        if 'District' in row_data:
                                            districts.append(row_data['District'])
                                    
                                    # Check all rows for statistics
                                    print("\n" + "=" * 80)
                                    print("STATISTICS (all rows):")
                                    print("=" * 80)
                                    
                                    all_sources = []
                                    all_districts = []
                                    centaline_districts = []
                                    
                                    for row in rows[1:]:  # Skip header
                                        cells = row.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c')
                                        row_data = {}
                                        
                                        for cell in cells:
                                            cell_ref = cell.get('r')
                                            col_letter = ''.join([c for c in cell_ref if c.isalpha()])
                                            col_idx = ord(col_letter) - ord('A') if len(col_letter) == 1 else (ord(col_letter[0]) - ord('A') + 1) * 26 + (ord(col_letter[1]) - ord('A'))
                                            
                                            v = cell.find('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v')
                                            if v is not None and v.text:
                                                if cell.get('t') == 's':
                                                    idx = int(v.text)
                                                    if idx < len(shared_strings):
                                                        value = shared_strings[idx]
                                                    else:
                                                        value = v.text
                                                else:
                                                    value = v.text
                                                
                                                if col_idx < len(headers):
                                                    row_data[headers[col_idx]] = value
                                        
                                        if 'Source' in row_data:
                                            all_sources.append(row_data['Source'])
                                        if 'District' in row_data:
                                            all_districts.append(row_data['District'])
                                        
                                        # Track Centaline districts specifically
                                        if 'Source' in row_data and row_data['Source'] == 'Centaline':
                                            if 'District' in row_data:
                                                centaline_districts.append(row_data['District'])
                                    
                                    source_counts = Counter(all_sources)
                                    print(f"\nBy Source:")
                                    for source, count in source_counts.most_common():
                                        print(f"  {source}: {count}")
                                    
                                    print(f"\nCentaline records: {source_counts.get('Centaline', 0)}")
                                    print(f"Centaline districts: {len(centaline_districts)}")
                                    
                                    if centaline_districts:
                                        district_counts = Counter(centaline_districts)
                                        print(f"\nCentaline district distribution:")
                                        for dist, count in district_counts.most_common(10):
                                            print(f"  {dist}: {count}")
                                        
                                        # Check for N/A or missing
                                        na_count = sum(1 for d in centaline_districts if d == 'N/A' or not d)
                                        print(f"\nCentaline records with missing district: {na_count} / {len(centaline_districts)} ({na_count/len(centaline_districts)*100:.1f}%)")
                            
                            break
                break
