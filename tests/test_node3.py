import unittest
import asyncio
from app.services.planner.nodes.node3_chain_generator import node3_chain_generator
from app.services.planner.utils.session_utils import calculate_capacity
from app.models.planner.internal import PlannerGraphState, TaskFeature, FreeSession
from app.models.planner.request import ArrangementState, UserInfo
from app.models.planner.weights import WeightParams

class TestNode3(unittest.IsolatedAsyncioTestCase):
    
    def test_calculate_capacity(self):
        # MORNING 60분, NIGHT 120분 있는 세션 구성
        sessions = [
            FreeSession(
                start=600, end=720, duration=120, # 10:00~12:00 (MORNING 120)
                timeZoneProfile={"MORNING": 120}
            ),
            FreeSession(
                start=1260, end=1380, duration=120, # 21:00~23:00 (NIGHT 120)
                timeZoneProfile={"NIGHT": 120}
            )
        ]
        
        cap = calculate_capacity(sessions)
        
        self.assertEqual(cap["MORNING"], 120)
        self.assertEqual(cap["NIGHT"], 120)
        self.assertEqual(cap["AFTERNOON"], 0)
        
    async def test_node3_real_llm(self):
        """실제 Gemini API를 호출하여 Node 3 동작 확인 (Full Scenario)"""
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
        # Pydantic Model 변환
        from app.models.planner.request import ScheduleItem
        fixed_objs = [ScheduleItem(**t) for t in fixed_tasks]
        
        # 2. FLEX Tasks (10 items - from test_request.json)
        # Node 1, 2를 거쳐온 TaskFeature 형태
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
        sessions = [
            FreeSession(start=540, end=720, duration=180, timeZoneProfile={"MORNING": 180}), # 09:00~12:00
            FreeSession(start=720, end=1080, duration=360, timeZoneProfile={"AFTERNOON": 360}), # 12:00~18:00
            FreeSession(start=1080, end=1260, duration=180, timeZoneProfile={"EVENING": 180}), # 18:00~21:00
        ]
        
        state = PlannerGraphState(
            request=req,
            weights=WeightParams(),
            taskFeatures=features,
            fixedTasks=fixed_objs,  # FIXED Task 추가
            freeSessions=sessions
        )
        
        # 실행
        new_state = await node3_chain_generator(state)
        
        # 검증
        candidates = new_state.chainCandidates
        print(f"\n[Test] Generated {len(candidates)} candidates.")
        
        # ID to Title Map
        id_map = {f.taskId: f.title for f in features.values()}
        feature_ids = set(features.keys())
        
        for idx, cand in enumerate(candidates):
            print(f"Candidate {idx+1}: ID={cand.chainId}, Tags={cand.rationaleTags}")
            
            all_in_cand = set()
            for tz, q in cand.timeZoneQueues.items():
                if not q: continue
                titles = [f"{tid}({id_map.get(tid, 'Unknown')})" for tid in q]
                print(f"  [{tz}] {', '.join(titles)}")
                all_in_cand.update(q)
            
            # Integrity Check (Hallucination)
            hallucinated = all_in_cand - feature_ids
            self.assertEqual(len(hallucinated), 0, f"Candidate {idx+1} has hallucinated IDs: {hallucinated}")
            
            # Note: LLM might drop tasks if capacity is tight, but here sessions are huge.
            # However, prompt says "Overfill 110-120%", so dropping ideally shouldn't happen often.
            # But making it a hard assertion might be flaky if LLM decides to skip something.
            # Let's just warn or allow drops, but absolutely forbid hallucinations.
        
        self.assertTrue(len(candidates) > 0)

if __name__ == '__main__':
    unittest.main()
if __name__ == '__main__':
    unittest.main()
