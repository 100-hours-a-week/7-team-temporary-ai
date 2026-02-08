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
from app.services.planner.utils.session_utils import calculate_free_sessions
from app.graphs.planner_graph import planner_graph

# Sample Request Data (Same as test_logic_mock.py)
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

class TestPlannerGraph(unittest.IsolatedAsyncioTestCase):
    """
    LangGraph 통합 테스트
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
    async def test_graph_execution(self, mock_get_client_node3, mock_get_client_node1):
        """LangGraph 파이프라인 전체 실행 검증"""
        print("\n>>> [Graph Mock] LangGraph 파이프라인 시뮬레이션 시작")
        
        # Setup Mock
        mock_client = MockGeminiClient()
        mock_get_client_node1.return_value = mock_client
        mock_get_client_node3.return_value = mock_client
        
        # Execute Graph
        # planner_graph.ainvoke returns a dict
        result_dict = await planner_graph.ainvoke(self.state)
        
        # Convert back to object for assertion convenience
        result_state = PlannerGraphState.model_validate(result_dict)
        
        # Assertions
        print("[Check] Final Results populated")
        self.assertTrue(len(result_state.finalResults) > 0)
        
        # Check result of Task 201
        res_201 = next((r for r in result_state.finalResults if r.taskId == 201), None)
        self.assertIsNotNone(res_201)
        self.assertEqual(res_201.assignmentStatus, "ASSIGNED")
        print(f"[Pass] Task 201 Assigned: {res_201.startAt}~{res_201.endAt}")
        
        # Check Trace (Optional check if logic was correct)
        print("[Pass] Graph Execution Complete")

if __name__ == '__main__':
    unittest.main()
