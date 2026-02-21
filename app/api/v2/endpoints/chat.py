import logging
from fastapi import APIRouter, Path, Request
from fastapi.responses import StreamingResponse, HTMLResponse
from starlette.status import HTTP_200_OK, HTTP_204_NO_CONTENT

from app.models.chat import ChatRespondRequest, ChatRespondAckResponse
from app.services.report.chat_service import ChatService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Chatbot"])
chat_service = ChatService()


@router.post(
    "/reports/{reportId}/chat/respond",
    response_model=ChatRespondAckResponse,
    status_code=HTTP_200_OK,
    summary="[챗봇] 응답 생성 접수",
    description="실제 메시지 생성은 수행하지 않고 스트리밍 준비만 합니다. messageId는 stream 키로 활용됩니다.",
)
async def chat_respond(
    request: ChatRespondRequest,
    reportId: int = Path(..., description="리포트 대화창 식별자"),
):
    """
    POST /ai/v2/reports/{reportId}/chat/respond
    """
    return await chat_service.respond(report_id=reportId, request=request)


@router.get(
    "/reports/{reportId}/chat/test",
    response_class=HTMLResponse,
    include_in_schema=False,
    summary="[테스트용] 챗봇 화면 UI HTML 렌더링",
)
async def chat_test_page(reportId: int = Path(...)):
    """
    테스트용 챗봇 프론트엔드 제공
    """
    import os
    html_path = os.path.join(os.path.dirname(__file__), "../../../../tests/chat_test.html")
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)


@router.get(
    "/reports/{reportId}/chat/respond/{messageId}/stream",
    response_class=StreamingResponse,
    status_code=HTTP_200_OK,
    summary="[챗봇] 응답 실시간 스트리밍 (SSE)",
    description="Gemini API를 호출하여 생성된 메세지를 chunk 단위로 전송합니다.",
)
async def chat_stream(
    reportId: int = Path(..., description="리포트 식별자"),
    messageId: int = Path(..., description="구독할 스트림의 messageId"),
):
    """
    GET /ai/v2/reports/{reportId}/chat/respond/{messageId}/stream
    """
    return StreamingResponse(
        chat_service.stream(report_id=reportId, message_id=messageId),
        media_type="text/event-stream"
    )


@router.delete(
    "/reports/{reportId}/chat/respond/{messageId}/stream",
    status_code=HTTP_204_NO_CONTENT,
    summary="[챗봇] 응답 취소",
    description="현재 진행 중인 챗봇 응답 스트림을 중단(Cancel)합니다.",
)
async def chat_cancel(
    reportId: int = Path(..., description="리포트 식별자"),
    messageId: int = Path(..., description="취소할 스트림 구독 키(messageId)"),
):
    """
    DELETE /ai/v2/reports/{reportId}/chat/respond/{messageId}/stream
    """
    cancelled = await chat_service.cancel(message_id=messageId)
    # 204 No Content is returned regardless of success in our spec context to ensure idempotency.
    return
