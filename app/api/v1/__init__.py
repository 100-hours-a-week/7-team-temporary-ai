from fastapi import APIRouter

from app.api.v1.endpoints import personalization, planners, runpod_control

router = APIRouter()

# v1의 모든 라우터를 통합 관리
router.include_router(planners.router, prefix="/planners", tags=["AI Planner"])
router.include_router(personalization.router, prefix="/personalizations", tags=["Personalization"])
router.include_router(runpod_control.router, prefix="/runpod", tags=["RunPod"])

