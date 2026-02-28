import asyncio
import json
import logging
import time
from typing import AsyncGenerator, Annotated, Any

from fastapi import HTTPException
from google.genai import types
from google.genai.errors import APIError

from app.llm.gemini_client import get_gemini_client
from app.llm.prompts.chat_prompt import CHAT_SYSTEM_PROMPT
from app.models.chat import (
    ChatRespondRequest,
    ChatRespondAckResponse,
    ChatRespondAckData,
    ChatStreamStartEvent,
    ChatStreamChunkEvent,
    ChatStreamCompleteEvent,
    ChatStreamErrorEvent,
    StreamStatus,
    SenderType,
    MessageType,
)

logger = logging.getLogger(__name__)

# 장기 연결 세션 및 큐 관리
# Key: message_id, Value: dict("queue": asyncio.Queue, "task": asyncio.Task)
_active_sessions: dict[int, dict[str, Any]] = {}

class ChatService:
    def __init__(self):
        self.gemini = get_gemini_client()

    async def respond(self, report_id: int, request: ChatRespondRequest) -> ChatRespondAckResponse:
        """
        POST API 로직: 응답 생성 접수 및 백그라운드 태스크 시작
        """
        if request.message_id in _active_sessions:
            raise HTTPException(status_code=409, detail="A stream for this messageId is already active.")

        # SSE 이벤트를 담을 큐 생성
        queue = asyncio.Queue()
        
        # 백그라운드에서 Gemini API를 호출하고 큐에 이벤트를 넣는 태스크 시작
        task = asyncio.create_task(self._generate_task(report_id, request.message_id, request.messages))
        
        _active_sessions[request.message_id] = {
            "queue": queue,
            "task": task
        }

        return ChatRespondAckResponse(
            success=True,
            processTime=0.01,
            data=ChatRespondAckData(messageId=request.message_id)
        )

    async def _generate_task(self, report_id: int, message_id: int, messages: list):
        """본격적인 API 호출 및 Queue 적재 로직 (백그라운드 실행)"""
        session = _active_sessions.get(message_id)
        if not session:
            return
        queue = session["queue"]

        try:
            # Event: Start 전송
            start_event = ChatStreamStartEvent(messageId=message_id)
            await queue.put(("start", start_event.model_dump(by_alias=True)))

            gemini_contents = []
            for msg in messages:
                if msg.sender_type == SenderType.SYSTEM:
                    gemini_contents.append(
                        types.Content(
                            role="user",
                            parts=[types.Part.from_text(text=f"[System Background]\n{msg.content}")]
                        )
                    )
                elif msg.sender_type == SenderType.USER:
                    gemini_contents.append(
                        types.Content(
                            role="user",
                            parts=[types.Part.from_text(text=msg.content)]
                        )
                    )
                elif msg.sender_type == SenderType.AI:
                    gemini_contents.append(
                        types.Content(
                            role="model",
                            parts=[types.Part.from_text(text=msg.content)]
                        )
                    )

            # --- Retry 로직 ---
            max_retries = 4
            retry_count = 0
            current_model_name = "gemini-2.5-flash"
            fallback_model_name = "gemini-3-flash-preview"

            response_stream = None
            is_success = False
            last_error = None

            # User ID 조회 추가 (report_id 기반)
            from app.db.repositories.report_repository import ReportRepository
            repo = ReportRepository()
            user_id = await repo.fetch_user_id_by_report_id(report_id)
            if not user_id:
                raise ValueError(f"Valid user_id not found for report {report_id}")

            from app.mcp.server import search_schedules_by_date, search_tasks_by_similarity
            # Gemini에 제공할 도구 목록
            tools = [search_schedules_by_date, search_tasks_by_similarity]

            while retry_count < max_retries and not is_success:
                try:
                    logger.info(f"Chat stream attempt {retry_count+1} with model {current_model_name} for message_id: {message_id}")
                    
                    # 모델이 user_id를 바로 알 수 있도록 시스템 프롬프트에 주입
                    dynamic_system_prompt = CHAT_SYSTEM_PROMPT + f"\n\n[System Data]\n현재 대화 중인 사용자의 userId는 {user_id} 입니다. 도구를 호출할 때 이 userId를 반드시 사용하세요."
                    
                    # Tool 호출 처리를 위한 반복 루프 (최대 5회)
                    max_tool_loops = 5
                    loop_count = 0
                    seq = 1
                    
                    while loop_count < max_tool_loops:
                        loop_count += 1
                        
                        logger.info(f"Loop {loop_count} starting Gemini Model stream")
                        response_stream = await self.gemini.client.aio.models.generate_content_stream(
                            model=current_model_name,
                            contents=gemini_contents,
                            config=types.GenerateContentConfig(
                                temperature=0.7,
                                system_instruction=dynamic_system_prompt,
                                tools=tools
                            )
                        )
                        
                        tool_calls = []
                        async for chunk in response_stream:
                            if chunk.function_calls:
                                tool_calls.extend(chunk.function_calls)
                            elif chunk.text:
                                is_success = True
                                chunk_event = ChatStreamChunkEvent(
                                    messageId=message_id,
                                    delta=chunk.text,
                                    sequence=seq
                                )
                                await queue.put(("chunk", chunk_event.model_dump(by_alias=True)))
                                seq += 1
                        
                        if not tool_calls:
                            # 툴 호출이 없었고 텍스트가 스트리밍되었다면 완료
                            is_success = True
                            break
                        
                        # 도구를 호출해야 하는 경우 
                        function_responses = []
                        for call in tool_calls:
                            tool_name = call.name
                            args = call.args if call.args else {}
                            
                            # 만약 LLM이 user_id를 주지 않았다면 강제 주입
                            if "user_id" not in args:
                                args["user_id"] = user_id
                                
                            logger.info(f"Executing tool {tool_name} with args: {args}")
                            try:
                                if tool_name == "search_schedules_by_date":
                                    result = await search_schedules_by_date(**args)
                                elif tool_name == "search_tasks_by_similarity":
                                    result = await search_tasks_by_similarity(**args)
                                else:
                                    result = f"Unknown tool: {tool_name}"
                            except Exception as e:
                                result = f"Error executing tool {tool_name}: {e}"
                                logger.error(result)
                            
                            function_responses.append(
                                types.Part.from_function_response(
                                    name=tool_name,
                                    response={"result": result}
                                )
                            )
                            
                        # LLM의 함수 호출과 실행 결과를 Messages 목록에 추가
                        gemini_contents.append(
                            types.Content(role="model", parts=[types.Part.from_function_call(name=c.name, args=c.args) for c in tool_calls])
                        )
                        gemini_contents.append(
                            types.Content(role="user", parts=function_responses)
                        )
                        
                        # 모델에 다시 스트리밍을 요청하기 위해 루프 반복
                    
                    if loop_count >= max_tool_loops and not is_success:
                         logger.warning("Max tool execution depth reached.")
                         raise Exception("Max tool execution depth reached.")
                         
                    break # 성공 시 외부 재시도 루프 탈출
                except Exception as e:
                    last_error = e
                    status_code = getattr(e, "code", 500)
                    if status_code == 500 and "503" in str(e):
                        status_code = 503
                        
                    logger.warning(f"Gemini streaming error ({status_code}): {e}")
                    
                    if status_code in (503, 500, 429):
                        retry_count += 1
                        if retry_count < 3:
                            # 1, 2차 실패 시: 0.5초 대기 후 기본 모델로 재시도
                            await asyncio.sleep(0.5)
                        elif retry_count == 3:
                            # 3차 실패 시: 모델을 fallback 모델로 변경하고 0.5초 대기 후 재시도
                            logger.warning(f"Fallback to {fallback_model_name} for message_id: {message_id}")
                            current_model_name = fallback_model_name
                            await asyncio.sleep(0.5)
                    else:
                        # 재시도 불가 에러(예: 400 Bad Request, 403 Forbidden)
                        break

            if not is_success:
                err_event = ChatStreamErrorEvent(
                    messageId=message_id,
                    errorCode="GEMINI_API_ERROR",
                    message=str(last_error)
                )
                await queue.put(("error", err_event.model_dump(by_alias=True)))
                await queue.put(None) # 스트림 종료 신호
                return

            # Event: Complete
            complete_event = ChatStreamCompleteEvent(
                messageId=message_id,
                status=StreamStatus.COMPLETED,
            )
            await queue.put(("complete", complete_event.model_dump(by_alias=True)))

        except asyncio.CancelledError:
            logger.info(f"Stream generation task for messageId {message_id} was cancelled.")
            cancel_event = ChatStreamCompleteEvent(
                messageId=message_id,
                status=StreamStatus.CANCELED,
            )
            await queue.put(("complete", cancel_event.model_dump(by_alias=True)))
            
        except Exception as e:
            logger.error(f"Unexpected error in stream {message_id}: {str(e)}", exc_info=True)
            err_event = ChatStreamErrorEvent(
                messageId=message_id,
                errorCode="INTERNAL_SERVER_ERROR",
                message=str(e)
            )
            await queue.put(("error", err_event.model_dump(by_alias=True)))
            
        finally:
            await queue.put(None) # 종료 신호
            
            # 여기서 삭제하면 GET을 아직 연결 안했을때 사라질 수 있으므로, 삭제는 GET 혹은 일정시간 후 수행해야 함
            # 일단 여기서는 삭제하지 않음 (GET 완료 시 혹은 Cancel 시 삭제)


    async def stream(self, report_id: int, message_id: int) -> AsyncGenerator[str, None]:
        """
        GET API 로직: 큐에서 이벤트를 읽어와 SSE로 yield
        """
        session = _active_sessions.get(message_id)
        if not session:
            # 404 NOT_FOUND 
            yield self._format_sse("error", {
                "status": "NOT_FOUND",
                "message": f"MessageId {message_id} not found or stream already closed"
            })
            return

        queue = session["queue"]
        
        try:
            while True:
                item = await queue.get()
                if item is None:
                    # 스트림 종료 신호
                    break
                
                event_name, data = item
                yield self._format_sse(event_name, data)
                
                # complete 나 error 이벤트면 종료
                if event_name in ("complete", "error"):
                    break
        finally:
            # 스트리밍 종료 시 세션 정리
            if message_id in _active_sessions:
                del _active_sessions[message_id]

    async def cancel(self, message_id: int) -> bool:
        """
        DELETE API 로직: 진행 중인 생성 세션을 취소(Task.cancel)
        """
        session = _active_sessions.get(message_id)
        if session:
            task = session["task"]
            if not task.done():
                task.cancel()
                logger.info(f"Cancelled active chat task for messageId: {message_id}")
            # 삭제는 _generate_task나 stream finally 블록에서 처리될 수 있으나 명시적으로 여기서 지움
            del _active_sessions[message_id]
            return True
        return False


    def _format_sse(self, event: str, data: dict) -> str:
        """SSE 포맷에 맞춰 문자열을 생성하는 헬퍼 함수"""
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

