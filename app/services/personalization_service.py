import time
from app.models.personalization import PersonalizationIngestRequest, PersonalizationIngestResponse


class PersonalizationService:
    def __init__(self):
        # self.repository = PersonalizationRepository()
        pass

    async def process_ingest_request(self, request: PersonalizationIngestRequest) -> PersonalizationIngestResponse:
        start_time = time.time()
        
        # TODO: Implement actual logic for user_ids and target_date
        # Currently just echoing back the request data as per requirement
        
        end_time = time.time()
        process_time = end_time - start_time
        
        return PersonalizationIngestResponse(
            success=True,
            process_time=process_time,
            user_ids=request.user_ids,
            message="Ingest triggered successfully"
        )

