from fastapi import APIRouter
from app.api.v2.endpoints import reports

router = APIRouter()

# v2 라우터 통합
router.include_router(reports.router, prefix="/reports", tags=["Weekly Report"])
