import json
import os
from fastapi import APIRouter
from app.models.personalization import PersonalizationIngestRequest, PersonalizationIngestResponse
from app.services.personalization_service import PersonalizationService

router = APIRouter()
service = PersonalizationService()

# 테스트 데이터 로드 함수
def load_example_data():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 프로젝트 루트 경로 찾기 (app/api/v1/endpoints -> app/api/v1 -> app/api -> app -> PROJECT_ROOT)
    # 조금 더 안전하게 상대 경로로 접근
    data_path = os.path.join(current_dir, "../../../../tests/data/personalization_ingest_week_sample.json")
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Failed to load example data: {e}")
        return {}

example_data = load_example_data()

# 모델의 Config에 예제 데이터 주입
if example_data:
    if "json_schema_extra" not in PersonalizationIngestRequest.model_config:
        PersonalizationIngestRequest.model_config["json_schema_extra"] = {}
    
    # FastAPI Docs (Swagger) Example 설정
    PersonalizationIngestRequest.model_config["json_schema_extra"]["examples"] = [example_data]


@router.post("/ingest", response_model=PersonalizationIngestResponse)
async def ingest_personalization_data(request: PersonalizationIngestRequest):
    """
    개인화 데이터 수집(Ingest) API
    
    - 사용자의 지난 일주일 플래너 데이터 및 수정 이력을 수신하여 DB에 저장합니다.
    - 입력 예시는 'Example Value'를 참고하세요 (일주일치 샘플 데이터 포함).
    """
    return await service.process_ingest_request(request)
