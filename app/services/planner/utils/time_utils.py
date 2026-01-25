from app.models.planner.request import TimeZone

def hhmm_to_minutes(t: str) -> int:
    """Converts 'HH:MM' string to minutes from midnight."""
    if not t:
        return 0
    h, m = map(int, t.split(":"))
    return h * 60 + m

def minutes_to_hhmm(minutes: int) -> str:
    """Converts minutes from midnight to 'HH:MM' string."""
    h = minutes // 60
    m = minutes % 60
    # Handle overflow (24:00+) if necessary, but usually we wrap or keep as is?
    # Let's keep strict 24h format for now or allow 25:00 if needed.
    # For now, simple formatting.
    return f"{h:02d}:{m:02d}"

def get_timezone(minutes: int) -> TimeZone:
    """Returns TimeZone based on minutes from midnight."""
    # 08:00 (480) ~ 12:00 (720) -> MORNING
    # 12:00 (720) ~ 18:00 (1080) -> AFTERNOON
    # 18:00 (1080) ~ 21:00 (1260) -> EVENING
    # 21:00 (1260) ~ 08:00 (480 next day) -> NIGHT
    
    # Normalize to 0-1440
    m = minutes % 1440
    
    if 480 <= m < 720:
        return "MORNING"
    if 720 <= m < 1080:
        return "AFTERNOON"
    if 1080 <= m < 1260:
        return "EVENING"
    return "NIGHT"
