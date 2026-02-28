
# RunPod Serverless LLM 관리 시스템 가이드

본 문서는 **FastAPI**, **RunPod Serverless**, 그리고 **Supabase**를 결합하여 매일 정해진 시간에 GPU 자원을 할당하고 종료하는 자동화 시스템의 설계 및 구현 방법을 다룹니다.

---

## 1. 시스템 아키텍처 개요

Docker 환경에서 서버 배포 시 발생하는 데이터 휘발성 문제를 해결하기 위해 외부 데이터베이스(Supabase)를 상태 저장소로 활용합니다.

- **Storage**: Supabase (RunPod Endpoint ID 영속성 유지)
- **Compute**: RunPod Serverless (GPU 자원 점유 및 LLM 추론)
- **API**: FastAPI (비즈니스 로직 및 스케줄링 제어)
- **Environment**: Docker / PM2

---

## 2. 데이터베이스 설정 (Supabase)

엔드포인트 식별자를 안전하게 보관하기 위해 Supabase에 아래와 같은 테이블을 생성합니다.

### SQL Schema
```sql
CREATE TABLE runpod_management (
    service_name TEXT PRIMARY KEY,
    endpoint_id TEXT,
    is_active BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

```

---

## 3. 핵심 구현 코드 (`runpod_manager.py`)

환경변수 조작 대신 데이터베이스 싱크를 통해 상태를 관리합니다.

```python
import os
import runpod
from supabase import create_client, Client

# 1. 초기 설정
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

runpod.api_key = RUNPOD_API_KEY
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 2. 상태 동기화 함수
def update_supabase_status(endpoint_id: str, active: bool):
    supabase.table("runpod_management").upsert({
        "service_name": "llm_serverless",
        "endpoint_id": endpoint_id,
        "is_active": active,
        "updated_at": "now()"
    }).execute()

# 3. 서버리스 구동 (08:00)
def start_llm_service():
    # 엔드포인트 생성
    endpoint = runpod.create_endpoint(
        name="Daily_LLM_Worker",
        template_id="YOUR_TEMPLATE_ID",
        gpu_ids="NVIDIA GeForce RTX 3090"
    )
    endpoint_id = endpoint["id"]
    
    # DB 기록
    update_supabase_status(endpoint_id, True)
    return endpoint_id

# 4. 서버리스 종료 (17:00)
def terminate_llm_service():
    # DB에서 현재 실행 중인 ID 조회
    res = supabase.table("runpod_management").select("endpoint_id").eq("service_name", "llm_serverless").execute()
    
    if res.data and res.data[0]['endpoint_id']:
        endpoint_id = res.data[0]['endpoint_id']
        try:
            runpod.terminate_endpoint(endpoint_id)
            update_supabase_status(None, False)
            print(f"Successfully terminated: {endpoint_id}")
        except Exception as e:
            print(f"Termination failed: {e}")

```

---

## 4. 운영 및 스케줄링 전략

### Docker 배포 시 고려사항

* **영속성**: 서버가 재시작되어도 `FastAPI`의 `on_startup` 이벤트에서 Supabase를 조회하여 기존 `endpoint_id`를 복구할 수 있습니다.
* **보안**: `.env` 파일에 `RUNPOD_API_KEY`와 `SUPABASE_KEY`를 보관하며, Endpoint ID 자체는 유출되어도 API Key 없이는 제어가 불가능하므로 안전합니다.

### 스케줄링 (Cron)

FastAPI 내부 스케줄러가 배포 중단으로 멈출 것을 대비해, OS 레벨의 **Crontab** 사용을 권장합니다.

```bash
# 매일 오전 8시 구동 스크립트 실행
0 8 * * * /usr/bin/python3 /ai/scripts/start_pod.py

# 매일 오후 5시 종료 스크립트 실행
0 17 * * * /usr/bin/python3 /ai/scripts/terminate_pod.py

```

---

## 5. 요약 및 주의사항

1. **상태 관리**: 전역 변수나 환경변수 수정 대신 반드시 **Supabase**를 진실의 원천(Source of Truth)으로 사용하세요.
2. **비용 최적화**: RunPod 설정에서 `Idle Timeout`을 설정하여 네트워크 오류로 종료 명령이 누락될 경우를 대비하세요.
3. **인증**: LLM 다운로드 시 Docker 내부 Handler에서 `huggingface_hub.login`을 호출하도록 구성하세요.

