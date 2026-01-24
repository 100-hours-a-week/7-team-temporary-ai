from fastapi import APIRouter
from app.api.v1 import gemini_test_planners

router = APIRouter()

# v1의 모든 라우터를 통합 관리
router.include_router(gemini_test_planners.router)
