from typing import List, Dict
from app.models.planner.internal import FreeSession
from app.models.planner.request import ScheduleItem, TimeZone
from app.services.planner.utils.time_utils import hhmm_to_minutes, get_timezone

TIME_ZONES = [
    ("MORNING", 480, 720),      # 08:00 - 12:00
    ("AFTERNOON", 720, 1080),   # 12:00 - 18:00
    ("EVENING", 1080, 1260),    # 18:00 - 21:00
    ("NIGHT", 1260, 1920),      # 21:00 - 08:00 (next day 32:00 effectively)
    # Handle wrap around if needed, but usually planner is within a day or early morning
    # For simplicity, if simple Night (0-480) comes, we handle it.
]

def calculate_free_sessions(
    start_arrange_str: str,
    day_end_time_str: str,
    fixed_schedules: List[ScheduleItem]
) -> List[FreeSession]:
    start_min = hhmm_to_minutes(start_arrange_str)
    end_min = hhmm_to_minutes(day_end_time_str)
    
    # If end time is smaller than start (next day), add 24h (1440 min)
    if end_min < start_min:
        end_min += 1440
        
    # [Constraint] Cap at 24:00 (1440 min)
    # Dawn/Early morning planning is not supported yet
    if end_min > 1440:
        end_min = 1440

    # Sort by start time
    valid_fixed = []
    for s in fixed_schedules:
        if s.type == "FIXED" and s.startAt and s.endAt:
            s_start = hhmm_to_minutes(s.startAt)
            s_end = hhmm_to_minutes(s.endAt)
            if s_end < s_start:
                s_end += 1440
            valid_fixed.append((s_start, s_end))
            
    valid_fixed.sort(key=lambda x: x[0])
    
    sessions = []
    current = start_min
    
    for s_start, s_end in valid_fixed:
        # Gap exists?
        if current < s_start:
            # Check if gap is within range
            gap_end = min(s_start, end_min)
            if current < gap_end:
                sessions.append(_create_session(current, gap_end))
        
        current = max(current, s_end)
        if current >= end_min:
            break
            
    # Final gap
    if current < end_min:
        sessions.append(_create_session(current, end_min))
        
    return sessions

def _create_session(start: int, end: int) -> FreeSession:
    duration = end - start
    profile: Dict[TimeZone, int] = {}
    
    # Naive iteration is fast enough for day-scale (max 1440 iters)
    # and safer for complex edge cases
    for m in range(start, end):
        # Normalize to 0-1440 for timezone lookup
        # But wait, get_timezone handles it? 
        # get_timezone(1500) -> 1500%1440 = 60 -> NIGHT
        tz = get_timezone(m)
        profile[tz] = profile.get(tz, 0) + 1
        
    # Fill missing with 0
    for tz_name in ["MORNING", "AFTERNOON", "EVENING", "NIGHT"]:
        if tz_name not in profile:
            profile[tz_name] = 0 # type: ignore
            
    return FreeSession(
        start=start,
        end=end,
        duration=duration,
        timeZoneProfile=profile
    )

def calculate_capacity(free_sessions: List[FreeSession]) -> Dict[str, int]:
    """
    FreeSession 리스트를 순회하며 각 시간대(TimeZone)별 총 가용 시간(분)을 합산합니다.
    """
    capacity = {
        "MORNING": 0,
        "AFTERNOON": 0,
        "EVENING": 0,
        "NIGHT": 0
    }
    
    for session in free_sessions:
        for tz, minutes in session.timeZoneProfile.items():
            if tz in capacity:
                capacity[tz] += minutes
                
    return capacity
