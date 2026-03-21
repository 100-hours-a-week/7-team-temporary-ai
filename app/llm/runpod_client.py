import json
import logging
from typing import Any, Optional
from openai import AsyncOpenAI
import logfire
from langfuse import observe
from app.core.config import settings

logger = logging.getLogger(__name__)


class RunPodClient:
    """RunPod Pod vLLM 서버 클라이언트 (OpenAI 호환 API) + Gemini 자동 폴백"""

    def __init__(self):
        # RunPod 클라이언트 (설정이 있을 때만 초기화)
        self._runpod_available = bool(settings.runpod_base_url)
        if self._runpod_available:
            self.client = AsyncOpenAI(
                base_url=settings.runpod_base_url,
                api_key=settings.runpod_api_key or "EMPTY",
            )
            self.model_name = "Qwen2.5-72B-Instruct"

        # Gemini 폴백 클라이언트 (lazy init)
        self._gemini_client = None

    def _get_gemini_fallback(self):
        """Gemini 클라이언트를 lazy 로딩"""
        if self._gemini_client is None:
            from app.llm.gemini_client import get_gemini_client
            self._gemini_client = get_gemini_client()
            logger.info("Gemini fallback client initialized")
        return self._gemini_client

    @observe(as_type="generation")
    async def generate(self, system: str, user: str) -> dict[str, Any]:
        """JSON 응답 반환 — RunPod 실패 시 Gemini로 자동 폴백"""
        # RunPod 시도
        if self._runpod_available:
            try:
                return await self._runpod_generate(system, user)
            except Exception as e:
                logger.warning(f"RunPod generate failed, falling back to Gemini: {e}")

        # Gemini 폴백
        logger.info("Using Gemini fallback for generate()")
        return await self._get_gemini_fallback().generate(system, user)

    @observe(as_type="generation")
    async def generate_text(self, system: str, user: str) -> str:
        """텍스트 응답 반환 — RunPod 실패 시 Gemini로 자동 폴백"""
        # RunPod 시도
        if self._runpod_available:
            try:
                return await self._runpod_generate_text(system, user)
            except Exception as e:
                logger.warning(f"RunPod generate_text failed, falling back to Gemini: {e}")

        # Gemini 폴백
        logger.info("Using Gemini fallback for generate_text()")
        return await self._get_gemini_fallback().generate_text(system, user)

    async def _runpod_generate(self, system: str, user: str) -> dict[str, Any]:
        """RunPod vLLM JSON 생성"""
        with logfire.span("RunPod Generation") as span:
            span.set_attribute("gen_ai.system", system)
            span.set_attribute("gen_ai.request.model", self.model_name)
            span.set_attribute("gen_ai.prompt", user)

            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from vLLM")

            span.set_attribute("gen_ai.completion", content)
            if response.usage:
                span.set_attribute("gen_ai.usage.input_tokens", response.usage.prompt_tokens)
                span.set_attribute("gen_ai.usage.output_tokens", response.usage.completion_tokens)

            try:
                from langfuse import get_client
                get_client().flush()
            except Exception:
                pass

            return json.loads(content)

    async def _runpod_generate_text(self, system: str, user: str) -> str:
        """RunPod vLLM 텍스트 생성"""
        with logfire.span("RunPod Generation (text)") as span:
            span.set_attribute("gen_ai.system", system)
            span.set_attribute("gen_ai.request.model", self.model_name)
            span.set_attribute("gen_ai.prompt", user)

            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.7,
            )

            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from vLLM")

            span.set_attribute("gen_ai.completion", content)
            if response.usage:
                span.set_attribute("gen_ai.usage.input_tokens", response.usage.prompt_tokens)
                span.set_attribute("gen_ai.usage.output_tokens", response.usage.completion_tokens)

            try:
                from langfuse import get_client
                get_client().flush()
            except Exception:
                pass

            return content


# Singleton
_runpod_client: Optional[RunPodClient] = None


def get_runpod_client() -> RunPodClient:
    global _runpod_client
    if _runpod_client is None:
        _runpod_client = RunPodClient()
    return _runpod_client
