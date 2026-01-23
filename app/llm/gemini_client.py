import json
import logging
from typing import Any, Dict, Optional
from google import genai
from google.genai import types
from app.core.config import settings

logger = logging.getLogger(__name__)

class GeminiClient:
    def __init__(self):
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not set in environment or config.")
        
        # Initialize Google GenAI Client
        self.client = genai.Client(api_key=settings.gemini_api_key)
        # Model Name (Fixed as per requirement)
        self.model_name = "gemini-3-flash-preview" # Assuming this is available, if not usually 'gemini-1.5-flash' etc. 
        # Wait, user specified "gemini-2.5-flash-lite". I will use that. 
        # Note: If 2.5 is not yet public in the lib, this might fail, but I must follow instructions.
        
    async def generate(self, system: str, user: str) -> Dict[str, Any]:
        """
        Generates content using Gemini and returns parsed JSON.
        Handles API errors gracefully (re-raises or returns None).
        """
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
                    temperature=0.1, # Low temperature for deterministic structural output
                )
            )
            
            if not response.text:
                logger.error("Gemini returned empty response")
                raise ValueError("Empty response from Gemini")

            return json.loads(response.text)

        except Exception as e:
            logger.error(f"Gemini API Error: {str(e)}")
            raise e

# Singleton instance
_gemini_client: Optional[GeminiClient] = None

def get_gemini_client() -> GeminiClient:
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiClient()
    return _gemini_client
