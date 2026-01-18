#!/usr/bin/env python3
"""
Centaline Data Parser
Parses manually copied transaction data from Centaline website
"""

import re
from datetime import datetime
from typing import List, Dict


class CentalineParser:
    """Parse Centaline transaction data from text file"""
    
    def parse_transactions(self, filepath: str = "centaline_data.txt") -> List[Dict]:
        """
        Parse transactions from text file
        Handles both tab-separated format and block format
        
        Args:
            filepath: Path to the data file
            
        Returns:
            List of transaction dictionaries
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check format: if first line has tabs, it's table format
        lines = [line for line in content.split('\n') if line.strip()]
        
        if not lines:
            return []
        
        # Check if tab-separated format
        if '\t' in lines[0]:
            return self._parse_table_format(content)
        else:
            # Original block format
            return self._parse_block_format(content)
    
    def _parse_table_format(self, content: str) -> List[Dict]:
        """Parse tab-separated table format from Centaline"""
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        
        transactions = []
        i = 0
        
        while i < len(lines):
            # Skip header line
            if '日期' in lines[i]:
                i += 1
                continue
            
            # Each transaction block (8 lines):
            # Line i+0: Date (YYYY-MM-DD)
            # Line i+1: Property (葡萄園 1期 瑪歌大道 洋房19 瑪歌大道 19號屋)
            # Line i+2: Layout (3 房 or --)
            # Line i+3: Price ($1,950萬)
            # Line i+4: Area (2,016呎)
            # Line i+5: Unit price (@$9,673)
            # Line i+6: Change (-- or -11%)
            # Line i+7: Source (土地註冊處)
            
            if i + 7 < len(lines):
                try:
                    trans = {
                        'source': 'Company A',  # Privacy: actual name in config
                        'category': 'Residential',
                        'nature': 'Sales',
                        'area_basis': 'NFA',
                        'unit_basis': 'sqft'
                    }
                    
                    # Date
                    date_str = lines[i]
                    try:
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                        trans['date'] = date_obj.strftime('%d/%m/%Y')
                        trans['date_obj'] = date_obj
                    except:
                        trans['date'] = date_str
                    
                    # Property (line i+1)
                    property_full = lines[i + 1]
                    property_name, floor, unit = self._parse_property_details(property_full)
                    trans['property'] = property_name
                    trans['floor'] = floor
                    trans['unit'] = unit
                    
                    # Extract district from property name (first part usually)
                    parts = property_name.split()
                    if len(parts) > 0:
                        # District might be in property name, try to extract
                        trans['district'] = 'N/A'  # Will be extracted by AI or manual
                    
                    # Layout (line i+2)
                    layout = lines[i + 2]
                    if layout != '--':
                        trans['layout'] = layout
                    
                    # Price (line i+3) - format: "$1,950萬"
                    price = lines[i + 3]
                    trans['price'] = price
                    trans['price_numeric'] = self._parse_price(price)
                    
                    # Area (line i+4) - format: "2,016呎"
                    area_str = lines[i + 4]
                    area_match = re.search(r'([\d,]+)呎', area_str)
                    if area_match:
                        trans['area'] = area_match.group(1).replace(',', '')
                        trans['area_unit'] = trans['area']
                    
                    # Unit price (line i+5) - format: "@$9,673"
                    unit_price_str = lines[i + 5]
                    price_match = re.search(r'@\$?([\d,]+)', unit_price_str)
                    if price_match:
                        trans['unit_price'] = price_match.group(1).replace(',', '')
                    
                    # Asset type
                    if '洋房' in property_full:
                        trans['asset_type'] = '洋房'
                    elif '座' in property_full:
                        trans['asset_type'] = '住宅'
                    else:
                        trans['asset_type'] = '住宅'
                    
                    transactions.append(trans)
                    
                except Exception as e:
                    print(f"Error parsing transaction at line {i}: {e}")
                
                # Move to next transaction (8 lines per transaction)
                i += 8
            else:
                break
        
        return transactions
    
    def _parse_block_format(self, content: str) -> List[Dict]:
        """Parse block format (original 已售 separated)"""
        transactions = []
        blocks = content.split('已售')
        
        for block in blocks:
            if len(block.strip()) < 50:
                continue
            
            trans = self._parse_transaction_block(block)
            if trans:
                transactions.append(trans)
        
        return transactions
    
    def _parse_transaction_block(self, block: str) -> Dict:
        """Parse a single transaction block"""
        lines = [line.strip() for line in block.split('\n') if line.strip()]
        
        if len(lines) < 5:
            return None
        
        transaction = {
            'source': 'Centaline',
            'category': 'Residential',
            'nature': 'Sales',
            'area_basis': 'NFA',
            'unit_basis': 'sqft'
        }
        
        try:
            # After split by "已售", the block structure is:
            # Line 0: May be empty or part of previous property name (skip if not source)
            # Find the source line (土地註冊處 or 中原集團)
            source_idx = None
            for i, line in enumerate(lines):
                if '土地註冊處' in line or '中原集團' in line or '利嘉閣' in line or '美聯' in line:
                    source_idx = i
                    break
            
            if source_idx is None:
                return None
            
            # Property details is right after source
            property_details = lines[source_idx + 1] if source_idx + 1 < len(lines) else ''
            
            # District is right after property details
            potential_district = lines[source_idx + 2] if source_idx + 2 < len(lines) else ''
            
            # Extract property name and parse for building/floor/unit
            property_name, floor, unit = self._parse_property_details(property_details)
            transaction['property'] = property_name
            transaction['floor'] = floor
            transaction['unit'] = unit
            
            # Check if line 3 is actually a district (not a keyword)
            skip_keywords = ['註冊日期', '成交', '實用', '建築', '間隔', '升跌', '向東', '向西', '向南', '向北', '呎', '室', '樓']
            
            if (potential_district and 
                len(potential_district) < 15 and
                not any(keyword in potential_district for keyword in skip_keywords)):
                transaction['district'] = potential_district
            else:
                # Try to find it in subsequent lines
                for i in range(4, min(8, len(lines))):
                    line = lines[i]
                    if (len(line) < 15 and 
                        not any(keyword in line for keyword in skip_keywords) and
                        not re.search(r'\d{4}-\d{2}-\d{2}', line) and  # Not a date
                        len(line) > 0):
                        transaction['district'] = line
                        break
            
            # Find registration date
            for i, line in enumerate(lines):
                if '註冊日期' in line or '成交日期' in line:
                    if i + 1 < len(lines):
                        date_str = lines[i + 1]
                        # Parse date
                        try:
                            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                            transaction['date'] = date_obj.strftime('%d/%m/%Y')
                            transaction['date_obj'] = date_obj
                        except:
                            transaction['date'] = date_str
            
            # Find price (成交價)
            for i, line in enumerate(lines):
                if '成交價' in line:
                    if i + 1 < len(lines):
                        price_str = lines[i + 1]
                        transaction['price'] = price_str
                        # Extract numeric value
                        transaction['price_numeric'] = self._parse_price(price_str)
            
            # Find area (實用) - the area/unit price is on the line AFTER "實用"
            for i, line in enumerate(lines):
                if '實用' in line:
                    # Check the next line for area and unit price
                    if i + 1 < len(lines):
                        area_line = lines[i + 1]
                        # Format: "2,016呎 @$9,673" or "2,016呎 @$9,673 /呎"
                        area_match = re.search(r'([\d,]+)呎', area_line)
                        price_match = re.search(r'@\$?([\d,]+)', area_line)
                        
                        if area_match:
                            area = area_match.group(1).replace(',', '')
                            transaction['area'] = area
                            transaction['area_unit'] = area
                        
                        if price_match:
                            unit_price = price_match.group(1).replace(',', '')
                            transaction['unit_price'] = unit_price
                    break  # Found it, no need to continue
            
            # Find layout (間隔)
            for i, line in enumerate(lines):
                if '間隔' in line:
                    if i + 1 < len(lines):
                        layout = lines[i + 1]
                        if layout != '--':
                            transaction['layout'] = layout
            
            # Asset type
            if '洋房' in property_details or '洋房' in property_name:
                transaction['asset_type'] = '洋房'
            elif '座' in property_details:
                transaction['asset_type'] = '住宅'
            else:
                transaction['asset_type'] = '住宅'
            
            return transaction
            
        except Exception as e:
            print(f"Error parsing block: {e}")
            return None
    
    def _parse_property_details(self, details: str) -> tuple:
        """
        Parse property details to extract name, floor, unit
        
        Examples:
        - "葡萄園 1期 瑪歌大道 洋房19" → ("葡萄園 1期 瑪歌大道", "洋房", "19")
        - "愛都大廈 2座 30樓 C室" → ("愛都大廈 2座", "30樓", "C")
        - "加多利園" → ("加多利園", "N/A", "N/A")
        """
        floor = "N/A"
        unit = "N/A"
        
        # Check for 洋房 pattern (e.g., "洋房19", "洋房1A")
        house_match = re.search(r'洋房(\d+[A-Z]?|\d+號屋?|[A-Z]\d+)', details)
        if house_match:
            floor = "洋房"
            unit = house_match.group(1).replace('號屋', '')  # Remove 號屋 suffix
            # Property name is everything before "洋房"
            property_name = details[:house_match.start()].strip()
            property_name = re.sub(r'\s+', ' ', property_name).strip()
            return property_name, floor, unit
        
        # Extract floor (e.g., "30樓", "地下")
        floor_match = re.search(r'(\d+樓|地下|低層|中層|高層|頂層|全幢)', details)
        if floor_match:
            floor = floor_match.group(1)
        
        # Extract unit (e.g., "A室", "C室") - just the letter
        unit_match = re.search(r'([A-Z])室', details)
        if unit_match:
            unit = unit_match.group(1)  # Just the letter, not "A室"
        
        # Property name - keep everything up to (but not including) the floor
        # If no floor, keep everything
        property_name = details
        
        if floor != "N/A" and floor in details:
            # Split at floor and take the part before
            parts = details.split(floor)
            property_name = parts[0].strip()
        elif unit != "N/A" and f"{unit}室" in details:
            # If we have unit but no floor, split at unit
            parts = details.split(f"{unit}室")
            property_name = parts[0].strip()
        
        # Clean up extra spaces
        property_name = re.sub(r'\s+', ' ', property_name).strip()
        
        return property_name, floor, unit
    
    def _parse_price(self, price_str: str) -> str:
        """Extract numeric price"""
        # Remove $ and convert
        price_str = price_str.replace('$', '').replace(',', '').strip()
        
        if '億' in price_str:
            # e.g., "$1.52億" → 152000000
            num = float(re.sub(r'[^\d.]', '', price_str))
            return str(int(num * 100000000))
        elif '萬' in price_str:
            # e.g., "$1,950萬" → 19500000
            num = float(re.sub(r'[^\d.]', '', price_str))
            return str(int(num * 10000))
        else:
            return price_str


if __name__ == "__main__":
    # Test the parser
    parser = CentalineParser()
    
    # Test with sample data
    test_data = """葡萄園1期瑪歌大道 洋房19瑪歌大道19號屋 已售
土地註冊處
葡萄園 1期 瑪歌大道 洋房19
牛潭尾
註冊日期
2025-12-12
成交價
$1,950萬
實用
2,016呎 @$9,673
建築
2,898呎 @$6,729 /呎
間隔
3 房"""
    
    with open('centaline_data.txt', 'w', encoding='utf-8') as f:
        f.write(test_data)
    
    transactions = parser.parse_transactions()
    
    print(f"Found {len(transactions)} transactions")
    for trans in transactions:
        print(f"\n{trans}")

