import asyncio
import json
import logging
import time
from typing import AsyncGenerator, Annotated, Any

from fastapi import HTTPException
from openai import AsyncOpenAI

from app.core.config import settings
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
        self._runpod_available = bool(settings.runpod_base_url)
        if self._runpod_available:
            self.client = AsyncOpenAI(
                base_url=settings.runpod_base_url,
                api_key=settings.runpod_api_key or "EMPTY",
            )
        self.model_name = "Qwen2.5-72B-Instruct"

        # Gemini 폴백 (lazy init)
        self._gemini_client = None

    def _get_gemini_fallback(self):
        if self._gemini_client is None:
            from app.llm.gemini_client import get_gemini_client
            self._gemini_client = get_gemini_client()
            logger.info("ChatService: Gemini fallback client initialized")
        return self._gemini_client

    async def respond(self, report_id: int, request: ChatRespondRequest) -> ChatRespondAckResponse:
        """
        POST API 로직: 응답 생성 접수 및 백그라운드 태스크 시작
        """
        if request.message_id in _active_sessions:
            raise HTTPException(status_code=409, detail="A stream for this messageId is already active.")

        # SSE 이벤트를 담을 큐 생성
        queue = asyncio.Queue()

        # 백그라운드에서 LLM API를 호출하고 큐에 이벤트를 넣는 태스크 시작
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

            # User ID 조회 (report_id 기반)
            from app.db.repositories.report_repository import ReportRepository
            repo = ReportRepository()
            user_id = await repo.fetch_user_id_by_report_id(report_id)
            if not user_id:
                raise ValueError(f"Valid user_id not found for report {report_id}")

            # MCP 도구 정의 (OpenAI function calling 형식)
            from app.mcp.server import search_schedules_by_date, search_tasks_by_similarity
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "search_schedules_by_date",
                        "description": "특정 날짜 범위의 사용자 일정을 검색합니다.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "user_id": {"type": "integer", "description": "사용자 ID"},
                                "start_date": {"type": "string", "description": "시작 날짜 (YYYY-MM-DD)"},
                                "end_date": {"type": "string", "description": "종료 날짜 (YYYY-MM-DD)"}
                            },
                            "required": ["user_id", "start_date", "end_date"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "search_tasks_by_similarity",
                        "description": "사용자의 과거 태스크 중 입력된 텍스트와 의미적으로 가장 유사한 기록을 검색합니다.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "user_id": {"type": "integer", "description": "사용자 ID"},
                                "query": {"type": "string", "description": "검색할 자연어 문장"},
                                "top_k": {"type": "integer", "description": "반환할 결과 수", "default": 5}
                            },
                            "required": ["user_id", "query"]
                        }
                    }
                }
            ]

            # 시스템 프롬프트에 user_id 주입
            dynamic_system_prompt = CHAT_SYSTEM_PROMPT + f"\n\n[System Data]\n현재 대화 중인 사용자의 userId는 {user_id} 입니다. 도구를 호출할 때 이 userId를 반드시 사용하세요."

            # OpenAI 호환 메시지 변환
            openai_messages = [{"role": "system", "content": dynamic_system_prompt}]
            for msg in messages:
                if msg.sender_type == SenderType.SYSTEM:
                    openai_messages.append({"role": "user", "content": f"[System Background]\n{msg.content}"})
                elif msg.sender_type == SenderType.USER:
                    openai_messages.append({"role": "user", "content": msg.content})
                elif msg.sender_type == SenderType.AI:
                    openai_messages.append({"role": "assistant", "content": msg.content})

            # --- RunPod 스트리밍 (실패 시 Gemini 폴백) ---
            max_retries = 4
            retry_count = 0
            is_success = False
            last_error = None
            use_gemini_fallback = not self._runpod_available

            while retry_count < max_retries and not is_success and not use_gemini_fallback:
                try:
                    logger.info(f"Chat stream attempt {retry_count+1} (RunPod) for message_id: {message_id}")

                    # Tool 호출 처리를 위한 반복 루프 (최대 5회)
                    max_tool_loops = 5
                    loop_count = 0
                    seq = 1
                    current_messages = list(openai_messages)

                    while loop_count < max_tool_loops:
                        loop_count += 1

                        # 스트리밍 호출
                        response_stream = await self.client.chat.completions.create(
                            model=self.model_name,
                            messages=current_messages,
                            tools=tools,
                            tool_choice="auto",
                            temperature=0.7,
                            stream=True,
                        )

                        tool_calls_acc = {}
                        has_text = False

                        async for chunk in response_stream:
                            delta = chunk.choices[0].delta if chunk.choices else None
                            if not delta:
                                continue

                            # 텍스트 스트리밍
                            if delta.content:
                                has_text = True
                                is_success = True
                                words = delta.content.split(' ')
                                for i, word in enumerate(words):
                                    text_delta = word + (' ' if i < len(words) - 1 else '')
                                    if not text_delta:
                                        continue
                                    chunk_event = ChatStreamChunkEvent(
                                        messageId=message_id,
                                        delta=text_delta,
                                        sequence=seq
                                    )
                                    await queue.put(("chunk", chunk_event.model_dump(by_alias=True)))
                                    seq += 1
                                    await asyncio.sleep(0.05)

                            # Tool call 누적
                            if delta.tool_calls:
                                for tc in delta.tool_calls:
                                    idx = tc.index
                                    if idx not in tool_calls_acc:
                                        tool_calls_acc[idx] = {"id": tc.id or "", "name": "", "arguments": ""}
                                    if tc.id:
                                        tool_calls_acc[idx]["id"] = tc.id
                                    if tc.function:
                                        if tc.function.name:
                                            tool_calls_acc[idx]["name"] = tc.function.name
                                        if tc.function.arguments:
                                            tool_calls_acc[idx]["arguments"] += tc.function.arguments

                        if not tool_calls_acc:
                            is_success = True
                            break

                        # 도구 실행
                        assistant_tool_calls = []
                        tool_results = []

                        for idx in sorted(tool_calls_acc.keys()):
                            tc = tool_calls_acc[idx]
                            tool_name = tc["name"]
                            tool_call_id = tc["id"]
                            try:
                                args = json.loads(tc["arguments"])
                            except json.JSONDecodeError:
                                args = {}

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

                            assistant_tool_calls.append({
                                "id": tool_call_id,
                                "type": "function",
                                "function": {"name": tool_name, "arguments": tc["arguments"]}
                            })
                            tool_results.append({
                                "role": "tool",
                                "tool_call_id": tool_call_id,
                                "content": str(result)
                            })

                        # 메시지에 tool call 결과 추가
                        current_messages.append({"role": "assistant", "tool_calls": assistant_tool_calls})
                        current_messages.extend(tool_results)

                    if loop_count >= max_tool_loops and not is_success:
                        logger.warning("Max tool execution depth reached.")
                        raise Exception("Max tool execution depth reached.")

                    break  # 성공 시 외부 재시도 루프 탈출

                except Exception as e:
                    last_error = e
                    logger.warning(f"RunPod chat streaming error: {e}")
                    retry_count += 1
                    if retry_count >= max_retries:
                        logger.warning(f"RunPod max retries reached. Switching to Gemini fallback.")
                        use_gemini_fallback = True
                    else:
                        await asyncio.sleep(0.5)

            # --- Gemini 폴백 스트리밍 ---
            if use_gemini_fallback and not is_success:
                try:
                    logger.info(f"Using Gemini fallback for chat stream message_id: {message_id}")
                    from google.genai import types as gemini_types

                    gemini = self._get_gemini_fallback()

                    gemini_contents = []
                    for msg in messages:
                        if msg.sender_type == SenderType.SYSTEM:
                            gemini_contents.append(
                                gemini_types.Content(role="user", parts=[gemini_types.Part.from_text(text=f"[System Background]\n{msg.content}")])
                            )
                        elif msg.sender_type == SenderType.USER:
                            gemini_contents.append(
                                gemini_types.Content(role="user", parts=[gemini_types.Part.from_text(text=msg.content)])
                            )
                        elif msg.sender_type == SenderType.AI:
                            gemini_contents.append(
                                gemini_types.Content(role="model", parts=[gemini_types.Part.from_text(text=msg.content)])
                            )

                    response_stream = await gemini.client.aio.models.generate_content_stream(
                        model="gemini-2.5-flash",
                        contents=gemini_contents,
                        config=gemini_types.GenerateContentConfig(
                            temperature=0.7,
                            system_instruction=dynamic_system_prompt,
                        )
                    )

                    seq = 1
                    async for chunk in response_stream:
                        if chunk.text:
                            is_success = True
                            words = chunk.text.split(' ')
                            for i, word in enumerate(words):
                                text_delta = word + (' ' if i < len(words) - 1 else '')
                                if not text_delta:
                                    continue
                                chunk_event = ChatStreamChunkEvent(
                                    messageId=message_id,
                                    delta=text_delta,
                                    sequence=seq
                                )
                                await queue.put(("chunk", chunk_event.model_dump(by_alias=True)))
                                seq += 1
                                await asyncio.sleep(0.05)

                except Exception as fallback_error:
                    logger.error(f"Gemini fallback also failed: {fallback_error}")
                    last_error = fallback_error

            if not is_success:
                err_event = ChatStreamErrorEvent(
                    messageId=message_id,
                    errorCode="LLM_API_ERROR",
                    message=str(last_error)
                )
                await queue.put(("error", err_event.model_dump(by_alias=True)))
                await queue.put(None)
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
            await queue.put(None)  # 종료 신호


    async def stream(self, report_id: int, message_id: int) -> AsyncGenerator[str, None]:
        """
        GET API 로직: 큐에서 이벤트를 읽어와 SSE로 yield
        """
        session = _active_sessions.get(message_id)
        if not session:
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
                    break

                event_name, data = item
                yield self._format_sse(event_name, data)

                if event_name in ("complete", "error"):
                    break
        finally:
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
            del _active_sessions[message_id]
            return True
        return False


    def _format_sse(self, event: str, data: dict) -> str:
        """SSE 포맷에 맞춰 문자열을 생성하는 헬퍼 함수"""
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
