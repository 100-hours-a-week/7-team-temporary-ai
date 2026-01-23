import unittest
import json
import asyncio
import os
from app.services.planner.nodes.node1_structure import node1_structure_analysis
from app.services.planner.nodes.node2_importance import node2_importance
from app.models.planner.internal import PlannerGraphState
from app.models.planner.request import ArrangementState
from app.models.planner.weights import WeightParams
from app.core.config import settings

class TestIntegrationNode1ToNode2(unittest.IsolatedAsyncioTestCase):
    
    def setUp(self):
        if not settings.gemini_api_key:
            print("WARNING: GEMINI_API_KEY not found. Test might fail.")

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

    async def test_pipeline_flow(self):
        print("\n\n>>> Starting Integration Test: Node 1 -> Node 2 <<<")
        
        # -------------------------------------------------------------
        # 1. Run Node 1 (Structure Analysis - LLM)
        # -------------------------------------------------------------
        print("\n" + "=" * 60)
        print(" [Step 1] Running Node 1: Structure Analysis (LLM)")
        print("=" * 60)
        
        state_after_node1 = await node1_structure_analysis(self.state)
        f_n1 = state_after_node1.taskFeatures
        
        print(f"\n[Node 1 Output] Total Features: {len(f_n1)}")
        print("-" * 80)
        print(f"{'ID':<5} | {'Title':<30} | {'Category':<8} | {'Cog':<5} | {'Grp':<5}")
        print("-" * 80)
        for tid in sorted(f_n1.keys()):
            f = f_n1[tid]
            title = (f.title[:25] + "..") if len(f.title) > 27 else f.title
            grp = f.groupId if f.groupId else "-"
            print(f"{tid:<5} | {title:<30} | {f.category:<8} | {f.cognitiveLoad:<5} | {grp:<5}")
        print("-" * 80)

        # -------------------------------------------------------------
        # 2. Run Node 2 (Importance & Filtering - Logic)
        # -------------------------------------------------------------
        print("\n" + "=" * 60)
        print(" [Step 2] Running Node 2: Importance & Filtering (Request.py)")
        print("=" * 60)
        
        state_after_node2 = node2_importance(state_after_node1)
        f_n2 = state_after_node2.taskFeatures
        
        print(f"\n[Node 2 Output] Total Features (Filtered): {len(f_n2)}")
        print("-" * 80)
        print(f"{'ID':<5} | {'Title':<30} | {'ImpScore':<8} | {'Fatigue':<8} | {'PlanMin':<8}")
        print("-" * 80)
        for tid in sorted(f_n2.keys()):
            f = f_n2[tid]
            title = (f.title[:25] + "..") if len(f.title) > 27 else f.title
            print(f"{tid:<5} | {title:<30} | {f.importanceScore:<8.1f} | {f.fatigueCost:<8.1f} | {f.durationPlanMin:<8}")
        print("-" * 80)
        
        # -------------------------------------------------------------
        # 3. Assertions (Logic Verification)
        # -------------------------------------------------------------
        
        # Check ERROR Filtering
        # Nodes that were categorized as ERROR in Node 1 must NOT exist in Node 2
        tasks_in_n1 = set(f_n1.keys())
        tasks_in_n2 = set(f_n2.keys())
        dropped_tasks = tasks_in_n1 - tasks_in_n2
        
        print(f"\n[Summary] Dropped Tasks (ERROR): {list(dropped_tasks)}")
        
        for dropped_id in dropped_tasks:
             # Verify they were indeed ERROR in Node 1
             cat = f_n1[dropped_id].category
             if cat != "ERROR":
                 print(f"WARNING: Task {dropped_id} was dropped but N1 category was {cat}. Check Logic!")
             else:
                 self.assertEqual(cat, "ERROR")

        self.assertIn(1, f_n2, "Task 1 (Valid) should exist in Node 2")
        print("\n>>> Integration Test Completed Successfully <<<")

if __name__ == '__main__':
    unittest.main()
