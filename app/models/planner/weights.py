from pydantic import BaseModel
from typing import Dict

class WeightParams(BaseModel):
    w_focus: float = 1.0
    w_urgent: float = 5.0
    w_category: Dict[str, float] = {}
    w_carry_task: float = 2.0
    w_carry_group: float = 1.0
    w_reject_penalty: float = 2.0
    alpha_duration: float = 0.05
    beta_load: float = 1.0
    w_included: float = 1.0
    w_excluded: float = 1.2
    w_overflow: float = 2.0
    w_focus_align: float = 0.8
    w_switch: float = 0.2
    w_fatigue_risk: float = 0.5
    w_instruction: float = 0.3
    instruction_cap: float = 0.4
    clip_min: float = 0.1
    clip_max: float = 5.0
    ema_decay: float = 0.7
