from typing import List, Set
from app.models.planner.request import ScheduleItem

def filter_parent_tasks(schedules: List[ScheduleItem]) -> List[ScheduleItem]:
    """
    Filter out parent tasks (tasks that are referenced as parentScheduleId by other tasks)
    from the list of schedules. Only returns FLEX tasks that are NOT parents.
    
    Args:
        schedules: List of all schedules (FIXED and FLEX)
        
    Returns:
        List of FLEX ScheduleItem that are valid (not parents)
    """
    # Identify Parent Tasks (Container Tasks)
    parent_ids: Set[int] = set()
    for t in schedules:
        if t.parentScheduleId:
            parent_ids.add(t.parentScheduleId)
            
    # Filter out Parent Tasks from Flex Tasks
    # Parent Tasks are containers and should not be scheduled themselves
    return [
        t for t in schedules 
        if t.type == "FLEX" and t.taskId not in parent_ids
    ]
