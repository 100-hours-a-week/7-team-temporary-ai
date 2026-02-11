import json
import logging
import httpx
from typing import Any, Dict, Optional
import logfire
from langfuse import observe
from app.core.config import settings

logger = logging.getLogger(__name__)

class RunPodClient:
    def __init__(self):
        # API Key check (Optional for initialization, but required for calls)
        self.api_key = settings.vllm_api_key
        if not self.api_key:
            logger.warning("VLLM_API_KEY is not set. RunPod client will fail authentication.")

        # Base URL construction
        if settings.runpod_base_url:
            self.base_url = settings.runpod_base_url.rstrip('/')
        elif settings.runpod_pod_id:
            self.base_url = f"https://{settings.runpod_pod_id}-8000.proxy.runpod.net/v1"
        else:
            logger.warning("Neither RUNPOD_BASE_URL nor RUNPOD_POD_ID is set.")
            self.base_url = ""

        self.model_name = "Llama-3.1-8B-Instruct"

    @observe(as_type="generation")
    async def generate(self, system: str, user: str, max_tokens: int = 2000, stop: Optional[list] = None) -> Dict[str, Any]:
        """
        RunPod vLLM (OpenAI Compatible) API 호출
        """
        if not self.base_url:
             raise ValueError("RunPod configuration missing (Base URL or Pod ID)")

        url = f"{self.base_url}/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # Default stop tokens if not provided
        if stop is None:
            stop = ["<|eot_id|>", "<|end_of_text|>", "```"]

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "max_tokens": max_tokens, 
            "temperature": 0.1,
            "stop": stop
        }

        with logfire.span("RunPod Generation") as span:
            span.set_attribute("gen_ai.system", system)
            span.set_attribute("gen_ai.request.model", self.model_name)
            span.set_attribute("gen_ai.prompt", user)
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                try:
                    response = await client.post(url, headers=headers, json=payload)
                    response.raise_for_status()
                    
                    data = response.json()
                    
                    # Logfire Attributes
                    if "usage" in data:
                        span.set_attribute("gen_ai.usage.input_tokens", data["usage"].get("prompt_tokens", 0))
                        span.set_attribute("gen_ai.usage.output_tokens", data["usage"].get("completion_tokens", 0))
                    
                    content = ""
                    choices = data.get("choices", [])
                    if choices and len(choices) > 0:
                        content = choices[0].get("message", {}).get("content", "")
                        span.set_attribute("gen_ai.completion", content)
                    else:
                        logger.error(f"RunPod Empty Response Choices: {data}")
                        raise ValueError("Empty choices from RunPod")

                    # Langfuse Flush
                    try:
                        from langfuse import get_client
                        get_client().flush()
                    except Exception as flush_error:
                        logger.warning(f"Langfuse flush failed: {flush_error}")

                    cleaned_content = self._clean_json_block(content)
                    return json.loads(cleaned_content)

                except httpx.HTTPStatusError as e:
                    logger.error(f"RunPod HTTP Error: {e.response.status_code} - {e.response.text}")
                    raise e
                except json.JSONDecodeError as e:
                    logger.error(f"RunPod JSON Decode Error: {str(e)}")
                    logger.error(f"Raw Response Content: {response.text}")
                    raise e
                except Exception as e:
                    logger.error(f"RunPod Client Error: {str(e)}")
                    # Try to log response text if available in local scope (might not be if error happened before response assignment)
                    try:
                        if 'response' in locals():
                            logger.error(f"Last Response Content: {response.text}")
                    except:
                        pass
                    raise e

    def _clean_json_block(self, text: str) -> str:
        text = text.strip()
        
        # 1. Try to find markdown code block with json tag
        if "```json" in text:
            import re
            match = re.search(r"```json\s*([\s\S]*?)\s*```", text)
            if match:
                return match.group(1).strip()
        
        # 2. Try to find any markdown code block
        if "```" in text:
            import re
            match = re.search(r"```\s*([\s\S]*?)\s*```", text)
            if match:
                return match.group(1).strip()
                
        # 3. Fallback: Try to find the first '{' and last '}'
        first_brace = text.find("{")
        last_brace = text.rfind("}")
        if first_brace != -1 and last_brace != -1:
            return text[first_brace:last_brace+1]
            
        return text

# Singleton
_runpod_client: Optional[RunPodClient] = None

def get_runpod_client() -> RunPodClient:
    global _runpod_client
    if _runpod_client is None:
        _runpod_client = RunPodClient()
    return _runpod_client
