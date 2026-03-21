# RunPod에서 Hugging Face 모델 돌리기 - 기본 가이드 (v1.0)

현재 프로젝트는 `app/llm/gemini_client.py`에서 Gemini API(`google-genai`)를 사용하여 LLM 추론을 수행하고 있다.
이 문서는 Gemini API 대신 **RunPod + vLLM + Hugging Face 모델**로 전환하기 위한 기본 가이드이다.

---

## 1. 전체 아키텍처

```
[FastAPI 서버 (로컬/Docker)]
        |
        | OpenAI 호환 API (HTTP)
        v
[RunPod Pod - vLLM 서버]
        |
        | 모델 로드
        v
[Hugging Face 모델 (예: Llama, Qwen, Mistral 등)]
```

- **vLLM**: Hugging Face 모델을 OpenAI 호환 API로 서빙하는 고성능 추론 엔진
- **RunPod**: GPU 인스턴스 제공 (RTX 4090, A100 등)
- **클라이언트**: `openai` Python SDK로 vLLM에 요청 (Gemini SDK 대체)

---

## 2. RunPod Pod 설정

> 기존 `docs/runpod_setup_guide.md` 참고. 여기서는 핵심만 요약.

### 2-1. Pod 생성

1. RunPod Console > Pods > Deploy
2. GPU 선택 (모델 크기에 따라):
   - **7~8B 모델**: RTX 4090 (24GB VRAM) 1장
   - **13~14B 모델**: A100 40GB 또는 RTX 4090 x2
   - **70B 모델**: A100 80GB x2 이상
3. Template: `vLLM Latest` (vllm/vllm-openai, 안정 버전 권장)
4. Environment Variables:
   - `HF_TOKEN`: Hugging Face 토큰 (gated 모델 다운로드용)
   - `VLLM_API_KEY`: vLLM 접근 비밀번호

### 2-2. 모델 다운로드

```bash
# Pod 터미널 접속 후
cd /workspace
huggingface-cli login --token $HF_TOKEN

# 예시: Qwen2.5-7B-Instruct
huggingface-cli download Qwen/Qwen2.5-7B-Instruct \
  --local-dir /workspace/model/Qwen2.5-7B-Instruct
```

### 2-3. vLLM 서버 실행

```bash
python3 -m vllm.entrypoints.openai.api_server \
  --model /workspace/model/Qwen2.5-7B-Instruct \
  --served-model-name Qwen2.5-7B-Instruct \
  --port 8000 \
  --api-key $VLLM_API_KEY \
  --gpu-memory-utilization 0.95 \
  --max-model-len 8192
```

Container Start Command에 위 옵션을 넣으면 Pod 시작 시 자동 실행된다.

---

## 3. 클라이언트 코드 변경

### 3-1. 필요 패키지

```bash
pip install openai>=1.0.0
```

### 3-2. 환경 변수 추가 (.env)

```ini
# RunPod vLLM 접속 정보
RUNPOD_BASE_URL=https://{POD_ID}-8000.proxy.runpod.net/v1
VLLM_API_KEY=your_vllm_api_key
VLLM_MODEL_NAME=Qwen2.5-7B-Instruct
```

### 3-3. config.py에 설정 추가

```python
# app/core/config.py 에 추가
runpod_base_url: str = ""
vllm_api_key: str = ""
vllm_model_name: str = "Qwen2.5-7B-Instruct"
```

### 3-4. RunPod LLM 클라이언트 구현

현재 `app/llm/gemini_client.py`와 동일한 인터페이스로 RunPod 클라이언트를 만든다.

```python
# app/llm/runpod_client.py

import json
import logging
from typing import Any, Optional
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)


class RunPodClient:
    """RunPod vLLM 서버와 통신하는 클라이언트 (OpenAI 호환 API 사용)"""

    def __init__(self):
        if not settings.runpod_base_url:
            raise ValueError("RUNPOD_BASE_URL이 설정되지 않았습니다.")

        self.client = AsyncOpenAI(
            base_url=settings.runpod_base_url,
            api_key=settings.vllm_api_key,
        )
        self.model_name = settings.vllm_model_name

    async def generate(self, system: str, user: str) -> dict[str, Any]:
        """JSON 응답 반환 (GeminiClient.generate와 동일한 인터페이스)"""
        try:
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

            return json.loads(content)

        except Exception as e:
            logger.error(f"RunPod vLLM API Error: {str(e)}")
            raise

    async def generate_text(self, system: str, user: str) -> str:
        """텍스트 응답 반환 (GeminiClient.generate_text와 동일한 인터페이스)"""
        try:
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

            return content

        except Exception as e:
            logger.error(f"RunPod vLLM API Error (generate_text): {str(e)}")
            raise


# Singleton
_runpod_client: Optional[RunPodClient] = None


def get_runpod_client() -> RunPodClient:
    global _runpod_client
    if _runpod_client is None:
        _runpod_client = RunPodClient()
    return _runpod_client
```

### 3-5. 기존 코드에서 전환

Gemini를 사용하는 곳에서 클라이언트만 교체하면 된다.

```python
# Before (Gemini)
from app.llm.gemini_client import get_gemini_client
client = get_gemini_client()
result = await client.generate(system_prompt, user_prompt)

# After (RunPod)
from app.llm.runpod_client import get_runpod_client
client = get_runpod_client()
result = await client.generate(system_prompt, user_prompt)
```

---

## 4. Hugging Face 모델 선택 가이드

| 모델 | 크기 | 최소 VRAM | 특징 |
|------|------|-----------|------|
| Qwen2.5-7B-Instruct | 7B | 16GB | 한국어 성능 우수, JSON 출력 안정적 |
| Llama-3.1-8B-Instruct | 8B | 16GB | 범용 성능 좋음, Meta 승인 필요 |
| Mistral-7B-Instruct-v0.3 | 7B | 16GB | 빠른 추론, 유럽어 강점 |
| Qwen2.5-14B-Instruct | 14B | 28GB | 7B 대비 품질 향상 |
| Llama-3.1-70B-Instruct | 70B | 140GB+ | 최고 품질, 다중 GPU 필요 |

> **권장**: 한국어 서비스 기준으로 **Qwen2.5-7B-Instruct** 또는 **Qwen2.5-14B-Instruct**가 비용 대비 성능이 좋다.

---

## 5. 주의사항

### JSON 출력 안정성
- Gemini는 `response_mime_type="application/json"`으로 안정적인 JSON을 반환한다.
- vLLM의 `response_format={"type": "json_object"}`도 지원하지만, 모델에 따라 JSON 형식이 깨질 수 있다.
- 시스템 프롬프트에 JSON 형식을 명확히 지시하고, 파싱 실패 시 재시도 로직을 추가하는 것을 권장한다.

### vLLM guided decoding (JSON Schema 강제)
vLLM은 JSON Schema를 기반으로 출력 형식을 강제할 수 있다:
```python
response_format={
    "type": "json_object",
    "schema": {
        "type": "object",
        "properties": {
            "answer": {"type": "string"},
            "confidence": {"type": "number"}
        },
        "required": ["answer", "confidence"]
    }
}
```

### 비용 비교
| 항목 | Gemini API | RunPod (RTX 4090) |
|------|-----------|-------------------|
| 과금 방식 | 토큰당 과금 | 시간당 과금 (~$0.69/hr) |
| 콜드 스타트 | 없음 | 모델 로딩 1~3분 |
| 확장성 | 자동 | 수동 (Pod 추가) |
| 커스터마이징 | 제한적 | Fine-tuning 가능 |

### 하이브리드 전략
기존 `docs/runpod_strategy.md`에 정의된 RunPod-Gemini 하이브리드 라우팅 전략을 활용하면,
RunPod 장애 시 Gemini로 자동 폴백하는 안정적인 구조를 만들 수 있다.

---

## 6. RunPod Pod으로 Qwen2.5-72B-Instruct 구동하기 (실제 적용)

> Serverless는 초기화 이슈로 Pod 방식으로 전환했다.
> Pod은 상시 구동되며, OpenAI 호환 API를 직접 호출할 수 있어 코드가 심플하고 디버깅이 쉽다.

### 6-1. 모델 스펙

| 항목 | 값 |
|------|-----|
| 모델 | Qwen/Qwen2.5-72B-Instruct |
| 아키텍처 | Dense Transformer |
| 파라미터 | 72B |
| 정밀도 | BF16 |
| 필요 VRAM | ~144GB |
| Function Calling | 지원 (`hermes` tool call parser) |

> Gemini 2.5 Flash급 성능, 한국어 우수, MCP function calling 지원.

### 6-2. Pod 생성 설정

1. **RunPod Console** > **Pods** > **Deploy**
2. **GPU**: A40 48GB x3 (총 144GB VRAM)
3. **Template**: RunPod vLLM
4. **Disk 설정**:
   - Container Disk: **20GB** (런타임 환경)
   - Volume Disk: **150GB** (모델 가중치 저장, Pod 재시작 시 재다운로드 방지)
5. **Environment Variables**:
   ```
   HF_TOKEN=hf_your_token_here
   ```
6. **Container Start Command**:
   ```bash
   python3 -m vllm.entrypoints.openai.api_server --model Qwen/Qwen2.5-72B-Instruct --served-model-name Qwen2.5-72B-Instruct --port 8000 --tensor-parallel-size 3 --gpu-memory-utilization 0.95 --max-model-len 4096 --dtype bfloat16 --enable-auto-tool-choice --tool-call-parser hermes
   ```

> **A40 x3 = 144GB**로 VRAM이 빠듯하므로 `--max-model-len 4096`으로 시작한다. 안정화 후 여유가 있으면 `8192`로 올릴 수 있다.
> A40은 NVLink 없이 PCIe 연결이라 A100/H100 대비 추론 속도가 다소 느릴 수 있다.

### 6-3. Pod API 접속 정보

Pod이 시작되면 RunPod Console에서 Pod ID를 확인할 수 있다. vLLM 서버는 OpenAI 호환 API를 제공한다.

```
Base URL: https://{POD_ID}-8000.proxy.runpod.net/v1
```

#### curl 테스트

```bash
curl -X POST "https://{POD_ID}-8000.proxy.runpod.net/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen2.5-72B-Instruct",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant. Answer in Korean."},
      {"role": "user", "content": "한국의 수도는 어디인가요?"}
    ],
    "max_tokens": 256,
    "temperature": 0.7
  }'
```

### 6-4. 환경변수 추가 (.env)

```ini
# RunPod Pod vLLM 접속 정보
RUNPOD_BASE_URL=https://{POD_ID}-8000.proxy.runpod.net/v1
RUNPOD_API_KEY=your_runpod_api_key
```

### 6-5. config.py 설정

```python
# app/core/config.py 에 추가
runpod_api_key: str | None = None
runpod_endpoint_id: str | None = None  # Serverless용 (현재 미사용)
runpod_base_url: str | None = None     # Pod용
```

### 6-6. Python 클라이언트 (Pod용 — OpenAI 호환)

`app/llm/runpod_client.py`에 구현되어 있다. GeminiClient와 동일한 인터페이스 (`generate`, `generate_text`)를 제공한다.

```python
from app.llm.runpod_client import get_runpod_client
client = get_runpod_client()

# JSON 응답
result = await client.generate(system_prompt, user_prompt)

# 텍스트 응답
text = await client.generate_text(system_prompt, user_prompt)
```

### 6-7. Function Calling (MCP 연동)

Container Start Command에 `--enable-auto-tool-choice --tool-call-parser hermes` 옵션이 포함되어 있어, OpenAI 호환 function calling을 바로 사용할 수 있다.

```bash
curl -X POST "https://{POD_ID}-8000.proxy.runpod.net/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen2.5-72B-Instruct",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant with access to tools."},
      {"role": "user", "content": "서울의 현재 날씨를 알려줘"}
    ],
    "tools": [
      {
        "type": "function",
        "function": {
          "name": "get_weather",
          "description": "Get current weather for a location",
          "parameters": {
            "type": "object",
            "properties": {
              "location": {"type": "string", "description": "City name"}
            },
            "required": ["location"]
          }
        }
      }
    ],
    "tool_choice": "auto",
    "max_tokens": 512
  }'
```

> MCP 서버와 연동 시, MCP 도구 목록을 위 `tools` 형식으로 변환하여 전달하면 된다.

### 6-8. 비용 예상 (상시 구동)

| GPU 구성 | 시간당 비용 | 일 비용 | 월 비용 (대략) |
|----------|-----------|---------|---------------|
| A40 48GB x3 | ~$1.11/hr | ~$26.64/day | ~$800/mo |

> Pod은 상시 과금된다. 사용하지 않을 때는 Pod을 Stop하여 비용을 절약할 수 있다 (Volume Disk은 유지됨).

---

## 7. 빠른 시작 체크리스트

### Pod (Qwen2.5-72B-Instruct) — 현재 적용

- [ ] RunPod 계정 생성 및 API Key 발급
- [ ] Hugging Face 토큰 발급
- [ ] RunPod Pod 생성 (A40 48GB x3, vLLM 템플릿)
- [ ] Container Disk 20GB, Volume Disk 150GB 설정
- [ ] Container Start Command 입력 (vLLM 서버 + tool call parser)
- [ ] Environment Variables에 `HF_TOKEN` 설정
- [ ] Pod 시작 후 모델 로딩 완료 대기 (로그 확인)
- [ ] curl로 OpenAI 호환 API 테스트
- [ ] `.env`에 `RUNPOD_BASE_URL`, `RUNPOD_API_KEY` 추가
- [ ] `app/llm/runpod_client.py` 생성 (완료)
- [ ] `app/core/config.py`에 RunPod 설정 추가 (완료)
- [ ] 기존 Gemini 호출 부분을 RunPod 클라이언트로 교체
- [ ] 통합 테스트
