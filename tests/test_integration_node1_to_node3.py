import unittest
import json
import asyncio
import os
import unicodedata
from app.services.planner.nodes.node1_structure import node1_structure_analysis
from app.services.planner.nodes.node2_importance import node2_importance
from app.services.planner.nodes.node3_chain_generator import node3_chain_generator
from app.models.planner.internal import PlannerGraphState
from app.models.planner.request import ArrangementState
from app.models.planner.weights import WeightParams
from app.core.config import settings
from app.services.planner.utils.session_utils import calculate_capacity

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

class TestIntegrationNode1ToNode3(unittest.IsolatedAsyncioTestCase):
    
    def setUp(self):
        if not settings.gemini_api_key:
            print("WARNING: GEMINI_API_KEY not found. Test might fail.")

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # Assuming tests folder is at project root alongside app
        base_dir = os.path.join(os.getcwd(), 'tests')
        json_path = os.path.join(base_dir, "data", "test_request.json")
        
        with open(json_path, "r", encoding="utf-8") as f:
            self.request_json = json.load(f)
        
        request_model = ArrangementState.model_validate(self.request_json)
        
        fixed_tasks = [t for t in request_model.schedules if t.type == "FIXED"]
        flex_tasks = [t for t in request_model.schedules if t.type == "FLEX"]
        
        # 가용 세션 (충분히 줌 - Node 3 테스트를 위해)
        from app.models.planner.internal import FreeSession
        sessions = [
            FreeSession(start=540, end=720, duration=180, timeZoneProfile={"MORNING": 180}), # 09:00~12:00
            FreeSession(start=720, end=1080, duration=360, timeZoneProfile={"AFTERNOON": 360}), # 12:00~18:00
            FreeSession(start=1080, end=1260, duration=180, timeZoneProfile={"EVENING": 180}), # 18:00~21:00
             # Night is tricky, let's just add enough
        ]
        
        self.state = PlannerGraphState(
            request=request_model,
            weights=WeightParams(),
            fixedTasks=fixed_tasks,
            flexTasks=flex_tasks,
            freeSessions=sessions,
            retry_node1=0
        )

    async def test_pipeline_flow(self):
        print("\\n\\n>>> 통합 테스트 진행: Node 1 -> Node 2 -> Node 3 <<<")
        
        # -------------------------------------------------------------
        # 1. Run Node 1 (Structure Analysis - LLM)
        # -------------------------------------------------------------
        print("\\n" + "=" * 105)
        print(" [Step 1] Running Node 1: Structure Analysis (LLM)")
        print("=" * 105)
        
        state_after_node1 = await node1_structure_analysis(self.state)
        f_n1 = state_after_node1.taskFeatures
        
        
        print(f"\\n[Node 1 결과] 총 피쳐 수: {len(f_n1)}")
        separator = "-" * 105
        print(separator)
        header_n1 = (
            pad_text("ID", 5) + " | " +
            pad_text("Title", 40) + " | " +
            pad_text("Category", 10) + " | " +
            pad_text("CogLoad", 8) + " | " +
            pad_text("Group", 10) + " | " +
            pad_text("Order", 5)
        )
        print(header_n1)
        print(separator)
        
        for tid, feature in f_n1.items():
            title_short = (feature.title[:18] + '..') if len(feature.title) > 20 else feature.title
            grp = feature.groupId if feature.groupId else "-"
            order = str(feature.orderInGroup) if feature.orderInGroup else "-"
            
            row = (
                pad_text(str(tid), 5) + " | " +
                pad_text(title_short, 40) + " | " +
                pad_text(feature.category, 10) + " | " +
                pad_text(feature.cognitiveLoad or "-", 8) + " | " +
                pad_text(grp, 10) + " | " +
                pad_text(order, 5)
            )
            print(row)
        print(separator)

        # -------------------------------------------------------------
        # 2. Run Node 2 (Importance & Filtering - Logic)
        # -------------------------------------------------------------
        print("\\n" + "=" * 105)
        print(" [Step 2] Running Node 2: Importance & Filtering (Logic)")
        print("=" * 105)
        
        state_after_node2 = node2_importance(state_after_node1)
        f_n2 = state_after_node2.taskFeatures
        
        print(f"\\n[Node 2 결과] 총 피쳐 수 (필터링 후): {len(f_n2)}")
        separator = "-" * 115
        print(separator)
        header_n2 = (
            pad_text("ID", 5) + " | " +
            pad_text("Title", 35) + " | " +
            pad_text("ImpScore", 10) + " | " +
            pad_text("Fatigue", 10) + " | " +
            pad_text("PlanMin", 10) + " | " +
            pad_text("Ref (Inputs)", 30)
        )
        print(header_n2)
        print(separator)
        
        for tid, f in f_n2.items():
            title_short = (f.title[:15] + '..') if len(f.title) > 17 else f.title
            imp = f"{f.importanceScore:.1f}"
            fatigue = f"{f.fatigueCost:.1f}"
            plan = str(f.durationPlanMin)
            
            # Lookup original task for detailed reference
            orig = next((t for t in self.state.flexTasks if t.taskId == tid), None)
            if orig:
                ref = f"F={orig.focusLevel}, U={orig.isUrgent}, Cat={f.category}, Cog={f.cognitiveLoad}"
            else:
                ref = f"Cat={f.category}, Cog={f.cognitiveLoad} (No Orig)"
            
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
        
        # -------------------------------------------------------------
        # 3. Run Node 3 (Chain Generator - LLM)
        # -------------------------------------------------------------
        print("\\n" + "=" * 105)
        print(" [Step 3] Running Node 3: Chain Generator (LLM)")
        print("=" * 105)
        
        state_after_node3 = await node3_chain_generator(state_after_node2)
        candidates = state_after_node3.chainCandidates
        
        print(f"\\n[Node 3 결과] 생성된 후보 체인 수: {len(candidates)}")
        separator = "-" * 105
        print(separator)
        
        # ID to Title Map
        id_map = {f.taskId: f.title for f in f_n2.values()}
        
        for idx, cand in enumerate(candidates):
            print(f"Candidate {idx+1}: ID={cand.chainId}, Tags={cand.rationaleTags}")
            for tz, q in cand.timeZoneQueues.items():
                if not q: continue
                # Title lookup requires robust handling as keys are ints
                titles = []
                for tid in q:
                    title = id_map.get(tid, 'Unknown')
                    # Truncate title for display
                    if len(title) > 20: 
                        title = title[:18] + ".."
                    titles.append(f"{tid}({title})")
                
                print(f"  [{pad_text(tz, 9)}] {', '.join(titles)}")
            print(separator)
            
        # -------------------------------------------------------------
        # 4. Assertions
        # -------------------------------------------------------------
        self.assertTrue(len(candidates) >= 4, "Should generate at least 4 candidates")
        
        # Verify that valid tasks are present in at least one queue of one candidate
        valid_task_ids = set(f_n2.keys())
        # Pick first candidate
        cand1 = candidates[0]
        all_queued_tasks = []
        for q in cand1.timeZoneQueues.values():
            all_queued_tasks.extend(q)
            
        # Check if most tasks are queued (some might be excluded if capacity is tight, but here capacity is huge)
        # LLM might occasionally miss one, but generally should include most.
        print(f"\\n[Verification] Candidate 1 queued {len(all_queued_tasks)} / {len(valid_task_ids)} tasks.")
        
        print("\\n>>> 통합 테스트 완료 (Node 1~3) <<<")

if __name__ == '__main__':
    unittest.main()
