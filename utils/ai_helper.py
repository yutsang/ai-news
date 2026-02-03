#!/usr/bin/env python3
"""
AI Helper Module
Handles AI-powered analysis and content generation
Makes AI usage conditional on API key being present for cross-computer compatibility
"""

import yaml
from typing import Dict, List, Optional
import httpx
from openai import OpenAI
import logging

logger = logging.getLogger(__name__)


class AIHelper:
    """AI-powered helper for content analysis"""
    
    def __init__(self, config_path: str = "config.yml"):
        """
        Initialize AI Helper
        
        Args:
            config_path: Path to config file
        """
        self.config_path = config_path
        self.client = None
        self.model = None
        self.ai_enabled = False
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
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
                self.ai_enabled = True
                logger.info("AI helper initialized successfully")
            else:
                logger.warning("No AI API key configured - AI features disabled")
                
        except Exception as e:
            logger.warning(f"Could not initialize AI helper: {e}")
            self.ai_enabled = False
    
    def _get_response(self, system_prompt: str, user_prompt: str, 
                     temperature: float = 0.3, max_tokens: int = 2000) -> Optional[str]:
        """
        Get response from AI model
        
        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            temperature: Temperature setting
            max_tokens: Max tokens in response
        
        Returns:
            AI response content or None if AI not enabled
        """
        if not self.ai_enabled:
            return None
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"Error generating AI response: {str(e)}")
            return None
    
    def extract_district(self, property_name: str) -> str:
        """
        Extract district from property name using AI
        
        Args:
            property_name: Property name
            
        Returns:
            District name or 'N/A' if AI not available
        """
        if not self.ai_enabled or not property_name:
            return 'N/A'
        
        system_prompt = "你是香港地產專家，擅長從物業名稱識別地區。只返回地區名稱，不要解釋。"
        
        user_prompt = f"""從以下香港物業名稱中提取地區名稱。只返回地區名稱，不要其他內容。

物業名稱：{property_name}

地區名稱（例如：中半山、沙田、大埔、西貢、九龍城、南區等）："""

        try:
            response = self._get_response(system_prompt, user_prompt, temperature=0.1, max_tokens=50)
            if response:
                district = response.strip()
                # Clean up the response
                district = district.replace('地區名稱：', '').replace('：', '').strip()
                return district if district else 'N/A'
            return 'N/A'
        except Exception as e:
            logger.debug(f"AI district extraction failed: {e}")
            return 'N/A'
    
    def deduplicate_articles(self, topic1: str, summary1: str, topic2: str, summary2: str) -> bool:
        """
        Determine if two articles are highly similar using AI
        
        Args:
            topic1, summary1: First article
            topic2, summary2: Second article
            
        Returns:
            True if articles are duplicates, False otherwise (or if AI not enabled)
        """
        if not self.ai_enabled:
            return False
        
        system_prompt = "你是專業的新聞去重專家。請準確判斷兩則新聞是否講述相同或高度相似的事件。要寬鬆判斷相似性，避免重複報道同一事件。"
        
        user_prompt = f"""請判斷以下兩則香港地產新聞是否講述相同或高度相似的事件/內容。

新聞1:
標題: {topic1}
摘要: {summary1[:200]}

新聞2:
標題: {topic2}
摘要: {summary2[:200]}

**判斷標準**（請更寬鬆地判斷相似性）:
- 如果兩則新聞講述「相同事件」（例如：同一家銀行的同一份報告），即使報道角度不同，也應視為相似
- 如果兩則新聞講述「同一類型的內容」（例如：多家銀行預測樓價上升的幅度），且主要數據/結論相似，也應視為相似
- 如果一則新聞是另一則的「擴展版本」（內容包含對方），應視為相似
- **只有當兩則新聞是完全不同的事件/主題時，才視為不相似**

請只回答"是"（相似）或"否"（不相似），不要其他說明。"""

        try:
            response = self._get_response(system_prompt, user_prompt, temperature=0.1, max_tokens=10)
            if response:
                result = response.strip().lower()
                return '是' in result or 'yes' in result or result == 'y' or 'similar' in result
            return False
        except Exception as e:
            logger.debug(f"Error in AI deduplication: {e}")
            return False
    
    def score_market_relevance(self, topic: str, summary: str) -> int:
        """
        Score article's relevance to HK market valuation (0-10)
        
        **Important**: Excludes Greater Bay Area (大灣區) news and focuses on Hong Kong only
        
        Args:
            topic: Article topic
            summary: Article summary
            
        Returns:
            Score from 0-10 (10 = most relevant), or 5 if AI not enabled
        """
        if not self.ai_enabled:
            return 5  # Neutral score
        
        system_prompt = "你是香港地產市場分析專家，專門評估新聞對香港市場估值的重要性。**必須排除大灣區新聞，只關注香港本地市場。**"
        
        user_prompt = f"""請評分以下香港地產新聞對整體市場估值的重要性和相關性。

**重要排除規則**:
- **大灣區新聞 = 0分**（任何提及大灣區、灣區、粵港澳大灣區的新聞）
- **內地地產新聞 = 0分**（非香港本地的地產新聞）
- 必須是**香港本地**地產市場新聞才能評分

評分標準 (0-10分):
10分: 重大政策變動、利率調整、整體市場數據/趨勢，對香港市場估值有直接重大影響
8-9分: 重要市場數據、土地供應、大型發展商動向，有明確市場影響
6-7分: 一般市場新聞、區域數據、次要政策，有一定參考價值
4-5分: 個別項目新聞、地區性消息，市場影響有限
2-3分: 評論文章、個別案例、零散資訊，參考價值低
0-1分: 與市場估值無關、質素問題、個人故事、社區瑣事、**大灣區新聞**

標題: {topic}
摘要: {summary}

請只回答一個數字(0-10)，不要其他說明。"""

        try:
            response = self._get_response(system_prompt, user_prompt, temperature=0.3, max_tokens=10)
            if response:
                import re
                score_match = re.search(r'\d+', response.strip())
                if score_match:
                    score = int(score_match.group())
                    return min(10, max(0, score))
            return 5  # Default moderate score
        except Exception as e:
            logger.error(f"Error scoring article: {e}")
            return 5
