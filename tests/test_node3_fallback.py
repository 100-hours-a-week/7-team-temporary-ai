import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.planner.nodes.node3_chain_generator import node3_chain_generator
from app.models.planner.internal import PlannerGraphState, TaskFeature
from app.models.planner.request import ArrangementState, UserInfo
from app.models.planner.weights import WeightParams

class TestNode3Fallback(unittest.IsolatedAsyncioTestCase):
    @patch("app.services.planner.nodes.node3_chain_generator.get_gemini_client")
    async def test_node3_fallback_logic(self, mock_get_client):
        """
        AI가 5번(4회 재시도 + 1회) 실패했을 때 시스템이 Fallback Chain을 생성하는지 테스트
        """
        print("\\n>>> Starting Node 3 Fallback/Retry Simulation <<<")
        
        # Mock Client: 항상 에러 발생하도록 설정
        mock_client = MagicMock()
        mock_client.generate = AsyncMock(side_effect=Exception("API Connection Failed"))
        mock_get_client.return_value = mock_client
        
        # State 준비
        # State 준비
        req = ArrangementState(
            user=UserInfo(userId=1, focusTimeZone="MORNING", dayEndTime="23:00"),
            startArrange="08:00",
            schedules=[]
        )
        # 1. FIXED Tasks (4 items)
        fixed_tasks = [
            {"taskId": 1001, "dayPlanId": 1, "title": "기상 및 아침 식사", "type": "FIXED", "startAt": "07:30", "endAt": "08:30"},
            {"taskId": 1002, "dayPlanId": 1, "title": "점심 식사", "type": "FIXED", "startAt": "12:00", "endAt": "13:00"},
            {"taskId": 1003, "dayPlanId": 1, "title": "연구실 랩미팅", "type": "FIXED", "startAt": "14:00", "endAt": "15:30"},
            {"taskId": 1004, "dayPlanId": 1, "title": "저녁 식사 및 휴식", "type": "FIXED", "startAt": "18:00", "endAt": "19:00"}
        ]
        from app.models.planner.request import ScheduleItem
        fixed_objs = [ScheduleItem(**t) for t in fixed_tasks]

        # 2. FLEX Tasks (10 items)
        features = {
            1: TaskFeature(taskId=1, dayPlanId=1, title="졸업 논문 논문 리딩", type="FLEX", importanceScore=14.0, category="학업", durationAvgMin=90, groupId=None),
            2: TaskFeature(taskId=2, dayPlanId=1, title="토익 스피킹 모의고사", type="FLEX", importanceScore=9.0, category="학업", durationAvgMin=45, groupId=None),
            3: TaskFeature(taskId=3, dayPlanId=1, title="채용 공고/자소서", type="FLEX", importanceScore=13.5, category="업무", durationAvgMin=90, groupId=None),
            4: TaskFeature(taskId=4, dayPlanId=1, title="알고리즘 코테 풀이", type="FLEX", importanceScore=9.0, category="학업", durationAvgMin=90, groupId=None),
            5: TaskFeature(taskId=5, dayPlanId=1, title="헬스장 운동", type="FLEX", importanceScore=4.5, category="운동", durationAvgMin=90, groupId=None),
            6: TaskFeature(taskId=6, dayPlanId=1, title="방 정리 및 빨래", type="FLEX", importanceScore=3.2, category="생활", durationAvgMin=45, groupId=None),
            # Group 100
            101: TaskFeature(taskId=101, dayPlanId=1, title="졸업 PJT 백엔드 구현", type="FLEX", importanceScore=15.0, category="업무", durationAvgMin=90, groupId="100", orderInGroup=1),
            102: TaskFeature(taskId=102, dayPlanId=1, title="졸업 PJT 문서 작성", type="FLEX", importanceScore=7.0, category="업무", durationAvgMin=45, groupId="100", orderInGroup=2),
            103: TaskFeature(taskId=103, dayPlanId=1, title="졸업 PJT 코드 리뷰", type="FLEX", importanceScore=8.0, category="업무", durationAvgMin=45, groupId="100", orderInGroup=3),
            # Group 200
            201: TaskFeature(taskId=201, dayPlanId=1, title="정처기 기출 1회독", type="FLEX", importanceScore=13.0, category="학업", durationAvgMin=90, groupId="200", orderInGroup=1),
        }

        # 가용 세션 (충분히 줌)
        from app.models.planner.internal import FreeSession
        sessions = [
            FreeSession(start=540, end=720, duration=180, timeZoneProfile={"MORNING": 180}),
            FreeSession(start=720, end=1080, duration=360, timeZoneProfile={"AFTERNOON": 360}),
            FreeSession(start=1080, end=1260, duration=180, timeZoneProfile={"EVENING": 180})
        ]

        state = PlannerGraphState(
            request=req,
            weights=WeightParams(),
            taskFeatures=features,
            fixedTasks=fixed_objs,
            freeSessions=sessions
        )

        # 실행
        new_state = await node3_chain_generator(state)
        
        # 검증 1: 호출 횟수 (초기 1회 + 재시도 4회 = 5회)
        self.assertEqual(mock_client.generate.call_count, 5)
        
        # 검증 2: Fallback 결과 확인
        candidates = new_state.chainCandidates
        self.assertEqual(len(candidates), 1)
        fallback_chain = candidates[0]
        self.assertEqual(fallback_chain.chainId, "fallback_distributed")
        
        # 할당된 taskId 전수 조사
        all_assigned = []
        for q in fallback_chain.timeZoneQueues.values():
            all_assigned.extend(q)
            
        print(f"Fallback Assigned: {len(all_assigned)} / {len(features)}")
        self.assertEqual(len(all_assigned), len(features), "Fallback chain must include ALL flex tasks")
        
        # 검증 3: Integrity Check (Hallucination)
        # 생성된 ID가 원본 features에 모두 존재하는지
        feature_ids = set(features.keys())
        assigned_ids = set(all_assigned)
        
        # 존재하지 않는 ID가 있는지 (Hallucinated IDs)
        hallucinated = assigned_ids - feature_ids
        self.assertEqual(len(hallucinated), 0, f"Detected hallucinated Task IDs: {hallucinated}")
        
        # 누락된 ID가 있는지 (Dropped IDs)
        dropped = feature_ids - assigned_ids
        self.assertEqual(len(dropped), 0, f"Detected dropped Task IDs: {dropped}")
        
        # 상세 출력 (User Request)
        print("\\n[Test] Generated Fallback Candidate:")
        id_map = {f.taskId: f.title for f in features.values()}
        
        cand = fallback_chain
        print(f"Candidate: ID={cand.chainId}, Tags={cand.rationaleTags}")
        for tz, q in cand.timeZoneQueues.items():
            if not q: continue
            titles = [f"{tid}({id_map.get(tid, 'Unknown')})" for tid in q]
            print(f"  [{tz}] {', '.join(titles)}")
        
        print(">>> Node 3 Fallback Logic Verification Success <<<")

if __name__ == '__main__':
    unittest.main()
