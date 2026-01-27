import unittest
import json
import asyncio
import os
import sys
import unicodedata
import logfire  # [Logfire] Import

# [Logfire] Configure
logfire.configure(send_to_logfire='if-token-present')
logfire.instrument_pydantic()

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.planner.nodes.node1_structure import node1_structure_analysis
from app.services.planner.nodes.node2_importance import node2_importance
from app.services.planner.nodes.node3_chain_generator import node3_chain_generator
from app.services.planner.nodes.node4_chain_judgement import node4_chain_judgement
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

class TestIntegrationNode1ToNode4(unittest.IsolatedAsyncioTestCase):
    
    def setUp(self):
        if not settings.gemini_api_key:
            print("WARNING: GEMINI_API_KEY not found. Test might fail.")

        # Assuming tests folder is at project root alongside app
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # Adjust if needed based on typical structure.
        # If this file is in tests/, base_dir should be project root.
        base_dir = os.path.join(os.getcwd(), 'tests')
        json_path = os.path.join(base_dir, "data", "test_request.json")
        
        with open(json_path, "r", encoding="utf-8") as f:
            self.request_json = json.load(f)
        
        request_model = ArrangementState.model_validate(self.request_json)
        
        fixed_tasks = [t for t in request_model.schedules if t.type == "FIXED"]
        flex_tasks = [t for t in request_model.schedules if t.type == "FLEX"]
        
        from app.services.planner.utils.session_utils import calculate_free_sessions
        
        # Request 정보 기반으로 FreeSession 동적 계산
        sessions = calculate_free_sessions(
            start_arrange_str=request_model.startArrange,
            day_end_time_str=request_model.user.dayEndTime,
            fixed_schedules=fixed_tasks
        )
        
        self.state = PlannerGraphState(
            request=request_model,
            weights=WeightParams(),
            fixedTasks=fixed_tasks,
            flexTasks=flex_tasks,
            freeSessions=sessions,
            retry_node1=0
        )

    async def test_pipeline_flow(self):
        print("\n\n>>> 통합 테스트 진행: Node 1 -> Node 2 -> Node 3 -> Node 4 <<<")
        
        # [Logfire] Wrap test execution
        with logfire.span("tests/test_integration_node1_to_node4.py"):
        
            # -------------------------------------------------------------
            # 1. Run Node 1 (Structure Analysis - LLM)
            # -------------------------------------------------------------
            print("\n" + "=" * 105)
            print(" [Step 1] Running Node 1: Structure Analysis (LLM)")
            print("=" * 105)
            
            state_after_node1 = await node1_structure_analysis(self.state)
            f_n1 = state_after_node1.taskFeatures
            print(f"\n[Node 1 결과] 총 피쳐 수: {len(f_n1)}")

            # -------------------------------------------------------------
            # 2. Run Node 2 (Importance & Filtering - Logic)
            # -------------------------------------------------------------
            print("\n" + "=" * 105)
            print(" [Step 2] Running Node 2: Importance & Filtering (Logic)")
            print("=" * 105)
            
            state_after_node2 = node2_importance(state_after_node1)
            f_n2 = state_after_node2.taskFeatures
            print(f"\n[Node 2 결과] 총 피쳐 수 (필터링 후): {len(f_n2)}")

            # -------------------------------------------------------------
            # 3. Run Node 3 (Chain Generator - LLM)
            # -------------------------------------------------------------
            print("\n" + "=" * 105)
            print(" [Step 3] Running Node 3: Chain Generator (LLM)")
            print("=" * 105)
            
            state_after_node3 = await node3_chain_generator(state_after_node2)
            candidates = state_after_node3.chainCandidates
            print(f"\n[Node 3 결과] 생성된 후보 체인 수: {len(candidates)}")
            
            self.assertTrue(len(candidates) > 0, "Should generate at least 1 candidate")

            # -------------------------------------------------------------
            # 4. Run Node 4 (Chain Judgement - Logic)
            # -------------------------------------------------------------
            print("\n" + "=" * 105)
            print(" [Step 4] Running Node 4: Chain Judgement (Logic)")
            print("=" * 105)
            
            state_after_node4 = node4_chain_judgement(state_after_node3)
            selected_id = state_after_node4.selectedChainId
            
            print(f"\n[Node 4 결과] 선택된 최적 체인 ID: {selected_id}")
            
            separator = "-" * 105
            print(separator)
            
            # 선택된 체인 상세 정보 출력
            selected_chain = next((c for c in state_after_node4.chainCandidates if c.chainId == selected_id), None)
            
            self.assertIsNotNone(selected_chain, "Selected chain must exist in candidates")
            
            print(f"Selected Chain: {selected_id}")
            if selected_chain:
                print(f"Tags: {selected_chain.rationaleTags}")
                
                # ID to Title Map
                id_map = {f.taskId: f.title for f in f_n2.values()}
                
                for tz, q in selected_chain.timeZoneQueues.items():
                    if not q: continue
                    titles = []
                    for tid in q:
                        title = id_map.get(tid, 'Unknown')
                        if len(title) > 20: 
                            title = title[:18] + ".."
                        titles.append(f"{tid}({title})")
                    
                    print(f"  [{pad_text(tz, 9)}] {', '.join(titles)}")
            
            print(separator)
            print("\n>>> 통합 테스트 1~4 완료 <<<")

if __name__ == '__main__':
    unittest.main()
