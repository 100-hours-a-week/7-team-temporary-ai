import unittest
import json
import asyncio
import os
import unicodedata
from app.services.planner.nodes.node1_structure import node1_structure_analysis
from app.services.planner.nodes.node2_importance import node2_importance
from app.models.planner.internal import PlannerGraphState
from app.models.planner.request import ArrangementState
from app.models.planner.weights import WeightParams
from app.core.config import settings

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
        print("\n\n>>> 통합 테스트 진행: Node 1 -> Node 2 <<<")
        
        # -------------------------------------------------------------
        # 1. Run Node 1 (Structure Analysis - LLM)
        # -------------------------------------------------------------
        print("\n" + "=" * 105)
        print(" [Step 1] Running Node 1: Structure Analysis (LLM)")
        print("=" * 105)
        
        state_after_node1 = await node1_structure_analysis(self.state)
        f_n1 = state_after_node1.taskFeatures
        
        print(f"\n[Node 1 결과] 총 피쳐 수: {len(f_n1)}")
        separator = "-" * 105
        print(separator)
        header_n1 = (
            pad_text("ID", 5) + " | " +
            pad_text("Title", 40) + " | " +
            pad_text("Category", 12) + " | " +
            pad_text("CogLoad", 10) + " | " +
            pad_text("GroupId", 10)
        )
        print(header_n1)
        print(separator)
        
        for tid in sorted(f_n1.keys()):
            f = f_n1[tid]
            title_short = (f.title[:18] + '..') if len(f.title) > 20 else f.title
            grp = f.groupId if f.groupId else "-"
            
            row = (
                pad_text(str(tid), 5) + " | " +
                pad_text(title_short, 40) + " | " +
                pad_text(f.category, 12) + " | " +
                pad_text(f.cognitiveLoad or "-", 10) + " | " +
                pad_text(grp, 10)
            )
            print(row)
        print(separator)

        # -------------------------------------------------------------
        # 2. Run Node 2 (Importance & Filtering - Logic)
        # -------------------------------------------------------------
        print("\n" + "=" * 105)
        print(" [Step 2] Running Node 2: Importance & Filtering (Logic)")
        print("=" * 105)
        
        state_after_node2 = node2_importance(state_after_node1)
        f_n2 = state_after_node2.taskFeatures
        
        print(f"\n[Node 2 결과] 총 피쳐 수 (필터링 후): {len(f_n2)}")
        print(separator)
        header_n2 = (
            pad_text("ID", 5) + " | " +
            pad_text("Title", 40) + " | " +
            pad_text("ImpScore", 12) + " | " +
            pad_text("Fatigue", 12) + " | " +
            pad_text("PlanMin", 10)
        )
        print(header_n2)
        print(separator)
        
        for tid in sorted(f_n2.keys()):
            f = f_n2[tid]
            title_short = (f.title[:18] + '..') if len(f.title) > 20 else f.title
            imp = f"{f.importanceScore:.1f}"
            fatigue = f"{f.fatigueCost:.1f}"
            plan = str(f.durationPlanMin)
            
            row = (
                pad_text(str(tid), 5) + " | " +
                pad_text(title_short, 40) + " | " +
                pad_text(imp, 12) + " | " +
                pad_text(fatigue, 12) + " | " +
                pad_text(plan, 10)
            )
            print(row)
        print(separator)
        
        # -------------------------------------------------------------
        # 3. Assertions (Logic Verification)
        # -------------------------------------------------------------
        
        # Check ERROR Filtering
        tasks_in_n1 = set(f_n1.keys())
        tasks_in_n2 = set(f_n2.keys())
        dropped_tasks = tasks_in_n1 - tasks_in_n2
        
        if dropped_tasks:
            print(f"\n[Summary] Dropped Tasks (ERROR): {list(dropped_tasks)}")
        
        for dropped_id in dropped_tasks:
             cat = f_n1[dropped_id].category
             self.assertEqual(cat, "ERROR")

        self.assertIn(1, f_n2, "Task 1 (Valid) should exist in Node 2")
        print("\n>>> 통합 테스트 완료 <<<")

if __name__ == '__main__':
    unittest.main()
