import json
import logfire  # [Logfire] Import
from typing import List, Dict, Any
from app.models.planner.internal import TaskFeature

NODE3_SYSTEM_PROMPT = """
당신은 일정 최적화 전문가(Scheduler Agent)입니다.
주어진 작업(Tasks)들과 시간대별 가용량(Capacity)을 분석하여, 작업을 배치할 수 있는 **4~6개의 후보 시나리오(Chain Candidates)** 를 제안하세요.

# 목표
- 사용자의 집중 시간대(Focus TimeZone)와 작업의 중요도/특성을 고려하여 최적의 시간대에 작업을 할당해야 합니다.
- 각 시나리오는 서로 다른 전략(예: 중요 작업 우선, 집중 시간대 몰입, 골고루 분산 등)을 가져야 합니다.

# 입력 데이터 설명
1. **Tasks**: 배치해야 할 작업 목록 (중요도, 예상 시간, 그룹 정보 포함)
2. **Capacity**: 각 시간대별(MORNING/AFTERNOON/EVENING/NIGHT) 가용 시간(분 단위)
3. **Focus TimeZone**: 사용자가 가장 집중력 있게 일할 수 있는 선호 시간대
4. **Fixed Schedules**: 이미 확정된 일정 목록 (참고용. 배치 시 이 시간대를 피하거나 전후 관계 고려)

# 배치 규칙 (Constraints)
1. **Capacity Overfill (과적재) 허용**:
   - 각 시간대별 Capacity의 **110% ~ 120%** 까지 할당해도 됩니다. (이후 단계에서 조정됨)
   - Capacity가 0인 시간대에는 절대 배정하지 마세요.

2. **그룹 순서 준수 (Hard Constraint)**:
   - 같은 `groupId`를 가진 작업들은 `orderInGroup` 순서를 반드시 지켜야 합니다.
   - 예: `orderInGroup: 1`인 작업은 `orderInGroup: 2`인 작업보다 먼저(또는 같은 시간대에 앞서) 배치되어야 합니다.

3. **시간대 정의**:
   - MORNING: 08:00 ~ 12:00
   - AFTERNOON: 12:00 ~ 18:00
   - EVENING: 18:00 ~ 21:00
   - NIGHT: 21:00 ~ 08:00

# 출력 형식 (JSON Only)
반드시 아래 JSON 스키마를 준수하여 출력하세요. 마크다운(` ```json `) 없이 raw JSON만 출력하세요.

```json
{
  "candidates": [
    {
      "chainId": "C1",
      "rationaleTags": ["focus_zone_utilization", "high_importance_first"],
      "timeZoneQueues": {
        "MORNING": [101, 102],
        "AFTERNOON": [103],
        "EVENING": [],
        "NIGHT": []
      }
    },
    {
      "chainId": "C2",
      "rationaleTags": ["distribute_load_evenly"],
      "timeZoneQueues": {
        "MORNING": [101],
        "AFTERNOON": [102, 103],
        "EVENING": [],
        "NIGHT": []
      }
    }
  ]
}
```
"""

def format_node3_input(
    task_features: Dict[int, TaskFeature],
    fixed_schedules: List[Dict[str, Any]],
    capacity: Dict[str, int],
    focus_timezone: str
) -> str:
    """
    Node 3 LLM 입력용 데이터 포맷팅
    """
    tasks_list = []
    # 중요도 순으로 정렬하여 보여주는 것이 LLM이 파악하기 좋음
    sorted_features = sorted(task_features.values(), key=lambda x: x.importanceScore, reverse=True)

    for f in sorted_features:
        task_info = {
            "taskId": f.taskId,
            "title": f.title,
            "category": f.category,
            "importance": round(f.importanceScore, 2), # 소수점 2자리 등
            "durationAvg": f.durationAvgMin, # 평가용 평균 시간 사용
            "groupId": f.groupId,
            "orderInGroup": f.orderInGroup
        }
        tasks_list.append(task_info)

    # Fixed Schedules 포맷팅 (LLM에 참고용으로 입력됨)
    fixed_list = []
    for s in fixed_schedules:
        fixed_list.append({
            "title": s.get("title"),
            "startAt": s.get("startAt"),
            "endAt": s.get("endAt")
        })

    user_input = {
        "focusTimeZone": focus_timezone,
        "capacity": capacity,
        "fixedSchedules": fixed_list,
        "tasks": tasks_list
    }
    
    # [Logfire] LLM 입력 데이터 로깅 (Capacity 확인용)
    logfire.info("Node 3 Input Data", input=user_input)

    return json.dumps(user_input, ensure_ascii=False, indent=2)
