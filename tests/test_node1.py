import unittest
import json
import logging
import asyncio
import os
import sys
import unicodedata
from app.services.planner.nodes.node1_structure import node1_structure_analysis
from app.models.planner.internal import PlannerGraphState
from app.models.planner.request import ArrangementState
from app.models.planner.weights import WeightParams
from app.core.config import settings

# Configure logging to show output
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

class TestNode1Structure(unittest.IsolatedAsyncioTestCase):
    
    def setUp(self):
        if not settings.gemini_api_key:
            print("WARNING: GEMINI_API_KEY not found. Test might fail or should be skipped.")

        base_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(base_dir, "data", "test_request.json") # 테스트용 Request 데이터
        
        with open(json_path, "r", encoding="utf-8") as f:
            self.request_json = json.load(f)
        
        request_model = ArrangementState.model_validate(self.request_json) # json 타입 체크 후 클래스 객체 변환
        
        fixed_tasks = [t for t in request_model.schedules if t.type == "FIXED"]
        flex_tasks = [t for t in request_model.schedules if t.type == "FLEX"]
        
        self.state = PlannerGraphState(
            request=request_model,
            weights=WeightParams(),
            fixedTasks=fixed_tasks,
            flexTasks=flex_tasks,
            retry_node1=0
        )

    async def test_real_llm_execution(self):
        print("\n\n>>> Node 1 테스트 진행 <<<")
        try:
            new_state = await node1_structure_analysis(self.state)
            features = new_state.taskFeatures
            
            print(f"\n Node 1 생성 결과 : 총 피쳐 수 {len(features)}개")
            separator = "-" * 105
            print(separator)
            header = (
                pad_text("ID", 5) + " | " +
                pad_text("Title", 40) + " | " +
                pad_text("Category", 10) + " | " +
                pad_text("CogLoad", 8) + " | " +
                pad_text("Group", 10) + " | " +
                pad_text("Order", 5)
            )
            print(header)
            print(separator)
            
            for tid, feature in features.items():
                title_short = (feature.title[:18] + '..') if len(feature.title) > 20 else feature.title
                grp = feature.groupId if feature.groupId else "-"
                order = str(feature.orderInGroup) if feature.orderInGroup else "-"
                
                row = (
                    pad_text(str(tid), 5) + " | " +
                    pad_text(title_short, 40) + " | " +
                    pad_text(feature.category, 10) + " | " +
                    pad_text(feature.cognitiveLoad, 8) + " | " +
                    pad_text(grp, 10) + " | " +
                    pad_text(order, 5)
                )
                print(row)
            print(separator)

        except Exception as e:
             print(f"Node 1 테스트 실패 : {e}")
             raise e

if __name__ == '__main__':
    unittest.main()
