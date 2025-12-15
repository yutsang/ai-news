#!/usr/bin/env python3
"""
AI Categorizer using DeepSeek API
Categorizes news articles into: Transactions, Real Estate News, or New Property
"""

import yaml
import logging
from typing import List, Dict
from openai import OpenAI
from tqdm import tqdm
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DeepSeekCategorizer:
    """Use DeepSeek AI to categorize news articles"""
    
    def __init__(self, config_path: str = "config.yml"):
        """
        Initialize the categorizer with DeepSeek API
        
        Args:
            config_path: Path to the YAML configuration file
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        deepseek_config = self.config['deepseek']
        
        # Initialize OpenAI client with DeepSeek API
        self.client = OpenAI(
            api_key=deepseek_config['api_key'],
            base_url=deepseek_config['api_base']
        )
        
        self.model = deepseek_config['model']
        self.temperature = deepseek_config['temperature']
        self.max_tokens = deepseek_config['max_tokens']
        
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
        
        # Prepare the prompt
        prompt = f"""請將以下香港地產新聞分類到以下四個類別之一：

類別1: transactions (交易/成交) - 關於房地產買賣交易、租賃、成交記錄、價格交易等
類別2: news (地產新聞) - 一般房地產市場新聞、政策、趨勢、分析、估值相關等
   **重要**: news類別必須是關於市場整體趨勢、政策影響、估值分析等，不能是單一物業的成交詳情
類別3: new_property (新盤) - 關於新樓盤、新項目發售、新盤消息等
類別4: exclude (排除) - 以下類型的新聞應分類為exclude：
   - 單一物業交易詳情 (只講某個物業的成交，沒有市場分析或趨勢討論)
   - 物業質素問題、投訴、驗收問題 (如樓花質素差誤、手工粗糙、空鼓、用料問題等，除非涉及估值影響)
   - 物業管理相關 (管理費、業主會、法團等，除非涉及估值)
   - 專欄作家文章
   - 與物業估值、市場趨勢、價格分析無關的一般新聞
   - 非香港地產新聞

**重要規則**:
1. 只有與物業估值、市場趨勢、價格分析直接相關的新聞才應分類為news
2. 如果新聞主要是關於單一物業的成交詳情（如"某物業以X價格成交"），沒有市場分析，應分類為transactions或exclude，不是news
3. 如果新聞主要是關於質素問題、投訴、管理費等，且不涉及估值，應分類為exclude

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
    
    def extract_details(self, article: Dict) -> Dict:
        """
        Extract detailed information from article content using AI
        
        Args:
            article: Article dictionary with full_content
            
        Returns:
            Dictionary with extracted details
        """
        category = article.get('category', 'news')
        title = article.get('title', '')
        content = article.get('full_content', '')
        
        # Limit content length to avoid token limits
        if len(content) > 3000:
            content = content[:3000] + "..."
        
        # Different prompts based on category
        if category == 'transactions':
            prompt = f"""請從以下香港地產交易新聞中提取關鍵信息：

標題: {title}

內容: {content}

請提取以下信息（如果有的話）：
1. 物業名稱/地址
2. 交易類型（買賣/租賃）
3. 成交價格或租金
4. 物業類型（住宅/商舖/寫字樓等）
5. 面積
6. 呎價
7. 買家/賣家信息（如果有）
8. 其他重要細節

請以結構化的方式回答，格式如下：
物業: [物業名稱]
類型: [交易類型]
價格: [價格]
物業類別: [類別]
面積: [面積]
呎價: [呎價]
詳情: [其他重要信息]"""

        elif category == 'new_property':
            prompt = f"""請從以下香港新樓盤新聞中提取關鍵信息：

標題: {title}

內容: {content}

請提取以下信息（如果有的話）：
1. 樓盤名稱
2. 位置/地區
3. 發展商
4. 單位數量
5. 戶型（1房/2房/3房等）
6. 價格範圍
7. 開售日期/階段
8. 其他重要細節

請以結構化的方式回答，格式如下：
樓盤: [名稱]
位置: [地區]
發展商: [公司]
單位數: [數量]
戶型: [戶型]
價格: [價格範圍]
詳情: [其他重要信息]"""

        else:  # news
            prompt = f"""請總結以下香港地產新聞的要點：

標題: {title}

內容: {content}

請提供：
1. 新聞摘要（2-3句）
2. 主要涉及的地區/物業類型
3. 關鍵數據或趨勢
4. 影響或意義

請以結構化的方式回答。"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一個香港地產新聞分析專家。請準確提取和總結關鍵信息。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            extracted_info = response.choices[0].message.content.strip()
            
            return {
                'extracted_info': extracted_info,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error extracting details: {e}")
            return {
                'extracted_info': f"提取失敗: {str(e)}",
                'success': False
            }
    
    def process_articles_with_details(self, articles: List[Dict]) -> List[Dict]:
        """
        Process articles to extract detailed information
        
        Args:
            articles: List of categorized articles
            
        Returns:
            List of articles with extracted details
        """
        logger.info(f"Extracting details from {len(articles)} articles...")
        
        for article in tqdm(articles, desc="Extracting details", unit="article"):
            details = self.extract_details(article)
            article['extracted_info'] = details['extracted_info']
            article['extraction_success'] = details['success']
            
            # Small delay to avoid rate limiting
            time.sleep(0.5)
        
        return articles


if __name__ == "__main__":
    # Test the categorizer
    categorizer = DeepSeekCategorizer()
    
    # Test articles
    test_articles = [
        {
            'title': '御林皇府洋房3千萬沽 設計師20年蝕11%',
            'description': '二手豪宅市場交投回升，不少名人趁旺出售手上豪宅單位。',
            'tags': ['成交', '蝕讓', '走勢']
        },
        {
            'title': '地署擬收牛潭尾66公頃地 建住宅大學城',
            'description': '政府加速北都發展，地政總署刊憲收回牛潭尾新區內66公頃的私人土地',
            'tags': ['政策', '走勢', '改用']
        },
        {
            'title': '栢景峰今開售入場價427萬',
            'description': '發展商推盤步伐重新加快，本周末約有250個單位發售',
            'tags': ['新盤', '招標', '走勢']
        }
    ]
    
    categorized = categorizer.categorize_batch(test_articles)
    
    for article in categorized:
        print(f"\nTitle: {article['title']}")
        print(f"Category: {article['category']}")


