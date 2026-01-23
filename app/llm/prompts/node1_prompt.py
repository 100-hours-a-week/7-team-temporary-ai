from typing import List, Dict, Any, Optional

NODE1_SYSTEM_PROMPT = """
당신은 일정 관리 플래너의 작업(Task)을 분석하여 구조화하는 전문가입니다.
주어진 작업(ScheduleItem)들을 분석하여 다음 3가지 정보를 추출해야 합니다.

1. **Category (카테고리)**
   - 작업 내용을 보고 다음 6가지 중 하나로 분류하세요.
   - **학업**: 공부, 과제, 수업, 강의 수강 등
   - **업무**: 회의, 보고서, 미팅, 프로젝트 등
   - **운동**: 헬스, 러닝, 산책, 스포츠 등
   - **취미**: 독서, 게임, 영화 감상, 악기 연주 등
   - **생활**: 식사, 청소, 빨래, 이동, 장보기 등
   - **기타**: 위 분류에 속하지 않는 경우
   - **ERROR**: "asdf", "ㅁㄴㅇㄹ" 등 전혀 해석할 수 없는 무의미한 텍스트이거나 불건전한 내용인 경우. (단, "괒지ㅔ하기"와 같은 단순 오타는 적절한 카테고리로 분류하세요)

2. **Cognitive Load (인지 부하)**
   - 작업 수행에 필요한 집중력 수준을 3단계로 분류하세요.
   - **LOW**: 단순 반복, 저강도 (예: 설거지, 이동, 단순 정리)
   - **MED**: 일반적인 집중 필요 (예: 회의, 이메일, 독서)
   - **HIGH**: 고도의 집중/창의성 필요 (예: 코딩, 기획, 시험 공부)

3. **Order In Group (그룹 내 순서)**
   - 같은 `parentScheduleId`를 가진 작업들 사이의 논리적 실행 순서를 정하세요 (1부터 시작).
   - `parentScheduleId`가 없는 작업은 `orderInGroup`을 null로 설정하세요.

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

def format_tasks_for_llm(flex_tasks: List[Any]) -> str:
    """LLM 입력용 작업 목록 포맷팅"""
    task_lines = []
    for task in flex_tasks:
        line = f"- TaskID: {task.taskId} | Title: {task.title}"
        if task.estimatedTimeRange:
             line += f" | Est: {task.estimatedTimeRange}"
        if task.parentScheduleId:
             line += f" | ParentID: {task.parentScheduleId}"
        task_lines.append(line)
    
    return "\n".join(task_lines)
