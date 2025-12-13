"""
AI service for generating summaries using OpenAI.
"""
from typing import Optional, Dict, Any
from openai import AsyncOpenAI
from config import settings


class AIService:
    """Service for AI-powered summaries."""
    
    def __init__(self):
        self.client: Optional[AsyncOpenAI] = None
        if settings.openai_api_key:
            self.client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    async def generate_page_summary(self, page_data: Dict[str, Any]) -> Optional[str]:
        """
        Generate AI summary for a LinkedIn page.
        
        Args:
            page_data: Dictionary containing page information
            
        Returns:
            AI-generated summary string
        """
        if not self.client:
            return None
        
        try:
            # Prepare context for the AI
            context = f"""
            Company Name: {page_data.get('name', 'N/A')}
            Industry: {page_data.get('industry', 'N/A')}
            Description: {page_data.get('description', 'N/A')}
            Total Followers: {page_data.get('total_followers', 'N/A')}
            Head Count: {page_data.get('head_count', 'N/A')}
            Specialities: {', '.join(page_data.get('specialities', []))}
            Location: {page_data.get('location', 'N/A')}
            Website: {page_data.get('website', 'N/A')}
            """
            
            prompt = f"""
            Based on the following LinkedIn company page information, generate a comprehensive 
            and insightful summary. The summary should highlight:
            1. Company overview and industry positioning
            2. Key strengths and specialities
            3. Market presence (based on follower count and engagement)
            4. Company scale and growth indicators
            
            Company Information:
            {context}
            
            Provide a professional, concise summary (2-3 paragraphs) that would be useful for 
            business intelligence and market research purposes.
            """
            
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a business intelligence analyst specializing in company research and market analysis."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Error generating AI summary: {e}")
            return None


ai_service = AIService()

