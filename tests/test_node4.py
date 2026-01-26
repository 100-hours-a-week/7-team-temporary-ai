import unittest
from typing import Dict, List
from app.services.planner.nodes.node4_chain_judgement import apply_closure, overflow_penalty, node4_chain_judgement
from app.models.planner.internal import PlannerGraphState, ChainCandidate, TaskFeature, FreeSession
from app.models.planner.weights import WeightParams
from app.models.planner.request import UserInfo, ArrangementState, ScheduleItem
from app.models.planner.internal import FreeSession

class TestNode4ChainJudgement(unittest.TestCase):

    def make_feature(self, tid, imp, duration, group=None, order=None, fatigue=0.0):
        return TaskFeature(
            taskId=tid,
            dayPlanId=1,
            title=f"Task {tid}",
            type="FLEX",
            importanceScore=imp,
            durationAvgMin=duration,
            durationPlanMin=duration, # For Node 4 durationAvgMin is used but let's consistency
            groupId=group,
            orderInGroup=order,
            fatigueCost=fatigue
        )

    def test_apply_closure(self):
        # Setup: Group "G1" has Order 1 (Task 101) and Order 2 (Task 102)
        features = {
            101: self.make_feature(101, 10, 30, "G1", 1),
            102: self.make_feature(102, 10, 30, "G1", 2),
            999: self.make_feature(999, 10, 30) # Independent
        }
        
        # Case 1: Chain has 102 but not 101 -> Should remove 102
        chain_bad = ChainCandidate(
            chainId="bad",
            timeZoneQueues={"MORNING": [102, 999]}
        )
        closed_bad = apply_closure(chain_bad, features)
        self.assertNotIn(102, closed_bad.timeZoneQueues["MORNING"])
        self.assertIn(999, closed_bad.timeZoneQueues["MORNING"])
        
        # Case 2: Chain has 101 and 102 -> Should keep both
        chain_good = ChainCandidate(
            chainId="good",
            timeZoneQueues={"MORNING": [101, 102]}
        )
        closed_good = apply_closure(chain_good, features)
        self.assertIn(101, closed_good.timeZoneQueues["MORNING"])
        self.assertIn(102, closed_good.timeZoneQueues["MORNING"])

    def test_overflow_penalty(self):
        capacity = 100
        w_overflow = 2.0
        
        # 1. Safe Buffer (Overflow 10 <= 20) -> 0.001 * 10 = 0.01 (Small)
        p1 = overflow_penalty(10, capacity, w_overflow)
        self.assertAlmostEqual(p1, 0.01)
        
        # 2. Penalty Zone (Overflow 30 > 20) -> 2.0 * (30-20)^2 = 2 * 100 = 200
        p2 = overflow_penalty(30, capacity, w_overflow)
        self.assertAlmostEqual(p2, 200.0)

    def test_node4_chain_judgement(self):
        # 1. Setup State
        # Capacity: MORNING=100
        free_sessions = [
            FreeSession(
                start=480, end=580, duration=100, 
                timeZoneProfile={"MORNING": 100}
            )
        ]
        
        user_info = UserInfo(userId=1, focusTimeZone="MORNING", dayEndTime="22:00")
        request = ArrangementState(
            user=user_info,
            startArrange="08:00",
            schedules=[]
        )
        
        # Task Features
        # Task 1: Imp 50, Dur 90
        # Task 2: Imp 50, Dur 40
        features = {
            1: self.make_feature(1, 50.0, 90),
            2: self.make_feature(2, 50.0, 40)
        }
        
        # Chain A: Uses Task 1 (90min <= 100). Safe. Score ~ 50.
        chain_a = ChainCandidate(chainId="A", timeZoneQueues={"MORNING": [1]})
        
        # Chain B: Uses Task A + Task B (130min > 100). Overflow 30.
        # Safe buffer 20. Excess 10. Penalty = w(2.0) * 10^2 = 200.
        # Score = (Include 100) - (Exclude 0) - 200 = -100.
        chain_b = ChainCandidate(chainId="B", timeZoneQueues={"MORNING": [1, 2]})
        
        state = PlannerGraphState(
            request=request,
            weights=WeightParams(),
            freeSessions=free_sessions,
            taskFeatures=features,
            chainCandidates=[chain_a, chain_b]
        )
        
        # 2. Execute Node 4
        new_state = node4_chain_judgement(state)
        
        # 3. Assert Chain A is selected (Score 50 > -100)
        self.assertEqual(new_state.selectedChainId, "A")
        
        # Verify closure didn't break anything
        candidates_map = {c.chainId: c for c in new_state.chainCandidates}
        self.assertEqual(len(candidates_map), 2)

if __name__ == '__main__':
    unittest.main()
