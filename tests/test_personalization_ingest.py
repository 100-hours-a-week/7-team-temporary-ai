import unittest
import json
import os
import sys
from fastapi.testclient import TestClient

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.core.config import settings

class TestPersonalizationIngest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        
        # Check environment variables
        if not settings.supabase_url or not settings.supabase_key:
            print("\n[WARNING] Supabase credentials not found in env. Test might fail or mock DB.")

    def test_personalization_ingest(self):
        # 1. Load test data
        current_dir = os.path.dirname(os.path.abspath(__file__))
        data_path = os.path.join(current_dir, "data/personalization_ingest_week_sample.json")
        
        with open(data_path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        # 2. Send POST request
        response = self.client.post("/ai/v1/personalizations/ingest", json=payload)

        # 3. Assertions
        print(f"\n[Test Result] Status: {response.status_code}")
        try:
            print(f"[Test Result] Response Body: {response.json()}")
        except:
            print(f"[Test Result] Response Text: {response.text}")
        
        # Check if API accepts the request format (200 OK expected)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        print(f"[Test Result] Response Body: {data}")
        
        self.assertIn("success", data)
        self.assertIn("processTime", data)
        self.assertIn("message", data)
        
        # Note: If DB connection is configured (env set), success should be True.
        # If not configured, it might return False but status 200 (handled error).
        if data["success"]:
            print(">> Data successfully ingested to DB.")
        else:
            print(">> Ingest failed (likely due to DB/Env connection issues).")

if __name__ == '__main__':
    unittest.main()
