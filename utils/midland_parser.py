#!/usr/bin/env python3
"""
Midland ICI Data Parser
Parses manually copied transaction data from Midland ICI website
"""

import re
from datetime import datetime
from typing import List, Dict


class MidlandParser:
    """Parse Midland ICI transaction data from text file"""
    
    def parse_transactions(self, filepath: str = "midland_data.txt") -> List[Dict]:
        """Parse Midland transactions from text file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remove comments
        lines = [line.strip() for line in content.split('\n') 
                if line.strip() and not line.strip().startswith('#')]
        
        if not lines:
            return []
        
        # Skip all header lines
        start_idx = 0
        for i, line in enumerate(lines):
            if line in ['成交日期', '用途', '地址', '面積(約)', '成交價/呎價', '資料來源']:
                start_idx = i + 1
        
        lines = lines[start_idx:]
        
        transactions = []
        i = 0
        
        while i < len(lines):
            # Each transaction is 8 lines:
            # 0: Asset type (寫字樓/工商/舖位)
            # 1: Property details (District Property Floor Unit)
            # 2: Area (5,835 呎)
            # 3: Date (2025/12/13)
            # 4: Source (市場資訊/土地註冊處)
            # 5: Nature (租/售)
            # 6: Price ($93,360 or $2.05億)
            # 7: Unit price (@$16)
            
            if i + 7 < len(lines):
                try:
                    trans = self._parse_transaction_block(lines[i:i+8])
                    if trans:
                        transactions.append(trans)
                    i += 8
                    
                    # Skip "相關放盤" if it appears
                    if i < len(lines) and '相關' in lines[i]:
                        i += 1
                        
                except Exception as e:
                    print(f"Error parsing at line {i}: {e}")
                    i += 1
            else:
                break
        
        return transactions
    
    def _parse_transaction_block(self, block: list) -> Dict:
        """Parse 8-line transaction block"""
        if len(block) < 8:
            return None
        
        trans = {
            'source': 'Company B',  # Privacy: actual name in config
            'category': 'Commercial',
            'area_basis': 'GFA',
            'unit_basis': 'sqft'
        }
        
        try:
            # Line 0: Asset type
            asset_type = block[0]
            if '寫字樓' in asset_type:
                trans['asset_type'] = '寫字樓'
            elif '商舖' in asset_type or '舖位' in asset_type:
                trans['asset_type'] = '商舖'
            elif '工商' in asset_type or '工廈' in asset_type:
                trans['asset_type'] = '工廈'
            else:
                trans['asset_type'] = 'Commercial'
            
            # Line 1: Property details
            property_line = block[1]
            district, property_name, floor, unit = self._parse_property_line(property_line)
            trans['district'] = district
            trans['property'] = property_name
            trans['floor'] = floor
            trans['unit'] = unit
            
            # Line 2: Area
            area_str = block[2]
            area_match = re.search(r'([\d,]+)\s*呎', area_str)
            if area_match:
                trans['area'] = area_match.group(1).replace(',', '')
                trans['area_unit'] = trans['area']
            
            # Line 3: Date
            date_str = block[3]
            try:
                date_obj = datetime.strptime(date_str, '%Y/%m/%d')
                trans['date'] = date_obj.strftime('%d/%m/%Y')
                trans['date_obj'] = date_obj
            except:
                trans['date'] = date_str
            
            # Line 4: Source (skip, we use "Midland ICI")
            
            # Line 5: Nature (租/售)
            nature = block[5]
            if '租' in nature:
                trans['nature'] = 'Lease'
            elif '售' in nature:
                trans['nature'] = 'Sales'
            
            # Line 6: Price
            price_str = block[6]
            trans['price'] = price_str
            trans['price_numeric'] = self._parse_price(price_str)
            
            # Line 7: Unit price
            unit_price_str = block[7]
            price_match = re.search(r'@\$?([\d,]+)', unit_price_str)
            if price_match:
                trans['unit_price'] = price_match.group(1).replace(',', '')
            
            return trans
            
        except Exception as e:
            print(f"Error in block: {e}")
            return None
    
    def _parse_property_line(self, line: str) -> tuple:
        """
        Parse property line to extract district, property, floor, unit
        Example: "長沙灣 擎天廣場 低層 全層"
        Returns: (district, property, floor, unit)
        """
        parts = line.split()
        
        district = parts[0] if len(parts) > 0 else 'N/A'
        
        # Find floor keywords
        floor = 'N/A'
        floor_keywords = ['高層', '中層', '低層', '全層', '地下']
        floor_idx = -1
        for kw in floor_keywords:
            for i, part in enumerate(parts):
                if kw in part:
                    floor = kw
                    floor_idx = i
                    break
            if floor_idx >= 0:
                break
        
        # Unit is usually after floor
        unit = 'N/A'
        if floor_idx >= 0 and floor_idx + 1 < len(parts):
            unit_part = parts[floor_idx + 1]
            # Check if it's a unit (contains 室 or looks like unit)
            if '室' in unit_part:
                unit = unit_part.replace('室', '')
            elif re.match(r'^[A-Z0-9\-,]+$', unit_part):
                unit = unit_part
            elif unit_part == '全層':
                floor = '全層'
                unit = 'N/A'
        
        # Property is between district and floor
        if floor_idx > 1:
            property_name = ' '.join(parts[1:floor_idx])
        elif len(parts) > 1:
            property_name = parts[1]
        else:
            property_name = 'N/A'
        
        return district, property_name, floor, unit
    
    def _parse_price(self, price_str: str) -> str:
        """Parse price to numeric HKD"""
        price_str = price_str.replace('$', '').replace(',', '').strip()
        
        if '億' in price_str:
            num = float(re.sub(r'[^\d.]', '', price_str))
            return str(int(num * 100000000))
        elif '萬' in price_str:
            num = float(re.sub(r'[^\d.]', '', price_str))
            return str(int(num * 10000))
        else:
            # Already in dollars
            try:
                return str(int(float(price_str)))
            except:
                return price_str


if __name__ == "__main__":
    # Test
    test_data = """成交日期
用途
地址
面積(約)
成交價/呎價
資料來源
寫字樓
長沙灣 擎天廣場 低層 全層
5,835 呎
2025/12/13
市場資訊
租
$93,360
@$16
相關放盤"""
    
    with open('midland_data.txt', 'w', encoding='utf-8') as f:
        f.write(test_data)
    
    parser = MidlandParser()
    transactions = parser.parse_transactions()
    
    print(f"Found {len(transactions)} transactions")
    for trans in transactions:
        print(f"\n{trans}")

