#!/usr/bin/env python3
"""
Detail Extractor - Extract structured transaction details using DeepSeek AI
"""

import yaml
import logging
from typing import Dict, List
from openai import OpenAI
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DetailExtractor:
    """Extract detailed transaction information using AI"""
    
    def __init__(self, config_path: str = "config.yml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        deepseek_config = self.config['deepseek']
        self.client = OpenAI(
            api_key=deepseek_config['api_key'],
            base_url=deepseek_config['api_base']
        )
        self.model = deepseek_config['model']
        self.temperature = deepseek_config['temperature']
    
    def extract_transaction_details(self, article: Dict) -> Dict:
        """Extract detailed transaction information"""
        title = article.get('title', '')
        content = article.get('full_content', article.get('description', ''))
        date_str = article.get('date', '')
        
        # Convert date to dd/mm/yyyy format
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%d/%m/%Y')
        except:
            formatted_date = date_str
        
        prompt = f"""請從以下香港地產交易新聞中提取詳細資訊。請以JSON格式回覆，只包含數據，不要有其他說明。

新聞標題: {title}
新聞日期: {formatted_date}
新聞內容: {content[:2000]}

請提取以下資訊(如果沒有提及請填"N/A"):
1. district: 地區(如: 金鐘, 中半山, 九龍灣)
2. property: 物業名稱。重要規則:
   - 如有座號(如"2座"、"3座")，必須包含在物業名稱中(例如: "名門 2座", "The Austin 3座")
   - 如果只有地址沒有物業名稱，只填地址，不要加"全幢住宅"等描述
3. asset_type: 物業類別(寫字樓/商鋪/住宅/洋房/工廈/酒店/停車位)
4. floor: 樓層。規則:
   - 如果是"全幢"，只填"全幢"，不要括號說明
   - 如果是"頂層"、"高層"、"低層"等，照填
   - 洋房如無樓層資料填"N/A"
5. unit: 單位。規則:
   - 如已在floor填寫"全幢"或"頂層複式戶"等完整描述，unit填"N/A"
   - 如有具體單位如"A室"、"C室"，只填單位字母/號碼
   - 洋房通常填"N/A"
6. nature: 交易性質(Sales或Lease)
7. price: 成交價(只填數字,以港元計)
8. area: 面積(只填數字,單位呎)
9. unit_price: 呎價(只填數字,四捨五入至整數)
10. yield_rate: 回報率/租金回報(如有提及，請轉換為小數格式，例如"7厘"或"7%"應填"0.07"，如果是"逾7厘"填"0.07")
11. seller: 賣家/業主
12. buyer: 買家/租客

請只回覆JSON格式,例如:
{{
  "district": "中環",
  "property": "國際金融中心 2座",
  "asset_type": "寫字樓",
  "floor": "88",
  "unit": "A",
  "nature": "Sales",
  "price": "30000000",
  "area": "2500",
  "unit_price": "12000",
  "yield_rate": "N/A",
  "seller": "某某公司",
  "buyer": "某某投資者"
}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是香港地產交易數據提取專家。請準確提取交易細節，並以JSON格式回覆。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            result = response.choices[0].message.content.strip()
            
            # Try to parse JSON
            import json
            # Remove markdown code blocks if present
            if '```' in result:
                result = result.split('```')[1]
                if result.startswith('json'):
                    result = result[4:]
            
            details_dict = json.loads(result)
            
            # Ensure it's a dict, not a list
            if isinstance(details_dict, list):
                details_dict = details_dict[0] if details_dict else {}
            
            details_dict['date'] = formatted_date
            
            # Convert yield to decimal format if needed
            yield_val = details_dict.get('yield_rate', 'N/A')
            if yield_val and yield_val != 'N/A':
                try:
                    yield_str = str(yield_val).replace('%', '').replace('厘', '').replace('逾', '').strip()
                    yield_num = float(yield_str)
                    if yield_num > 1:
                        details_dict['yield_rate'] = yield_num / 100
                    else:
                        details_dict['yield_rate'] = yield_num
                except:
                    details_dict['yield_rate'] = yield_val
            
            return details_dict
            
        except Exception as e:
            logger.error(f"Error extracting details: {e}")
            return {
                'date': formatted_date,
                'district': 'N/A',
                'property': title[:50],
                'asset_type': 'N/A',
                'floor': 'N/A',
                'unit': 'N/A',
                'nature': 'N/A',
                'price': 'N/A',
                'area': 'N/A',
                'unit_price': 'N/A',
                'yield_rate': 'N/A',
                'seller': 'N/A',
                'buyer': 'N/A'
            }
    
    def extract_news_summary(self, article: Dict) -> Dict:
        """Extract news summary using AI"""
        title = article.get('title', '')
        content = article.get('full_content', article.get('description', ''))
        date_str = article.get('date', '')
        
        # Convert date
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%d/%m/%Y')
        except:
            formatted_date = date_str
        
        prompt = f"""請根據以下新聞提供一段總結, 大約120中文字, 需要事實, 毋需你的評語, 如果有數據或引用, 請儘量包括在總結中, 但不需要提及當前報章的名字:

標題: {title}
內容: {content[:3000]}

另外，請判斷這則新聞的物業類別(選擇一個):
- Residential (住宅市場相關，包括住宅交易趨勢、估值、市場分析)
- Commercial (商業物業相關，包括寫字樓、商鋪、工廈市場趨勢和估值)

**重要過濾規則**:
1. **只選擇與物業估值、市場趨勢、價格分析直接相關的新聞**
2. **排除以下類型**:
   - 專欄作家文章 (專欄作家、專欄作者等)
   - 單一物業交易詳情 (只講某個物業的成交，沒有市場分析)
   - 非香港地產新聞 (內地、海外地產新聞)
   - 與估值無關的一般新聞 (如社會新聞、政治新聞等)
   - **物業質素問題、投訴、驗收問題** (如樓花質素差誤、手工粗糙、空鼓、用料問題等，除非涉及估值影響)
   - **物業管理相關** (管理費、業主會、法團等，除非涉及估值)
3. **必須是關於香港地產市場的估值、價格趨勢、市場分析**
4. 政策新聞如果影響物業估值或市場價格，選Residential或Commercial；如果只是一般政策不涉及估值，選General
5. 如果新聞不符合以上條件，請選擇"General"以排除

請以JSON格式回覆:
{{
  "summary": "您的120字總結",
  "asset_category": "Residential/Commercial/General"
}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是專業的香港地產新聞分析師。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            result = response.choices[0].message.content.strip()
            
            import json
            if '```' in result:
                result = result.split('```')[1]
                if result.startswith('json'):
                    result = result[4:]
            
            details_dict = json.loads(result)
            
            # Ensure it's a dict
            if isinstance(details_dict, list):
                details_dict = details_dict[0] if details_dict else {}
            
            details_dict['date'] = formatted_date
            details_dict['topic'] = title
            return details_dict
            
        except Exception as e:
            logger.error(f"Error extracting summary: {e}")
            return {
                'date': formatted_date,
                'topic': title,
                'summary': content[:120] if content else 'N/A',
                'asset_category': 'General'
            }

