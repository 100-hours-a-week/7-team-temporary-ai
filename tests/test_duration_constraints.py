import unittest
import sys
import os
from typing import List, Dict, Optional

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.planner.internal import PlannerGraphState, FreeSession, TaskFeature, ChainCandidate
from app.models.planner.request import ArrangementState, ScheduleItem
from app.models.planner.weights import WeightParams
from app.services.planner.nodes.node2_importance import node2_importance, DURATION_PARAMS
from app.services.planner.nodes.node5_time_assignment import node5_time_assignment

class TestDurationConstraints(unittest.TestCase):
    def setUp(self):
        # Basic Setup for tests
        self.request = ArrangementState(
            user={
                "userId": 1,
                "focusTimeZone": "MORNING",
                "dayEndTime": "22:00"
            },
            startArrange="09:00",
            schedules=[]
        )
        self.state = PlannerGraphState(
            request=self.request,
            weights=WeightParams()
        )

    def _create_feature(self, task_id, duration_plan, min_chunk=30) -> TaskFeature:
        return TaskFeature(
            taskId=task_id,
            dayPlanId=1,
            title=f"Task {task_id}",
            type="FLEX",
            category="Study",
            durationPlanMin=duration_plan,
            durationMinChunk=min_chunk,
            durationMaxChunk=duration_plan # Simplified
        )

    def _create_session(self, start_min, duration_min) -> FreeSession:
        return FreeSession(
            start=start_min,
            # Ensure end is explicitly start + duration
            end=start_min + duration_min,
            duration=duration_min,
            timeZoneProfile={"MORNING": duration_min}
        )

    def test_minute_under_30_params(self):
        """1. MINUTE_UNDER_30이 30분~40분으로 설정되었는지 확인"""
        params = DURATION_PARAMS["MINUTE_UNDER_30"]
        self.assertEqual(params["min"], 30)
        self.assertEqual(params["plan"], 30)
        self.assertEqual(params["avg"], 30)
        self.assertEqual(params["max"], 40)
        
        # MINUTE_30_TO_60 최소값도 30분인지 확인
        params_30_60 = DURATION_PARAMS["MINUTE_30_TO_60"]
        self.assertEqual(params_30_60["min"], 30)

    def test_scenario_short_session_exclusion(self):
        """2. 세션이 작업(30분)보다 짧은 경우 (예: 20분) -> 배정 실패 확인"""
        # Session: 20 mins
        self.state.freeSessions = [self._create_session(540, 20)] # 09:00~09:20
        
        # Task: 30 mins (MINUTE_UNDER_30의 최소값)
        task_id = 10
        feature = self._create_feature(task_id, 30, min_chunk=30)
        self.state.taskFeatures = {task_id: feature}
        
        # Queueing
        self.state.chainCandidates = [ChainCandidate(chainId="c1", timeZoneQueues={"MORNING": [task_id]})]
        self.state.selectedChainId = "c1"
        
        # Run
        final_state = node5_time_assignment(self.state)
        
        # Check
        res = next((r for r in final_state.finalResults if r.taskId == task_id), None)
        self.assertIsNotNone(res)
        self.assertEqual(res.assignmentStatus, "EXCLUDED", "20분 세션에는 30분 작업이 들어갈 수 없어야 함")

    def test_scenario_splitting_prevented_if_remainder_small(self):
        """3. 분할 시 남은 조각이 30분 미만이면 분할하지 않음 (Splitting Prevention)"""
        # Session: 40 mins
        self.state.freeSessions = [self._create_session(540, 40)] # 09:00~09:40
        
        # Task: 65 mins
        # allocatable: 40 mins
        # remainder: 65 - 40 = 25 mins (< 30 mins MinChunk)
        # -> Should FAIL to assign (EXCLUDED) because splitting creates invalid child
        task_id = 20
        feature = self._create_feature(task_id, 65, min_chunk=30)
        self.state.taskFeatures = {task_id: feature}
        
        self.state.chainCandidates = [ChainCandidate(chainId="c1", timeZoneQueues={"MORNING": [task_id]})]
        self.state.selectedChainId = "c1"
        
        final_state = node5_time_assignment(self.state)
        
        res = next((r for r in final_state.finalResults if r.taskId == task_id), None)
        self.assertEqual(res.assignmentStatus, "EXCLUDED", "남은 조각이 25분이므로 분할되면 안됨")

    def test_scenario_splitting_allowed_if_remainder_valid(self):
        """4. 분할 시 남은 조각이 30분 이상이면 분할 허용"""
        # Session 1: 40 mins
        # Session 2: 40 mins (Context switch gap etc implies separate chunks)
        s1 = self._create_session(540, 40) # 09:00~09:40
        s2 = self._create_session(600, 40) # 10:00~10:40
        self.state.freeSessions = [s1, s2]
        
        # Task: 70 mins
        # allocatable in S1: 40 mins
        # remainder: 70 - 40 = 30 mins (== 30 mins MinChunk)
        # -> Should SPLIT. Child (30 mins) goes to S2.
        task_id = 30
        feature = self._create_feature(task_id, 70, min_chunk=30)
        self.state.taskFeatures = {task_id: feature}
        
        self.state.chainCandidates = [ChainCandidate(chainId="c1", timeZoneQueues={"MORNING": [task_id]})]
        self.state.selectedChainId = "c1"
        
        final_state = node5_time_assignment(self.state)
        
        res = next((r for r in final_state.finalResults if r.taskId == task_id), None)
        self.assertEqual(res.assignmentStatus, "ASSIGNED")
        # Check Children
        # Child 1: 40 mins (S1)
        # Child 2: 30 mins (S2)
        # Note: Depending on Flattening logic, if it has 2 children it stays as children.
        self.assertIsNotNone(res.children)
        self.assertEqual(len(res.children), 2)
        c1 = res.children[0]
        c2 = res.children[1]
        
        # Verify durations roughly
        self.assertTrue("09:00" in c1.startAt)
        self.assertTrue("09:40" in c1.endAt) # 40 mins
        
        self.assertTrue("10:00" in c2.startAt)
        self.assertTrue("10:30" in c2.endAt) # 30 mins

if __name__ == '__main__':
    unittest.main()
