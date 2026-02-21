import sys
import os
import json
import asyncio
import pytest
from unittest.mock import patch, AsyncMock, ANY, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from google.genai.errors import APIError
from app.services.report.chat_service import ChatService, _active_sessions
from app.models.chat import ChatRespondRequest, ChatHistoryMessage, SenderType, MessageType

@pytest.fixture
def chat_service():
    with patch("app.services.report.chat_service.get_gemini_client") as mock_get_client:
        mock_gemini = MagicMock()
        mock_aio = AsyncMock()
        mock_gemini.client.aio = mock_aio
        mock_get_client.return_value = mock_gemini
        
        service = ChatService()
        yield service
        
        # Cleanup
        _active_sessions.clear()

@pytest.fixture
def sample_request():
    return ChatRespondRequest(
        userId=100,
        messageId=123,
        messages=[
            ChatHistoryMessage(
                messageId=1, 
                senderType=SenderType.USER, 
                messageType=MessageType.TEXT, 
                content="Hello"
            )
        ]
    )


@pytest.mark.asyncio
async def test_respond_creates_session(chat_service, sample_request):
    """
    POST respond 호출 시:
    ACK를 반환하고 _active_sessions에 내역이 저장되는지 확인
    """
    report_id = 1
    response = await chat_service.respond(report_id, sample_request)
    
    assert response.success is True
    assert response.data.message_id == 123
    
    # 세션 확인
    assert 123 in _active_sessions
    assert "queue" in _active_sessions[123]
    assert "task" in _active_sessions[123]
    
    # 생성된 백그라운드 태스크 정리 (cancel)
    _active_sessions[123]["task"].cancel()

@pytest.mark.asyncio
async def test_stream_returns_format(chat_service, sample_request):
    """
    stream 제너레이터가 Queue의 데이터를 SSE 포맷으로 올바르게 꺼내는지 확인
    """
    report_id = 1
    message_id = 123
    
    # 큐 수동 주입
    queue = asyncio.Queue()
    _active_sessions[message_id] = {"queue": queue, "task": None}
    
    # 이벤트 적재
    await queue.put(("start", {"messageId": message_id}))
    await queue.put(("chunk", {"messageId": message_id, "delta": "Hi", "sequence": 1}))
    await queue.put(("complete", {"messageId": message_id, "status": "COMPLETED"}))
    await queue.put(None)
    
    events = []
    async for item in chat_service.stream(report_id, message_id):
        events.append(item)
        
    assert len(events) == 3
    assert 'event: start' in events[0]
    assert 'event: chunk' in events[1]
    assert '"delta": "Hi"' in events[1]
    assert 'event: complete' in events[2]
    
    # 스트림 종료 후 세션이 삭제되는지 확인
    assert message_id not in _active_sessions


@pytest.mark.asyncio
async def test_generate_task_fallback_logic(chat_service, sample_request):
    """
    _generate_task 내에서 503 에러 발생 시 재시도 및 Fallback이 일어나는지 검증
    """
    message_id = 123
    queue = asyncio.Queue()
    _active_sessions[message_id] = {"queue": queue, "task": asyncio.current_task()} # 더미 타스크
    
    # Mock AsyncGenerator 반환 
    async def mock_async_generator():
        class MockChunk:
            def __init__(self, text):
                self.text = text
        yield MockChunk("Fallback")
        yield MockChunk("Success")
        
    mock_generate = chat_service.gemini.client.aio.models.generate_content_stream
    
    # 3번 실패 (503 에러), 4번째 (fallback) 성공
    class FakeAPIError(APIError):
        def __init__(self, message, code):
            super().__init__(message, {"error": {"message": message}})
            self.code = code
            
    mock_generate.side_effect = [
        FakeAPIError("503 Server Error 1", code=503),
        FakeAPIError("503 Server Error 2", code=503),
        FakeAPIError("503 Server Error 3", code=503),
        mock_async_generator() # 4번째 호출은 제너레이터 정상 반환
    ]
    
    with patch("app.services.report.chat_service.asyncio.sleep", new_callable=AsyncMock):
        await chat_service._generate_task(message_id, sample_request.messages)
        
    # 총 4번 호출되었는지 검증
    assert mock_generate.call_count == 4
    
    # 4번째 호출의 모델 인자가 gemini-2.5-flash 인지 검증
    last_call_kwargs = mock_generate.call_args.kwargs
    assert last_call_kwargs["model"] == "gemini-2.5-flash"
    
    # Queue 이벤트 수집하여 정상 chunk가 들어갔는지 확인
    events = []
    while not queue.empty():
        item = await queue.get()
        if item is not None:
            events.append(item)
            
    # start, chunk1, chunk2, complete
    assert events[0][0] == "start"
    assert events[1][0] == "chunk"
    assert events[1][1]["delta"] == "Fallback"
    assert events[2][0] == "chunk"
    assert events[2][1]["delta"] == "Success"
    assert events[3][0] == "complete"
    
    
@pytest.mark.asyncio
async def test_cancel_removes_session(chat_service, sample_request):
    message_id = 123
    dummy_task = asyncio.create_task(asyncio.sleep(10))
    _active_sessions[message_id] = {"queue": asyncio.Queue(), "task": dummy_task}
    
    success = await chat_service.cancel(message_id)
    assert success is True
    assert message_id not in _active_sessions
    # Cancellation propagates next event loop tick
    await asyncio.sleep(0)
    assert dummy_task.cancelled() or dummy_task.cancelling()
