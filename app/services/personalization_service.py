import time
from app.db.repositories.personalization_repository import PersonalizationRepository
from app.models.personalization import PersonalizationIngestRequest, PersonalizationIngestResponse
from app.models.planner.errors import PersonalizationErrorCode
from postgrest.exceptions import APIError


class PersonalizationService:
    def __init__(self):
        self.repository = PersonalizationRepository()

    async def process_ingest_request(self, request: PersonalizationIngestRequest) -> PersonalizationIngestResponse:
        start_time = time.time()
        
        try:
            # 1. Repository를 통해 데이터 저장
            await self.repository.save_ingest_data(request)
            
            end_time = time.time()
            process_time = end_time - start_time
            
            return PersonalizationIngestResponse(
                success=True,
                processTime=process_time,
                message="개인화 데이터 저장 성공"
            )
            
        except APIError as e:
            # Supabase(Postgrest) API 에러
            end_time = time.time()
            process_time = end_time - start_time
            print(f"[PersonalizationService] DB API Error: {e}")
            
            return PersonalizationIngestResponse(
                success=False,
                processTime=process_time,
                message=f"DB 저장 중 오류 발생: {str(e)}",
                errorCode=PersonalizationErrorCode.DB_INSERT_ERROR
            )
            
        except Exception as e:
            # 기타 일반 에러
            end_time = time.time()
            process_time = end_time - start_time
            print(f"[PersonalizationService] Unknown Error: {e}")
            
            return PersonalizationIngestResponse(
                success=False,
                processTime=process_time,
                message=f"서버 내부 오류: {str(e)}",
                errorCode=PersonalizationErrorCode.INTERNAL_SERVER_ERROR
            )

