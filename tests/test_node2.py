import unittest
import json
import os
from app.services.planner.nodes.node2_importance import node2_importance
from app.models.planner.internal import PlannerGraphState, TaskFeature
from app.models.planner.request import ArrangementState, ScheduleItem
from app.models.planner.weights import WeightParams

class TestNode2Importance(unittest.TestCase):
    
    def setUp(self):
        # 1. Full Dataset from JSON
        base_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(base_dir, "data", "test_request.json")
        
        with open(json_path, "r", encoding="utf-8") as f:
            self.request_json = json.load(f)
        
        request_model = ArrangementState.model_validate(self.request_json)
        
        # 2. Mock Node 1 Inputs (What Node 1 would ideally produce)
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
        
        # Categorization (Manual Mock matching Node 1 expectations)
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
            weights=WeightParams(),
            fixedTasks=fixed_tasks,
            flexTasks=flex_tasks,
            taskFeatures=self.mock_features
        )

    def test_node2_structure_processing(self):
        print("\n>>> Starting Node 2 Test (Full Dataset, Mocked Node 1) <<<")
        
        new_state = node2_importance(self.state)
        features = new_state.taskFeatures
        
        print(f"\n[Node 2 Result] Total Features Processed: {len(features)}")
        print("-" * 100)
        print(f"{'ID':<5} | {'Title':<20} | {'ImpScore':<8} | {'Fatigue':<8} | {'PlanMin':<8} | {'Ref (Input)'}")
        print("-" * 100)
        
        for tid, f in features.items():
            title_short = (f.title[:18] + '..') if len(f.title) > 20 else f.title
            imp = f"{f.importanceScore:.1f}"
            fatigue = f"{f.fatigueCost:.1f}"
            plan = f.durationPlanMin
            
            orig = next(t for t in self.state.flexTasks if t.taskId == tid)
            ref = f"F={orig.focusLevel}, U={orig.isUrgent}, Cog={f.cognitiveLoad}"
            
            print(f"{tid:<5} | {title_short:<20} | {imp:<8} | {fatigue:<8} | {plan:<8} | {ref}")
            
        print("-" * 100)
        
        # Task 1 (Thesis) Check
        f1 = features[1]
        self.assertAlmostEqual(f1.importanceScore, 14.0)
        
        # Task 6 (Laundry) Check
        f6 = features[6]
        self.assertAlmostEqual(f6.importanceScore, 2.0)
            
        # Verify Filtering (ERROR tasks should be dropped)
        for dropped_id in [900, 901, 902, 903]:
            self.assertNotIn(dropped_id, features, f"Task {dropped_id} (ERROR) should have been dropped.")

        print(">>> Node 2 Full Dataset Verification Success (ERRORs Dropped) <<<")

if __name__ == '__main__':
    unittest.main()
