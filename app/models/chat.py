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
    model_config = ConfigDict(
        populate_by_name=True, 
        extra="forbid",
        json_schema_extra={
            "example": {
                "userId": 999999,
                "messageId": 1001,
                "messages": [
                    {
                        "messageId": 1,
                        "senderType": "SYSTEM",
                        "messageType": "TEXT",
                        "content": "# 📅 주간 리포트 (2026-01-25 ~ 2026-02-20)\n\n지난 4주간의 기록을 바탕으로 분석한 주간 레포트입니다. 사용자님은 바쁜 일정 속에서도 전공 역량 강화와 자기계발 사이의 균형을 잡기 위해 꾸준히 노력해 오셨습니다.\n\n---\n\n### 1. 이번 주 요약 (Weekly Summary)\n최근 1주일(2/15~2/20)은 이전 주들에 비해 **실행력이 매우 높았던 시기**였습니다. 특히 2월 중순(2/9~2/14)에 발생했던 일부 미이행 과제(TODO)들을 이번 주에는 대부분 완료(DONE)로 전환하며 밀린 일정들을 성공적으로 소화해냈습니다. \n\n졸업 과제의 핵심인 백엔드 개발과 알고리즘 최적화에 집중하면서도, 기술 블로그 작성과 헬스장 방문 등 루틴을 지키려는 의지가 돋보였습니다. 전반적으로 'AFTERNOON'과 'NIGHT' 시간대의 집중력을 활용해 복잡한 개발 업무를 해결하는 경향을 보였습니다.\n\n---\n\n### 2. 주요 성과 및 일정 분석 (Key Achievements & Schedule Analysis)\n\n#### **🚀 주요 성과**\n*   **졸업 과제 고도화:** '추천 알고리즘 성능 최적화'와 '졸작 백엔드 핵심 API 개발'을 4주 내내 최우선 순위로 두고 진행하셨습니다. 특히 2월 16일부터 18일까지 집중적인 최적화 작업을 통해 프로젝트의 완성도를 높였습니다.\n*   **기술적 성장 기록:** 매주 '기술 블로그 작성(주간 회고)'을 잊지 않고 수행하며, 단순 개발에 그치지 않고 본인의 지식을 정리하는 습관을 유지하고 있습니다.\n*   **철저한 테스트 문화:** '테스트 코드 작성 방어'와 '프론트엔드 API 연동 테스트'를 일정에 배치하여 시스템의 안정성을 확보하려는 노력이 확인됩니다.\n\n#### **📅 일정 패턴 및 변경 이력 분석**\n*   **운동 시간의 고착화:** 헬스장(웨이트 트레이닝) 일정이 거의 매번 **19:30에서 20:00로 변경(MOVE_TIME)**되는 패턴이 관찰됩니다. 이는 저녁 식사 후 휴식 시간이 계획보다 조금 더 필요하거나, 이동 시간에 변수가 있음을 시사합니다.\n*   **집중 시간대 활용:** 주로 'NIGHT' 혹은 'AFTERNOON'에 높은 집중력을 발휘하고 있으며, 실제로 어려운 알고리즘 문제나 논문 수정 작업이 이 시간대에 집중되어 있습니다.\n*   **유연한 위기 대처:** 1월 30일의 급작스러운 면접 제안에 따른 포트폴리오 수정, 2월 7일의 웹소켓 서버 에러 긴급 복구 등 예기치 못한 상황에서도 기존 일정을 조정하며 문제를 해결하는 뛰어난 적응력을 보여주셨습니다.\n\n---\n\n### 3. 다음 주 스케줄링 조언 (Suggestions for Next Week)\n\n*   **운동 시작 시간 현실화:** 헬스장 일정을 처음부터 **20:00**로 설정해 보세요. 4주간의 데이터가 보여주듯, 19:30은 사용자님께 다소 촉박한 시간일 수 있습니다. 처음부터 현실적인 시간을 계획하면 '일정 변경'에 따른 심리적 부담을 줄일 수 있습니다.\n*   **오전 시간대의 'Warm-up' 활용:** 현재 오전 9시부터 11시 사이에 '졸작 백엔드 개발'이나 '알고리즘' 같은 고강도 업무가 배치되어 있습니다. 만약 오전 집중도가 낮게 느껴진다면, 이 시간에는 상대적으로 가벼운 'AI 트렌드 리서치'나 '메일 확인' 등을 배치하고 고강도 업무를 오후 집중 시간대로 옮기는 전략도 고려해 보세요.\n*   **여유 시간(Buffer) 확보:** 2월 6일의 번개 모임이나 2월 7일의 긴급 서버 복구 사례처럼 예상치 못한 이벤트는 언제든 발생할 수 있습니다. 하루 중 1시간 정도는 '예비 시간'으로 비워두어, 돌발 상황이 발생해도 전체 스케줄이 뒤로 밀리지 않도록 관리해 보시길 권장합니다.\n\n사용자님은 이미 충분히 훌륭한 몰입도를 보여주고 계십니다. 다음 주에도 계획하신 목표들을 하나씩 달성해 나가는 즐거움을 누리시길 응원합니다! 🌟"
                    },
                    {
                        "messageId": 2,
                        "senderType": "USER",
                        "messageType": "TEXT",
                        "content": "이 레포트를 바탕으로 다음 주 목표를 하나 추천해줄래?"
                    }
                ]
            }
        }
    )

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
