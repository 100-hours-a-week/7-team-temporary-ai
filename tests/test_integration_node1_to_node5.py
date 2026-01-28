import unittest
import json
import asyncio
import os
import sys
import unicodedata
import logfire

# [Logfire] Configure
logfire.configure(send_to_logfire='if-token-present')
logfire.instrument_pydantic()

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.planner.nodes.node1_structure import node1_structure_analysis
from app.services.planner.nodes.node2_importance import node2_importance
from app.services.planner.nodes.node3_chain_generator import node3_chain_generator
from app.services.planner.nodes.node4_chain_judgement import node4_chain_judgement
from app.services.planner.nodes.node5_time_assignment import node5_time_assignment
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

class TestIntegrationNode1ToNode5(unittest.IsolatedAsyncioTestCase):
    
    def setUp(self):
        if not settings.gemini_api_key:
            print("WARNING: GEMINI_API_KEY not found. Test might fail.")

        # Assuming tests folder is at project root alongside app
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # Adjust if needed based on typical structure.
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
        print("\n\n>>> 통합 테스트 진행: Node 1 -> Node 5 (Full Pipeline) <<<")
        
        with logfire.span("tests/test_integration_node1_to_node5.py"):
        
            # 1. Node 1
            print("\n[Step 1] Running Node 1: Structure Analysis (LLM)")
            state_after_node1 = await node1_structure_analysis(self.state)
            
            # 2. Node 2
            print("\n[Step 2] Running Node 2: Importance & Filtering (Logic)")
            state_after_node2 = node2_importance(state_after_node1)
            f_n2 = state_after_node2.taskFeatures

            # 3. Node 3
            print("\n[Step 3] Running Node 3: Chain Generator (LLM)")
            state_after_node3 = await node3_chain_generator(state_after_node2)
            candidates = state_after_node3.chainCandidates
            self.assertTrue(len(candidates) > 0, "No chain candidates generated")

            # 4. Node 4
            print("\n[Step 4] Running Node 4: Chain Judgement (Logic)")
            state_after_node4 = node4_chain_judgement(state_after_node3)
            selected_id = state_after_node4.selectedChainId
            print(f"Selected Chain: {selected_id}")
            
            # Print Selected Chain Details
            selected_chain = next((c for c in state_after_node4.chainCandidates if c.chainId == selected_id), None)
            if selected_chain:
                print(f" -> Rationale: {selected_chain.rationaleTags}")
                print(f" -> Queues:")
                for tz, tids in selected_chain.timeZoneQueues.items():
                    print(f"    - {pad_text(tz, 10)}:")
                    for tid in tids:
                        # taskFeatures에서 title 조회
                        feat = state_after_node4.taskFeatures.get(tid)
                        title = feat.title if feat else "Unknown"
                        print(f"      * [{tid}] {title}")
            else:
                print(" -> WARNING: Selected chain not found in candidates list.")

            # 5. Node 5
            print("\n[Step 5] Running Node 5: Time Assignment (Logic)")
            state_after_node5 = node5_time_assignment(state_after_node4)
            final_results = state_after_node5.finalResults
            
            # ----------------------------------------------------------------
            # 결과 출력 및 검증
            # ----------------------------------------------------------------
            print("\n" + "=" * 115)
            print(" [FINAL RESULTS (Including FIXED)]")
            print("=" * 115)
            
            header = (
                pad_text("ID", 5) + " | " +
                pad_text("Title", 30) + " | " +
                pad_text("Type", 8) + " | " +
                pad_text("Status", 10) + " | " +
                pad_text("Time", 15) + " | " +
                pad_text("HasChild", 8)
            )
            print(header)
            print("-" * 115)
            
            # Combine FLEX results and FIXED tasks for display
            display_list = []
            
            # 1. FLEX Results from Node 5
            # 1. FLEX Results from Node 5
            for res in final_results:
                if res.children:
                    # Parent with children: Add children as individual items
                    for i, child in enumerate(res.children):
                        display_list.append({
                            "id": f"{res.taskId}-{i+1}", # Show sub-id
                            "title": child.title,
                            "type": "SUB",
                            "status": "ASSIGNED",
                            "start": child.startAt,
                            "end": child.endAt,
                            "parent_id": res.taskId,
                            "sort_key": child.startAt,
                            "children": None
                        })
                else:
                    # Normal task (or Excluded)
                    display_list.append({
                        "id": res.taskId,
                        "title": res.title,
                        "type": "FLEX",
                        "status": res.assignmentStatus,
                        "start": res.startAt,
                        "end": res.endAt,
                        "parent_id": None,
                        "sort_key": res.startAt if res.startAt else "99:99",
                        "children": res.children
                    })
                
            # 2. FIXED Tasks from State
            fixed_tasks = state_after_node5.fixedTasks
            for ft in fixed_tasks:
                display_list.append({
                    "id": ft.taskId,
                    "title": ft.title,
                    "type": "FIXED",
                    "status": "ASSIGNED",
                    "start": ft.startAt,
                    "end": ft.endAt,
                    "children": None,
                    "sort_key": ft.startAt
                })
                
            # Sort by start time
            display_list.sort(key=lambda x: x["sort_key"])
            
            assigned_count = 0
            split_count = 0
            
            for item in display_list:
                title_short = (item["title"][:28] + '..') if len(item["title"]) > 30 else item["title"]
                status = item["status"]
                
                time_range = "-"
                if item["start"] and item["end"]:
                    time_range = f"{item['start']}~{item['end']}"
                
                has_child = "Yes" if item["children"] else "No"
                if item["children"]:
                    split_count += 1
                
                if status == "ASSIGNED":
                    assigned_count += 1

                row = (
                    pad_text(str(item["id"]), 5) + " | " +
                    pad_text(title_short, 30) + " | " +
                    pad_text(item["type"], 8) + " | " +
                    pad_text(status, 10) + " | " +
                    pad_text(time_range, 15) + " | " +
                    pad_text(has_child, 8)
                )
                print(row)
                
                # 자식(분할 작업)이 있다면 추가 출력
                if item["children"]:
                    for child in item["children"]:
                        c_title = (child.title[:25] + '..') if len(child.title) > 27 else child.title
                        c_row = (
                            pad_text("  ->", 5) + " | " +
                            pad_text(c_title, 30) + " | " +
                            pad_text("SUB", 8) + " | " +
                            pad_text("ASSIGNED", 10) + " | " +
                            pad_text(f"{child.startAt}~{child.endAt}", 15) + " | " +
                            pad_text("-", 8)
                        )
                        print(c_row)
            
            print("=" * 115)
            # Counts are mixed now, but that's fine for display

            print(f"Total Tasks: {len(final_results)}")
            print(f"Assigned: {assigned_count}")
            print(f"Excluded: {len(final_results) - assigned_count}")
            print(f"Split Tasks: {split_count}")
            print(f"Fill Rate: {state_after_node5.fillRate:.2f}")
            print("=" * 115)
            
            self.assertTrue(len(final_results) > 0)
            self.assertTrue(state_after_node5.fillRate >= 0.0)

if __name__ == '__main__':
    unittest.main()
