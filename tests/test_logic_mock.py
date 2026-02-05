import unittest
import asyncio
import os
import sys
import json
from unittest.mock import MagicMock, patch

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.planner.internal import PlannerGraphState
from app.models.planner.request import ArrangementState
from app.models.planner.weights import WeightParams
from app.services.planner.nodes.node1_structure import node1_structure_analysis
from app.services.planner.nodes.node2_importance import node2_importance
from app.services.planner.nodes.node3_chain_generator import node3_chain_generator
from app.services.planner.nodes.node4_chain_judgement import node4_chain_judgement
from app.services.planner.nodes.node5_time_assignment import node5_time_assignment
from app.services.planner.utils.session_utils import calculate_free_sessions

# Sample Request Data (Embedded for Cloud Safety)
SAMPLE_REQUEST = {
    "user": {
        "userId": 999,
        "dayStartTime": "09:00",
        "dayEndTime": "22:00",
        "focusTimeZone": "AFTERNOON"
    },
    "startArrange": "09:00",
    "schedules": [
        {"taskId": 101, "dayPlanId": 1, "title": "Fixed Meeting", "type": "FIXED", "startAt": "10:00", "endAt": "11:00"},
        {"taskId": 201, "dayPlanId": 1, "title": "Math Study", "type": "FLEX", "estimatedTimeRange": "HOUR_1_TO_2", "dueDateTime": "2024-01-01 22:00"},
        {"taskId": 202, "dayPlanId": 1, "title": "Exercise", "type": "FLEX", "estimatedTimeRange": "MINUTE_30_TO_60", "dueDateTime": "2024-01-01 22:00"}
    ]
}

# Mock Responses
MOCK_NODE1_RESPONSE = {
    "tasks": [
        {"taskId": 201, "category": "학업", "cognitiveLoad": "HIGH", "orderInGroup": 1},
        {"taskId": 202, "category": "운동", "cognitiveLoad": "MED", "orderInGroup": 1}
    ]
}

MOCK_NODE3_RESPONSE = {
    "candidates": [
        {
            "chainId": "mock_chain_1",
            "timeZoneQueues": {
                "MORNING": [],
                "AFTERNOON": [201],
                "EVENING": [202],
                "NIGHT": []
            },
            "rationaleTags": ["mock_tag"]
        }
    ]
}

class MockGeminiClient:
    async def generate(self, system: str, user: str) -> dict:
        # Detect which node is calling based on system prompt content or user input
        if "NODE 1" in system or "category" in system:
            return MOCK_NODE1_RESPONSE
        elif "NODE 3" in system or "chain" in system:
            return MOCK_NODE3_RESPONSE
        return {}

class TestLogicMock(unittest.IsolatedAsyncioTestCase):
    """
    로직 검증용 Mock 테스트
    - 외부 API(LLM)나 DB 연결 없이 순수 '파이썬 코드 로직'만 검증
    - CI/CD 환경에서 안전하게 실행 가능
    """

    def setUp(self):
        # 1. Prepare State
        request_model = ArrangementState.model_validate(SAMPLE_REQUEST)
        fixed_tasks = [t for t in request_model.schedules if t.type == "FIXED"]
        flex_tasks = [t for t in request_model.schedules if t.type == "FLEX"]
        
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

    @patch("app.services.planner.nodes.node1_structure.get_gemini_client")
    @patch("app.services.planner.nodes.node3_chain_generator.get_gemini_client")
    async def test_full_pipeline_logic(self, mock_get_client_node3, mock_get_client_node1):
        """Node 1 -> Node 5 전체 파이프라인 로직 검증 (with Mock LLM)"""
        print("\n>>> [Logic Mock] 전체 파이프라인 시뮬레이션 시작")
        
        # Setup Mock
        mock_client = MockGeminiClient()
        mock_get_client_node1.return_value = mock_client
        mock_get_client_node3.return_value = mock_client
        
        # Node 1: Structure
        state_n1 = await node1_structure_analysis(self.state)
        self.assertIn(201, state_n1.taskFeatures)
        self.assertEqual(state_n1.taskFeatures[201].category, "학업")
        print("[Pass] Node 1 Structure Logic")
        
        # Node 2: Importance
        state_n2 = node2_importance(state_n1)
        self.assertIsNotNone(state_n2.taskFeatures[201].importanceScore)
        print("[Pass] Node 2 Importance Logic")
        
        # Node 3: Chain Gen
        state_n3 = await node3_chain_generator(state_n2)
        self.assertTrue(len(state_n3.chainCandidates) > 0)
        print("[Pass] Node 3 Chain Gen Logic")
        
        # Node 4: Chain Judgement
        state_n4 = node4_chain_judgement(state_n3)
        self.assertIsNotNone(state_n4.selectedChainId)
        print(f"[Pass] Node 4 Judgment Logic (Selected: {state_n4.selectedChainId})")
        
        # Node 5: Time Assignment
        state_n5 = node5_time_assignment(state_n4)
        self.assertTrue(len(state_n5.finalResults) > 0)
        
        # Check result of Task 201 (should be assigned)
        res_201 = next((r for r in state_n5.finalResults if r.taskId == 201), None)
        self.assertIsNotNone(res_201)
        self.assertEqual(res_201.assignmentStatus, "ASSIGNED")
        print(f"[Pass] Node 5 Time Assignment Logic (Task 201: {res_201.startAt}~{res_201.endAt})")

if __name__ == '__main__':
    unittest.main()
