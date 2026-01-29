import json
import logging
from typing import Any, Dict, Optional
from google import genai
from google.genai import types
import logfire
from langsmith import traceable
from app.core.config import settings

logger = logging.getLogger(__name__)

class GeminiClient:
    def __init__(self):
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY가 등록되지 않았습니다.")
        
        # Gemini Client 초기화
        self.client = genai.Client(api_key=settings.gemini_api_key)
        # 사용할 Gemini 모델 지정
        self.model_name = "gemini-2.5-flash-lite"
        
    @traceable(run_type="llm", name="Gemini Generation")
    async def generate(self, system: str, user: str) -> Dict[str, Any]:
        """
        Gemini API를 호출하여 JSON 응답을 반환
        """
        with logfire.span("Gemini Generation") as span:
            # Set Request Attributes (OpenTelemetry GenAI Semantic Conventions)
            span.set_attribute("gen_ai.system", system)
            span.set_attribute("gen_ai.request.model", self.model_name)
            span.set_attribute("gen_ai.prompt", user)
            
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=[
                        types.Content(
                            role="user",
                            parts=[types.Part.from_text(text=user)]
                        )
                    ],
                    config=types.GenerateContentConfig(
                        system_instruction=system,
                        response_mime_type="application/json",
                        temperature=0.1,
                    )
                )
                
                # Set Response & Usage Attributes
                if response.usage_metadata:
                    span.set_attribute("gen_ai.usage.input_tokens", response.usage_metadata.prompt_token_count)
                    span.set_attribute("gen_ai.usage.output_tokens", response.usage_metadata.candidates_token_count)
                
                if response.text:
                    span.set_attribute("gen_ai.completion", response.text)
                else:
                    logger.error("Gemini returned empty response")
                    raise ValueError("Empty response from Gemini")
    
                return json.loads(response.text)
    
            except Exception as e:
                logger.error(f"Gemini API Error: {str(e)}")
                # Span will automatically capture the exception
                raise e

# Singleton instance
_gemini_client: Optional[GeminiClient] = None

def get_gemini_client() -> GeminiClient:
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiClient()
    return _gemini_client
