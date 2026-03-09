#!/usr/bin/env python3
"""
AI Categorizer — classifies articles into: transactions, news, new_property, or exclude.
"""

import logging
from typing import List, Dict
from openai import OpenAI
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from .utils import load_config

logger = logging.getLogger(__name__)


class DeepSeekCategorizer:
    """Use an AI API to categorize news articles."""

    def __init__(self, config_path: str = "config.yml"):
        self.config = load_config(config_path)
        
        deepseek_config = self.config['deepseek']
        self.client = OpenAI(
            api_key=deepseek_config.get('api_key', 'local-key'),
            base_url=deepseek_config.get('api_base', 'https://api.deepseek.com'),
        )
        self.model = deepseek_config.get('chat_model', deepseek_config.get('model', 'deepseek-chat'))
        self.temperature = deepseek_config.get('temperature', 0.3)
        self.max_tokens = deepseek_config.get('max_tokens', 4000)
        self.categories = self.config['categories']
    
    def categorize_article(self, title: str, description: str = "", tags: List[str] = None) -> str:
        """
        Categorize a single article using DeepSeek AI
        
        Args:
            title: Article title
            description: Article description/preview
            tags: List of tags from the website
            
        Returns:
            Category: 'transactions', 'news', or 'new_property'
        """
        tags = tags or []
        
        # Prepare the prompt - STRICT filtering for market valuation relevance
        prompt = f"""請將以下香港地產新聞分類到以下四個類別之一：

類別1: transactions (交易/成交) - 關於房地產買賣交易、租賃、成交記錄、價格交易等
類別2: news (地產新聞) - **只限於對整體香港市場估值有重大影響的新聞**
   **嚴格要求**: news類別必須符合以下條件之一：
   - 政府政策變動 (樓市辣招、印花稅、按揭政策等)
   - 整體市場數據/統計 (成交量、價格指數、整體升跌趨勢)
   - 金融/經濟因素 (利率、樓按、銀行政策、經濟環境)
   - 土地供應/規劃 (賣地、建屋量、城市規劃)
   - 重大市場事件 (如大型發展商動向、市場預測)
   
   **不符合的排除**:
   - 評論文章、專欄、個人意見
   - 單一物業/屋苑的成交詳情
   - 物業質素問題、投訴
   - 個別業主/買家故事
   - 社區新聞、地區瑣事

類別3: new_property (新盤) - 關於新樓盤、新項目發售、新盤消息等

類別4: exclude (排除) - 以下類型的新聞應分類為exclude：
   - 單一物業交易詳情
   - 物業質素問題、投訴、驗收問題
   - 物業管理相關 (管理費、業主會、法團等)
   - 評論文章、專欄作家觀點、個人意見
   - 社區新聞、地區瑣事
   - 與市場估值無直接關係的新聞
   - 非香港地產新聞

**分類原則**:
只有對香港整體地產市場估值有實質影響的新聞才應分類為news。
如果只是報導個別交易、評論、或不影響市場估值的資訊，應分類為exclude。

新聞標題: {title}

描述: {description}

標籤: {', '.join(tags)}

請只回答以下其中一個類別名稱: transactions, news, new_property, exclude
不要添加任何解釋，只需回答類別名稱。"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一個香港地產新聞分類專家。請根據新聞內容準確分類。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=50
            )
            
            category = response.choices[0].message.content.strip().lower()
            
            # Validate category
            valid_categories = ['transactions', 'news', 'new_property', 'exclude']
            if category in valid_categories:
                return category
            else:
                # Try to match partial response
                for valid_cat in valid_categories:
                    if valid_cat in category:
                        return valid_cat
                
                # Default fallback based on tags
                return self._fallback_categorization(title, description, tags)
                
        except Exception as e:
            logger.error(f"Error calling DeepSeek API: {e}")
            return self._fallback_categorization(title, description, tags)
    
    def _fallback_categorization(self, title: str, description: str, tags: List[str]) -> str:
        """
        Fallback categorization based on keywords when API fails
        
        Args:
            title: Article title
            description: Article description
            tags: List of tags
            
        Returns:
            Category string
        """
        text = f"{title} {description} {' '.join(tags)}".lower()
        
        # Check for transaction keywords
        transaction_keywords = ['成交', '交易', '沽', '售', '租', '蝕讓', '銀主', '收購', '撻訂']
        if any(keyword in text for keyword in transaction_keywords):
            # But if it also has new property keywords, prioritize that
            new_property_keywords = ['新盤', '開售', '首輪', '發售']
            if any(keyword in text for keyword in new_property_keywords):
                return 'new_property'
            return 'transactions'
        
        # Check for new property keywords
        new_property_keywords = ['新盤', '開售', '首輪', '發售', '樓盤', '項目']
        if any(keyword in text for keyword in new_property_keywords):
            return 'new_property'
        
        # Default to news
        return 'news'
    
    def categorize_batch(self, articles: List[Dict], max_workers: int = 10) -> List[Dict]:
        """
        Categorize multiple articles using parallel processing
        
        Args:
            articles: List of article dictionaries
            max_workers: Number of parallel workers (default: 10)
            
        Returns:
            List of articles with 'category' field added
        """
        logger.info(f"Categorizing {len(articles)} articles with {max_workers} workers...")
        
        def categorize_one(article):
            category = self.categorize_article(
                title=article.get('title', ''),
                description=article.get('description', ''),
                tags=article.get('tags', [])
            )
            article['category'] = category
            return article
        
        categorized = []
        
        # Use ThreadPoolExecutor for parallel API calls
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_article = {executor.submit(categorize_one, article): article 
                               for article in articles}
            
            # Collect results with progress bar
            for future in tqdm(as_completed(future_to_article), total=len(articles), 
                              desc="Categorizing", unit="article"):
                try:
                    result = future.result()
                    categorized.append(result)
                except Exception as e:
                    logger.error(f"Error categorizing article: {e}")
                    # Add with fallback
                    article = future_to_article[future]
                    article['category'] = 'news'
                    categorized.append(article)
        
        # Log categorization summary
        category_counts = {}
        for article in categorized:
            cat = article['category']
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        logger.info("Categorization summary:")
        for cat, count in category_counts.items():
            logger.info(f"  {cat}: {count} articles")
        
        return categorized
    


