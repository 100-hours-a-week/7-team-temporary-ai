import json
from datetime import date
from typing import List, Dict, Any

WEEKLY_REPORT_SYSTEM_PROMPT = """You are a professional and empathetic personal AI assistant.
Your task is to analyze the user's past 4 weeks of planner data and generate a comprehensive 'Weekly Report' in Markdown format.
The report should be insightful, encouraging, and structured clearly.

Follow these guidelines for the report structure:
1. **이번 주 요약 (Weekly Summary)**
   - Provide a brief, encouraging summary of how the user spent the last week compared to previous weeks.
2. **주요 성과 (Key Achievements)**
   - Highlight the most important or time-consuming tasks the user successfully completed (status: 'DONE').
3. **시간 및 카테고리 분석 (Time & Category Analysis)**
   - Based on 'category', 'fill_rate', and 'duration_plan_min', analyze what the user focused on.
   - Mention any trends (e.g., "Spent more time on 'Work' this week").
4. **다음 주 스케줄링 조언 (Suggestions for Next Week)**
   - Provide actionable, positive advice for the upcoming week based on their past patterns (e.g., avoiding burnout, balancing hobbies).

Requirements:
- NEVER hallucinate data. Only use the provided history data.
- Write the entire report strictly in Markdown text.
- The language of the report must be Korean.
- Do NOT output any JSON wrapper. Just the raw Markdown string.
"""

def format_report_data_for_llm(base_date: date, raw_data: List[Dict[str, Any]]) -> str:
    """
    Supabase에서 조회한 planner_records 및 record_tasks 데이터를
    LLM이 이해하기 쉬운 형태의 텍스트(또는 JSON-like string)로 변환합니다.
    """
    if not raw_data:
        return f"기준 날짜 ({base_date}) 이전 4주간의 데이터가 없습니다."
        
    formatted_entries = []
    
    # plan_date 기준으로 오름차순 정렬
    sorted_data = sorted(raw_data, key=lambda x: x.get("plan_date", ""))
    
    for record in sorted_data:
        plan_date = record.get("plan_date")
        fill_rate = record.get("fill_rate", 0.0)
        total_tasks = record.get("total_tasks", 0)
        assigned_count = record.get("assigned_count", 0)
        
        # record_tasks 가공
        tasks = record.get("record_tasks", [])
        tasks_summary = []
        for task in tasks:
            title = task.get("title", "")
            status = task.get("status", "TODO")
            category = task.get("category", "기타")
            duration = task.get("duration_plan_min", 0)
            
            # FLEX면서 ASSIGNED이고 시간이 있는 경우가 유의미하겠지만,
            # FIXED 일정도 있으므로 간단히 요약
            tasks_summary.append(f"  - [{status}] {title} (카테고리: {category}, 예상/진행 시간: {duration}분)")
            
        entry_str = f"### 날짜: {plan_date}\n"
        entry_str += f"- 가동률(Fill Rate): {float(fill_rate)*100:.1f}%\n"
        entry_str += f"- 전체 FLEX 작업 수: {total_tasks}, 배정된 수: {assigned_count}\n"
        entry_str += "- 기록된 주요 작업:\n" + "\n".join(tasks_summary)
        
        formatted_entries.append(entry_str)

    user_prompt = f"기준 날짜: {base_date}\n\n"
    user_prompt += "다음은 과거 4주간의 플래너 기록입니다. 이 데이터를 바탕으로 사용자에게 주간 레포트를 작성해주세요:\n\n"
    user_prompt += "\n\n".join(formatted_entries)
    
    return user_prompt
