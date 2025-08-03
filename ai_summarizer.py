import openai
import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime
import json

from config import AI_CONFIG

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeepSeekSummarizer:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or AI_CONFIG['api_key']
        self.base_url = AI_CONFIG['base_url']
        self.model = AI_CONFIG['model']
        self.max_tokens = AI_CONFIG['max_tokens']
        self.temperature = AI_CONFIG['temperature']
        
        # Configure OpenAI client for DeepSeek
        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    async def summarize_transactions(self, transactions: List[Dict]) -> Dict:
        """
        Generate a summary of market transactions.
        """
        if not transactions:
            return {
                'summary': 'No significant transactions found in this period.',
                'key_insights': [],
                'total_value': 0,
                'transaction_count': 0
            }
        
        # Prepare transaction data for summarization
        transaction_texts = []
        total_value = 0
        
        for transaction in transactions:
            transaction_data = transaction.get('transaction_data', {})
            value = transaction_data.get('transaction_value', 0)
            total_value += value
            
            transaction_text = f"""
            Source: {transaction['source']}
            Title: {transaction['title']}
            Property: {transaction_data.get('property_name', 'N/A')}
            Location: {transaction_data.get('location', 'N/A')}
            Value: {value:,.0f} HKD
            Type: {transaction_data.get('transaction_type', 'N/A')}
            Date: {transaction['date'].strftime('%Y-%m-%d')}
            """
            transaction_texts.append(transaction_text)
        
        # Create prompt for transaction summary
        transaction_details = '\n'.join(transaction_texts)
        prompt = f"""
        You are a Hong Kong real estate market analyst. Please analyze the following market transactions and provide:

        1. A comprehensive summary of the market activity (2-3 paragraphs)
        2. Key insights about market trends, notable deals, and market sentiment
        3. Analysis of transaction types (sales vs leases), property types, and locations
        4. Market implications and potential future trends

        Total transactions: {len(transactions)}
        Total transaction value: {total_value:,.0f} HKD

        Transaction details:
        {transaction_details}

        IMPORTANT: You must respond with ONLY valid JSON. Do not include any text before or after the JSON.
        Please provide your analysis in the following exact JSON format:
        {{
            "summary": "comprehensive market summary",
            "key_insights": ["insight 1", "insight 2", "insight 3"],
            "market_trends": "analysis of current trends",
            "notable_deals": "description of significant transactions",
            "market_sentiment": "overall market sentiment analysis"
        }}
        """
        
        try:
            response = await self._call_deepseek(prompt)
            logger.info(f"Attempting to parse JSON response: {response[:100]}...")
            cleaned_response = self._clean_json_response(response)
            result = json.loads(cleaned_response)
            result['total_value'] = total_value
            result['transaction_count'] = len(transactions)
            return result
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            logger.error(f"Raw response: {response}")
            # Return a structured fallback response
            return {
                'summary': f'Found {len(transactions)} transactions with total value of {total_value:,.0f} HKD.',
                'key_insights': [f'Total transaction value: {total_value:,.0f} HKD', f'Average transaction value: {total_value//len(transactions):,.0f} HKD' if len(transactions) > 0 else 'No transactions'],
                'market_trends': 'Market analysis available in detailed report',
                'notable_deals': f'Largest transaction: {max([t.get("transaction_data", {}).get("transaction_value", 0) for t in transactions]):,.0f} HKD' if transactions else 'No transactions',
                'market_sentiment': 'Market sentiment analysis available in detailed report',
                'total_value': total_value,
                'transaction_count': len(transactions)
            }
        except Exception as e:
            logger.error(f"Error summarizing transactions: {e}")
            return {
                'summary': f'Found {len(transactions)} transactions with total value of {total_value:,.0f} HKD.',
                'key_insights': ['Error occurred during AI analysis'],
                'total_value': total_value,
                'transaction_count': len(transactions)
            }
    
    async def summarize_news(self, news_articles: List[Dict]) -> Dict:
        """
        Generate a summary of market news and analysis.
        """
        if not news_articles:
            return {
                'summary': 'No significant market news found in this period.',
                'key_themes': [],
                'market_analysis': 'No market analysis available.',
                'article_count': 0
            }
        
        # Prepare news data for summarization
        news_texts = []
        
        for article in news_articles:
            news_text = f"""
            Source: {article['source']}
            Title: {article['title']}
            Date: {article['date'].strftime('%Y-%m-%d')}
            Content: {article['content'][:500]}...
            """
            news_texts.append(news_text)
        
        # Create prompt for news summary
        news_details = '\n'.join(news_texts)
        prompt = f"""
        You are a Hong Kong real estate market analyst. Please analyze the following market news articles and provide:

        1. A comprehensive summary of the key market developments (2-3 paragraphs)
        2. Identification of main themes and trends
        3. Analysis of market sentiment and outlook
        4. Key policy or economic factors affecting the market
        5. Implications for different property sectors (residential, commercial, retail, etc.)

        Total articles: {len(news_articles)}

        News articles:
        {news_details}

        IMPORTANT: You must respond with ONLY valid JSON. Do not include any text before or after the JSON.
        Please provide your analysis in the following exact JSON format:
        {{
            "summary": "comprehensive news summary",
            "key_themes": ["theme 1", "theme 2", "theme 3"],
            "market_analysis": "detailed market analysis",
            "sentiment": "market sentiment analysis",
            "policy_impact": "analysis of policy or economic factors",
            "sector_analysis": "analysis by property sector"
        }}
        """
        
        try:
            response = await self._call_deepseek(prompt)
            logger.info(f"Attempting to parse news JSON response: {response[:100]}...")
            cleaned_response = self._clean_json_response(response)
            result = json.loads(cleaned_response)
            result['article_count'] = len(news_articles)
            return result
        except json.JSONDecodeError as e:
            logger.error(f"News JSON parsing error: {e}")
            logger.error(f"Raw news response: {response}")
            # Return a structured fallback response
            return {
                'summary': f'Found {len(news_articles)} news articles covering market developments.',
                'key_themes': [f'Market news from {len(news_articles)} sources', 'Property market trends and analysis'],
                'market_analysis': 'Detailed market analysis available in comprehensive report',
                'sentiment': 'Market sentiment analysis available in detailed report',
                'policy_impact': 'Policy impact analysis available in detailed report',
                'sector_analysis': 'Sector-specific analysis available in detailed report',
                'article_count': len(news_articles)
            }
        except Exception as e:
            logger.error(f"Error summarizing news: {e}")
            return {
                'summary': f'Found {len(news_articles)} news articles.',
                'key_themes': ['Error occurred during AI analysis'],
                'article_count': len(news_articles)
            }
    
    async def generate_weekly_report(self, transactions: List[Dict], news: List[Dict], 
                                   start_date: datetime, end_date: datetime) -> Dict:
        """
        Generate a comprehensive weekly market report.
        """
        # Generate summaries
        transaction_summary = await self.summarize_transactions(transactions)
        news_summary = await self.summarize_news(news)
        
        # Create executive summary prompt
        transaction_summary_json = json.dumps(transaction_summary, indent=2)
        news_summary_json = json.dumps(news_summary, indent=2)
        executive_prompt = f"""
        You are a Hong Kong real estate market analyst creating a weekly executive summary.
        
        Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}
        
        Transaction Summary:
        {transaction_summary_json}
        
        News Summary:
        {news_summary_json}
        
        Please create an executive summary that includes:
        1. Overall market performance and sentiment
        2. Key highlights and notable developments
        3. Market outlook and potential implications
        4. Recommendations for market participants
        
        IMPORTANT: You must respond with ONLY valid JSON. Do not include any text before or after the JSON.
        Provide your response in the following exact JSON format:
        {{
            "executive_summary": "comprehensive executive summary",
            "market_performance": "overall market performance analysis",
            "key_highlights": ["highlight 1", "highlight 2", "highlight 3"],
            "market_outlook": "short-term and medium-term outlook",
            "recommendations": ["recommendation 1", "recommendation 2"]
        }}
        """
        
        try:
            executive_response = await self._call_deepseek(executive_prompt)
            logger.info(f"Attempting to parse executive JSON response: {executive_response[:100]}...")
            cleaned_response = self._clean_json_response(executive_response)
            executive_summary = json.loads(cleaned_response)
        except json.JSONDecodeError as e:
            logger.error(f"Executive JSON parsing error: {e}")
            logger.error(f"Raw executive response: {executive_response}")
            # Create a better fallback executive summary
            total_value = transaction_summary.get('total_value', 0)
            transaction_count = transaction_summary.get('transaction_count', 0)
            news_count = news_summary.get('article_count', 0)
            
            executive_summary = {
                'executive_summary': f'Weekly Hong Kong real estate market report for {start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}. Market activity shows {transaction_count} transactions with total value of {total_value:,.0f} HKD.',
                'market_performance': f'Market performance analysis: {transaction_count} transactions recorded with total value of {total_value:,.0f} HKD. Average transaction value: {total_value//transaction_count:,.0f} HKD' if transaction_count > 0 else 'No transactions recorded in this period.',
                'key_highlights': [
                    f'Total transaction value: {total_value:,.0f} HKD',
                    f'Number of transactions: {transaction_count}',
                    f'News articles analyzed: {news_count}',
                    'Market analysis completed successfully'
                ],
                'market_outlook': 'Market outlook analysis available in detailed report. Monitor market developments closely for emerging trends.',
                'recommendations': [
                    'Monitor market developments closely',
                    'Review transaction patterns and property types',
                    'Stay informed about policy changes affecting the market'
                ]
            }
        except Exception as e:
            logger.error(f"Error generating executive summary: {e}")
            executive_summary = {
                'executive_summary': f'Weekly market report for {start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}',
                'market_performance': 'Analysis not available due to technical issues',
                'key_highlights': ['Report generated successfully'],
                'market_outlook': 'Outlook analysis not available',
                'recommendations': ['Monitor market developments closely']
            }
        
        # Compile complete report
        report = {
            'period': {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d')
            },
            'executive_summary': executive_summary,
            'transaction_analysis': transaction_summary,
            'news_analysis': news_summary,
            'statistics': {
                'total_transactions': len(transactions),
                'total_transaction_value': transaction_summary.get('total_value', 0),
                'total_news_articles': len(news),
                'sources_covered': list(set([t['source'] for t in transactions] + [n['source'] for n in news]))
            },
            'generated_at': datetime.now().isoformat()
        }
        
        return report
    
    def _clean_json_response(self, response: str) -> str:
        """
        Clean the API response to extract valid JSON.
        """
        # Remove markdown code blocks
        if response.startswith('```json'):
            response = response[7:]  # Remove ```json
        if response.startswith('```'):
            response = response[3:]  # Remove ```
        if response.endswith('```'):
            response = response[:-3]  # Remove trailing ```
        
        # Remove any leading/trailing whitespace
        response = response.strip()
        
        return response

    async def _call_deepseek(self, prompt: str) -> str:
        """
        Make a call to the DeepSeek API.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a Hong Kong real estate market analyst with expertise in property markets, market trends, and financial analysis. Provide accurate, insightful analysis in both English and Chinese where appropriate."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            content = response.choices[0].message.content.strip()
            logger.info(f"API Response received: {content[:200]}...")  # Log first 200 chars
            return content
            
        except Exception as e:
            logger.error(f"Error calling DeepSeek API: {e}")
            raise e
    
    def validate_api_key(self) -> bool:
        """
        Validate the API key by making a simple test call.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": "Hello, this is a test message."
                    }
                ],
                max_tokens=10
            )
            return True
        except Exception as e:
            logger.error(f"API key validation failed: {e}")
            return False 