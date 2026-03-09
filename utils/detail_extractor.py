#!/usr/bin/env python3
"""
Detail Extractor — extracts structured transaction details from articles using AI.
"""

import logging
from typing import Dict
from openai import OpenAI
import httpx
from .utils import load_config, parse_json_response, format_date_str

logger = logging.getLogger(__name__)


class DetailExtractor:
    """Extract detailed transaction information using AI."""

    def __init__(self, config_path: str = "config.yml"):
        config = load_config(config_path)
        deepseek_config = config.get('deepseek', {})
        api_key = deepseek_config.get('api_key', '')
        
        # Only initialize AI if API key is provided
        if api_key and api_key.strip() and api_key != 'YOUR_API_KEY_HERE':
            self.client = OpenAI(
                api_key=api_key,
                base_url=deepseek_config.get('api_base', 'https://api.deepseek.com'),
                http_client=httpx.Client(verify=False)
            )
            self.model = deepseek_config.get('chat_model', deepseek_config.get('model', 'deepseek-chat'))
            self.temperature = deepseek_config.get('temperature', 0.3)
            self.ai_enabled = True
        else:
            self.client = None
            self.model = None
            self.temperature = 0.3
            self.ai_enabled = False
            logger.warning("No AI API key configured - AI features disabled")
    
    def extract_transaction_details(self, article: Dict) -> Dict:
        """Extract detailed transaction information."""
        if not self.ai_enabled:
            logger.warning("AI not enabled - returning basic details only")
            return self._get_basic_transaction_details(article)

        title = article.get('title', '')
        content = article.get('full_content', article.get('description', ''))
        date_str = article.get('date', '')
        formatted_date = format_date_str(date_str)
        
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
            details_dict = parse_json_response(result)
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
    
    def _get_basic_transaction_details(self, article: Dict) -> Dict:
        """Get basic transaction details when AI is not available."""
        title = article.get('title', '')
        formatted_date = format_date_str(article.get('date', ''))
        
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
        """Extract news summary using AI."""
        if not self.ai_enabled:
            logger.warning("AI not enabled - returning basic news summary")
            return self._get_basic_news_summary(article)

        title = article.get('title', '')
        content = article.get('full_content', article.get('description', ''))
        formatted_date = format_date_str(article.get('date', ''))
        
        prompt = f"""請根據以下新聞提供一段總結, 大約120中文字, 需要事實, 毋需你的評語, 如果有數據或引用, 請儘量包括在總結中, 但不需要提及當前報章的名字:

標題: {title}
內容: {content[:3000]}

另外，請判斷這則新聞的物業類別(選擇一個):
- Residential (住宅市場相關，包括住宅交易趨勢、估值、市場分析)
- Commercial (商業物業相關，包括寫字樓、商鋪、工廈市場趨勢和估值)

**重要過濾規則**:
1. **只選擇與物業估值、市場趨勢、價格分析直接相關的新聞**
2. **必須排除以下類型 (選General)**:
   - **大灣區新聞** (任何提及大灣區、灣區、粵港澳大灣區的新聞)
   - **內地地產新聞** (非香港本地的地產新聞，如深圳、廣州等)
   - 專欄作家文章 (專欄作家、專欄作者等)
   - 單一物業交易詳情 (只講某個物業的成交，沒有市場分析)
   - 海外地產新聞
   - 與估值無關的一般新聞 (如社會新聞、政治新聞等)
   - **物業質素問題、投訴、驗收問題** (如樓花質素差誤、手工粗糙、空鼓、用料問題等，除非涉及估值影響)
   - **物業管理相關** (管理費、業主會、法團等，除非涉及估值)
3. **必須是關於香港本地地產市場的估值、價格趨勢、市場分析**
4. 政策新聞如果影響香港物業估值或市場價格，選Residential或Commercial；如果只是一般政策不涉及估值，選General
5. **重點**: 大灣區、內地、海外新聞 = General (排除)
6. 如果新聞不符合以上條件，請選擇"General"以排除

請以JSON格式回覆:
{{
  "summary": "您的120字總結",
  "asset_category": "Residential/Commercial/General"
}}"""

        def _call_api(prompt_text: str) -> dict:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是專業的香港地產新聞分析師。"},
                    {"role": "user", "content": prompt_text},
                ],
                temperature=0.3,
                max_tokens=500,
            )
            result = response.choices[0].message.content.strip()
            d = parse_json_response(result)
            d['date'] = formatted_date
            d['topic'] = title
            return d

        try:
            return _call_api(prompt)
        except Exception as e:
            err_str = str(e)
            # DeepSeek rejects some content due to its moderation filter.
            # Retry with title-only (no article body) before giving up.
            if 'Content Exists Risk' in err_str or '400' in err_str:
                logger.warning(
                    f"Content moderation triggered for '{title[:40]}' — "
                    "retrying with title only"
                )
                title_only_prompt = (
                    f"請根據以下新聞標題判斷物業類別並提供簡短總結:\n\n"
                    f"標題: {title}\n\n"
                    f"請以JSON格式回覆:\n"
                    f'{{"summary": "短摘要", "asset_category": "Residential/Commercial/General"}}'
                )
                try:
                    return _call_api(title_only_prompt)
                except Exception as e2:
                    logger.warning(f"Retry also failed for '{title[:40]}': {e2}")
            else:
                logger.error(f"Error extracting summary: {e}")

            return {
                'date': formatted_date,
                'topic': title,
                'summary': content[:120] if content else 'N/A',
                'asset_category': 'General',
            }
    
    def _get_basic_news_summary(self, article: Dict) -> Dict:
        """Get basic news summary when AI is not available."""
        title = article.get('title', '')
        content = article.get('full_content', article.get('description', ''))
        formatted_date = format_date_str(article.get('date', ''))
        return {
            'date': formatted_date,
            'topic': title,
            'summary': content[:120] if content else 'N/A',
            'asset_category': 'General'
        }

