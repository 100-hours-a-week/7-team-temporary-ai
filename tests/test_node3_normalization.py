import unittest
import json
from app.llm.prompts.node3_prompt import format_node3_input
from app.models.planner.internal import TaskFeature

class TestNode3Normalization(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

    def test_normalization_standard(self):
        """Test normalization with a standard range of importance scores."""
        # Scores: 10, 20, 30 -> Min: 10, Max: 30
        # Normalized: (10-10)/20=0.0, (20-10)/20=0.5, (30-10)/20=1.0
        features = {
            1: TaskFeature(taskId=1, dayPlanId=1, title="Low", type="FLEX", importanceScore=10.0),
            2: TaskFeature(taskId=2, dayPlanId=1, title="Mid", type="FLEX", importanceScore=20.0),
            3: TaskFeature(taskId=3, dayPlanId=1, title="High", type="FLEX", importanceScore=30.0),
        }
        
        result_json = format_node3_input(
            task_features=features,
            fixed_schedules=[],
            capacity={"MORNING": 100},
            focus_timezone="MORNING"
        )
        
        result = json.loads(result_json)
        tasks = result["tasks"]
        
        # Sort by taskId to ensure order for checking
        tasks.sort(key=lambda x: x["taskId"])
        
        self.assertEqual(tasks[0]["importance"], 0.0)
        self.assertEqual(tasks[1]["importance"], 0.5)
        self.assertEqual(tasks[2]["importance"], 1.0)

    def test_normalization_single_value(self):
        """Test normalization when there is only one task."""
        # Score: 10 -> Min: 10, Max: 10 -> Normalized: 1.0
        features = {
            1: TaskFeature(taskId=1, dayPlanId=1, title="Only", type="FLEX", importanceScore=10.0),
        }
        
        result_json = format_node3_input(
            task_features=features,
            fixed_schedules=[],
            capacity={"MORNING": 100},
            focus_timezone="MORNING"
        )
        
        result = json.loads(result_json)
        tasks = result["tasks"]
        
        self.assertEqual(tasks[0]["importance"], 1.0)

    def test_normalization_all_same(self):
        """Test normalization when all tasks have the same score."""
        # Scores: 10, 10 -> Min: 10, Max: 10 -> Normalized: 1.0, 1.0
        features = {
            1: TaskFeature(taskId=1, dayPlanId=1, title="A", type="FLEX", importanceScore=10.0),
            2: TaskFeature(taskId=2, dayPlanId=1, title="B", type="FLEX", importanceScore=10.0),
        }
        
        result_json = format_node3_input(
            task_features=features,
            fixed_schedules=[],
            capacity={"MORNING": 100},
            focus_timezone="MORNING"
        )
        
        result = json.loads(result_json)
        tasks = result["tasks"]
        
        for t in tasks:
            self.assertEqual(t["importance"], 1.0)

    def test_normalization_empty(self):
        """Test normalization with empty task list."""
        features = {}
        
        result_json = format_node3_input(
            task_features=features,
            fixed_schedules=[],
            capacity={"MORNING": 100},
            focus_timezone="MORNING"
        )
        
        result = json.loads(result_json)
        self.assertEqual(len(result["tasks"]), 0)

if __name__ == '__main__':
    unittest.main()
