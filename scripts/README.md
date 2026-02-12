# RunPod Serverless Integration Scripts (Paused)

**최종 수정일**: 2026-02-12
**상태**: 잠정 중단 (MVP 개발을 위해 Gemini API로 전환)

이 디렉토리는 RunPod Serverless 기반의 LLM (`Llama-3.1-8B-Instruct`) 서빙을 위한 테스트 및 유틸리티 스크립트를 포함하고 있습니다. 현재는 개발 속도와 비용 효율성을 위해 **Google Gemini API**를 우선 사용하기로 결정하였으나, 추후 고도화 단계에서 RunPod을 재도입할 때 참고하기 위해 기록을 남깁니다.

---

## 1. 현재 파일 (Current Files)

### `test_runpod_serverless.py`
RunPod API를 사용하여 Serverless Endpoint를 **생성(Create)**하고 **삭제(Terminate)**하는 기능을 수행합니다.
- **주요 기능**:
    - `create`: `RUNPOD_TEMPLATE_ID`, `RUNPOD_VOLUME_ID` 등을 환경변수에서 읽어와 엔드포인트를 생성합니다.
        - **설정**: `ADA_24` (RTX 4090), Idle Timeout 3600초, Network Volume 연결.
    - `terminate`: **GraphQL API**를 직접 호출하여 엔드포인트를 강제 삭제합니다. (RunPod Python SDK v1.8.x의 기능 누락 대응)
- **사용법**:
    ```bash
    # 엔드포인트 생성
    python scripts/test_runpod_serverless.py create

    # 엔드포인트 삭제
    python scripts/test_runpod_serverless.py terminate <ENDPOINT_ID>
    ```

---

## 2. 시도했던 접근 방식 (History & Pivot)

개발 과정에서 시도했던 기술적 접근과 트러블슈팅 이력입니다. (추후 재개 시 참고)

### A. Network Volume + vLLM Serverless
- **목표**: 매번 모델(15GB+)을 다운로드받는 시간을 절약하기 위해 **Network Volume**에 모델을 저장하고 Serverless 워커가 이를 마운트하여 사용.
- **성과**:
    - `EU-RO-1` 리전에 40GB 볼륨 생성 완료.
    - 임시 Pod를 통해 `Llama-3.1-8B-Instruct` 모델 다운로드 완료 (`/runpod-volume/Llama-3.1-8B-Instruct`).
- **이슈 (Blocker)**:
    - **Queue Stuck**: 엔드포인트 생성 후 요청이 처리되지 않고 `In Queue` 상태로 무한 대기.
    - **원인**:
        1. **Health Check**: vLLM 기본 경로(`/`)와 RunPod Health Check(`/health`) 경로 불일치.
        2. **Handler 부재**: `vllm/vllm-openai` 이미지는 웹 서버일 뿐, RunPod Queue 작업을 처리하는 핸들러가 없음. -> 커스텀 핸들러(`runpod_wrapper.py`) 필요.
        3. **이미지 호환성**: 공식 vLLM 이미지는 `ENTRYPOINT`가 고정되어 있어 커스텀 핸들러 실행(`bash -c ...`)이 어려움.

### B. Custom Wrapper Script (`runpod_wrapper.py`)
- **목표**: `runpod` SDK를 사용하여 Queue 작업을 수신하고, 내부적으로 `vLLM` 서버에 HTTP 요청을 보내는 중계 스크립트 작성.
- **진행 상황**: 스크립트 작성 및 볼륨 업로드 완료. 그러나 위 이미지 호환성 문제로 실행 실패.
- **추가 시도 (Failed Attemp)**:
    - **시도**: `runpod/worker-v1-vllm:stable-cuda11.8.0` (RunPod 공식 워커 이미지)로 교체하여 핸들러 없이 구동 시도.
    - **결과**: 여전히 GPU 할당이 되지 않거나(`In Queue` 무한 대기), 초기 설정 문제로 인해 실행 실패.
    - **결론**: Serverless 환경의 복잡성과 리소스 할당 이슈로 인해, MVP 단계에서는 더 안정적인 **Gemini API**로 선회 결정.
