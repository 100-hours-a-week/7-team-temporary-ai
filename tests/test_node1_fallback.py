import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import logging
import sys
import os
import unicodedata
from app.services.planner.nodes.node1_structure import node1_structure_analysis
from app.models.planner.internal import PlannerGraphState
from app.models.planner.request import ArrangementState
from app.models.planner.weights import WeightParams

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

class TestNode1Fallback(unittest.IsolatedAsyncioTestCase):
    
    def setUp(self):
        self.request_json = {
            "user": {
                "userId": 1,
                "focusTimeZone": "MORNING",
                "dayEndTime": "23:00"
            },
            "startArrange": "08:00",
            "schedules": [
                # FIXED (4 items) - Fixed daily routine
                {"taskId": 1001, "dayPlanId": 1, "title": "기상 및 아침 식사", "type": "FIXED", "startAt": "07:30", "endAt": "08:30"},
                {"taskId": 1002, "dayPlanId": 1, "title": "점심 식사", "type": "FIXED", "startAt": "12:00", "endAt": "13:00"},
                {"taskId": 1003, "dayPlanId": 1, "title": "연구실 랩미팅", "type": "FIXED", "startAt": "14:00", "endAt": "15:30"},
                {"taskId": 1004, "dayPlanId": 1, "title": "저녁 식사 및 휴식", "type": "FIXED", "startAt": "18:00", "endAt": "19:00"},
                
                # FLEX - Independent (6 items)
                {"taskId": 1, "dayPlanId": 1, "title": "졸업 논문 관련 논문 리딩", "type": "FLEX", "estimatedTimeRange": "HOUR_1_TO_2", "focusLevel": 9, "isUrgent": True},
                {"taskId": 2, "dayPlanId": 1, "title": "토익 스피킹 모의고사 풀기", "type": "FLEX", "estimatedTimeRange": "MINUTE_30_TO_60", "focusLevel": 8, "isUrgent": False},
                {"taskId": 3, "dayPlanId": 1, "title": "채용 공고 확인 및 자소서 작성", "type": "FLEX", "estimatedTimeRange": "HOUR_1_TO_2", "focusLevel": 9, "isUrgent": True},
                {"taskId": 4, "dayPlanId": 1, "title": "알고리즘 문제 풀이 (코딩테스트)", "type": "FLEX", "estimatedTimeRange": "HOUR_1_TO_2", "focusLevel": 8, "isUrgent": False},
                {"taskId": 5, "dayPlanId": 1, "title": "헬스장 운동", "type": "FLEX", "estimatedTimeRange": "HOUR_1_TO_2", "focusLevel": 4, "isUrgent": False},
                {"taskId": 6, "dayPlanId": 1, "title": "방 정리 및 빨래", "type": "FLEX", "estimatedTimeRange": "MINUTE_30_TO_60", "focusLevel": 2, "isUrgent": False},
                
                # FLEX - Group 1: "졸업 프로젝트" (Parent Task ID: 100)
                {"taskId": 101, "dayPlanId": 1, "title": "졸업 프로젝트 백엔드 API 구현", "type": "FLEX", "estimatedTimeRange": "HOUR_1_TO_2", "parentScheduleId": 100, "focusLevel": 10, "isUrgent": True},
                {"taskId": 102, "dayPlanId": 1, "title": "졸업 프로젝트 API 문서 작성", "type": "FLEX", "estimatedTimeRange": "MINUTE_30_TO_60", "parentScheduleId": 100, "focusLevel": 6, "isUrgent": False},
                {"taskId": 103, "dayPlanId": 1, "title": "졸업 프로젝트 팀원 코드 리뷰", "type": "FLEX", "estimatedTimeRange": "MINUTE_30_TO_60", "parentScheduleId": 100, "focusLevel": 7, "isUrgent": False},

                # FLEX - Group 2: "정보처리기사 실기 준비" (Parent Task ID: 200)
                {"taskId": 201, "dayPlanId": 1, "title": "정보처리기사 기출 1회독", "type": "FLEX", "estimatedTimeRange": "HOUR_1_TO_2", "parentScheduleId": 200, "focusLevel": 8, "isUrgent": True},
                {"taskId": 202, "dayPlanId": 1, "title": "오답 노트 정리", "type": "FLEX", "estimatedTimeRange": "MINUTE_30_TO_60", "parentScheduleId": 200, "focusLevel": 7, "isUrgent": True},
                {"taskId": 203, "dayPlanId": 1, "title": "암기 과목 요약본 암기", "type": "FLEX", "estimatedTimeRange": "MINUTE_30_TO_60", "parentScheduleId": 200, "focusLevel": 6, "isUrgent": False},
                
                # FLEX - Errors (Gibberish)
                {"taskId": 900, "dayPlanId": 1, "title": "asdfasdf", "type": "FLEX", "estimatedTimeRange": "MINUTE_UNDER_30"},
                {"taskId": 901, "dayPlanId": 1, "title": "ㅁㄴㅇㄹ", "type": "FLEX", "estimatedTimeRange": "MINUTE_UNDER_30"},
                {"taskId": 902, "dayPlanId": 1, "title": "!@#$!@#$", "type": "FLEX", "estimatedTimeRange": "MINUTE_UNDER_30"},
                {"taskId": 903, "dayPlanId": 1, "title": "Unknown Gibberish", "type": "FLEX", "estimatedTimeRange": "MINUTE_UNDER_30"},
                
                # Parent Tasks (FIXED types to represent Group Headers)
                {"taskId": 100, "dayPlanId": 1, "title": "졸업 프로젝트", "type": "FIXED", "startAt": "09:00", "endAt": "09:10"},
                {"taskId": 200, "dayPlanId": 1, "title": "정보처리기사 실기 준비", "type": "FIXED", "startAt": "09:10", "endAt": "09:20"}
            ]
        }
        request_model = ArrangementState.model_validate(self.request_json)
        
        # Split fixed and flex tasks properly
        fixed_tasks = [t for t in request_model.schedules if t.type == "FIXED"]
        flex_tasks = [t for t in request_model.schedules if t.type == "FLEX"]
        
        self.state = PlannerGraphState(
            request=request_model,
            weights=WeightParams(),
            fixedTasks=fixed_tasks,
            flexTasks=flex_tasks,
            retry_node1=0
        )

    @patch("app.services.planner.nodes.node1_structure.get_gemini_client")
    async def test_node1_fallback_logic(self, mock_get_client):
        """
        AI가 5번 실패했을 때 시스템이 '기타' 카테고리와 '시간 기반' 인지부하를 정상적으로 부여하는지 테스트
        """
        print("\n>>> Starting Node 1 Fallback/Retry Simulation <<<")
        
        # 5번 모두 예외 발생 시뮬레이션
        mock_client = MagicMock()
        mock_client.generate = AsyncMock(side_effect=Exception("API Connection Failed"))
        mock_get_client.return_value = mock_client
        
        new_state = await node1_structure_analysis(self.state)
        features = new_state.taskFeatures
        
        print(f"\n[Fallback Execution Result] Total Features: {len(features)}")
        separator = "-" * 85
        print(separator)
        header = (
            pad_text("ID", 5) + " | " +
            pad_text("Title", 40) + " | " +
            pad_text("Category", 10) + " | " +
            pad_text("CogLoad", 8)
        )
        print(header)
        print(separator)
        
        for tid, feature in features.items():
            title_short = (feature.title[:18] + '..') if len(feature.title) > 20 else feature.title
            row = (
                pad_text(str(tid), 5) + " | " +
                pad_text(title_short, 40) + " | " +
                pad_text(feature.category, 10) + " | " +
                pad_text(feature.cognitiveLoad, 8)
            )
            print(row)
        print(separator)

        # 검증 1: 재시도 횟수 확인 (초기 1회 + 재시도 4회 = 총 5회)
        self.assertEqual(mock_client.generate.call_count, 5)
        self.assertEqual(new_state.retry_node1, 5)
        
        # 검증 2: Fallback 결과 확인
        f1 = features[1]
        self.assertEqual(f1.category, "기타")
        self.assertEqual(f1.cognitiveLoad, "HIGH") # HOUR_1_TO_2 -> HIGH
        
        # Task 2: MINUTE_30_TO_60 -> MED
        f2 = features[2]
        self.assertEqual(f2.cognitiveLoad, "MED")
        
        print(">>> Fallback Logic Verification Success <<<")

if __name__ == '__main__':
    unittest.main()
