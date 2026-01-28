import json
import unittest
from typing import List, Dict

from app.models.planner.internal import PlannerGraphState, FreeSession, TaskFeature, ChainCandidate
from app.models.planner.request import ArrangementState, UserInfo, ScheduleItem, TimeZone
from app.models.planner.weights import WeightParams
from app.services.planner.nodes.node5_time_assignment import node5_time_assignment

# Mock Helper
def create_mock_state(sessions: List[FreeSession], tasks: Dict[int, TaskFeature], 
                      chain_qs: Dict[str, List[int]]) -> PlannerGraphState:
    user = UserInfo(userId=1, focusTimeZone="MORNING", dayEndTime="23:00")
    req = ArrangementState(user=user, startArrange="09:00", schedules=[], groups=[])
    
    chain = ChainCandidate(chainId="C1", timeZoneQueues=chain_qs)
    
    return PlannerGraphState(
        request=req,
        weights=WeightParams(),
        freeSessions=sessions,
        taskFeatures=tasks,
        chainCandidates=[chain],
        selectedChainId="C1",
        fillRate=0.0
    )

class TestNode5(unittest.TestCase):
    
    def test_basic_assignment(self):
        """기본 배정 테스트: 세션에 쏙 들어가는 경우"""
        print("\n\n[Test: Basic Assignment]")
        # 세션: 09:00(540) ~ 10:00(600) -> 60분 (MORNING)
        session = FreeSession(start=540, end=600, duration=60, timeZoneProfile={"MORNING": 60})
        
        # 작업: 30분짜리
        task = TaskFeature(
            taskId=1, dayPlanId=100, title="Task 1", type="FLEX",
            durationPlanMin=30, durationMaxChunk=90, durationMinChunk=10,
            importanceScore=10
        )
        
        chain_qs = {"MORNING": [1], "AFTERNOON": [], "EVENING": [], "NIGHT": []}
        
        state = create_mock_state([session], {1: task}, chain_qs)
        
        new_state = node5_time_assignment(state)
        
        results = new_state.finalResults
        for res in results:
            print(f" -> {res.title} | {res.startAt}~{res.endAt} | Children: {len(res.children) if res.children else 0}")
            
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].assignmentStatus, "ASSIGNED")
        self.assertEqual(results[0].startAt, "09:00")
        self.assertEqual(results[0].endAt, "09:30")
        self.assertIsNone(results[0].children)
        self.assertEqual(new_state.fillRate, 1.0)

    def test_splitting_and_gap(self):
        """분할 및 Gap 테스트"""
        print("\n[Test: Splitting & Gap]")
        # 세션 1: 09:00(540) ~ 09:40(580) -> 40분 (MORNING)
        s1 = FreeSession(start=540, end=580, duration=40, timeZoneProfile={"MORNING": 40})
        # 세션 2: 10:00(600) ~ 11:00(660) -> 60분 (MORNING)
        s2 = FreeSession(start=600, end=660, duration=60, timeZoneProfile={"MORNING": 60})
        
        # 작업: 60분짜리 (세션 1보다 큼 -> 쪼개져야 함)
        task = TaskFeature(
            taskId=2, dayPlanId=100, title="Long Task", type="FLEX",
            durationPlanMin=60, durationMaxChunk=90, durationMinChunk=10,
            importanceScore=10
        )
        
        chain_qs = {"MORNING": [2], "AFTERNOON": [], "EVENING": [], "NIGHT": []}
        
        state = create_mock_state([s1, s2], {2: task}, chain_qs)
        
        new_state = node5_time_assignment(state)
        
        results = new_state.finalResults
        for res in results:
            print(f" -> {res.title} | {res.assignmentStatus}")
            if res.children:
                for c in res.children:
                    print(f"    - SUB: {c.title} | {c.startAt}~{c.endAt}")
        
        self.assertEqual(len(results), 1)
        res = results[0]
        
        # 부모는 시간 Null, 자식이 있어야 함
        self.assertEqual(res.assignmentStatus, "ASSIGNED")
        self.assertIsNone(res.startAt)
        self.assertIsNone(res.endAt)
        self.assertIsNotNone(res.children)
        self.assertEqual(len(res.children), 2)
        
        # Child 1: 09:00 ~ 09:40 (40분)
        self.assertEqual(res.children[0].startAt, "09:00")
        self.assertEqual(res.children[0].endAt, "09:40")
        self.assertEqual(res.children[0].title, "Long Task - 1")
        
        # Child 2: 10:00 ~ 10:20 (나머지 20분)
        self.assertEqual(res.children[1].startAt, "10:00")
        self.assertEqual(res.children[1].endAt, "10:20")
        self.assertEqual(res.children[1].title, "Long Task - 2")

    def test_max_chunk_gap_deferred(self):
        """MaxChunk 초과 시 분할 없음 (V2로 연기됨)"""
        print("\n[Test: MaxChunk Deferred (No Split)]")
        # 세션: 09:00(540) ~ 12:00(720) -> 180분
        s1 = FreeSession(start=540, end=720, duration=180, timeZoneProfile={"MORNING": 180})
        
        # 작업: 100분짜리 (MaxChunk 90분 초과하지만, 세션이 충분하므로 분할 안 함)
        task = TaskFeature(
            taskId=3, dayPlanId=100, title="Huge Task", type="FLEX",
            durationPlanMin=100, durationMaxChunk=90, durationMinChunk=10,
            importanceScore=10
        )
        
        chain_qs = {"MORNING": [3]}
        state = create_mock_state([s1], {3: task}, chain_qs)
        
        new_state = node5_time_assignment(state)
        results = new_state.finalResults
        
        for res in results:
            print(f" -> {res.title} | {res.startAt}~{res.endAt} | Children: {len(res.children) if res.children else 0}")
            
        res = results[0]
        
        # 분할되지 않아야 함 (V1 정책 변경)
        self.assertEqual(res.assignmentStatus, "ASSIGNED")
        self.assertIsNone(res.children)
        self.assertEqual(res.startAt, "09:00")
        self.assertEqual(res.endAt, "10:40") # 100분

    def test_tail_drop_flattening(self):
        """시간 부족 시 Tail Drop + Flattening 테스트"""
        print("\n[Test: Tail Drop & Flattening]")
        # 세션: 30분만 있음
        s1 = FreeSession(start=540, end=570, duration=30, timeZoneProfile={"MORNING": 30})
        
        # 작업: 60분짜리
        task = TaskFeature(
            taskId=4, dayPlanId=100, title="Drop Task", type="FLEX",
            durationPlanMin=60, durationMaxChunk=90, durationMinChunk=10,
            importanceScore=10
        )
        
        chain_qs = {"MORNING": [4]}
        state = create_mock_state([s1], {4: task}, chain_qs)
        
        new_state = node5_time_assignment(state)
        res = new_state.finalResults[0]
        
        print(f" -> {res.title} | {res.startAt}~{res.endAt} | Children: {len(res.children) if res.children else 0}")

        # 1. 세션 부족으로 30분만 배정 (Splitting 시도)
        # 2. 나머지 30분은 배정 못함 (Tail Drop)
        # 3. 결과적으로 자식이 1개뿐 -> Flattening 로직 발동
        # -> children은 None이고, 본체에 start/end가 박혀야 함
        
        self.assertEqual(res.assignmentStatus, "ASSIGNED")
        self.assertIsNone(res.children) # Flattened!
        self.assertEqual(res.startAt, "09:00")
        self.assertEqual(res.endAt, "09:30") # 30분만 배정됨
        
        # 참고: 사용자는 "60분짜리가 30분만 배정됨"을 알 방법이 현재 스펙상으로는 모호하나(durationPlanMin vs 실제 시간),
        # V1에서는 '가능한 만큼 배정'으로 처리됨.

if __name__ == '__main__':
    unittest.main()
