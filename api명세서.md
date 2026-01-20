## 최종 수정일 : 2026년 1월 15일   
> 수정 이력
> - 26.01.09 AI 플래너 생성 API 명세서 초안 작성 (`who_change`, `is_excluded_Task`, `is_Todolist` 변수명 가칭)  
> - 26.01.11 개인화 AI, 주간 레포트 작성 API 명세서 초안 작성
> - 26.01.12 AI 플래너 생성 API 변수 변경 수정 (`who_change`, `is_excluded_Task`, `is_Todolist`)
> - 26.01.14 챗봇, 실시간 응답 스트림(SSE), 응답 취소 API 명세서 초안 작성  
> - 26.01.15 챗봇, 실시간 응답 스트림(SSE), 응답 취소 API 명세서 구조 수정

## 작성자 : ![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=GitHub&logoColor=white) [max.ji](https://github.com/Max-JI64/)
---

# 목차

> 제출. [API 명세서 문서](#제출-API-명세서) ※중요  
>
> I. [API 엔드포인트 목록](#I-API-엔드포인트-목록)  
>
> II. API 입출력 명세(Pydantic Model)  
> &nbsp;&nbsp;&nbsp;&nbsp;II-1. [AI 플래너 생성 (POST /ai/v1/planners)](#II-1-AI-플래너-생성-POST-aiv1planners)  
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;1) [Enum](#1-Enum-POST-aiv1planners)  
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2) [Request Models](#2-Request-Models-POST-aiv1planners)  
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3) [Response Models](#3-Response-Models-POST-aiv1planners)  
> &nbsp;&nbsp;&nbsp;&nbsp;II-2. [개인화 AI (POST /ai/v1/personalizations/ingest)](#II-2-개인화-AI-POST-aiv1personalizationsingest)  
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;1) [Enum](#1-Enum-POST-aiv1personalizationsingest)  
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2) [Request Models](#2-Request-Models-POST-aiv1personalizationsingest)  
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3) [Response Models](#3-Response-Models-POST-aiv1personalizationsingest)  
> &nbsp;&nbsp;&nbsp;&nbsp;II-3. [주간 레포트 작성 (POST /ai/v2/reports/weekly)](#II-3-주간-레포트-작성-POST-aiv2reportsweekly)    
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;1) [Request Models](#1-Request-Models-POST-aiv2reportsweekly)  
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2) [Response Models](#2-Response-Models-POST-aiv2reportsweekly)  
> &nbsp;&nbsp;&nbsp;&nbsp;II-4-1. [챗봇 (POST /ai/v2/reports/{reportId}/chat/respond)](#ii-4-1-챗봇-post-aiv2reportsreportidchatrespond)  
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;1) [Enum](#1-enum-post-aiv2reportsreportidchatrespond)  
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2) [Request Models](#2-request-models-post-aiv2reportsreportidchatrespond)  
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3) [Response Models](#3-response-models-post-aiv2reportsreportidchatrespond)  
> &nbsp;&nbsp;&nbsp;&nbsp;II-4-2. [실시간 응답 스트림 (GET /ai/v2/reports/{reportId}/chat/respond/{messageId}/stream)](#ii-4-2-실시간-응답-스트림-get-aiv2reportsreportidchatrespondmessageidstream)  
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;0) [공통 타입 / Enum](#0-공통-타입--enum-get-aiv2reportsreportidchatrespondmessageidstream)  
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;1) [SSE 이벤트 페이로드 Models](#1-sse-이벤트-페이로드-models-get-aiv2reportsreportidchatrespondmessageidstream)  
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2) [입출력 명세 Models](#2-입출력-명세-models-get-aiv2reportsreportidchatrespondmessageidstream)  
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3) [에러 응답(HTTP)](#3-에러-응답http-get-aiv2reportsreportidchatrespondmessageidstream)  
> &nbsp;&nbsp;&nbsp;&nbsp;II-4-3. [응답 생성 취소 (DELETE /ai/v2/reports/{reportId}/chat/respond/{messageId}/stream)](#ii-4-3-응답-생성-취소-delete-aiv2reportsreportidchatrespondmessageidstream)  
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;0) [공통 타입 / Enum](#0-공통-타입--enum-delete-aiv2reportsreportidchatrespondmessageidstream)  
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;1) [Request](#1-request-delete-aiv2reportsreportidchatrespondmessageidstream)  
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2) [Response](#2-response-delete-aiv2reportsreportidchatrespondmessageidstream)  
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3) [Error Response Models](#3-error-response-models-delete-aiv2reportsreportidchatrespondmessageidstream)  
> 
> III. API 역할 및 연동 관계  
> &nbsp;&nbsp;&nbsp;&nbsp;III-1. [시스템 아키텍처](#III-1-시스템-아키텍처)  
> &nbsp;&nbsp;&nbsp;&nbsp;III-2. [API별 역할 및 책임](#III-2-API별-역할-및-책임) ※중요  
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;1) [Planner Auto-Scheduling API (POST /ai/v1/planners)](#1-Planner-Auto-Scheduling-API-POST-aiv1planners)  
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2) [Personalization Ingest API (POST /ai/v1/personalizations/ingest)](#2-Personalization-Ingest-API-POST-aiv1personalizationsingest)  
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3) [Weekly Report API (POST /ai/v2/reports/weekly)](#3-Weekly-Report-API-POST-aiv2reportsweekly)  
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4-1) [Chat Respond API (POST /ai/v2/reports/{reportId}/chat/respond)](#4-1-chat-respond-api-post-aiv2reportsreportidchatrespond)  
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4-2) [Chat Stream API (GET /ai/v2/reports/{reportId}/chat/respond/{messageId}/stream)](#4-2-chat-stream-api-get-aiv2reportsreportidchatrespondmessageidstream)  
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4-3) [Chat Stream Cancel API (DELETE /ai/v2/reports/{reportId}/chat/respond/{messageId}/stream)](#4-3-chat-stream-cancel-api-delete-aiv2reportsreportidchatrespondmessageidstream)  
> 
> IV. API 호출 및 응답 예시  
> &nbsp;&nbsp;&nbsp;&nbsp;IV-1. 엔드포인트 : POST /ai/v1/planners    
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;1 ~ 2) [Planners Request Body 구조와 예시](#1-Planners-Request-Body) ※중요  
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 ~ 4) [Planners Response Body (200 OK) 구조와 예시](#3-Planners-Response-Body-200-OK) ※중요   
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5 ~ 9) [Planners Response Body (Error 모음):](#5-Planners-Response-400-Bad-Request)  
> &nbsp;&nbsp;&nbsp;&nbsp;IV-2. 엔드포인트 : POST /ai/v1/personalizations/ingest  
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;1 ~ 2) [Personalizations Request Body 구조와 예시](#1-Personalizations-Request-Body) ※중요  
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 ~ 4) [Personalizations Response Body (200 OK) 구조와 예시](#3-Personalizations-Response-Body-200-OK) ※중요   
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5 ~ 9) [Personalizations Response Body (Error 모음):](#5-Personalizations-Response-400-Bad-Request)  
> &nbsp;&nbsp;&nbsp;&nbsp;IV-3. 엔드포인트 : POST /ai/v2/reports/weekly   
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;1 ~ 2) [Reports Request Body 구조와 예시](#1-Reports-Request-Body) ※중요  
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 ~ 4) [Reports Response Body (200 OK) 구조와 예시](#3-Reports-Response-Body-200-OK) ※중요   
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5 ~ 10) [Reports Response Body (Error 모음):](#5-Reports-Response-400-Bad-Request)  
> &nbsp;&nbsp;&nbsp;&nbsp;IV-4-1. 엔드포인트 : /ai/v2/reports/{reportId}/chat/respond  
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;1 ~ 2) [Chat Respond Request Body 구조와 예시](#1-chat-respond-request-body) ※중요  
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 ~ 4) [Chat Respond Response Body (200 OK) 구조와 예시](#3-chat-respond-response-body-200-ok) ※중요   
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5 ~ 10) [Chat Respond Response Body (Error 모음):](#5-chat-respond-response-400-bad-request)  
> &nbsp;&nbsp;&nbsp;&nbsp;IV-4-2. 엔드포인트 : GET /ai/v2/reports/{reportId}/chat/respond/{messageId}/stream  
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;1 ~ 2) [Chat Stream Request Body 구조와 예시](#1-chat-stream-request-body) ※중요  
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 ~ 4) [Chat Stream Response Body (200 OK) 구조와 예시](#3-chat-stream-response-body-200-ok) ※중요   
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5 ~ 10) [Chat Stream Response Body (Error 모음):](#5-chat-stream-response-400-bad-request)  
> &nbsp;&nbsp;&nbsp;&nbsp;IV-4-3. 엔드포인트 : DELETE /ai/v2/reports/{reportId}/chat/respond/{messageId}/stream  
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;1 ~ 2) [Chat Stream Cancel Request Body 구조와 예시](#1-chat-stream-cancel-request-body) ※중요  
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 ~ 4) [Chat Stream Cancel Response (204 No Content) — 성공](#3-chat-stream-cancel-response-204-no-content--성공) ※중요   
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5 ~ 9) [Chat Stream Cancel Response (Error 모음):](#5-chat-stream-cancel-response-401-unauthorized)  



> &nbsp;&nbsp;&nbsp;&nbsp;IV-5. API별 Status Code 리스트 ※중요  
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;1) [FUNCTION_NAME 리스트](#1-FUNCTION_NAME-리스트) ※중요   
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2) [PLANNER_GENERATE의 Status Code](#2-PLANNER_GENERATE의-Status-Code)  
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3) [PLANNER_GENERATE의 Status Code](#3-PERSONALIZATION_INGEST의-Status-Code)  
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4) [PLANNER_GENERATE의 Status Code](#4-WEEKLY_REPORT의-Status-Code)  
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5) [CHAT_RESPOND의 Status Code](#5-chat_respond의-status-code)  
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6) [CHAT_STREAM의 Status Code](#6-chat_stream의-status-code)  
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7) [CHAT_CANCEL의 Status Code](#7-chat_cancel의-status-code)  
> 
>
> 부록. [서비스 관점의 필요성](#부록-서비스-관점의-필요성)  

---

# 제출. API 명세서
### **↑** [목차로 돌아가기](#목차)

- https://docs.google.com/spreadsheets/d/1A5t_iNQ0oLMcExzv5E8xVIkFPS9RHNo-5nr7BGNHFfA/edit?gid=1878554884#gid=1878554884

---

# I. API 엔드포인트 목록
### **↑** [목차로 돌아가기](#목차)

번호 | HTTP Method | 엔드포인트 | 기능 설명
-- | -- | -- | --
1 | POST | /ai/v1/planners | AI 플래너 생성
2 | POST | /ai/v1/personalizations/ingest | 개인화 AI
3 | POST | /ai/v2/reports/weekly | 주간 레포트 작성
4-1 | POST | /ai/v2/reports/{reportId}/chat/respond | 챗봇
4-2 | GET  | /ai/v2/reports/{reportId}/chat/respond/{messageId}/stream | 실시간 응답 스트림
4-3 | DELETE | /ai/v2/reports/{reportId}/chat/respond/{messageId}/stream | 응답 생성 취소

## I-1. AI 플래너 생성
- 백엔드가 보낸 Todo list + 사용자 프로필 + 배치 기준 시간을 받아 플래너 배정 결과 생성
- 결과로 배정된 Task 리스트(시간 포함) 반환

## I-2. 개인화 AI
- 백엔드가 주기적으로 보내는 완료 플래너 + 수정이력을 수신
- 매주 일요일 밤 10시에 이전주 일요일부터 어제자 토요일까지의 모든 플래너 데이터를 AI 서버로 전송
- 이것을 AI DB에 저장 후 완료 메세지 송출

## I-3. 주간 레포트 작성
- 백엔드 트리거(매주 월요일 0시 20분)로 실행
- 과거 데이터 기반 레포트 생성(LLM)
- 결과 레포트 반환(챗봇 대화내역에 삽입해야함)

## I-4-1. 챗봇
- 백엔드가 reportId 대화창에서의 이번 사용자 입력 + (필요 시) 최근 대화 이력(messages[]) + messageId를 AI 서버로 전달해 응답 생성을 시작한다
- AI 서버는 요청을 접수하고, 이후 스트리밍 구독에 사용할 messageId를 기준으로 생성 세션을 준비한다
- 응답은 항상 MARKDOWN 형식이다

## I-4-2. 실시간 응답 스트림
- 백엔드가 messageId를 구독 키로 SSE 연결을 열어, AI가 생성하는 답변을 chunk 단위로 실시간 스트리밍으로 수신한다
- AI 서버는 start → chunk → complete/error 이벤트 흐름으로 MARKDOWN(TEXT) 응답을 전송한다

## I-4-3. 응답 생성 취소
- 진행 중인 messageId 생성 세션을 취소하고 스트리밍을 종료한다
- AI 서버는 내부 상태를 CANCELED로 전환하고, 열린 스트림이 있으면 취소 종료 이벤트를 보내 마무리한다


# II. API 입출력 명세(Pydantic Model)

## II-1. AI 플래너 생성 (POST /ai/v1/planners)
### **↑** [목차로 돌아가기](#목차)

>공통 타입: API에서 시간은 항상 "HH:MM" 문자열로 주고받는다  
>(DB 저장 포맷(DATETIME 등)은 백엔드가 알아서 처리)

```python
from __future__ import annotations

from enum import Enum
from typing import Annotated, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


TimeHHMM = Annotated[
    str,
    Field(
        pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$",
        description="24시간제 HH:MM 형식",
        examples=["09:00", "18:30", "23:59"],
    ),
]

BigInt64 = Annotated[
    int,
    Field(
        ge=1,
        le=9_223_372_036_854_775_807,  # signed BIGINT max
        description="BIGINT(64-bit) 범위 정수",
        examples=[123456789],
    ),
]


def _hhmm_to_minutes(t: str) -> int:
    hh, mm = t.split(":")
    return int(hh) * 60 + int(mm)

```

### 1) Enum (POST /ai/v1/planners)
### **↑** [목차로 돌아가기](#목차)

```python
class FocusTimeZone(str, Enum):
    """
    사용자 몰입 가능 시간대.

    - Backend가 Users.focusTimeZone 값을 그대로 전달.
    - AI는 몰입 시간대에 '집중/중요 작업'을 우선 배치하는 등 배치 전략에 활용.
    """
    MORNING = "MORNING"
    AFTERNOON = "AFTERNOON"
    EVENING = "EVENING"
    NIGHT = "NIGHT"


class TaskType(str, Enum):
    """
    일정(Task)의 타입.

    - FIXED: 사용자가 startAt/endAt을 확정한 고정 일정(시간 변경 대상 아님)
    - FLEX : 시간이 미정이거나(또는 재배치가 필요한) 유동 일정(AI가 시간 배치)
    """
    FIXED = "FIXED"
    FLEX = "FLEX"


class EstimatedTimeRange(str, Enum):
    """
    FLEX 작업 배치에 사용하는 예상 소요 시간 구간(Enum).

    - 실제 분(minute) 숫자 대신 구간값으로 전달받아 배치 로직에 사용.
    """
    MINUTE_UNDER_30 = "MINUTE_UNDER_30"
    MINUTE_30_TO_60 = "MINUTE_30_TO_60"
    HOUR_1_TO_2 = "HOUR_1_TO_2"
    HOUR_2_TO_4 = "HOUR_2_TO_4"
    HOUR_OVER_4 = "HOUR_OVER_4"


class AssignedBy(str, Enum):
    """
    배치/수정 주체(기존 whoChange를 assignedBy로 변경).

    이 API의 출력 규칙(고정):
    - type=FIXED -> USER
    - type=FLEX  -> AI
    """
    USER = "USER"
    AI = "AI"


class AssignmentStatus(str, Enum):
    """
    배치 상태(기존 is_excluded_Task / is_Todolist를 통합).

    - NOT_ASSIGNED: 배치되지 않음(= Todo list에 존재)
    - ASSIGNED: 플래너에 배치됨
    - EXCLUDED: 제외 리스트에 배치됨
    """
    NOT_ASSIGNED = "NOT_ASSIGNED"
    ASSIGNED = "ASSIGNED"
    EXCLUDED = "EXCLUDED"

```

### 2) Request Models (POST /ai/v1/planners)
### **↑** [목차로 돌아가기](#목차)

```python
class PlannerUserContext(BaseModel):
    """
    [요청] 사용자 컨텍스트(Users 기반) — 요청 최상위에서 user 객체로 래핑됨.

    목적
    - 배치 로직에 필요한 사용자 설정값을 'user' 객체로 묶어 전달한다.

    필드
    - userId: Users.User_id (BIGINT)
    - focusTimeZone: Users.focusTimeZone
    - dayEndTime: Users.dayEndTime을 Backend가 HH:MM로 변환해 전달
    """
    model_config = ConfigDict(populate_by_name=True)

    user_id: BigInt64 = Field(..., alias="userId", description="Users.User_id(BIGINT)")
    focus_time_zone: FocusTimeZone = Field(..., alias="focusTimeZone", description="몰입 시간대")
    day_end_time: TimeHHMM = Field(..., alias="dayEndTime", description="하루 마무리 시간(HH:MM)")
```

```python
class PlannerScheduleInput(BaseModel):
    """
    [요청] 배치 대상 작업(Schedule 기반, dayPlanId의 전체 작업).

    목적
    - Backend가 해당 dayPlanId의 모든 작업(FIXED + FLEX)을 AI로 전달한다.
    - AI는 FIXED는 유지하고, FLEX는 배치/제외를 결정한다.

    필드
    - taskId/dayPlanId: Schedule PK/그룹 키(BIGINT)
    - title: 작업 제목(배치/분류/우선순위 결정 등에서 사용할 수 있음)
    - type: FIXED / FLEX
    - startAt/endAt:
        * FIXED는 필수(HH:MM)
        * FLEX는 null 허용(배치 전 미정)
    - estimatedTimeRange/focusLevel/isUrgent:
        * 주로 FLEX 배치에 활용
        * FIXED는 null이어도 됨
    """
    model_config = ConfigDict(populate_by_name=True)

    task_id: BigInt64 = Field(..., alias="taskId", description="Schedule.Task_id(BIGINT)")

    parent_schedule_id: Optional[BigInt64] = Field(
        None, 
        alias="parentScheduleId", 
        description="상위 작업 ID(부모 Schedule ID). 없으면 null"
    )

    day_plan_id: BigInt64 = Field(..., alias="dayPlanId", description="Schedule.dayPlanId(BIGINT)")

    title: str = Field(..., max_length=60, description="작업 제목", examples=["통계학 실습 과제"])
    type: TaskType = Field(..., description="작업 타입(FIXED/FLEX)")

    start_at: Optional[TimeHHMM] = Field(None, alias="startAt", description="시작 시간(HH:MM)")
    end_at: Optional[TimeHHMM] = Field(None, alias="endAt", description="종료 시간(HH:MM)")

    estimated_time_range: Optional[EstimatedTimeRange] = Field(
        None, alias="estimatedTimeRange", description="예상 소요 시간 구간"
    )
    focus_level: Optional[int] = Field(
        None, alias="focusLevel", ge=1, le=10, description="몰입도(1~10)"
    )
    is_urgent: Optional[bool] = Field(None, alias="isUrgent", description="급해요 여부")

    @model_validator(mode="after")
    def _validate_time_rules(self) -> "PlannerScheduleInput":
        # FIXED는 startAt/endAt 필수
        if self.type == TaskType.FIXED:
            if self.start_at is None or self.end_at is None:
                raise ValueError("type=FIXED 인 경우 startAt/endAt은 필수입니다.")
            if _hhmm_to_minutes(self.end_at) <= _hhmm_to_minutes(self.start_at):
                raise ValueError("FIXED 작업은 endAt이 startAt보다 뒤여야 합니다.")

        # FLEX는 null 허용(배치 전)
        if self.type == TaskType.FLEX:
            # FLEX에 시간이 들어오는 경우(재배치 시나리오)도 허용할지 정책 선택 가능.
            # 현재는 들어오면 형식/순서만 검증하도록 처리.
            if (self.start_at is None) != (self.end_at is None):
                raise ValueError("FLEX 작업은 startAt/endAt이 둘 다 null이거나, 둘 다 값이 있어야 합니다.")
            if self.start_at and self.end_at:
                if _hhmm_to_minutes(self.end_at) <= _hhmm_to_minutes(self.start_at):
                    raise ValueError("FLEX 작업의 endAt은 startAt보다 뒤여야 합니다.")

        return self

```

```python
class PlannerGenerateRequest(BaseModel):
    """
    [요청] POST /ai/v1/planners Request Body.

    변경사항(요구 반영)
    - userId/focusTimeZone/dayEndTime을 최상위에서 제거하고,
      user 객체로 래핑하여 전달한다.

    구성
    - user: 사용자 설정(Users 기반)
    - startArrange: '배치하기' 버튼 클릭 시각(HH:MM)
    - schedules: dayPlanId의 전체 작업 목록(Schedule 기반)
    """
    model_config = ConfigDict(populate_by_name=True)

    user: PlannerUserContext = Field(..., description="사용자 컨텍스트(Users 기반)")
    start_arrange: TimeHHMM = Field(..., alias="startArrange", description="배치하기 버튼 클릭 시각(HH:MM)")
    schedules: List[PlannerScheduleInput] = Field(..., description="배치 대상 작업 목록(Schedule 기반)")
```

### 3) Response Models (POST /ai/v1/planners)
### **↑** [목차로 돌아가기](#목차)

```python
class PlannerScheduleResult(BaseModel):
    """
    [응답] 작업별 배치 결과.

    규칙(요구 반영)
    - title은 반환하지 않음
    - assignedBy(기존 whoChange):
        * FIXED -> USER
        * FLEX  -> AI
    - assignmentStatus:
        * ASSIGNED: 플래너에 배치됨(startAt/endAt 필수)
        * EXCLUDED or NOT_ASSIGNED: startAt/endAt은 null 가능(정책상 null 권장)
    """
    model_config = ConfigDict(populate_by_name=True)

    task_id: BigInt64 = Field(..., alias="taskId", description="Schedule.Task_id(BIGINT)")
    day_plan_id: BigInt64 = Field(..., alias="dayPlanId", description="Schedule.dayPlanId(BIGINT)")

    type: TaskType = Field(..., description="작업 타입(FIXED/FLEX)")
    assigned_by: AssignedBy = Field(..., alias="assignedBy", description="배치/수정 주체(FIXED=USER, FLEX=AI)")
    assignment_status: AssignmentStatus = Field(..., alias="assignmentStatus", description="배치 상태")

    start_at: Optional[TimeHHMM] = Field(None, alias="startAt", description="시작 시간(HH:MM)")
    end_at: Optional[TimeHHMM] = Field(None, alias="endAt", description="종료 시간(HH:MM)")

    @model_validator(mode="after")
    def _validate_result_rules(self) -> "PlannerScheduleResult":
        # assignedBy 규칙 강제
        if self.type == TaskType.FIXED and self.assigned_by != AssignedBy.USER:
            raise ValueError("type=FIXED 인 경우 assignedBy는 USER여야 합니다.")
        if self.type == TaskType.FLEX and self.assigned_by != AssignedBy.AI:
            raise ValueError("type=FLEX 인 경우 assignedBy는 AI여야 합니다.")

        # assignmentStatus에 따른 시간 규칙
        if self.assignment_status == AssignmentStatus.ASSIGNED:
            if self.start_at is None or self.end_at is None:
                raise ValueError("assignmentStatus=ASSIGNED 인 경우 startAt/endAt은 필수입니다.")
            if _hhmm_to_minutes(self.end_at) <= _hhmm_to_minutes(self.start_at):
                raise ValueError("endAt은 startAt보다 뒤여야 합니다.")
        else:
            # NOT_ASSIGNED / EXCLUDED는 시간 미지정(null) 권장
            # (정책상 시간을 보내고 싶다면 여기 규칙을 완화하면 됨)
            if self.start_at is not None or self.end_at is not None:
                raise ValueError("assignmentStatus가 ASSIGNED가 아니면 startAt/endAt은 null이어야 합니다.")

        return self
```

```python
class PlannerGenerateResponse(BaseModel):
    """
    [응답] POST /ai/v1/planners Response Body.

    - success/processTime: 공통 응답
    - userId: 결과가 어느 사용자 요청인지 매칭용(요청의 user.userId를 그대로 반환)
    - results: 작업별 배치 결과 목록
    - totalCount: 결과 개수
    """
    model_config = ConfigDict(populate_by_name=True)

    success: bool = Field(..., description="배치 생성 성공 여부", example=True)
    process_time: float = Field(..., alias="processTime", description="서버 처리 시간(초)", example=1.25)

    user_id: BigInt64 = Field(..., alias="userId", description="요청 사용자 ID(BIGINT)")
    results: List[PlannerScheduleResult] = Field(..., description="작업별 배치 결과 목록")
    total_count: int = Field(..., alias="totalCount", ge=0, description="결과 개수")
```
## II-2. 개인화 AI (POST /ai/v1/personalizations/ingest)
### **↑** [목차로 돌아가기](#목차)

>공통 타입: API에서 시간은 항상 "HH:MM" 문자열로 주고받는다  
>(DB 저장 포맷(DATETIME 등)은 백엔드가 알아서 처리)
```python
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

TimeHHMM = Annotated[
    str,
    Field(
        pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$",
        description="24시간제 HH:MM 형식",
        examples=["09:30", "18:00", "23:59"],
    ),
]


def _hhmm_to_minutes(t: str) -> int:
    hh, mm = t.split(":")
    return int(hh) * 60 + int(mm)
```

### 1) Enum (POST /ai/v1/personalizations/ingest)
### **↑** [목차로 돌아가기](#목차)

```python
class Gender(str, Enum):
    """
    Users.gender를 API 계약으로 제한하기 위한 Enum.

    - DB는 VARCHAR일 수 있으나, 모델 학습/개인화 파라미터 생성 시 일관성을 위해 제한.
    - 서비스 정책에 따라 OTHER 등을 확장 가능.
    """
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"


class FocusTimeZone(str, Enum):
    """
    Users.focusTimeZone(사용자 몰입 가능 시간대).

    개인화에서의 활용 예:
    - 몰입 시간대에 배치된 작업의 완료율/연장 빈도 기반 선호 가중치 업데이트
    """
    MORNING = "MORNING"
    AFTERNOON = "AFTERNOON"
    EVENING = "EVENING"
    NIGHT = "NIGHT"


class ScheduleStatus(str, Enum):
    """
    Schedule.status(일정 완료 상태).
    - TODO: 미완료
    - DONE: 완료 처리됨
    """
    TODO = "TODO"
    DONE = "DONE"


class TaskType(str, Enum):
    """
    Schedule.type(일정 타입).
    - FIXED: 사용자 고정 시간
    - FLEX : AI 배치 대상
    """
    FIXED = "FIXED"
    FLEX = "FLEX"


class AssignedBy(str, Enum):
    """
    Schedule.assignedBy(배치/할당 주체).

    기본 규칙(플래너 생성 API와 동일):
    - type=FIXED -> USER
    - type=FLEX  -> AI
    """
    USER = "USER"
    AI = "AI"


class AssignmentStatus(str, Enum):
    """
    Schedule.assignmentStatus(배치 상태 통합 값).

    - NOT_ASSIGNED: 배치되지 않음(= Todo에 존재)
    - ASSIGNED: 플래너에 배치됨
    - EXCLUDED: 제외 리스트로 이동
    """
    NOT_ASSIGNED = "NOT_ASSIGNED"
    ASSIGNED = "ASSIGNED"
    EXCLUDED = "EXCLUDED"


class EstimatedTimeRange(str, Enum):
    """
    Schedule.estimatedTimeRange(예상 소요 시간 구간).

    개인화에서의 활용 예:
    - 사용자 실제 수정(CHANGE_DURATION) 패턴과 결합해 '예상시간 보정' 파라미터 생성
    """
    MINUTE_UNDER_30 = "MINUTE_UNDER_30"
    MINUTE_30_TO_60 = "MINUTE_30_TO_60"
    HOUR_1_TO_2 = "HOUR_1_TO_2"
    HOUR_2_TO_4 = "HOUR_2_TO_4"
    HOUR_OVER_4 = "HOUR_OVER_4"


class ScheduleHistoryEventType(str, Enum):
    """
    ScheduleHistory.eventType(사용자 편집 이벤트 타입).

    - ASSIGN_TIME: 시간 배치 확정(예: null -> 13:00~14:00)
    - MOVE_TIME: 시간대 이동(예: 13:00~14:00 -> 14:00~15:00)
    - CHANGE_DURATION: 길이 변경(예: 13:00~14:00 -> 13:00~15:00)
    """
    ASSIGN_TIME = "ASSIGN_TIME"
    MOVE_TIME = "MOVE_TIME"
    CHANGE_DURATION = "CHANGE_DURATION"
```


### 2) Request Models (POST /ai/v1/personalizations/ingest)
### **↑** [목차로 돌아가기](#목차)
```python
class PersonalizationUserInput(BaseModel):
    """
    [요청] Users 테이블 기반 사용자 정보.

    목적
    - 개인화 파라미터 생성의 '기본 사용자 컨텍스트' 입력.

    필드 설명
    - userId: Users.User_id
    - gender: Users.gender
    - age: 백엔드가 birth 등을 가공하여 정수로 제공
    - focusTimeZone: Users.focusTimeZone
    - dayEndTime: Users.dayEndTime을 백엔드가 HH:MM으로 변환하여 제공
    """
    model_config = ConfigDict(populate_by_name=True)

    user_id: int = Field(..., alias="userId", description="Users.User_id", example=123456789)
    gender: Gender = Field(..., description="Users.gender", example="MALE")
    age: int = Field(..., ge=0, le=130, description="나이(정수, 백엔드 가공)", example=26)
    focus_time_zone: FocusTimeZone = Field(..., alias="focusTimeZone", description="몰입 시간대", example="EVENING")
    day_end_time: TimeHHMM = Field(..., alias="dayEndTime", description="하루 마무리 시간(HH:MM)", example="23:00")

```
```python
class ScheduleIngestItem(BaseModel):
    """
    [요청] Schedule 테이블 기반 작업(일정) 데이터.

    목적
    - 해당 날짜 플래너에서 각 작업이 어떤 상태로 종료되었는지(DONE/TODO)
    - 배치 상태가 어땠는지(ASSIGNED/EXCLUDED/NOT_ASSIGNED)
    - 작업 특성(예상시간/몰입도/급함)을 포함하여 개인화 파라미터를 갱신한다.

    시간 규칙
    - assignmentStatus=ASSIGNED -> startAt/endAt(HH:MM) 필수
    - NOT_ASSIGNED/EXCLUDED -> startAt/endAt은 null
    """
    model_config = ConfigDict(populate_by_name=True)

    task_id: int = Field(..., alias="taskId", description="Schedule.Task_id", example=1)
    day_plan_id: int = Field(..., alias="dayPlanId", description="Schedule.dayPlanId", example=101)

    title: str = Field(..., max_length=60, description="작업 제목(개인화 학습에 사용)", example="통계학 실습 과제")
    status: ScheduleStatus = Field(..., description="완료 상태", example="DONE")
    type: TaskType = Field(..., description="작업 타입", example="FLEX")

    assigned_by: AssignedBy = Field(..., alias="assignedBy", description="배치 주체", example="AI")
    assignment_status: AssignmentStatus = Field(..., alias="assignmentStatus", description="배치 상태", example="ASSIGNED")

    start_at: Optional[TimeHHMM] = Field(
        None, alias="startAt", description="시작 시간(HH:MM). ASSIGNED면 필수", example="21:15"
    )
    end_at: Optional[TimeHHMM] = Field(
        None, alias="endAt", description="종료 시간(HH:MM). ASSIGNED면 필수", example="22:45"
    )

    estimated_time_range: Optional[EstimatedTimeRange] = Field(
        None, alias="estimatedTimeRange", description="예상 소요 시간 구간", example="HOUR_1_TO_2"
    )
    focus_level: Optional[int] = Field(
        None, alias="focusLevel", ge=1, le=10, description="몰입도(1~10)", example=8
    )
    is_urgent: Optional[bool] = Field(None, alias="isUrgent", description="급해요 여부", example=True)

    @model_validator(mode="after")
    def _validate_rules(self) -> "ScheduleIngestItem":
        # type 기반 assignedBy 기본 규칙
        if self.type == TaskType.FIXED and self.assigned_by != AssignedBy.USER:
            raise ValueError("type=FIXED 인 경우 assignedBy는 USER여야 합니다.")
        if self.type == TaskType.FLEX and self.assigned_by != AssignedBy.AI:
            raise ValueError("type=FLEX 인 경우 assignedBy는 AI여야 합니다.")

        # assignmentStatus 기반 시간 규칙
        if self.assignment_status == AssignmentStatus.ASSIGNED:
            if self.start_at is None or self.end_at is None:
                raise ValueError("assignmentStatus=ASSIGNED 인 경우 startAt/endAt은 필수입니다.")
            if _hhmm_to_minutes(self.end_at) <= _hhmm_to_minutes(self.start_at):
                raise ValueError("endAt은 startAt보다 뒤여야 합니다.")
        else:
            if self.start_at is not None or self.end_at is not None:
                raise ValueError("assignmentStatus가 ASSIGNED가 아닌 경우 startAt/endAt은 null이어야 합니다.")

        return self
```
```python
class ScheduleHistoryIngestItem(BaseModel):
    """
    [요청] ScheduleHistory 테이블 기반 변경 이력 데이터.

    핵심 포인트
    - createdAt(DATETIME(6))를 포함한다.
    - 하나의 작업(taskId)에 대해 수정이 여러 번 발생한 경우,
      AI는 createdAt을 기준으로 정렬하여 '수정 시퀀스'를 재구성한다.

    필드 설명
    - scheduleId: ScheduleHistory.scheduleId (= Schedule.taskId)
    - eventType: ASSIGN_TIME / MOVE_TIME / CHANGE_DURATION
    - prevStartAt/prevEndAt/newStartAt/newEndAt: HH:MM (단, ASSIGN_TIME의 prev는 null 가능)
    - createdAt: DATETIME(6) (예: "2026-01-10T21:40:15.123456")
      * 백엔드가 DB의 DATETIME(6)을 ISO 8601로 변환하여 전달
    """
    model_config = ConfigDict(populate_by_name=True)

    schedule_id: int = Field(..., alias="scheduleId", description="ScheduleHistory.scheduleId (= taskId)", example=2)
    event_type: ScheduleHistoryEventType = Field(..., alias="eventType", description="이벤트 타입", example="MOVE_TIME")

    prev_start_at: Optional[TimeHHMM] = Field(None, alias="prevStartAt", description="변경 전 시작(HH:MM)", example="20:30")
    prev_end_at: Optional[TimeHHMM] = Field(None, alias="prevEndAt", description="변경 전 종료(HH:MM)", example="22:00")

    new_start_at: Optional[TimeHHMM] = Field(None, alias="newStartAt", description="변경 후 시작(HH:MM)", example="21:15")
    new_end_at: Optional[TimeHHMM] = Field(None, alias="newEndAt", description="변경 후 종료(HH:MM)", example="22:45")

    created_at: datetime = Field(
        ...,
        alias="createdAt",
        description="이벤트 발생 시각(DATETIME(6) -> ISO 8601). 수정 시퀀스 정렬에 사용",
        examples=["2026-01-10T21:40:15.123456"],
    )

    @model_validator(mode="after")
    def _validate_history(self) -> "ScheduleHistoryIngestItem":
        # new 값은 원칙적으로 필수(변경 결과)
        if self.new_start_at is None or self.new_end_at is None:
            raise ValueError("newStartAt/newEndAt은 필수입니다.")
        if _hhmm_to_minutes(self.new_end_at) <= _hhmm_to_minutes(self.new_start_at):
            raise ValueError("newEndAt은 newStartAt보다 뒤여야 합니다.")

        # MOVE_TIME / CHANGE_DURATION은 prev도 필수
        if self.event_type in (ScheduleHistoryEventType.MOVE_TIME, ScheduleHistoryEventType.CHANGE_DURATION):
            if self.prev_start_at is None or self.prev_end_at is None:
                raise ValueError("MOVE_TIME/CHANGE_DURATION 인 경우 prevStartAt/prevEndAt이 필요합니다.")
            if _hhmm_to_minutes(self.prev_end_at) <= _hhmm_to_minutes(self.prev_start_at):
                raise ValueError("prevEndAt은 prevStartAt보다 뒤여야 합니다.")

        # ASSIGN_TIME은 prev가 null일 수 있음(최초 배치)
        return self
```
```python
class PersonalizationIngestRequest(BaseModel):
    """
    [요청] POST /ai/v1/personalizations/ingest Request Body.

    목적
    - 플래너 종료 48시간 후, Backend가 수집 데이터를 한 번에 전달한다.
    - AI 서버는 이를 기반으로 개인화 파라미터를 생성해 AI DB에 저장한다.

    구성
    - user: Users 기반 사용자 정보(가공 포함: age)
    - schedules: Schedule 기반 해당 날짜 작업 목록
    - scheduleHistories: ScheduleHistory 기반 변경 이력(정렬 키: createdAt)
    """
    model_config = ConfigDict(populate_by_name=True)

    user: PersonalizationUserInput = Field(..., description="Users 기반 사용자 정보")
    schedules: List[ScheduleIngestItem] = Field(default_factory=list, description="Schedule 기반 작업 목록")
    schedule_histories: List[ScheduleHistoryIngestItem] = Field(
        default_factory=list,
        alias="scheduleHistories",
        description="ScheduleHistory 기반 변경 이력 목록(createdAt으로 정렬 가능)",
    )
```

### 3) Response Models (POST /ai/v1/personalizations/ingest)
### **↑** [목차로 돌아가기](#목차)
```python
class PersonalizationIngestResponse(BaseModel):
    """
    [응답] 저장 결과만 반환(요구사항).

    - success: AI DB 저장 성공 여부
    - processTime: 처리 시간(초)
    - message: 결과 메시지(예: '저장 성공')
    """
    model_config = ConfigDict(populate_by_name=True)

    success: bool = Field(..., description="저장 성공 여부", example=True)
    process_time: float = Field(..., alias="processTime", description="서버 처리 시간(초)", example=0.84)
    message: str = Field(..., description="결과 메시지", example="저장 성공")
```

## II-3. 주간 레포트 작성 (POST /ai/v2/reports/weekly)
### **↑** [목차로 돌아가기](#목차)
> 공통 타입: ISO 8601 datetime
```python
from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

ISO8601DateTime = Annotated[
    datetime,
    Field(
        description="ISO 8601 datetime (timezone 포함 권장). 예: 2026-01-12T00:20:00+09:00",
        examples=["2026-01-12T00:20:00+09:00", "2026-01-12T00:20:00.123456+09:00"],
    ),
]

BigInt64 = Annotated[
    int,
    Field(
        ge=1,
        le=9_223_372_036_854_775_807,  # signed BIGINT max
        description="BIGINT(64-bit) 범위 정수",
        examples=[1000000000001],
    ),
]
```

### 1) Request Models (POST /ai/v2/reports/weekly)
### **↑** [목차로 돌아가기](#목차)
```python
class WeeklyReportGenerateRequest(BaseModel):
    """
    [요청] POST /ai/v2/reports/weekly

    입력
    - baseTime(ISO 8601): 기준 시간(월요일이라고 가정). AI는 이 값을 기준으로 과거 1주 데이터를 조회.
    - reportId(BIGINT): 레포트 식별자(백엔드 발급)
    - userId(BIGINT): 대상 사용자 식별자

    처리
    - AI 서버는 /ai/v1/personalizations/ingest로 누적된 내부 데이터를 사용해 레포트를 생성한다.
    """
    model_config = ConfigDict(populate_by_name=True)

    report_id: BigInt64 = Field(..., alias="reportId", description="레포트 ID(BIGINT)")
    user_id: BigInt64 = Field(..., alias="userId", description="Users.User_id(BIGINT)")

    base_time: ISO8601DateTime = Field(..., alias="baseTime", description="기준 시각(월요일 가정)")

    @model_validator(mode="after")
    def _validate_base_time_is_monday(self) -> "WeeklyReportGenerateRequest":
        # 월요일(Monday=0). '가정'을 계약으로 강제하고 싶으면 유지, 아니면 삭제 가능.
        if self.base_time.weekday() != 0:
            raise ValueError("baseTime은 월요일이어야 합니다(주간 레포트 기준 시각).")
        return self
```

### 2) Response Models (POST /ai/v2/reports/weekly)
### **↑** [목차로 돌아가기](#목차)
```python
class WeeklyReportGenerateResponse(BaseModel):
    """
    [응답] POST /ai/v2/reports/weekly

    출력
    - reportId(BIGINT): 요청과 동일한 레포트 ID
    - content(VARCHAR(3000)): 생성된 레포트 본문(최대 3000자)
      - 형태는 MARKDOWN 고정
    - sendAt(ISO 8601): 백엔드로 전달(발송) 시각
    """
    model_config = ConfigDict(populate_by_name=True)

    success: bool = Field(..., description="레포트 생성 및 전달 성공 여부", example=True)
    process_time: float = Field(..., alias="processTime", description="서버 처리 시간(초)", example=2.41)

    report_id: BigInt64 = Field(..., alias="reportId", description="레포트 ID(BIGINT)")
    content: str = Field(
        ...,
        max_length=3000,
        description="주간 레포트 본문(VARCHAR(3000))",
        examples=["# 1월 2주차 주간 레포트\n\n- 완료율: 72%\n- ..."],
    )
    send_at: ISO8601DateTime = Field(..., alias="sendAt", description="발송 시각(ISO 8601)")
```

## II-4-1. 챗봇 (POST ai/v2/reports/{reportId}/chat/respond)
### **↑** [목차로 돌아가기](#목차)
> - messageType=TEXT인 경우 content는 MARKDOWN 문자열로 취급한다.
> - 이 API는 **응답 생성 시작(접수)**만 담당하며, 실제 생성 결과는 SSE 스트림에서 전달한다.

```python
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

```

### 1) Enum (POST /ai/v2/reports/{reportId}/chat/respond)
### **↑** [목차로 돌아가기](#목차)
```python
cclass SenderType(str, Enum):
    """
    발신자 타입.
    - USER: 사용자가 입력한 메시지
    - AI: 챗봇(LLM)이 생성한 메시지
    """
    USER = "USER"
    AI = "AI"


class MessageType(str, Enum):
    """
    메시지 타입.

    규칙
    - USER: TEXT 또는 FILE 가능
    - AI  : TEXT만 가능(출력은 MARKDOWN)
    """
    TEXT = "TEXT"
    FILE = "FILE"

```

### 2) Request Models (POST /ai/v2/reports/{reportId}/chat/respond)
### **↑** [목차로 돌아가기](#목차)

```python
class ChatHistoryMessage(BaseModel):
    """
    [요청] 대화 이력 메시지 단위(Backend가 Redis/DB에서 구성).

    - messageId: 메시지 식별자(BIGINT)
    - senderType: USER/AI
    - messageType:
        * senderType=USER -> TEXT/FILE 가능
        * senderType=AI   -> TEXT만 가능(= MARKDOWN)
    - content:
        * TEXT: MARKDOWN 문자열(권장)
        * FILE: 파일 자체가 아니라, AI가 이해 가능한 '설명/요약/추출 텍스트'를 담는 것을 권장
    """
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    message_id: BigInt64 = Field(..., alias="messageId", description="메시지 ID(BIGINT)")
    sender_type: SenderType = Field(..., alias="senderType", description="발신자 타입(USER/AI)")
    message_type: MessageType = Field(..., alias="messageType", description="메시지 타입(TEXT/FILE)")
    content: ChatContent = Field(..., description="메시지 본문(TEXT=MARKDOWN 권장)")

    @model_validator(mode="after")
    def _validate_sender_message_type(self) -> "ChatHistoryMessage":
        if self.sender_type == SenderType.AI and self.message_type != MessageType.TEXT:
            raise ValueError("senderType=AI 인 경우 messageType은 TEXT만 허용됩니다.")
        return self

```

```python
class ChatRespondRequest(BaseModel):
    """
    [요청] POST /ai/v2/reports/{reportId}/chat/respond

    목적
    - Backend가 reportId 대화창에서의 '이번 AI 응답 세션 messageId'를 미리 발급하고,
      최신 USER 입력 + 최근 대화 이력(messages[])을 전달하여 응답 생성을 시작한다.

    필드
    - userId: 사용자 식별자(BIGINT)
    - messageId: 이번에 생성될 'AI 응답 메시지'의 식별자(= stream 구독 키)
    - messages: 대화 이력(최근 N턴). 마지막 메시지는 반드시 USER.
    """
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    user_id: BigInt64 = Field(..., alias="userId", description="사용자 ID(BIGINT)")
    message_id: BigInt64 = Field(..., alias="messageId", description="AI 응답 메시지 ID(= stream 구독 키)")
    messages: List[ChatHistoryMessage] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="대화 이력(최근 N턴). 마지막은 USER 메시지여야 함",
    )

    @model_validator(mode="after")
    def _validate_messages(self) -> "ChatRespondRequest":
        if not self.messages:
            raise ValueError("messages는 1개 이상이어야 합니다.")
        if self.messages[-1].sender_type != SenderType.USER:
            raise ValueError("messages의 마지막 메시지는 senderType=USER여야 합니다.")
        return self

```

### 3) Response Models (POST /ai/v2/reports/{reportId}/chat/respond)
### **↑** [목차로 돌아가기](#목차)

```python
class ChatRespondAckData(BaseModel):
    """
    [응답 data] 생성 세션 식별자.
    - messageId: stream 구독 키(요청의 messageId와 동일)
    """
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    message_id: BigInt64 = Field(..., alias="messageId", description="AI 응답 메시지 ID(= stream 구독 키)")


```

```python
class ChatRespondAckResponse(BaseModel):
    """
    [응답] POST /ai/v2/reports/{reportId}/chat/respond (즉시 응답)

    - success/processTime: 공통 응답
    - data.messageId: SSE stream 구독 키 반환
    """
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    success: bool = Field(..., description="요청 접수 성공 여부", examples=[True])
    process_time: float = Field(..., alias="processTime", description="서버 처리 시간(초)", examples=[0.02])

    data: ChatRespondAckData = Field(..., description="생성 세션 정보(messageId)")

```

## II-4-2. 실시간 응답 스트림 (GET /ai/v2/reports/{reportId}/chat/respond/{messageId}/stream)
### **↑** [목차로 돌아가기](#목차)

### 0) 공통 타입 / Enum (GET /ai/v2/reports/{reportId}/chat/respond/{messageId}/stream)
### **↑** [목차로 돌아가기](#목차)
> - 이 엔드포인트는 SSE(Server-Sent Events) 로 스트리밍한다
> - 응답 Content-Type: text/event-stream; charset=utf-8 이벤트는 start → chunk(반복) → complete 순서이며, 실패 시 error로 종료된다

```python
from __future__ import annotations

from enum import Enum
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field


BigInt64 = Annotated[
    int,
    Field(
        ge=1,
        le=9_223_372_036_854_775_807,
        description="BIGINT(64-bit) 범위 정수",
        examples=[101],
    ),
]


class SenderType(str, Enum):
    USER = "USER"
    AI = "AI"


class MessageType(str, Enum):
    TEXT = "TEXT"
    FILE = "FILE"


class StreamStatus(str, Enum):
    GENERATING = "GENERATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"
```

### 1) SSE 이벤트 페이로드 Models (GET /ai/v2/reports/{reportId}/chat/respond/{messageId}/stream)
### **↑** [목차로 돌아가기](#목차)

#### 1-1) event: start
```python
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

```

#### 1-2) event: chunk
```python
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

```

#### 1-3) event: complete
```python
class ChatStreamCompleteEvent(BaseModel):
    """
    event: complete
    - 정상 종료(또는 정책에 따라 취소 종료) 알림

    content 정책(선택)
    - 포함: 최종본을 함께 전달(Backend가 누적 없이 저장 가능)
    - 생략(권장): Backend가 chunk 누적 후 최종 저장
    """
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    message_id: BigInt64 = Field(..., alias="messageId")
    sender_type: SenderType = Field(SenderType.AI, alias="senderType", description="AI 고정")
    message_type: MessageType = Field(MessageType.TEXT, alias="messageType", description="TEXT(MARKDOWN) 고정")

    status: StreamStatus = Field(StreamStatus.COMPLETED, description="COMPLETED (또는 CANCELED)")

    content: Optional[str] = Field(None, description="최종 MARKDOWN 본문(선택)")

```

#### 1-4) event: error
```python
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

```

### 2) 입출력 명세 Models (GET /ai/v2/reports/{reportId}/chat/respond/{messageId}/stream)
### **↑** [목차로 돌아가기](#목차)
- Request (GET)
    - Path Params
        - reportId (BIGINT): 리포트/대화창 식별자
        - messageId (BIGINT): 스트림 구독 키(응답 생성 세션)
    - Headers (필수)
        - Authorization: Bearer {accessToken}
        - (권장) Accept: text/event-stream
- Response (200 OK)
    - Content-Type: text/event-stream; charset=utf-8
    - Body: SSE 이벤트 스트림

이벤트 형식(예)
```markfile
event: start
data: {...JSON...}

event: chunk
data: {...JSON...}

event: complete
data: {...JSON...}
```

### 3) 에러 응답(HTTP) (GET /ai/v2/reports/{reportId}/chat/respond/{messageId}/stream)
### **↑** [목차로 돌아가기](#목차)
> - SSE 연결 자체가 실패한 경우(권한/존재/충돌 등)는 일반 JSON 에러로 응답한다

```python
class ErrorResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    status: str = Field(..., description="에러 상태 코드 문자열", examples=["UNAUTHORIZED"])
    message: str = Field(..., description="에러 메시지")
    data: Optional[dict] = Field(None, description="추가 정보(없으면 null)")
```

- 401 UNAUTHORIZED: 토큰 불일치/만료
- 403 FORBIDDEN: reportId 접근 권한 없음
- 404 NOT_FOUND: reportId 또는 messageId 없음
- 409 CONFLICT: 이미 종료된 스트림 / 이미 다른 스트림이 열려 있음(정책에 따라)
- 500 INTERNAL_SERVER_ERROR: 서버 장애





## II-4-3. 응답 생성 취소 (DELETE /ai/v2/reports/{reportId}/chat/respond/{messageId}/stream)
### **↑** [목차로 돌아가기](#목차)
> - 목적: 진행 중인(messageId) 응답 생성 세션을 취소하고, 서버 내부 상태를 CANCELED로 전환한다
> - 스트림이 이미 열려 있다면(연결 유지 중), 서버는 (권장) event: complete + status=CANCELED 로 종료 이벤트를 내려 마무리한다

### 0) 공통 타입 / Enum (DELETE /ai/v2/reports/{reportId}/chat/respond/{messageId}/stream)
### **↑** [목차로 돌아가기](#목차)
```python
from __future__ import annotations

from enum import Enum
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field


BigInt64 = Annotated[
    int,
    Field(
        ge=1,
        le=9_223_372_036_854_775_807,
        description="BIGINT(64-bit) 범위 정수",
        examples=[101],
    ),
]


class StreamStatus(str, Enum):
    GENERATING = "GENERATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"
```

### 1) Request (DELETE /ai/v2/reports/{reportId}/chat/respond/{messageId}/stream)
### **↑** [목차로 돌아가기](#목차)

- Path Params
    - reportId (BIGINT): 리포트/대화창 식별자
    - messageId (BIGINT): 취소 대상 생성 세션(= 스트림 구독 키)
- Headers (필수)
    - Authorization: Bearer {accessToken}
- Body
    - 없음

### 2) Response (DELETE /ai/v2/reports/{reportId}/chat/respond/{messageId}/stream)
### **↑** [목차로 돌아가기](#목차)
- 204 No Content 권장
- Body 없음
    - 의미: “취소 요청 처리 완료(이미 취소/종료된 경우에도 멱등 처리 가능)” 정책에 적합
    - 스트림이 열려 있었다면, 별도 SSE 연결에서 event: complete / status=CANCELED 이벤트가 내려오고 종료된다(스트림 명세 참고)

### 3) Error Response Models (DELETE /ai/v2/reports/{reportId}/chat/respond/{messageId}/stream)
### **↑** [목차로 돌아가기](#목차)
```json
class ErrorResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    status: str = Field(..., description="에러 상태 코드 문자열", examples=["UNAUTHORIZED"])
    message: str = Field(..., description="에러 메시지")
    data: Optional[dict] = Field(None, description="추가 정보(없으면 null)")
```

# III. API 역할 및 연동 관계

## III-1. 시스템 아키텍처
### **↑** [목차로 돌아가기](#목차)

```bash
USER
  ↕
Frontend
  ↕
Backend
  ├─→ MySQL (Users, Schedule, ScheduleHistory)
  │    ├─→ Users
  │    │    └─→ userId, gender, age(가공), focusTimeZone, dayEndTime 조회
  │    ├─→ Schedule
  │    │    ├─→ dayPlanId 기준 작업 목록 조회(FIXED + FLEX)
  │    │    └─→ 배치 결과 업데이트(startAt/endAt, assignedBy, assignmentStatus 등)
  │    └─→ ScheduleHistory
  │        └─→ scheduleId=taskId 기준 변경 이력 조회(eventType, prev/new time, createdAt)
  │
  ├─→ Redis (Chat Session Store)
  │    ├─→ sessionKey = (userId + reportId) 기준 대화 이력 저장(최근 N턴)
  │    ├─→ 대화 이력 append / trim (턴/토큰 제한)
  │    └─→ TTL 기반 세션 만료(유휴 세션 정리)
  │
  ├─→ Chat DB / Conversation Store (영구 저장소)
  │    ├─→ 사용자-챗봇 대화 로그 영구 저장
  │    ├─→ Weekly Report seed 메시지 저장(챗봇 대화 시작점)
  │    └─→ 분석/리포트/검색(RAG) 확장 가능(선택)
  │
  └─→ AI API Server (FastAPI)
      ├─→ AI Planner Engine
      │    └─→ POST /ai/v1/planners
      │        ├─→ (입력) Users + Schedule 전체 작업 + startArrange
      │        └─→ (출력) 작업별 배치 결과(assignedBy, assignmentStatus, startAt/endAt)
      │    └─→ AI DB (개인화 파라미터 저장소)
      │
      ├─→ Personalization Engine
      │    └─→ POST /ai/v1/personalizations/ingest
      │        ├─→ (입력) Users + Schedule + ScheduleHistory(1주치)
      │        └─→ (출력) 저장 결과(success/message)
      │    └─→ AI DB (개인화 파라미터 저장소)
      │
      ├─→ Weekly Report Engine
      │    ├─→ (정기 트리거: 매주 월요일 00:20) Backend → AI Server
      │    │    └─→ POST /ai/v2/reports/weekly (baseTime, reportId, userId)
      │    ├─→ AI DB (누적 데이터 조회: 개인화/히스토리/성과)
      │    └─→ Backend (레포트 반환: reportId, content(VARCHAR(3000)), sendAt(ISO 8601))
      │        └─→ Chat DB / Conversation Store에 seed로 저장
      │
      └─→ Chat Respond Engine (LLM)
          ├─→ POST /ai/v2/reports/{reportId}/chat/respond (응답 생성 시작/접수)
          │    ├─→ Backend가 reportId 기반으로 Redis에서 대화 이력(messages[]) 구성
          │    ├─→ Backend가 이번 응답의 messageId 발급 후 요청에 포함
          │    └─→ AI는 입력(messages[])을 바탕으로 MARKDOWN 응답 생성 시작(대화 저장은 수행하지 않음)
          │
          ├─→ GET /ai/v2/reports/{reportId}/chat/respond/{messageId}/stream (SSE 스트리밍)
          │    ├─→ event:start → 생성 시작 알림(messageId/status)
          │    ├─→ event:chunk → MARKDOWN delta 전송(sequence 증가)
          │    └─→ event:complete / event:error → 완료/실패 후 종료
          │
          └─→ DELETE /ai/v2/reports/{reportId}/chat/respond/{messageId}/stream (응답 생성 취소)
              └─→ 생성 중 세션 중단(권장: 멱등 204 / 스트림에는 status=CANCELED로 종료 이벤트 송신)
```

## III-2. API별 역할 및 책임

### 1) Planner Auto-Scheduling API (POST /ai/v1/planners)
### **↑** [목차로 돌아가기](#목차)

#### 주요 기능
사용자의 설정(몰입 시간대, 하루 마무리 시간)과 해당 dayPlanId의 전체 작업 목록을 입력받아,     
FLEX 작업의 시간 배치/제외 여부를 결정하고 일괄 결과를 반환한다.  
(결과는 Backend가 Schedule 테이블에 업데이트)

#### 핵심 역할

- 고정 일정(FIXED) 유지
  - type=FIXED 작업은 입력된 startAt/endAt(HH:MM)을 유지(원칙적으로 변경하지 않음)

- 유동 일정(FLEX) 자동 배치
    - estimatedTimeRange, focusLevel, isUrgent, focusTimeZone, startArrange, dayEndTime을 고려해 startAt/endAt(HH:MM) 산출

- 제외 작업 판정
    - 남은 시간/제약 조건으로 배치가 불가능한 FLEX 작업은 isExcludedTask=true로 반환(시간은 null 가능)

- 출력 규칙 강제
    - whoChange: FIXED → USER, FLEX → AI
    - isTodolist: 응답은 전부 false
    - 시간 입출력은 항상 HH:MM 문자열

#### 입력 데이터 (Backend → AI API)

- 사용자 설정(Users 기반)
  - userId
  - focusTimeZone
  - dayEndTime (HH:MM)

- 배치 트리거 정보
  - startArrange (HH:MM) : “배치하기” 버튼을 누른 시각

- 작업 목록(Schedule 기반: 해당 dayPlanId의 전체 작업)
  - taskId, dayPlanId, title, type
  - startAt, endAt (HH:MM, FIXED는 필수 / FLEX는 null)
  - estimatedTimeRange, focusLevel, isUrgent (주로 FLEX 배치에 사용)
>참고: AI API는 DB에 직접 접근하지 않는 구조를 전제로 한다(필요 데이터는 Backend가 모두 제공).

#### 출력 데이터 (AI API → Backend)

- 공통
  - success: 작업 성공 여부
  - processTime: 서버 처리 시간

- 작업별 결과(results[])
- userId, taskId, dayPlanId
- title, type
- whoChange (FIXED=USER / FLEX=AI)
- startAt, endAt (HH:MM, 제외 시 null 가능)
- isExcludedTask (true/false)
- isTodolist (전부 false)

#### 데이터 흐름

1. Frontend → Backend: 사용자가 특정 날짜 플래너에서 “배치하기” 클릭(→ startArrange 생성)

2. Backend → MySQL
    - Users에서 userId, focusTimeZone, dayEndTime 조회
    - Schedule에서 해당 dayPlanId의 전체 작업 목록 조회(FIXED+FLEX)
    - 시간 관련 값은 Backend가 HH:MM으로 변환/정규화

3. Backend → AI API Server: POST /ai/v1/planners로 배치 요청 전송(사용자 설정 + 전체 작업)

4. AI API 내부 처리
   - FIXED 유지
   - FLEX 배치(시간 산출) 또는 제외 판정
   - 출력 규칙 적용(whoChange, isTodolist=false, HH:MM 포맷)

5. AI API → Backend: 배치 결과(results) 반환

6. Backend → MySQL(Schedule): 반환된 결과를 기준으로 startAt/endAt, isExcludedTask, who_change 등 업데이트/저장

7. Backend → Frontend: 최종 플래너(배치된 작업 + 제외 목록) 응답/표시

### 2) Personalization Ingest API (POST /ai/v1/personalizations/ingest)
### **↑** [목차로 돌아가기](#목차)
#### 주요 기능
매주 일요일 밤 10시에,  
Backend가 Users/Schedule/ScheduleHistory 일주일치 데이터(저번주 일요일 ~ 어제자 토요일)를 모아 AI 서버로 전달하면,   
AI 서버가 이를 기반으로 개인화 파라미터를 생성하여 AI DB에 저장하고,  
Backend에 “저장 성공/실패” 응답만 반환한다.

#### 핵심 역할

- 사용자 기본 컨텍스트 수집
  - gender, age(정수), focusTimeZone, dayEndTime 등 개인화의 기준이 되는 “사용자 설정” 입력

- 해당 날짜 플래너 결과 수집(Schedule)
  - 작업별 status(DONE/TODO), type(FIXED/FLEX), assignedBy, assignmentStatus, estimatedTimeRange, focusLevel, isUrgent
  - 실제 배치된 작업은 startAt/endAt(HH:MM) 포함

- 사용자 수정 패턴 수집(ScheduleHistory)
  - eventType(ASSIGN_TIME / MOVE_TIME / CHANGE_DURATION) + 변경 전/후 시간(HH:MM)
  - “시간대를 자주 옮기는지”, “길이를 늘리는지/줄이는지” 같은 행동 특성 학습 근거 확보

- 개인화 파라미터 생성 및 저장
  - AI 서버 내부에서 개인화 파라미터(예: 시간대 선호 가중치, 과소/과대 추정 보정, 수정 빈도 기반 신뢰도 등) 산출
  - 결과를 AI DB에 저장(Backend DB에 저장하지 않음)

- 응답은 저장 결과만 반환
  - 민감/복잡한 개인화 파라미터 자체를 Backend로 되돌려 보내지 않고 “저장 성공/실패”만 반환하여 책임 경계를 명확화

#### 입력 데이터 (Backend → AI API)

- Users 기반
  - userId, gender, age(정수, 백엔드 가공), focusTimeZone, dayEndTime(HH:MM)
- Schedule 기반(해당 날짜/플랜의 전체 작업)
  - taskId, dayPlanId, title, status, type
  - assignedBy, assignmentStatus
  - startAt, endAt (HH:MM, 배치된 경우)
  - estimatedTimeRange, focusLevel, isUrgent

- ScheduleHistory 기반(변경 이력)
  - scheduleId(=taskId), eventType
  - prevStartAt, prevEndAt, newStartAt, newEndAt (모두 HH:MM)
>참고: 이 API는 “플래너 종료 48시간 후”에 호출되도록 Backend 스케줄러/배치 잡이 트리거하는 것을 전제로 한다.

#### 출력 데이터 (AI API → Backend)

- success: 저장 성공 여부
- processTime: 서버 처리 시간
- message: 결과 메시지(예: "저장 성공")

#### 데이터 흐름
1. 매주 일요일 밤 10시

2. Backend → MySQL
    - Users에서 개인화 입력(gender, age, focusTimeZone, dayEndTime) 조회(나이는 Backend가 정수로 가공)
    - Schedule에서 해당 dayPlanId의 작업 결과 조회(배치 상태/완료 여부 포함)
    - ScheduleHistory에서 해당 날짜 플랜의 변경 이력 조회(scheduleId=taskId 기준)
    - 시간 관련 값은 Backend가 HH:MM으로 변환/정규화

3. Backend → AI API Server: POST /ai/v1/personalizations/ingest로 수집 데이터 전송

4. AI API 내부 처리
    - 입력 데이터를 기반으로 개인화 파라미터 생성
    - AI DB에 개인화 파라미터 저장(업서트/버전 관리 등은 AI DB 정책에 따름)

5. AI API → Backend: 저장 결과(success, message) 반환

6. Backend(선택): 성공/실패 로그 기록, 재시도 큐 적재, 모니터링 지표 수집 등 운영 처리

### 3) Weekly Report API (POST /ai/v2/reports/weekly)
### **↑** [목차로 돌아가기](#목차)

#### 주요 기능
매주 월요일 00:20에 Backend가 트리거를 보내면,  
AI 서버는 baseTime(월요일 기준)을 기반으로 직전 1주 데이터를 내부(AI DB)에서 조회하여 **주간 레포트(content)**를 생성하고,  
reportId, content(VARCHAR(3000)), sendAt(ISO 8601)를 Backend로 반환한다.  
Backend는 이 레포트를 챗봇 대화 시작점(seed) 으로 저장하여 사용자가 추후 질문할 수 있게 한다.

#### 핵심 역할

- 주간 범위 결정(기준 시간 기반)

입력 baseTime을 “월요일”로 가정하고, AI 서버가 내부적으로 직전 7일(1주) 데이터를 조회 범위로 산정

예: baseTime=2026-01-12T00:20:00+09:00 → 2026-01-05~2026-01-11 데이터 기반 생성

- 내부 누적 데이터 활용

레포트 원천 데이터는 별도 입력으로 받지 않음

AI 서버는 과거에 수집된 /ai/v1/personalizations/ingest 기반 데이터를 포함해
개인화 파라미터/플래너 결과/수정 패턴 등 내부 저장소(AI DB)의 누적 데이터를 조회하여 레포트 생성

- 레포트 생성(LLM 기반 요약/해석)
  - 주간 성과/패턴/개선 포인트를 자연어로 정리
  - Backend가 챗봇 UI에서 바로 보여줄 수 있도록 MARKDOWN에 맞춘 텍스트 생성
  - content는 DB 제약에 맞춰 최대 3000자(VARCHAR(3000)) 이내로 생성

- 식별자 및 전달 시각 보장
  - reportId(BIGINT)를 그대로 반환해 Backend 저장 키로 사용 가능
  - sendAt(ISO 8601)를 포함하여 “언제 생성/발송된 레포트인지”를 Backend가 기록할 수 있게 함

- 챗봇 대화 시작점(seed) 생성 지원
  - 응답 content는 Backend가 그대로 챗봇 대화의 첫 메시지로 저장하기 적합한 형태
  - 사용자는 이후 챗봇 화면에서 해당 레포트를 읽고 후속 질문 가능

#### 입력 데이터 (Backend → AI API) 

- reportId (BIGINT): 레포트 식별자(백엔드 발급)
- userId (BIGINT): 대상 사용자 ID
- baseTime (ISO 8601): 기준 시각(월요일 가정, 직전 1주 조회 기준)

#### 출력 데이터 (AI API → Backend)

- 공통
  - success: 작업 성공 여부
  - processTime: 서버 처리 시간(초)
- 레포트 결과
  - reportId (BIGINT)
  - content (VARCHAR(3000))
  - sendAt (ISO 8601)

#### 데이터 흐름

1. (정기 트리거) 매주 월요일 00:20, Backend 스케줄러가 주간 레포트 생성을 트리거

2. Backend → AI API Server: POST /ai/v2/reports/weekly 호출 (baseTime, reportId, userId)

3. AI API 내부 처리
  - baseTime 기준으로 직전 1주 범위 산정
  - AI DB에서 해당 사용자의 누적 데이터(개인화/이력/성과)를 조회
  - LLM 기반으로 주간 레포트 content 생성(3000자 제한 준수) (형태는 MARKDOWN 고정)
  - sendAt 생성

4. AI API → Backend: reportId, content, sendAt 반환

5. Backend 저장
  - 레포트를 챗봇 대화 시작점(seed) 으로 Conversation Store에 저장
  - 추후 사용자가 챗봇 화면에서 레포트를 열람하며 질문 가능

6. Frontend
  - 사용자는 챗봇 화면에서 “이번 주 레포트”를 첫 메시지로 확인하고, 후속 대화 진행


### 4-1) Chat Respond API (POST ai/v2/reports/{reportId}/chat/respond)
### **↑** [목차로 돌아가기](#목차)

#### 주요 기능
특정 리포트 대화창(reportId)에서 **사용자의 최신 입력 + (필요 시) 최근 대화 이력(messages[])**을 입력받아,  
해당 입력에 대한 AI 응답 생성을 시작하고, 스트리밍 구독 키인 messageId 기준으로 SSE 스트림에서 응답을 전송할 준비를 완료한다.  
(이 엔드포인트는 결과 본문을 즉시 반환하지 않고, “접수(ACK)”만 반환한다) 

#### 핵심 역할
- 응답 생성 “시작/접수” 전용
    - 실제 답변 본문(MARKDOWN)은 GET /ai/v2/reports/{reportId}/chat/respond/{messageId}/stream에서만 전달
    - 본 API 응답은 생성 시작을 위한 ACK(접수 확인)
- messageId 기반 생성 세션(Job) 생성/등록
    - messageId를 키로 내부 생성 세션을 만들고, 이후 스트림 연결에서 해당 세션을 조회해 chunk를 송신
- 입력 정합성/정책 검증
    - messages[]는 1개 이상
    - messages[]의 마지막 메시지는 반드시 USER
    - senderType=AI 메시지는 messageType=TEXT만 허용(= MARKDOWN 텍스트)
- 출력 규칙 강제(생성 정책)
    - AI 응답은 TEXT(MARKDOWN)만 생성
    - FILE 출력 금지(사용자 입력만 TEXT/FILE 허용)
- 상태/저장 책임 분리(Stateless 운영)
    - AI 서버는 대화 이력 저장(Redis/DB) 수행하지 않음
    - 저장/세션 유지(append/trim/TTL)는 Backend가 담당

#### 입력 데이터 (Backend → AI API)
- Path Parameter
    - reportId (Long) : 하나의 챗봇 대화창(주간 리포트 기반 대화)의 식별자
- Request Body
    - userId (Long) : 사용자 식별자(권한/개인화 라우팅/로그용)
    - messageId (BIGINT) : 이번 AI 응답 생성 세션의 구독 키(이후 stream 경로에 사용)
    - messages[] : 최근 대화 이력(Backend가 Redis/Conversation Store에서 구성)
        - 각 원소: messageId, senderType(USER/AI), messageType(TEXT/FILE), content
        - 규칙: 마지막 원소는 USER, AI는 TEXT만

> 참고: AI API는 DB/Redis에 직접 접근하지 않는 구조를 전제로 한다(필요한 대화 맥락은 Backend가 messages[]로 제공)

#### 출력 데이터 (AI API → Backend)
- 200 OK (ACK)
    - success : 접수 성공 여부
    - processTime : 서버 처리 시간(초)
    - data.messageId : 스트림 구독 키(요청의 messageId와 동일)
- Error (예: 400/401/403/404/409/500)
    - 공통 에러 바디(프로젝트 표준에 맞춰) + status/message/data(null) 형태 권장
    - 409 CONFLICT : 동일 messageId로 이미 생성 중(중복 생성 방지)

#### 데이터 흐름
1. Frontend → Backend
    - 사용자가 reportId 대화창에서 메시지 전송
2. Backend → Redis(Session Store)
    - sessionKey(reportId/userId 등)로 최근 N턴 조회
    - 최신 사용자 입력을 포함해 messages[] 구성(마지막 USER 보장)
    - messageId 발급(스트림 구독 키)
3. Backend → AI API:
    - POST /ai/v2/reports/{reportId}/chat/respond 호출( userId + messageId + messages[] )
4. AI API 내부 처리
    - 요청 검증 → messageId 기준 생성 세션 등록 → LLM 생성 시작(버퍼/큐에 chunk 적재)
5. AI API → Backend
    - POST는 즉시 ACK 반환(messageId)
6. Backend → AI API (구독)
    - GET /ai/v2/reports/{reportId}/chat/respond/{messageId}/stream로 SSE 연결(실시간 수신 시작)

7. Backend 후처리
    - 스트림 완료 후
        - Redis(sessionKey)에 AI 메시지 append(세션 유지)
        - Conversation Store에 영구 저장(대화 로그)


### 4-2) Chat Stream API (GET /ai/v2/reports/{reportId}/chat/respond/{messageId}/stream)
### **↑** [목차로 돌아가기](#목차)

#### 주요 기능
POST /ai/v2/reports/{reportId}/chat/respond로 시작된 응답 생성 세션(messageId)에 대해,  
AI가 생성하는 MARKDOWN 텍스트를 SSE(Server-Sent Events)로 chunk 단위 스트리밍한다.

#### 핵심 역할
- messageId 기반 스트림 구독(연결 유지)
    - Backend는 messageId로 특정 생성 세션을 구독
    - AI는 해당 세션의 생성 결과를 동일 연결로 순차 전송
- 표준 SSE 이벤트 제공
    - event: start : 생성 시작 알림(세션 상태 = GENERATING)
    - event: chunk : MARKDOWN delta 조각 전송(1부터 증가하는 sequence 포함)
    - event: complete : 완료 알림(status=COMPLETED 또는 CANCELED 정책 반영)
    - event: error : 실패 알림(status=FAILED + errorCode/message)
- 출력 규칙 강제
    - AI 응답은 senderType=AI, messageType=TEXT 고정
    - delta/content는 MARKDOWN 문자열
- 운영/안정성 고려
    - 이미 종료된 세션/존재하지 않는 세션은 404 또는 409로 처리
    - 중복 구독(동일 messageId 동시 다중 연결) 정책은 서버 운영 정책에 따라 제한 가능

#### 입력 데이터 (Backend → AI API)
- Path Parameter
    - reportId (Long) : 대화창 식별자(라우팅/권한/스코프 확인용)
    - messageId (BIGINT) : 스트리밍 구독 키(응답 생성 세션 ID)
- Header (권장)
    - Accept: text/event-stream
    - Authorization: Bearer {token} (서비스 표준에 맞는 인증)

#### 출력 데이터 (AI API → Backend)
- 200 OK (SSE Stream, Content-Type: text/event-stream; charset=utf-8)
- 이벤트는 아래 모델의 data: {JSON} 형태로 전송
```text
event: start
data: {"messageId":101,"senderType":"AI","messageType":"TEXT","status":"GENERATING"}

event: chunk
data: {"messageId":101,"senderType":"AI","messageType":"TEXT","delta":"오늘은","sequence":1}

event: chunk
data: {"messageId":101,"senderType":"AI","messageType":"TEXT","delta":" 오전 몰입 시간에","sequence":2}

event: complete
data: {"messageId":101,"senderType":"AI","messageType":"TEXT","status":"COMPLETED"}
```
- Error (HTTP)
    - 401 UNAUTHORIZED : 토큰/인증 실패
    - 403 FORBIDDEN : reportId 접근 권한 없음
    - 404 NOT_FOUND : messageId 세션 없음
    - 409 CONFLICT : 이미 종료된 스트림, 또는 다중 구독 금지 정책 위반
    - 500 INTERNAL_SERVER_ERROR : 서버 오류

#### 데이터 흐름
1. Backend
    - POST ai/v2/reports/{reportId}/chat/respond에서 받은 messageId로 본 API에 연결한다.
2. AI API
    - messageId 세션을 조회해 생성 상태를 확인하고 event:start를 전송한다.
3. LLM 생성 토큰을 누적하며 MARKDOWN을 event:chunk로 순차 전송한다.
4. 생성이 정상 종료되면 event:complete(status=COMPLETED)를 전송하고 연결을 닫는다.
5. Backend는 수신한 chunk를 누적해 최종 content를 만들고 Redis/Conversation Store에 저장한다.


### 4-3) Chat Stream Cancel API (DELETE /ai/v2/reports/{reportId}/chat/respond/{messageId}/stream)
### **↑** [목차로 돌아가기](#목차)

#### 주요 기능
진행 중인 응답 생성 세션(messageId)을 취소(CANCEL) 한다.  
취소가 성공하면 AI 서버 내부 상태를 CANCELED로 전환하고, 스트림이 열려 있다면 취소 종료 이벤트로 연결을 정리한다.

#### 핵심 역할
- 응답 생성 중단
    - 해당 messageId의 생성 작업(LLM generation)을 중단(가능하면 즉시)
    - 서버 내부 상태를 StreamStatus.CANCELED로 전환
- 스트림 정리(권장 정책)
    - 스트림이 열려 있으면 아래 중 하나로 종료 신호를 명확히 전송
    - event: complete + data.status="CANCELED" (권장: complete 이벤트로 통일)
    - 또는 별도 event: canceled 이벤트(운영 정책에 따라 선택)
- 멱등/중복 취소 처리
    - 이미 COMPLETED/FAILED/CANCELED인 세션에 대한 재취소는
    - (운영 편의) 204로 멱등 처리하거나
    - (엄격) 409(CONFLICT) 로 반환 중 택1

#### 입력 데이터 (Backend → AI API)
- Path Parameter
    - reportId (Long) : 대화창 식별자(권한/스코프 확인)
    - messageId (BIGINT) : 취소 대상 생성 세션 ID(구독 키)
- Headers
    - Authorization: Bearer {token}

#### 출력 데이터 (AI API → Backend)
- 성공(권장)
    - 204 No Content (권장)
        - 취소 성공(또는 멱등 처리 성공) 시 본문 없이 종료
- 실패 케이스(요약)
    - 401 UNAUTHORIZED : 토큰/인증 실패
    - 403 FORBIDDEN : reportId 접근 권한 없음
    - 404 NOT_FOUND : messageId 세션 없음
    - 409 CONFLICT : 이미 종료된 세션인데 엄격 정책을 쓰는 경우
    - 500 INTERNAL_SERVER_ERROR : 서버 오류

#### 데이터 흐름
1. Frontend → Backend
    - 사용자가 “생성 중지” 버튼 클릭 또는 화면 이탈/새 요청 등으로 취소 트리거 발생
2. Backend → AI API
    - DELETE /ai/v2/reports/{reportId}/chat/respond/{messageId}/stream 호출
3. AI API
    - 세션 상태 확인 → 생성 중단 → 상태를 CANCELED로 변경
4. (스트림 연결이 열려있으면) event: complete with status=CANCELED 전송 후 종료
5. Backend
    - 정책(1/2)에 따라 Redis/Conversation Store 저장 처리 및 UI 반영

# IV. API 호출 및 응답 예시

## IV-1. 엔드포인트 : POST /ai/v1/planners

### 1) Planners Request Body:
### **↑** [목차로 돌아가기](#목차)

```json
{
  "user": {
    "userId": "integer",          // BIGINT
    "focusTimeZone": "string",    // "MORNING" | "AFTERNOON" | "EVENING" | "NIGHT"
    "dayEndTime": "string"        // "HH:MM"
  },
  "startArrange": "string",       // "HH:MM"
  "schedules": [
    {
      "taskId": "integer",        // BIGINT
      "parentScheduleId": "integer|null", // 상위 작업 ID
      "dayPlanId": "integer",     // BIGINT
      "title": "string",          // VARCHAR(60)
      "type": "string",           // "FIXED" | "FLEX"
      "startAt": "string|null",   // "HH:MM" (FIXED 필수, FLEX는 null 가능)
      "endAt": "string|null",     // "HH:MM" (FIXED 필수, FLEX는 null 가능)

      "estimatedTimeRange": "string|null",  // FLEX 주로 사용
      "focusLevel": "integer|null",         // 1~10 (FLEX 주로 사용)
      "isUrgent": "boolean|null"            // (FLEX 주로 사용)
    }
  ]
}

```

### 2) Planners Request 예시: 
### **↑** [목차로 돌아가기](#목차)

```json
{
  "user": {
    "userId": 123456789,
    "focusTimeZone": "EVENING",
    "dayEndTime": "23:00"
  },
  "startArrange": "20:10",
  "schedules": [
    {
      "taskId": 1,
      "parentScheduleId": null,
      "dayPlanId": 101,
      "title": "팀 주간회의",
      "type": "FIXED",
      "startAt": "19:00",
      "endAt": "20:00",
      "estimatedTimeRange": null,
      "focusLevel": null,
      "isUrgent": null
    },
    {
      "taskId": 2,
      "parentScheduleId": 1,
      "dayPlanId": 101,
      "title": "통계학 실습 과제",
      "type": "FLEX",
      "startAt": null,
      "endAt": null,
      "estimatedTimeRange": "HOUR_1_TO_2",
      "focusLevel": 8,
      "isUrgent": true
    },
    {
      "taskId": 3,
      "dayPlanId": 101,
      "title": "운동",
      "type": "FLEX",
      "startAt": null,
      "endAt": null,
      "estimatedTimeRange": "MINUTE_30_TO_60",
      "focusLevel": 5,
      "isUrgent": false
    }
  ]
}

```

### 3) Planners Response Body (200 OK):
### **↑** [목차로 돌아가기](#목차)

```json
{
  "success": "boolean",        // 작업 성공 여부
  "processTime": "number",     // 서버 처리 시간(초)

  "results": [
    {
      "userId": "integer",           // Users.User_id
      "taskId": "integer",           // Schedule.Task_id
      "dayPlanId": "integer",        // Schedule.dayPlanId

      "type": "string",              // "FIXED" | "FLEX"
      "assignedBy": "string",        // FIXED면 "USER", FLEX면 "AI"

      "assignmentStatus": "string",  // "NOT_ASSIGNED" | "ASSIGNED" | "EXCLUDED"

      "startAt": "string",           // "HH:MM" | null
                                     // assignmentStatus=ASSIGNED면 필수
      "endAt": "string"              // "HH:MM" | null
                                     // assignmentStatus=ASSIGNED면 필수
    }
  ]
}

```

### 4) Planners Response (200 OK) 예시: 
### **↑** [목차로 돌아가기](#목차)

- type=FIXED → assignedBy=USER + assignmentStatus=ASSIGNED(고정시간 유지)
- type=FLEX → AI가 시간 배치 → ASSIGNED
- type=FLEX → 남은 시간/제약으로 제외 → EXCLUDED (시간 null)
```json
{
  "success": true,
  "processTime": 1.37,
  "results": [
    {
      "userId": 123456789,
      "taskId": 1,
      "dayPlanId": 101,
      "type": "FIXED",
      "assignedBy": "USER",
      "assignmentStatus": "ASSIGNED",
      "startAt": "19:00",
      "endAt": "20:00"
    },
    {
      "userId": 123456789,
      "taskId": 2,
      "dayPlanId": 101,
      "type": "FLEX",
      "assignedBy": "AI",
      "assignmentStatus": "ASSIGNED",
      "startAt": "21:15",
      "endAt": "22:45"
    },
    {
      "userId": 123456789,
      "taskId": 3,
      "dayPlanId": 101,
      "type": "FLEX",
      "assignedBy": "AI",
      "assignmentStatus": "EXCLUDED",
      "startAt": null,
      "endAt": null
    },
    {
      "userId": 123456789,
      "taskId": 4,
      "dayPlanId": 101,
      "type": "FIXED",
      "assignedBy": "USER",
      "assignmentStatus": "ASSIGNED",
      "startAt": "20:30",
      "endAt": "21:10"
    }
  ]
}

```

### 5) Planners Response (400 Bad Request): 
### **↑** [목차로 돌아가기](#목차)

- 요청 형식 오류, 필수값 누락 등
```json
{
  "success": false,
  "processTime": 0.02,
  "errorCode": "PLANNER_BAD_REQUEST",
  "message": "요청 형식이 올바르지 않습니다.",
  "details": [
    {
      "field": "tasks",
      "reason": "작업 목록이 비어있습니다."
    }
  ],
  "traceId": "3f2a9c8d-7a8d-4b6a-9c3e-2e6a8a0d9c10"
}
```

### 6) Planners Response (409 Conflict) 
### **↑** [목차로 돌아가기](#목차)

- 요청 자체는 맞지만 상태가 충돌: dayPlanId 혼합 등
```json
{
  "success": false,
  "processTime": 0.02,
  "errorCode": "PLANNER_CONFLICT",
  "message": "요청 데이터가 서로 충돌합니다.",
  "details": [
    {
      "field": "tasks[].dayPlanId",
      "reason": "요청 내 dayPlanId는 모두 동일해야 합니다.",
      "received": [101, 102]
    }
  ],
  "traceId": "f9b0b2e1-0c6c-47c5-9f7a-35f1f9b0a94b"
}
```
### 7) Planners Response (422 Unprocessable Entity)
### **↑** [목차로 돌아가기](#목차)

- 스키마 검증 실패: HH:MM 포맷 등
```json
{
  "success": false,
  "processTime": 0.01,
  "errorCode": "PLANNER_VALIDATION_ERROR",
  "message": "입력 값 검증에 실패했습니다.",
  "details": [
    {
      "field": "dayEndTime",
      "reason": "시간 형식은 HH:MM 이어야 합니다.",
      "received": "23-00"
    },
    {
      "field": "tasks[0].type",
      "reason": "허용 값은 FIXED 또는 FLEX 입니다.",
      "received": "FLOAT"
    }
  ],
  "traceId": "c1b6d2d0-9b0f-4d0f-8a2d-8b99e56c0a2e"
}
```

### 8) Planners Response (500 Internal Server Error) 
### **↑** [목차로 돌아가기](#목차)

- 서버 내부 오류
```json
{
  "success": false,
  "processTime": 0.15,
  "errorCode": "PLANNER_INTERNAL_SERVER_ERROR",
  "message": "서버 처리 중 오류가 발생했습니다.",
  "details": [],
  "traceId": "b0c0b7a0-22a3-4f01-9f86-2ef35c2f6f0a"
}
```

### 9) Planners Response (503 Service Unavailable) 
### **↑** [목차로 돌아가기](#목차)

- AI 엔진 장애/타임아웃
```json
{
  "success": false,
  "processTime": 3.00,
  "errorCode": "PLANNER_SERVICE_UNAVAILABLE",
  "message": "현재 배치 서비스를 사용할 수 없습니다. 잠시 후 다시 시도해주세요.",
  "details": [
    {
      "reason": "AI engine timeout"
    }
  ],
  "traceId": "7c62b0c6-6f4d-4b1e-b5b8-1c3f2d6e7a10"
}
```

## IV-2. 엔드포인트 : POST /ai/v1/personalizations/ingest

### 1) Personalizations Request Body:
### **↑** [목차로 돌아가기](#목차)
```json
{
  "user": {
    "userId": "integer",           // Users.User_id
    "gender": "string",            // "MALE" | "FEMALE" | "OTHER"
    "age": "integer",              // 백엔드 가공 정수 (예: 26)
    "focusTimeZone": "string",     // "MORNING" | "AFTERNOON" | "EVENING" | "NIGHT"
    "dayEndTime": "string"         // "HH:MM" (예: "23:00")
  },

  "schedules": [
    {
      "taskId": "integer",              // Schedule.Task_id
      "dayPlanId": "integer",           // Schedule.dayPlanId

      "title": "string",                // 작업 제목(개인화 학습에 사용)
      "status": "string",               // "TODO" | "DONE"
      "type": "string",                 // "FIXED" | "FLEX"

      "assignedBy": "string",           // "USER" | "AI"
      "assignmentStatus": "string",     // "NOT_ASSIGNED" | "ASSIGNED" | "EXCLUDED"

      "startAt": "string",              // "HH:MM" | null (ASSIGNED면 필수)
      "endAt": "string",                // "HH:MM" | null (ASSIGNED면 필수)

      "estimatedTimeRange": "string",   // Enum 또는 null
                                       // "MINUTE_UNDER_30" | "MINUTE_30_TO_60" |
                                       // "HOUR_1_TO_2" | "HOUR_2_TO_4" | "HOUR_OVER_4"
      "focusLevel": "integer",          // 1~10 또는 null
      "isUrgent": "boolean"             // true/false 또는 null
    }
  ],

  "scheduleHistories": [
    {
      "scheduleId": "integer",          // ScheduleHistory.scheduleId (= Schedule.taskId)
      "eventType": "string",            // "ASSIGN_TIME" | "MOVE_TIME" | "CHANGE_DURATION"

      "prevStartAt": "string",          // "HH:MM" | null (ASSIGN_TIME은 null 가능)
      "prevEndAt": "string",            // "HH:MM" | null (ASSIGN_TIME은 null 가능)

      "newStartAt": "string",           // "HH:MM" (필수)
      "newEndAt": "string",             // "HH:MM" (필수)

      "createdAt": "string"             // DATETIME(6) (예: "2026-01-10T21:40:15.123456")
                                       // 한 작업에서 여러 이벤트 발생 시, 정렬 기준으로 사용
    }
  ]
}

```

### 2) Personalizations Request 예시: 
### **↑** [목차로 돌아가기](#목차)
```json
{
  "user": {
    "userId": 123456789,
    "gender": "MALE",
    "age": 26,
    "focusTimeZone": "EVENING",
    "dayEndTime": "23:00"
  },
  "schedules": [
    {
      "taskId": 1,
      "dayPlanId": 101,
      "title": "팀 주간회의",
      "status": "DONE",
      "type": "FIXED",
      "assignedBy": "USER",
      "assignmentStatus": "ASSIGNED",
      "startAt": "19:00",
      "endAt": "20:00",
      "estimatedTimeRange": null,
      "focusLevel": null,
      "isUrgent": null
    },
    {
      "taskId": 2,
      "dayPlanId": 101,
      "title": "통계학 실습 과제",
      "status": "DONE",
      "type": "FLEX",
      "assignedBy": "AI",
      "assignmentStatus": "ASSIGNED",
      "startAt": "21:15",
      "endAt": "22:45",
      "estimatedTimeRange": "HOUR_1_TO_2",
      "focusLevel": 8,
      "isUrgent": true
    },
    {
      "taskId": 3,
      "dayPlanId": 101,
      "title": "운동",
      "status": "TODO",
      "type": "FLEX",
      "assignedBy": "AI",
      "assignmentStatus": "EXCLUDED",
      "startAt": null,
      "endAt": null,
      "estimatedTimeRange": "MINUTE_30_TO_60",
      "focusLevel": 5,
      "isUrgent": false
    },
    {
      "taskId": 4,
      "dayPlanId": 101,
      "title": "독서",
      "status": "TODO",
      "type": "FLEX",
      "assignedBy": "AI",
      "assignmentStatus": "NOT_ASSIGNED",
      "startAt": null,
      "endAt": null,
      "estimatedTimeRange": "HOUR_1_TO_2",
      "focusLevel": 6,
      "isUrgent": false
    }
  ],
  "scheduleHistories": [
    {
      "scheduleId": 2,
      "eventType": "ASSIGN_TIME",
      "prevStartAt": null,
      "prevEndAt": null,
      "newStartAt": "21:15",
      "newEndAt": "22:45",
      "createdAt": "2026-01-10T19:05:10.123456"
    },
    {
      "scheduleId": 2,
      "eventType": "MOVE_TIME",
      "prevStartAt": "20:30",
      "prevEndAt": "22:00",
      "newStartAt": "21:15",
      "newEndAt": "22:45",
      "createdAt": "2026-01-10T19:10:40.456789"
    },
    {
      "scheduleId": 2,
      "eventType": "CHANGE_DURATION",
      "prevStartAt": "21:15",
      "prevEndAt": "22:15",
      "newStartAt": "21:15",
      "newEndAt": "22:45",
      "createdAt": "2026-01-10T19:18:05.987654"
    }
  ]
}

```

### 3) Personalizations Response Body (200 OK):
### **↑** [목차로 돌아가기](#목차)
```json
{
  "success": "boolean",      // 저장 성공 여부
  "processTime": "number",   // 서버 처리 시간(초)
  "message": "string"        // 결과 메시지(예: "저장 성공")
}

```

### 4) Personalizations Response (200 OK) 예시: 
### **↑** [목차로 돌아가기](#목차)
```json
{
  "success": true,
  "processTime": 0.84,
  "message": "저장 성공"
}

```

### 5) Personalizations Response (400 Bad Request): 
### **↑** [목차로 돌아가기](#목차)
- 필수 필드 누락/구조 오류
```json
{
  "success": false,
  "processTime": 0.02,
  "errorCode": "PERSONALIZATION_INGEST_BAD_REQUEST",
  "message": "요청 형식이 올바르지 않습니다.",
  "details": [
    {
      "field": "user",
      "reason": "필수 객체가 누락되었습니다.",
      "received": null
    }
  ],
  "traceId": "2b1e0f2a-6c2a-4a9b-8d5a-6d4b2c1a9f10"
}

```

### 6) Personalizations Response (409 Conflict)
### **↑** [목차로 돌아가기](#목차)
- 데이터 충돌/정책 위반: scheduleId 매핑 불일치 등
```json
{
  "success": false,
  "processTime": 0.03,
  "errorCode": "PERSONALIZATION_INGEST_CONFLICT",
  "message": "요청 데이터가 서로 충돌합니다.",
  "details": [
    {
      "field": "scheduleHistories[2].scheduleId",
      "reason": "scheduleId는 schedules[].taskId 중 하나와 일치해야 합니다.",
      "received": 999
    }
  ],
  "traceId": "b83a3f2c-2d1e-4a1c-9db1-1b2c3d4e5f60"
}


```

### 7) Personalizations Response (422 Unprocessable Entity) 
### **↑** [목차로 돌아가기](#목차)
- 값 검증 실패: HH:MM / createdAt 포맷 등
```json
{
  "success": false,
  "processTime": 0.01,
  "errorCode": "PERSONALIZATION_INGEST_VALIDATION_ERROR",
  "message": "입력 값 검증에 실패했습니다.",
  "details": [
    {
      "field": "schedules[1].startAt",
      "reason": "시간 형식은 HH:MM 이어야 합니다.",
      "received": "9:3"
    },
    {
      "field": "scheduleHistories[0].createdAt",
      "reason": "DATETIME(6) 형식(ISO 8601, 마이크로초 포함)이어야 합니다.",
      "received": "2026/01/10 19:05:10"
    }
  ],
  "traceId": "7d0c4d1a-9b55-4df8-9a2c-6a4f8f5d9c31"
}

```

### 8) Personalizations Response (500 Internal Server Error) 
### **↑** [목차로 돌아가기](#목차)
- 개인화 파라미터 생성/저장 중 내부 오류
```json
{
  "success": false,
  "processTime": 0.20,
  "errorCode": "PERSONALIZATION_INGEST_INTERNAL_SERVER_ERROR",
  "message": "서버 처리 중 오류가 발생했습니다.",
  "details": [],
  "traceId": "0c1a2b3c-4d5e-6f70-8a9b-1c2d3e4f5a6b"
}

```

### 9) Personalizations Response (503 Service Unavailable) 
### **↑** [목차로 돌아가기](#목차)
- AI DB/개인화 엔진 장애, 타임아웃 등
```json
{
  "success": false,
  "processTime": 3.00,
  "errorCode": "PERSONALIZATION_INGEST_SERVICE_UNAVAILABLE",
  "message": "현재 개인화 저장 서비스를 사용할 수 없습니다. 잠시 후 다시 시도해주세요.",
  "details": [
    {
      "field": "dependency",
      "reason": "AI DB timeout"
    }
  ],
  "traceId": "9f7a6b5c-4d3e-2c1b-0a9b-8c7d6e5f4a32"
}

```

## IV-3. 엔드포인트 : POST /ai/v2/reports/weekly

### 1) Reports Request Body:
### **↑** [목차로 돌아가기](#목차)
```json
{
  "reportId": "integer",          // BIGINT
  "userId": "integer",            // BIGINT
  "baseTime": "string",           // ISO 8601 (월요일 기준 시각)
}
```

### 2) Reports Request 예시: 
### **↑** [목차로 돌아가기](#목차)
```json
{
  "reportId": 9000000000001234,
  "userId": 123456789,
  "baseTime": "2026-01-12T00:20:00+09:00",
}
```

### 3) Reports Response Body (200 OK):
### **↑** [목차로 돌아가기](#목차)
```json
{
  "success": "boolean",
  "processTime": "number",      // 서버 처리 시간(초)

  "reportId": "integer",        // BIGINT
  "content": "string",          // VARCHAR(3000)
  "sendAt": "string",           // ISO 8601
}

```

### 4) Reports Response (200 OK) 예시: 
### **↑** [목차로 돌아가기](#목차)
```json
{
  "success": true,
  "processTime": 2.41,
  "reportId": 9000000000001234,
  "content": "# 1월 1주차 주간 리포트\n\n## 이번 주 요약\n- 완료한 작업: 12개 / 미완료: 5개\n- 가장 몰입이 잘 된 시간대: 저녁(19:00~22:00)\n- 시간 이동(MOVE_TIME): 3회, 길이 변경(CHANGE_DURATION): 2회\n\n## 패턴/인사이트\n- 'FLEX 과제/공부'류는 21시 이후에 배치했을 때 완료율이 높았습니다.\n- 반대로 '운동'은 EXCLUDED가 자주 발생했으니, 주중엔 30~60분으로 줄이거나 주말로 이동하는 편이 안정적입니다.\n\n## 다음 주 제안\n- 평일 저녁 21:00~23:00 구간을 ‘집중 블록’으로 고정해 FLEX 작업을 우선 배치해보세요.\n- 운동은 2회만 목표로 두고, 남는 날에 보너스로 추가하는 방식이 지속 가능해요.",
  "sendAt": "2026-01-12T00:20:02.351000+09:00",
}

```

### 5) Reports Response (400 Bad Request): 
### **↑** [목차로 돌아가기](#목차)
- 필수 필드 누락 / JSON 구조 오류

```json
{
  "success": false,
  "processTime": 0.01,
  "errorCode": "WEEKLY_REPORT_BAD_REQUEST",
  "message": "요청 형식이 올바르지 않습니다.",
  "details": [
    {
      "field": "reportId",
      "reason": "필수 필드가 누락되었습니다.",
      "received": null
    }
  ],
  "traceId": "7c1d0a7e-6ef8-4c4c-9df7-6b1fce8b1f42"
}

```
### 6) Reports Response (404 Not Found) 
### **↑** [목차로 돌아가기](#목차)
- 내부 조회 데이터 없음: 해당 주간/사용자 데이터 미존재

```json
{
  "success": false,
  "processTime": 0.08,
  "errorCode": "WEEKLY_REPORT_DATA_NOT_FOUND",
  "message": "주간 레포트 생성을 위한 데이터가 존재하지 않습니다.",
  "details": [
    {
      "field": "userId",
      "reason": "해당 userId의 직전 1주 데이터가 AI DB에 없습니다.",
      "received": 123456789
    }
  ],
  "traceId": "f3a1a4b2-0b2e-4b6f-9e1c-8b9f2e4c1a10"
}

```

### 7) Reports Response (409 Conflict)
### **↑** [목차로 돌아가기](#목차)
- 중복 생성/아이템포턴시 충돌: 동일 reportId가 이미 생성됨
- 
```json
{
  "success": false,
  "processTime": 0.03,
  "errorCode": "WEEKLY_REPORT_CONFLICT",
  "message": "동일한 reportId로 이미 레포트가 생성되어 있습니다.",
  "details": [
    {
      "field": "reportId",
      "reason": "reportId가 이미 존재합니다(재시도는 기존 결과를 조회하도록 처리하거나, 새 reportId를 발급하세요).",
      "received": 9000000000001234
    }
  ],
  "traceId": "3d7c7c3a-2f2b-4a57-9e08-4a0d9a2d3c9f"
}

```

### 8) Reports Response (422 Unprocessable Entity)
### **↑** [목차로 돌아가기](#목차)
- 값 검증 실패: baseTime 포맷/월요일 조건, BIGINT 범위 등

```json
{
  "success": false,
  "processTime": 0.02,
  "errorCode": "WEEKLY_REPORT_VALIDATION_ERROR",
  "message": "입력 값 검증에 실패했습니다.",
  "details": [
    {
      "field": "baseTime",
      "reason": "ISO 8601 datetime 형식이어야 합니다.",
      "received": "2026/01/12 00:20"
    },
    {
      "field": "baseTime",
      "reason": "baseTime은 월요일이어야 합니다.",
      "received": "2026-01-13T00:20:00+09:00"
    },
    {
      "field": "reportId",
      "reason": "BIGINT 범위를 벗어났습니다.",
      "received": 99999999999999999999
    }
  ],
  "traceId": "1f6de3b6-3b2e-4cc3-80bf-5c39ce6e24b1"
}

```

### 9) Reports Response (500 Internal Server Error) 
### **↑** [목차로 돌아가기](#목차)
- LLM/생성 로직 오류

```json
{
  "success": false,
  "processTime": 0.25,
  "errorCode": "WEEKLY_REPORT_INTERNAL_SERVER_ERROR",
  "message": "서버 처리 중 오류가 발생했습니다.",
  "details": [],
  "traceId": "b9b4d0d1-2b3a-4e19-9d1f-4b7b0d1a9c2e"
}

```

### 10) Reports Response (503 Service Unavailable) 
### **↑** [목차로 돌아가기](#목차)
- AI DB/LLM 의존성 장애 또는 타임아웃

```json
{
  "success": false,
  "processTime": 3.00,
  "errorCode": "WEEKLY_REPORT_SERVICE_UNAVAILABLE",
  "message": "현재 주간 레포트 생성 서비스를 사용할 수 없습니다. 잠시 후 다시 시도해주세요.",
  "details": [
    {
      "field": "dependency",
      "reason": "AI DB timeout"
    }
  ],
  "traceId": "8a7f6e5d-4c3b-2a19-0f8e-7d6c5b4a3f21"
}

```

## IV-4-1. 엔드포인트 : POST /ai/v2/reports/{reportId}/chat/respond

### 1) Chat Respond Request Body:
### **↑** [목차로 돌아가기](#목차)
```json
{
{
  "userId": "BIGINT",
  "messageId": "BIGINT", // 스트리밍 SSE 구독 키
  "messages": [
    {
      "messageId": "BIGINT", // 각 메세지 구별 아이디, 순서 정렬 (오름차순)
      "senderType": "USER | AI",
      "messageType": "TEXT | FILE",
      "content": "string"
    }
  ]
}

```

### 2) Chat Respond Request 예시: 
### **↑** [목차로 돌아가기](#목차)
```json
{
  "userId": 42,
  "messageId": 180,
  "messages": [
    {
      "messageId": 160,
      "senderType": "AI",
      "messageType": "TEXT",
      "content": "이번 주는 중반에 쉬어가고, 다시 올라온 한 주였네요!"
    },
    {
      "messageId": 179,
      "senderType": "USER",
      "messageType": "TEXT",
      "content": "다음주에 뭐부터 하면 좋을까?"
    }
  ]
}

```


### 3) Chat Respond Response Body (200 OK):
### **↑** [목차로 돌아가기](#목차)
```json
{
  "success": true,
  "processTime": 0.0, // 응답 시간
  "data": {
    "messageId": "BIGINT" // 스트림 구독 키(요청의 messageId와 동일)
  }
}
```

### 4) Chat Respond Response (200 OK) 예시: 
### **↑** [목차로 돌아가기](#목차)
```json
{
  "success": true,
  "processTime": 0.018,
  "data": {
    "messageId": 180
  }
}

```

### 5) Chat Respond Response (400 Bad Request): 
### **↑** [목차로 돌아가기](#목차)
- JSON 구조 오류 / 필수 필드 누락 / messages 비어있음 등

```json
{
  "success": false,
  "processTime": 0.02,
  "errorCode": "INVALID_REQUEST",
  "message": "요청 값이 올바르지 않습니다.",
  "details": [
    {
      "field": "messages",
      "reason": "messages는 1개 이상이어야 합니다.",
      "received": []
    }
  ],
  "traceId": "b2d1a2ae-8b63-4f62-9d3a-6e0e5b0f9b21"
}


```
### 6) Chat Respond Response (401 Unauthorized) 
### **↑** [목차로 돌아가기](#목차)
```json
{
  "success": false,
  "processTime": 0.01,
  "errorCode": "UNAUTHORIZED",
  "message": "유효하지 않은 토큰입니다.",
  "details": [
    {
      "field": "Authorization",
      "reason": "Bearer 토큰이 없거나 만료/위조되었습니다.",
      "received": null
    }
  ],
  "traceId": "0d8d6cf2-6aef-4a2b-8c4b-6e1f6b2c9a41"
}


```

### 7) Chat Respond Response (403 Forbidden)
### **↑** [목차로 돌아가기](#목차)

```json
{
  "success": false,
  "processTime": 0.01,
  "errorCode": "FORBIDDEN",
  "message": "해당 리포트에 접근할 권한이 없습니다.",
  "details": [
    {
      "field": "reportId",
      "reason": "사용자 권한 범위에 포함되지 않은 reportId 입니다.",
      "received": 20
    }
  ],
  "traceId": "c3d5a8e1-2f6b-4a9c-9a2e-7d4b2e1a9f10"
}


```

### 8) Chat Respond Response (404 Not Found) 
### **↑** [목차로 돌아가기](#목차)

```json
{
  "success": false,
  "processTime": 0.01,
  "errorCode": "REPORT_NOT_FOUND",
  "message": "리포트를 찾을 수 없습니다.",
  "details": [
    {
      "field": "reportId",
      "reason": "존재하지 않는 reportId 입니다.",
      "received": 999999
    }
  ],
  "traceId": "a7b2c1d4-9f33-4c1f-8e2a-0c9c2f1b6a77"
}

```

### 9) Chat Respond Response (409 Conflict) 
### **↑** [목차로 돌아가기](#목차)

```json
{
  "success": false,
  "processTime": 0.02,
  "errorCode": "CHAT_RESPOND_CONFLICT",
  "message": "이미 응답 생성이 진행 중입니다.",
  "details": [
    {
      "field": "messageId",
      "reason": "동일 messageId에 대한 스트리밍 세션이 이미 존재합니다.",
      "received": 101
    }
  ],
  "traceId": "2a9c8d7a-8b99-4df8-9a2c-6a4f8f5d9c31"
}

```

### 10) Chat Respond Response (500 Internal Server Error) 
### **↑** [목차로 돌아가기](#목차)
```json
{
  "success": false,
  "processTime": 0.03,
  "errorCode": "INTERNAL_SERVER_ERROR",
  "message": "일시적으로 접속이 원활하지 않습니다. 서버 팀에 문의 부탁드립니다.",
  "details": [
    {
      "field": null,
      "reason": "예기치 못한 서버 오류가 발생했습니다.",
      "received": null
    }
  ],
  "traceId": "e1c4b6a2-5d7e-4f90-9f65-4c3a2b1d0e8f"
}
```

## IV-4-2. 엔드포인트 : GET /ai/v2/reports/{reportId}/chat/respond/{messageId}/stream
### **↑** [목차로 돌아가기](#목차)

### 1) Chat Stream Request Body:
### **↑** [목차로 돌아가기](#목차)
- Path Parameters
    - reportId (LONG, required) : 리포트(대화창) 식별자
    - messageId (BIGINT, required) : 스트림 구독 키(이번 AI 응답 세션 ID)
- Headers (필수)
    - Authorization: Bearer {accessToken}
    - Accept: text/event-stream
- Headers (권장)
    - Cache-Control: no-cache
    - Connection: keep-alive

### 2) Chat Stream Request 예시: 
### **↑** [목차로 돌아가기](#목차)
```bash
GET /ai/v2/reports/20/chat/respond/101/stream?resumeFromSequence=13 HTTP/1.1
Host: ai.example.com
Authorization: Bearer eyJhbGciOi...
Accept: text/event-stream
Cache-Control: no-cache
Connection: keep-alive

```

### 3) Chat Stream Response Body (200 OK):
### **↑** [목차로 돌아가기](#목차)
- HTTP Status: 200 OK
- Content-Type: text/event-stream; charset=utf-8
- 바디는 아래처럼 SSE 이벤트 라인 스트림으로 흘러감:

### 4-1) Chat Stream Response (200 OK) 예시 — 정상 생성(COMPLETED): 
### **↑** [목차로 돌아가기](#목차)
```text
event: start
data: {"messageId":101,"senderType":"AI","messageType":"TEXT","status":"GENERATING"}

event: chunk
data: {"messageId":101,"senderType":"AI","messageType":"TEXT","delta":"다음 주는 ","sequence":1}

event: chunk
data: {"messageId":101,"senderType":"AI","messageType":"TEXT","delta":"저녁 몰입 시간대에 ","sequence":2}

event: chunk
data: {"messageId":101,"senderType":"AI","messageType":"TEXT","delta":"중요한 FLEX 작업부터 배치해보세요.\n\n- 1) 과제\n- 2) 회의 정리\n","sequence":3}

event: complete
data: {"messageId":101,"senderType":"AI","messageType":"TEXT","status":"COMPLETED"}
```
### 4-2) Chat Stream Response (200 OK) 예시 — 취소 종료(CANCELED): 
```text
event: start
data: {"messageId":101,"senderType":"AI","messageType":"TEXT","status":"GENERATING"}

event: chunk
data: {"messageId":101,"senderType":"AI","messageType":"TEXT","delta":"좋아요. ","sequence":1}

event: chunk
data: {"messageId":101,"senderType":"AI","messageType":"TEXT","delta":"다음 주 우선순위는 ","sequence":2}

event: complete
data: {"messageId":101,"senderType":"AI","messageType":"TEXT","status":"CANCELED"}
```

### 4-3) Chat Stream Response (200 OK) 예시 — 실패 종료(FAILED): 
```text
event: start
data: {"messageId":101,"senderType":"AI","messageType":"TEXT","status":"GENERATING"}

event: error
data: {"messageId":101,"status":"FAILED","errorCode":"CHAT_STREAM_INTERNAL_ERROR","message":"응답 생성 중 오류가 발생했습니다."}
```

### 5) Chat Stream Response (400 Bad Request): 
### **↑** [목차로 돌아가기](#목차)
```json
{
  "success": false,
  "processTime": 0.01,
  "errorCode": "CHAT_STREAM_INVALID_REQUEST",
  "message": "요청 파라미터가 올바르지 않습니다.",
  "details": [
    {
      "field": "resumeFromSequence",
      "reason": "resumeFromSequence는 1 이상이어야 합니다.",
      "received": 0
    }
  ],
  "traceId": "0f2f0c6a-6c32-4b1f-9f88-6c0b9c2b47a1"
}
```

### 6) Chat Stream Response (401 Unauthorized): 
### **↑** [목차로 돌아가기](#목차)
```json
{
  "success": false,
  "processTime": 0.01,
  "errorCode": "UNAUTHORIZED",
  "message": "유효하지 않은 토큰입니다.",
  "details": [
    {
      "field": "Authorization",
      "reason": "Bearer 토큰이 누락되었거나 만료되었습니다.",
      "received": null
    }
  ],
  "traceId": "c3b0f9e0-9dc9-4c70-b1a9-2e6a21c8b5d2"
}


```

### 7) Chat Stream Response (403 Forbidden) 
### **↑** [목차로 돌아가기](#목차)
```json
{
  "success": false,
  "processTime": 0.01,
  "errorCode": "FORBIDDEN",
  "message": "해당 리포트에 접근할 권한이 없습니다.",
  "details": [
    {
      "field": "reportId",
      "reason": "요청한 reportId에 대한 소유권 또는 권한이 없습니다.",
      "received": 20
    }
  ],
  "traceId": "5c9a0b91-8c33-47e0-8a5d-8193c4d0d1a8"
}

```

### 8) Chat Stream Response (404 Not Found)
### **↑** [목차로 돌아가기](#목차)
```json
{
  "success": false,
  "processTime": 0.01,
  "errorCode": "CHAT_STREAM_MESSAGE_NOT_FOUND",
  "message": "해당 메시지 스트림을 찾을 수 없습니다.",
  "details": [
    {
      "field": "messageId",
      "reason": "해당 messageId에 대한 스트리밍 세션이 존재하지 않거나 만료되었습니다.",
      "received": 101
    }
  ],
  "traceId": "9de2f59b-1fdd-4f53-9d1f-f1b61e8c1d51"
}

```

### 9) Chat Stream Response (409 Conflict) 
### **↑** [목차로 돌아가기](#목차)
- 이미 종료된 스트림(예: COMPLETED/FAILED/CANCELED) 재구독 시도, 또는 이미 다른 연결이 점유 중인 정책일 때
```json
{
  "success": false,
  "processTime": 0.01,
  "errorCode": "CHAT_STREAM_ALREADY_CLOSED",
  "message": "이미 종료된 스트림입니다.",
  "details": [
    {
      "field": "messageId",
      "reason": "해당 세션은 이미 종료(COMPLETED/FAILED/CANCELED)되었습니다.",
      "received": 101
    }
  ],
  "traceId": "2dd7f8e1-2a0d-4d7e-a1d4-5d3e1d6c2b0c"
}

```

### 10) Chat Stream Response (500 Internal Server Error) 
### **↑** [목차로 돌아가기](#목차)
```json
{
  "success": false,
  "processTime": 0.02,
  "errorCode": "INTERNAL_SERVER_ERROR",
  "message": "일시적으로 접속이 원활하지 않습니다. 서버 팀에 문의 부탁드립니다.",
  "details": [
    {
      "field": "stream",
      "reason": "스트림 처리 중 내부 오류가 발생했습니다.",
      "received": null
    }
  ],
  "traceId": "7a7f3f1c-3a8d-4b3d-8d0b-8b9a3b8b2c1e"
}

```

## IV-4-3. 엔드포인트 : DELETE /ai/v2/reports/{reportId}/chat/respond/{messageId}/stream
### **↑** [목차로 돌아가기](#목차)

### 1) Chat Stream Cancel Request Body:
### **↑** [목차로 돌아가기](#목차)
- Path Params
    - reportId (Long, required): 리포트(대화방) ID
    - messageId (BIGINT, required): 취소 대상 스트리밍 세션 키(= AI 응답 메시지 ID)
- Headers
    - Authorization: Bearer {accessToken}
    - Accept: application/json
- Request Body
    - 없음 (Body 없이 호출)

```http
DELETE /ai/v2/reports/{reportId}/chat/respond/{messageId}/stream
Authorization: Bearer {accessToken}
Accept: application/json
```

### 2) Chat Stream Cancel Request 예시: 
### **↑** [목차로 돌아가기](#목차)
```http
DELETE /ai/v2/reports/20/chat/respond/101/stream
Authorization: Bearer eyJhbGciOi...
Accept: application/json
```

### 3) Chat Stream Cancel Response (204 No Content) — 성공:
### **↑** [목차로 돌아가기](#목차)
- 취소 성공 시 바디 없음
```http
HTTP/1.1 204 No Content

```

### 4) Chat Stream Cancel Response (400 Bad Request): 
### **↑** [목차로 돌아가기](#목차)
```json
{
  "success": false,
  "processTime": 0.01,
  "errorCode": "CHAT_CANCEL_INVALID_REQUEST",
  "message": "요청 파라미터가 올바르지 않습니다.",
  "details": [
    {
      "field": "messageId",
      "reason": "messageId는 1 이상 BIGINT 범위의 정수여야 합니다.",
      "received": 0
    }
  ],
  "traceId": "b7b0e1b1-44d4-4a8e-9c66-1c1b2aa2a8d7"
}
```

### 5) Chat Stream Cancel Response (401 Unauthorized): 
### **↑** [목차로 돌아가기](#목차)
```json
{
  "success": false,
  "processTime": 0.01,
  "errorCode": "UNAUTHORIZED",
  "message": "유효하지 않은 토큰입니다.",
  "details": [
    {
      "field": "Authorization",
      "reason": "Bearer 토큰이 누락되었거나 만료되었습니다.",
      "received": null
    }
  ],
  "traceId": "2f0a0c3f-9f6b-4bf8-9e7e-4f8a57c6c0b1"
}

```

### 6) Chat Stream Cancel Response (403 Forbidden) 
### **↑** [목차로 돌아가기](#목차)
```json
{
  "success": false,
  "processTime": 0.01,
  "errorCode": "FORBIDDEN",
  "message": "해당 리포트에 접근할 권한이 없습니다.",
  "details": [
    {
      "field": "reportId",
      "reason": "요청한 reportId에 대한 소유권 또는 권한이 없습니다.",
      "received": 20
    }
  ],
  "traceId": "c8c4f0b2-5f3b-4d59-91fb-6d6cc8e6d0a3"
}

```

### 7) Chat Stream Cancel Response (404 Not Found)
### **↑** [목차로 돌아가기](#목차)
- 존재하지 않거나 만료된 messageId, 혹은 세션 정보를 찾을 수 없는 경우

```json
{
  "success": false,
  "processTime": 0.01,
  "errorCode": "CHAT_CANCEL_NOT_FOUND",
  "message": "취소할 메시지 스트림 세션을 찾을 수 없습니다.",
  "details": [
    {
      "field": "messageId",
      "reason": "해당 messageId에 대한 활성 스트리밍 세션이 존재하지 않습니다.",
      "received": 101
    }
  ],
  "traceId": "9a9c1f57-2a3b-4d35-90a2-9b1c2c9ed3f5"
}

```

### 8) Chat Stream Cancel Response (409 Conflict) 
### **↑** [목차로 돌아가기](#목차)
- 이미 종료된 세션(COMPLETED/FAILED/CANCELED)에 대해 취소를 시도하는 경우
- 또는 “이미 취소 처리 중” 같은 중복 취소 방지 정책에 걸린 경우

```json
{
  "success": false,
  "processTime": 0.02,
  "errorCode": "CHAT_CANCEL_CONFLICT",
  "message": "이미 종료된 응답 생성입니다.",
  "details": [
    {
      "field": "messageId",
      "reason": "해당 세션은 이미 COMPLETED 또는 CANCELED 상태입니다.",
      "received": 101
    }
  ],
  "traceId": "2a9c8d7a-8b99-4df8-9a2c-6a4f8f5d9c31"
}

```

### 9) Chat Stream Cancel Response (500 Internal Server Error) 
### **↑** [목차로 돌아가기](#목차)
```json
{
  "success": false,
  "processTime": 0.03,
  "errorCode": "INTERNAL_SERVER_ERROR",
  "message": "일시적으로 접속이 원활하지 않습니다. 서버 팀에 문의 부탁드립니다.",
  "details": [
    {
      "field": null,
      "reason": "서버 내부 오류가 발생했습니다.",
      "received": null
    }
  ],
  "traceId": "f2c0d2f2-7c3e-4f7d-8f6b-9b2a4f0e3c21"
}

```


## IV-5. API별 Status Code 리스트

### 1) FUNCTION_NAME 리스트
### **↑** [목차로 돌아가기](#목차)

| Request Method | URL | FUNCTION_NAME |
| -- | -- | -- |
| POST | /ai/v1/planners | PLANNER_GENERATE |
| POST | /ai/v1/personalizations/ingest | PERSONALIZATION_INGEST |
| POST | /ai/v2/reports/weekly | WEEKLY_REPORT |
| POST | /ai/v2/reports/{reportId}/chat/respond | CHAT_RESPOND |
| GET	| /ai/v2/reports/{reportId}/chat/respond/{messageId}/stream | CHAT_STREAM |
| DELETE | /ai/v2/reports/{reportId}/chat/respond/{messageId}/stream |	CHAT_CANCEL |

### 2) PLANNER_GENERATE의 Status Code
### **↑** [목차로 돌아가기](#목차)

| Status Code | Message                                | Description                                         |
| ----------- | -------------------------------------- | --------------------------------------------------- |
| 200         | PLANNER_GENERATE_SUCCESS               | 요청 성공 (배치 결과 생성 및 응답 반환)                            |
| 400         | PLANNER_GENERATE_BAD_REQUEST           | 잘못된 요청 형식(필수 필드 누락, JSON 구조 오류 등)                   |
| 422         | PLANNER_GENERATE_VALIDATION_ERROR      | 입력 값 검증 실패(HH:MM 형식 오류, enum 값 오류, 타입별 필드 조건 불일치 등) |
| 409         | PLANNER_GENERATE_CONFLICT              | 요청 데이터 충돌(예: tasks 내 dayPlanId 혼합 등, 정책 위반)         |
| 500         | PLANNER_GENERATE_INTERNAL_SERVER_ERROR | 서버 처리 중 오류 발생                                       |
| 503         | PLANNER_GENERATE_SERVICE_UNAVAILABLE   | AI 엔진 장애/타임아웃 등으로 서비스 이용 불가                         |


### 3) PERSONALIZATION_INGEST의 Status Code
### **↑** [목차로 돌아가기](#목차)
| Status Code | Message                                      | Description                                            |
| ----------- | -------------------------------------------- | ------------------------------------------------------ |
| 200         | PERSONALIZATION_INGEST_SUCCESS               | 개인화 파라미터 생성 및 AI DB 저장 성공                              |
| 400         | PERSONALIZATION_INGEST_BAD_REQUEST           | 잘못된 요청 형식(필수 필드 누락, JSON 구조 오류 등)                      |
| 422         | PERSONALIZATION_INGEST_VALIDATION_ERROR      | 입력 값 검증 실패(HH:MM 형식 오류, enum 값 오류, createdAt 포맷 오류 등)  |
| 409         | PERSONALIZATION_INGEST_CONFLICT              | 데이터 충돌/정책 위반(예: scheduleId가 schedules[].taskId와 불일치 등) |
| 500         | PERSONALIZATION_INGEST_INTERNAL_SERVER_ERROR | 개인화 파라미터 생성/저장 중 서버 내부 오류                              |
| 503         | PERSONALIZATION_INGEST_SERVICE_UNAVAILABLE   | AI DB/개인화 엔진 장애 또는 타임아웃으로 서비스 이용 불가                    |

### 4) WEEKLY_REPORT의 Status Code
### **↑** [목차로 돌아가기](#목차)
| Status Code | Message                             | Description                                                    |
| ----------- | ----------------------------------- | -------------------------------------------------------------- |
| 200         | WEEKLY_REPORT_SUCCESS               | 주간 레포트 생성 및 백엔드 전달 성공                                          |
| 400         | WEEKLY_REPORT_BAD_REQUEST           | 잘못된 요청 형식(필수 필드 누락, JSON 구조 오류 등)                              |
| 422         | WEEKLY_REPORT_VALIDATION_ERROR      | 입력 값 검증 실패(ISO 8601 포맷 오류, BIGINT 범위 오류, baseTime 월요일 조건 위반 등) |
| 404         | WEEKLY_REPORT_DATA_NOT_FOUND        | 레포트 생성에 필요한 직전 1주 데이터가 AI DB에 없음                               |
| 409         | WEEKLY_REPORT_CONFLICT              | 동일 reportId로 이미 레포트가 생성됨(중복 생성/아이템포턴시 충돌)                      |
| 500         | WEEKLY_REPORT_INTERNAL_SERVER_ERROR | 레포트 생성(LLM/로직) 중 서버 내부 오류                                      |
| 503         | WEEKLY_REPORT_SERVICE_UNAVAILABLE   | AI DB/LLM 등 의존성 장애 또는 타임아웃으로 서비스 이용 불가                         |

### 5) CHAT_RESPOND의 Status Code
### **↑** [목차로 돌아가기](#목차)
| Status Code | Message                            | Description                                           |
| ----------- | ---------------------------------- | ----------------------------------------------------- |
| 200         | CHAT_RESPOND_SUCCESS               | 요청 성공 (응답 생성 세션 접수 및 messageId 반환)                    |
| 400         | CHAT_RESPOND_INVALID_REQUEST | messages/content/messageId 등 검증 실패 |
| 401         | UNAUTHORIZED                 | 토큰 유효하지 않음                         |
| 403         | FORBIDDEN                    | reportId 접근 권한 없음                  |
| 404         | CHAT_RESPOND_NOT_FOUND       | reportId 없음 등                      |
| 409         | CHAT_RESPOND_CONFLICT        | 동일 세션/동일 messageId로 생성 중           |
| 500         | INTERNAL_SERVER_ERROR        | 서버 오류                              |


### 6) CHAT_STREAM의 Status Code
### **↑** [목차로 돌아가기](#목차)
| Status Code | Message                           | Description                                       |
| ----------- | --------------------------------- | ------------------------------------------------- |
| 200         | CHAT_STREAM_SUCCESS               | SSE 스트림 연결 성공(start/chunk/complete/error 이벤트로 응답) |
| 401         | UNAUTHORIZED          | 토큰 유효하지 않음             |
| 403         | FORBIDDEN             | reportId 접근 권한 없음      |
| 404         | CHAT_STREAM_NOT_FOUND | messageId 세션 없음/매핑 불가  |
| 409         | CHAT_STREAM_CONFLICT  | 이미 종료된 스트림/중복 구독 정책 위반 |
| 500         | INTERNAL_SERVER_ERROR | 서버 오류                  |


### 7) CHAT_CANCEL의 Status Code
### **↑** [목차로 돌아가기](#목차)
| Status Code | Message                           | Description                                         |
| ----------- | --------------------------------- | --------------------------------------------------- |
| 204         | CHAT_CANCEL_NO_CONTENT            | 취소 성공(세션 상태 CANCELED로 전환, 응답 바디 없음)                 |
| 400         | CHAT_CANCEL_INVALID_REQUEST | reportId/messageId 형식 오류      |
| 401         | UNAUTHORIZED                | 토큰 유효하지 않음                    |
| 403         | FORBIDDEN                   | reportId 접근 권한 없음             |
| 404         | CHAT_CANCEL_NOT_FOUND       | 취소 대상 세션 없음                   |
| 409         | CHAT_CANCEL_CONFLICT        | 이미 COMPLETED/CANCELED 등 상태 충돌 |
| 500         | INTERNAL_SERVER_ERROR       | 서버 오류                         |
  |

# 부록. 서비스 관점의 필요성
### **↑** [목차로 돌아가기](#목차)

### 1. AI 모델과 백엔드 서버의 분리를 통한 독립성 확보
- 입출력 규격(API Spec)이 고정되어 있다면, AI 파트에서 모델 구조를 변경하거나 고도화하더라도 백엔드 시스템은 수정 없이 운용 가능하다.
- 백엔드 개발자는 AI 모듈 내부의 추론 로직(특히 LangGraph의 복잡한 노드 간 통신)을 알 필요 없이 표준화된 인터페이스를 통해 데이터를 전송하고 결과값만 수신하면 된다. (캡슐화)

### 2. 데이터 무결성과 정규화
- API 명세서로 정의된 데이터 스키마는 데이터가 AI 모듈로 유입되는 즉시 **Pydantic**에 기반하여 검증된다. (런타임 에러 사전 차단)
- MCP를 이용한 DB 접근 시, 명세서는 에이전트가 수행할 쿼리 파라미터의 기준이 되어 데이터 검색 및 기록의 정확도를 보장합니다.

### 3. 멀티 에이전트 상태 관리
- LabgGraph와 같은 에이전트 시스템에서는 초기 상태(initial state)의 설정이 추론의 품질을 결정한다.  
API 요청 본문(Request Body)은 LabgGraph의 State 클래스 필드와 동기화 되어, 에이전트 추론 프로세스의 시작점으로서 명확한 설계 근거를 제공한다.

- 또한 API 명세서를 통해 출력되는 응답 포멧을 고정함으로써 프론트엔드에서 안정적으로 데이터를 렌더링할 수 있게 한다.

### 4. 비즈니스 로직
- '하루 1회 제공'과 같은 비즈니스 규칙은 API 단계에서 상태코드를 통해 명확히 제공되어야 한다.
- 명세서에 명시된 추론 속도 임계치는 부하 테스트 및 모니터링 시 서비스의 정상 동작 여부를 판단하는 핵심 지표가 된다.