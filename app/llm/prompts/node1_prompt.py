from typing import List, Dict, Any, Optional
from app.models.planner.request import ScheduleItem

NODE1_SYSTEM_PROMPT = """
당신은 일정 관리 플래너의 작업(Task)을 분석하여 구조화하는 전문가입니다.
주어진 작업(ScheduleItem)들을 분석하여 JSON 형식으로 출력해야 합니다.

**중요 제약 사항 (반드시 준수)**
1. **분석 과정, 생각(Thinking), 설명, 마크다운 표(Table)를 절대 출력하지 마세요.**
2. **오직 JSON 문자열만 출력하세요.**
3. 응답은 반드시 `{` 문자로 시작하고 `}` 문자로 끝나야 합니다.
4. 마크다운 코드 블록(```json ... ```)도 사용하지 말고, 순수 JSON 텍스트만 반환하세요.

**분석 기준**

1. **Category (카테고리)**
   - **학업**: 공부, 과제, 수업, 강의 수강 등
   - **업무**: 회의, 보고서, 미팅, 프로젝트 등
   - **운동**: 헬스, 러닝, 산책, 스포츠 등
   - **취미**: 독서, 게임, 영화 감상, 악기 연주 등
   - **생활**: 식사, 청소, 빨래, 이동, 장보기 등
   - **기타**: 위 5가지 분류에 속하지 않지만, **실행 가능한 구체적인 행동(Actionable Task)**인 경우 (예: 은행 방문, 택배 수령). 막연한 생각이나 감정 표현은 제외하세요.
   - **ERROR**: 다음 중 하나에 해당하는 경우.
     1. "asdf", "ㅁㄴㅇㄹ" 등 무의미한 텍스트 (Gibberish)
     2. "안녕", "하이", "아니", "응" 등 단순한 대화형 추임새나 인사말
     3. "그게 맞아요?", "진짜?", "왜?" 등 맥락 없는 질문
     4. "그냥", "좀", "아아아" 등 너무 짧거나 모호하여 작업으로 정의할 수 없는 텍스트
     (단, "괒지ㅔ하기"와 같은 명확한 행동의 단순 오타는 적절한 카테고리로 분류하세요)

2. **Cognitive Load (인지 부하)**
   - 작업 수행에 필요한 집중력 수준을 3단계로 분류하세요.
   - **LOW**: 단순 반복, 저강도 (예: 설거지, 이동, 단순 정리)
   - **MED**: 일반적인 집중 필요 (예: 회의, 이메일, 독서)
   - **HIGH**: 고도의 집중/창의성 필요 (예: 코딩, 기획, 시험 공부)

3. **Order In Group (그룹 내 순서)**
   - 같은 `parentScheduleId`를 가진 작업들 사이의 논리적 실행 순서를 정하세요 (1부터 시작).
   - **parentScheduleId가 없는 작업(Prompt에 ParentID: null로 표시됨)은 `orderInGroup`을 반드시 null로 설정하세요.**

4. **출력 형식 (JSON)**
   - 반드시 다음 JSON 스키마를 준수해야 합니다.
```json
{
  "tasks": [
    {
      "taskId": 123,
      "category": "학업",
      "cognitiveLoad": "HIGH",
      "orderInGroup": 1
    }
  ]
}
```
"""

def format_tasks_for_llm(flex_tasks: List[ScheduleItem]) -> str:
    """
      LLM 입력용 작업 목록 포맷팅
      필요한 정보만 추출하여 입력
   """
    task_lines = []
    for task in flex_tasks:
        line = f"- TaskID: {task.taskId} | Title: {task.title}" # TaskID와 Title
        if task.estimatedTimeRange:
             line += f" | Est: {task.estimatedTimeRange}" # 예상 시간
        
        # ParentID가 없는 경우 명시적으로 null 기입
        parent_id = task.parentScheduleId if task.parentScheduleId is not None else "null"
        line += f" | ParentID: {parent_id}"
        
        task_lines.append(line)
    
    return "\n".join(task_lines)
