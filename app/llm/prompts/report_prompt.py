import json
from datetime import date
from typing import AsyncGenerator, Annotated, Any

WEEKLY_REPORT_SYSTEM_PROMPT = """You are a professional and empathetic personal AI assistant.
Your task is to analyze the user's past 4 weeks of planner data and generate a comprehensive 'Weekly Report' in Markdown format.
The report should be insightful, encouraging, and structured clearly.

Follow these guidelines for the report structure:
1. **이번 주 요약 (Weekly Summary)**
   - Provide a brief, encouraging summary of how the user spent the last week compared to previous weeks.
2. **주요 성과 및 일정 분석 (Key Achievements & Schedule Analysis)**
   - Highlight the most important tasks the user successfully completed.
   - Analyze the user's schedule patterns based on start and end times.
   - Mention any notable disruptions, unexpected tasks, or schedule changes (based on schedule histories or changes).
3. **다음 주 스케줄링 조언 (Suggestions for Next Week)**
   - Provide actionable, positive advice for the upcoming week based on their past patterns (e.g., maintaining consistent routines, dealing with unexpected events).

Requirements:
- NEVER hallucinate data. Only use the provided history data.
- Write the entire report strictly in Markdown text.
- The language of the report must be Korean.
- Do NOT output any JSON wrapper. Just the raw Markdown string.
"""

def format_report_data_for_llm(base_date: date, raw_data: list[dict[str, Any]]) -> str:
    """
    Supabase에서 조회한 planner_records, record_tasks, schedule_histories 데이터를
    LLM이 이해하기 쉬운 형태의 텍스트로 변환합니다.
    """
    if not raw_data:
        return f"기준 날짜 ({base_date}) 이전 4주간의 데이터가 없습니다."
        
    formatted_entries = []
    
    # plan_date 기준으로 오름차순 정렬
    sorted_data = sorted(raw_data, key=lambda x: x.get("plan_date", ""))
    
    for record in sorted_data:
        plan_date = record.get("plan_date")
        start_arrange = record.get("start_arrange", "")
        day_end_time = record.get("day_end_time", "")
        focus_time_zone = record.get("focus_time_zone", "")
        
        # record_tasks 가공
        tasks = record.get("record_tasks", [])
        tasks_summary = []
        
        # schedule_histories 맵핑을 위해 task 별 내역 정리
        histories = record.get("schedule_histories", [])
        histories_by_task = {}
        for h in histories:
            t_id = h.get("schedule_id")
            if t_id not in histories_by_task:
                histories_by_task[t_id] = []
            
            event_type = h.get("event_type", "")
            prev_s = h.get("prev_start_at", "NULL")
            prev_e = h.get("prev_end_at", "NULL")
            new_s = h.get("new_start_at", "NULL")
            new_e = h.get("new_end_at", "NULL")
            
            if not prev_s: prev_s = "NULL"
            if not prev_e: prev_e = "NULL"
            if not new_s: new_s = "NULL"
            if not new_e: new_e = "NULL"
            
            histories_by_task[t_id].append(f"[{event_type}] {prev_s}~{prev_e} -> {new_s}~{new_e}")

        # Task 시간순 정렬 (start_at 기준)
        def get_start_minutes(t):
            st = t.get("start_at")
            if not st:
                return 9999
            try:
                h, m = map(int, st.split(":"))
                return h * 60 + m
            except:
                return 9999

        sorted_tasks = sorted(tasks, key=get_start_minutes)
        
        for task in sorted_tasks:
            assignment_status = task.get("assignment_status", "")
            if assignment_status == "EXCLUDED":
                continue # EXCLUDED 작업 제외
                
            task_type = task.get("task_type", "FLEX")
            title = task.get("title", "")
            status = task.get("status", "TODO")
            start_at = task.get("start_at") or "?"
            end_at = task.get("end_at") or "?"
            task_id = task.get("task_id")
            
            task_line = f"  - ({task_type}) [{status}] {title} ({start_at} ~ {end_at})"
            
            if task_id in histories_by_task:
                history_str = ", ".join(histories_by_task[task_id])
                task_line += f"  * 변경 이력: {history_str}"
                
            tasks_summary.append(task_line)
            
        entry_str = f"### 날짜: {plan_date}\n"
        entry_str += f"* 하루 설정 시간: {start_arrange} ~ {day_end_time}\n"
        entry_str += f"* 집중 시간대: {focus_time_zone}\n"
        entry_str += "[일정 목록]\n"
        if tasks_summary:
            entry_str += "\n".join(tasks_summary)
        else:
            entry_str += "  - (일정 없음)"
        
        formatted_entries.append(entry_str)

    user_prompt = f"기준 날짜: {base_date}\n\n"
    user_prompt += "다음은 과거 4주간의 플래너 기록입니다. 이 데이터를 바탕으로 사용자에게 분석적이고 유용한 주간 레포트를 작성해주세요:\n\n"
    user_prompt += "\n\n".join(formatted_entries)
    
    return user_prompt
