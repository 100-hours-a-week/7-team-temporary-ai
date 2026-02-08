import json
import os
from fastapi import APIRouter
from app.models.personalization import PersonalizationIngestRequest, PersonalizationIngestResponse
from app.services.personalization_service import PersonalizationService

router = APIRouter()
service = PersonalizationService()


@router.post("/ingest", response_model=PersonalizationIngestResponse)
async def ingest_personalization_data(request: PersonalizationIngestRequest):
    """
    개인화 데이터 수집(Ingest) API
    
    - 특정 날짜(targetDate)에 대해, 지정된 사용자 목록(userIds)의 개인화 파라미터 생성을 요청합니다.
    """
    return await service.process_ingest_request(request)
