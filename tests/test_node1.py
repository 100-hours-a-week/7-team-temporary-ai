import unittest
import json
import logging
import asyncio
import os
from app.services.planner.nodes.node1_structure import node1_structure_analysis
from app.models.planner.internal import PlannerGraphState
from app.models.planner.request import ArrangementState
from app.models.planner.weights import WeightParams
from app.core.config import settings

# Configure logging to show output
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestNode1Structure(unittest.IsolatedAsyncioTestCase):
    
    def setUp(self):
        if not settings.gemini_api_key:
            print("WARNING: GEMINI_API_KEY not found. Test might fail or should be skipped.")

        base_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(base_dir, "data", "test_request.json")
        
        with open(json_path, "r", encoding="utf-8") as f:
            self.request_json = json.load(f)
        
        request_model = ArrangementState.model_validate(self.request_json)
        
        fixed_tasks = [t for t in request_model.schedules if t.type == "FIXED"]
        flex_tasks = [t for t in request_model.schedules if t.type == "FLEX"]
        
        self.state = PlannerGraphState(
            request=request_model,
            weights=WeightParams(),
            fixedTasks=fixed_tasks,
            flexTasks=flex_tasks,
            retry_node1=0
        )

    async def test_real_llm_execution(self):
        print("\n\n>>> Starting Node 1 Real Execution (Korean Dataset) <<<")
        try:
            new_state = await node1_structure_analysis(self.state)
            features = new_state.taskFeatures
            
            print(f"\n[Execution Result] Total Features Generated: {len(features)}")
            print("-" * 60)
            print(f"{'ID':<5} | {'Title':<20} | {'Category':<8} | {'CogLoad':<6} | {'Group':<8} | {'Order':<5}")
            print("-" * 60)
            
            for tid, feature in features.items():
                title_short = (feature.title[:18] + '..') if len(feature.title) > 20 else feature.title
                grp = feature.groupId if feature.groupId else "-"
                order = feature.orderInGroup if feature.orderInGroup else "-"
                print(f"{tid:<5} | {title_short:<20} | {feature.category:<8} | {feature.cognitiveLoad:<6} | {grp:<8} | {order:<5}")
            print("-" * 60)
            
            f101 = features.get(101)
            if f101:
                self.assertEqual(f101.groupId, "100")
                self.assertEqual(f101.groupLabel, "졸업 프로젝트")
            
            f900 = features.get(900)
            if f900:
                self.assertEqual(f900.category, "ERROR")

        except Exception as e:
             print(f"!!! Execution Failed !!! : {e}")
             raise e

if __name__ == '__main__':
    unittest.main()
