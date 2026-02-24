# RunPod 챗봇 환경 구축 가이드

이 문서는 챗봇 기능 구현을 위해 **RunPod(서버)**와 **로컬 개발 환경(클라이언트)**에서 수행해야 할 작업들을 단계별로 안내합니다.

---

## 1. RunPod 환경 설정 (Server-Side)

RunPod에서 LLM을 구동하기 위한 서버 설정입니다. **vLLM 공식 템플릿**을 사용하여 배포 및 관리를 단순화합니다.

### 1-1. Pod 생성 및 템플릿 선택
1. **RunPod Console > Pods**로 이동합니다.
2. **Deploy** 버튼을 클릭하고 GPU(예: RTX 4090)를 선택합니다.
3. **Select Template**에서 `vLLM Latest` (**vllm/vllm-openai:v0.6.3.post1**)를 선택합니다.
    - **중요**: `latest` 태그는 CUDA 12.9 이상을 요구하여 실행되지 않을 수 있습니다. `v0.6.3.post1` 등 호환성 좋은 버전을 권장합니다.
4. **Customize Deployment**를 클릭하여 다음 설정을 확인합니다:
    - **Container Start Command**를 빈칸으로 비웁니다.
        - 이후 LLM 모델을 설치한 후, 아래의 **Container Start Command**를 입력하세요
    - **Container Disk**: 50 GB 이상 (넉넉하게 잡으세요)
    - **Volume Disk**: 50 GB 이상 (모델 파일 저장용, 필수)
    - **Environment Variables**:
        - `HF_TOKEN`: `hf_...` (HuggingFace 읽기 전용 토큰, 모델 다운로드용)
        - `VLLM_API_KEY`: `my_secret_password...` (vLLM 접속용 비밀번호, API Key)

### 1-2. 모델 다운로드 (최초 1회)
Pod가 실행(Running)되면 터미널에 접속하여 모델을 영구 볼륨(`/workspace`)에 다운로드합니다.

**방법 A: Web Terminal (간편)**
1. **Connect > Start Web Terminal**로 터미널 접속

**방법 B: SSH 접속 (VS Code 등 로컬 터미널, 권장)**
1. **Connect** 버튼 클릭 > **SSH over exposed TCP** 탭 선택
2. SSH 명령어 복사 (예: `ssh root@123.456.78.9 -p 12345`)
3. 로컬 터미널에 붙여넣고 실행 (`Are you sure...?` -> `yes` 입력)

**공통: 모델 다운로드 진행**
2. 모델 다운로드 디렉토리 생성 및 다운로드
   > **참고**: `RunPod vLLM` 공식 템플릿에는 `huggingface-cli`가 이미 설치되어 있습니다. (별도 설치 불필요)

```bash
# 영구 볼륨으로 이동
cd /workspace
# huggingface-cli 로그인 (Meta Llama 모델은 승인된 계정 토큰 필수!)
huggingface-cli login --token $HF_TOKEN
# 모델 다운로드
huggingface-cli download meta-llama/Llama-3.1-8B-Instruct --local-dir /workspace/model/Llama-3.1-8B-Instruct
```

### 1-3. (모델 다운로드 완료 후) 자동 실행 설정

모델 다운로드와 테스트가 모두 끝났다면, 매번 수동으로 실행할 필요 없이 **Pod가 켜질 때 자동으로 실행**되도록 설정을 변경할 수 있습니다.

1. RunPod 콘솔 -> **Edit Pod**
2. **Container Start Command**를 아래와 같이 변경합니다.
```bash
--model /workspace/model/Llama-3.1-8B-Instruct --served-model-name Llama-3.1-8B-Instruct --port 8000 --api-key $VLLM_API_KEY --gpu-memory-utilization 0.95 --max-model-len 8192
```
3. **Update Pod**를 누르면 Pod가 재시작되며 자동으로 메인 모델이 로드됩니다.

### 1-4. vLLM 서버 실행 테스트
모델이 잘 받아졌는지 확인하고 서버를 수동으로 띄워봅니다.

```bash
# OpenAI 호환 서버 실행 (Llama 3.1 8B 기준)
python3 -m vllm.entrypoints.openai.api_server \
  --model /workspace/model/Llama-3.1-8B-Instruct \
  --served-model-name Llama-3.1-8B-Instruct \
  --port 8000 \
  --api-key $VLLM_API_KEY
```
- **참고**: `Llama-3.1`은 표준 아키텍처이므로 `--trust-remote-code` 옵션이 필요 없습니다. (Qwen, Phi 등 일부 커스텀 모델에서만 필요)
- **API Key**: `--api-key $VLLM_API_KEY`와 같이 환경변수를 참조하게 하면, 키가 노출되지 않고 안전하게 설정됩니다.
- 서버가 정상적으로 뜨면 `Uvicorn running on http://0.0.0.0:8000` 메시지가 보입니다.
-   > **중요**: 정상적으로 실행되면 `INFO: ... Application startup complete.` 같은 로그가 뜨고 대기 상태가 됩니다.

### 1-5. (선택사항) 모델 구동 확인 (터미널 테스트)
서버가 정상적으로 떴는지 확인하려면, RunPod 터미널에서 `curl` 명령어로 간단한 요청을 보내보세요.
```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $VLLM_API_KEY" \
  -d '{
    "model": "Llama-3.1-8B-Instruct",
    "messages": [
      {"role": "user", "content": "Hello! Are you working?"}
    ],
    "max_tokens": 400
  }'
```
응답으로 JSON 형태의 답변(`"content": "Yes, I am working..."`)이 오면 성공입니다!

---

## 2. 로컬 개발 환경 설정 (Client-Side)

FastAPI 서버가 RunPod의 vLLM과 통신하기 위한 준비입니다.

### 2-1. 라이브러리 추가
`requirements.txt`에 다음 패키지를 추가하고 설치합니다. (또는 `pip install` 실행)

```bash
# vLLM과 통신하기 위한 OpenAI 파이썬 클라이언트
pip install openai>=1.0.0

# 스트리밍 응답(SSE) 처리를 위한 라이브러리
pip install sse-starlette>=1.0.0
```

### 2-2. 환경 변수 설정
로컬 프로젝트의 `.env` 파일에 RunPod 접속 정보를 추가합니다.

```ini
# .env 파일

# RunPod API Key (Pod 제어용)
RUNPOD_API_KEY=rpa_...

# RunPod Pod ID (대상 Pod 식별자)
RUNPOD_POD_ID=abc123xyz

# RunPod vLLM Base URL (추론 요청용)
# 포맷: https://{POD_ID}-8000.proxy.runpod.net/v1
RUNPOD_BASE_URL=https://abc123xyz-8000.proxy.runpod.net/v1

# (선택) vLLM API Key (설정한 경우)
# VLLM_API_KEY=...
```

### 2-3. 연결 테스트 (선택)
터미널에서 `curl`이나 파이썬 스크립트로 RunPod vLLM에 요청이 가는지 확인합니다.

```bash
curl https://027ijzo8g9s6uc-8000.proxy.runpod.net/v1/models \
  -H "Authorization: Bearer $VLLM_API_KEY"
```
응답으로 모델 목록이 JSON으로 오면 성공입니다.
