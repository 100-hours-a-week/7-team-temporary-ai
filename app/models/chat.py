from __future__ import annotations

from enum import Enum
from typing import Annotated, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


BigInt64 = Annotated[
    int,
    Field(
        ge=1,
        le=9_223_372_036_854_775_807,
        description="BIGINT(64-bit) 범위 정수",
        examples=[101],
    ),
]

ChatContent = Annotated[
    str,
    Field(
        min_length=1,
        max_length=8000,
        description="메시지 본문 텍스트(사용자 입력/대화 이력). TEXT는 MARKDOWN으로 취급",
        examples=[
            "다음주에 뭐부터 하면 좋을까?",
            "- 이번 주 요약해줘\n- 핵심만 bullet로",
        ],
    ),
]

class SenderType(str, Enum):
    """
    발신자 타입.
    - USER: 사용자가 입력한 메시지
    - AI: 챗봇(LLM)이 생성한 메시지
    - SYSTEM: 백엔드가 주입하는 시스템 메시지 (예: 주간 레포트 컨텍스트)
    """
    USER = "USER"
    AI = "AI"
    SYSTEM = "SYSTEM"


class MessageType(str, Enum):
    """
    메시지 타입.

    규칙
    - USER: TEXT 또는 FILE 가능
    - AI  : TEXT만 가능(출력은 MARKDOWN)
    """
    TEXT = "TEXT"
    FILE = "FILE"


class StreamStatus(str, Enum):
    """스트림 상태"""
    GENERATING = "GENERATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class ChatHistoryMessage(BaseModel):
    """
    [요청] 대화 이력 메시지 단위(Backend가 Redis/DB에서 구성).
    """
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    message_id: BigInt64 = Field(..., alias="messageId", description="메시지 ID(BIGINT)")
    sender_type: SenderType = Field(..., alias="senderType", description="발신자 타입(USER/AI/SYSTEM)")
    message_type: MessageType = Field(..., alias="messageType", description="메시지 타입(TEXT/FILE)")
    content: ChatContent = Field(..., description="메시지 본문(TEXT=MARKDOWN 권장)")

    @model_validator(mode="after")
    def _validate_sender_message_type(self) -> "ChatHistoryMessage":
        # AI 또는 SYSTEM인 경우 TEXT만 허용
        if self.sender_type in (SenderType.AI, SenderType.SYSTEM) and self.message_type != MessageType.TEXT:
            raise ValueError(f"senderType={self.sender_type.value} 인 경우 messageType은 TEXT만 허용됩니다.")
        return self


class ChatRespondRequest(BaseModel):
    """
    [요청] POST /ai/v2/reports/{reportId}/chat/respond
    """
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    user_id: BigInt64 = Field(..., alias="userId", description="사용자 ID(BIGINT)")
    message_id: BigInt64 = Field(..., alias="messageId", description="AI 응답 메시지 ID(= stream 구독 키)")
    messages: List[ChatHistoryMessage] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="대화 이력. (Backend가 API 3-2로 조회한 레포트 내용을 SYSTEM 메시지로 포함 권장)",
    )

    @model_validator(mode="after")
    def _validate_messages(self) -> "ChatRespondRequest":
        if not self.messages:
            raise ValueError("messages는 1개 이상이어야 합니다.")
        if self.messages[-1].sender_type != SenderType.USER:
            raise ValueError("messages의 마지막 메시지는 senderType=USER여야 합니다.")
        return self


class ChatRespondAckData(BaseModel):
    """
    [응답 data] 생성 세션 식별자.
    """
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    message_id: BigInt64 = Field(..., alias="messageId", description="AI 응답 메시지 ID(= stream 구독 키)")


class ChatRespondAckResponse(BaseModel):
    """
    [응답] POST /ai/v2/reports/{reportId}/chat/respond (즉시 응답)
    """
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    success: bool = Field(..., description="요청 접수 성공 여부", examples=[True])
    process_time: float = Field(..., alias="processTime", description="서버 처리 시간(초)", examples=[0.02])

    data: ChatRespondAckData = Field(..., description="생성 세션 정보(messageId)")


# --- SSE Event Models ---

class ChatStreamStartEvent(BaseModel):
    """
    event: start
    - 스트림 시작 알림(생성 상태 진입)
    """
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    message_id: BigInt64 = Field(..., alias="messageId")
    sender_type: SenderType = Field(SenderType.AI, alias="senderType", description="AI 고정")
    message_type: MessageType = Field(MessageType.TEXT, alias="messageType", description="TEXT(MARKDOWN) 고정")
    status: StreamStatus = Field(StreamStatus.GENERATING, description="GENERATING 고정")


class ChatStreamChunkEvent(BaseModel):
    """
    event: chunk
    - 생성 텍스트 조각(delta)을 순서대로 전달
    """
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    message_id: BigInt64 = Field(..., alias="messageId")
    sender_type: SenderType = Field(SenderType.AI, alias="senderType", description="AI 고정")
    message_type: MessageType = Field(MessageType.TEXT, alias="messageType", description="TEXT(MARKDOWN) 고정")

    delta: str = Field(..., description="MARKDOWN 텍스트 조각")
    sequence: int = Field(..., ge=1, description="chunk 순번(1부터 증가)")


class ChatStreamCompleteEvent(BaseModel):
    """
    event: complete
    - 정상 종료(또는 정책에 따라 취소 종료) 알림
    """
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    message_id: BigInt64 = Field(..., alias="messageId")
    sender_type: SenderType = Field(SenderType.AI, alias="senderType", description="AI 고정")
    message_type: MessageType = Field(MessageType.TEXT, alias="messageType", description="TEXT(MARKDOWN) 고정")

    status: StreamStatus = Field(StreamStatus.COMPLETED, description="COMPLETED (또는 CANCELED)")

    content: Optional[str] = Field(None, description="최종 MARKDOWN 본문(선택)")


class ChatStreamErrorEvent(BaseModel):
    """
    event: error
    - 생성 실패/예외 상황 종료 알림
    """
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    message_id: BigInt64 = Field(..., alias="messageId")
    status: StreamStatus = Field(StreamStatus.FAILED, description="FAILED 고정")
    error_code: str = Field(..., alias="errorCode", description="에러 코드")
    message: str = Field(..., description="에러 메시지")


class ErrorResponse(BaseModel):
    """공통 에러 응답"""
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    status: str = Field(..., description="에러 상태 코드 문자열", examples=["UNAUTHORIZED"])
    message: str = Field(..., description="에러 메시지")
    data: Optional[dict] = Field(None, description="추가 정보(없으면 null)")
