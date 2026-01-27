import unittest
import json
import os
import sys
import unicodedata
import logfire  # [Logfire] Import

# [Logfire] Configure
logfire.configure(send_to_logfire='if-token-present')
logfire.instrument_pydantic()

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.planner.nodes.node2_importance import node2_importance
from app.models.planner.internal import PlannerGraphState, TaskFeature
from app.models.planner.request import ArrangementState, ScheduleItem
from app.models.planner.weights import WeightParams



def get_display_width(text: str) -> int:
    """한글(CJK) 문자를 포함한 문자열의 실제 터미널 출력 폭 계산"""
    width = 0
    for char in text:
        if unicodedata.east_asian_width(char) in ('F', 'W', 'A'):
            width += 2
        else:
            width += 1
    return width

def pad_text(text: str, length: int) -> str:
    """한글 폭을 고려하여 공백 패딩"""
    current_width = get_display_width(text)
    return text + ' ' * max(0, length - current_width)

class TestNode2Importance(unittest.TestCase):
    
    def setUp(self):
        # 1. Full Dataset from JSON
        base_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(base_dir, "data", "test_request.json")
        
        with open(json_path, "r", encoding="utf-8") as f:
            self.request_json = json.load(f)
        
        request_model = ArrangementState.model_validate(self.request_json)
        
        # 2. Mock Node 1 테스트 출력 데이터
        self.mock_features = {}
        
        def make_feature(item, category, cog_load, group_id=None, order=None):
            return TaskFeature(
                taskId=item.taskId,
                dayPlanId=item.dayPlanId,
                title=item.title,
                type=item.type,
                category=category,
                cognitiveLoad=cog_load,
                groupId=str(group_id) if group_id else None,
                groupLabel=None,
                orderInGroup=order
            )
            
        schedule_map = {t.taskId: t for t in request_model.schedules}
        
        # Node 1 출력 테스트 Mock
        categorization = {
            1: ("학업", "HIGH"),
            2: ("학업", "MED"),
            3: ("업무", "HIGH"),
            4: ("학업", "HIGH"),
            5: ("운동", "MED"),
            6: ("생활", "LOW"),
            101: ("학업", "HIGH"),
            102: ("학업", "MED"),
            103: ("학업", "MED"),
            201: ("학업", "HIGH"),
            202: ("학업", "MED"),
            203: ("학업", "MED"),
            900: ("ERROR", "LOW"),
            901: ("ERROR", "LOW"),
            902: ("ERROR", "LOW"),
            903: ("ERROR", "LOW"),
        }
        
        for tid, (cat, cog) in categorization.items():
            if tid in schedule_map:
                item = schedule_map[tid]
                grp = item.parentScheduleId
                self.mock_features[tid] = make_feature(item, cat, cog, grp)

        fixed_tasks = [t for t in request_model.schedules if t.type == "FIXED"]
        flex_tasks = [t for t in request_model.schedules if t.type == "FLEX"]

        self.state = PlannerGraphState(
            request=request_model,
            weights=WeightParams(), # 테스트이므로 가중치 기본값 사용
            fixedTasks=fixed_tasks,
            flexTasks=flex_tasks,
            taskFeatures=self.mock_features
        )

    def test_node2_structure_processing(self):
        print("\n\n>>> Node 2 테스트 진행 <<<")
        
        # [Logfire] Wrap test execution
        with logfire.span("tests/test_node2.py"):
            new_state = node2_importance(self.state)
        features = new_state.taskFeatures
        
        print(f"\n[Node 2 결과] 총 피쳐 진행수: {len(features)}")
        separator = "-" * 115
        print(separator)
        header = (
            pad_text("ID", 5) + " | " +
            pad_text("Title", 35) + " | " +
            pad_text("ImpScore", 10) + " | " +
            pad_text("Fatigue", 10) + " | " +
            pad_text("PlanMin", 10) + " | " +
            pad_text("Ref (Inputs)", 30)
        )
        print(header)
        print(separator)
        
        for tid, f in features.items():
            title_short = (f.title[:15] + '..') if len(f.title) > 17 else f.title
            imp = f"{f.importanceScore:.1f}"
            fatigue = f"{f.fatigueCost:.1f}"
            plan = str(f.durationPlanMin)
            
            orig = next(t for t in self.state.flexTasks if t.taskId == tid)
            ref = f"F={orig.focusLevel}, U={orig.isUrgent}, Cat={f.category}, Cog={f.cognitiveLoad}"
            
            row = (
                pad_text(str(tid), 5) + " | " +
                pad_text(title_short, 35) + " | " +
                pad_text(imp, 10) + " | " +
                pad_text(fatigue, 10) + " | " +
                pad_text(plan, 10) + " | " +
                pad_text(ref, 30)
            )
            print(row)
            
        print(separator)
        
        # Error 카테고리 검정
        for dropped_id in [900, 901, 902, 903]:
            self.assertNotIn(dropped_id, features, f"Task {dropped_id} (ERROR) should have been dropped.")

if __name__ == '__main__':
    unittest.main()
