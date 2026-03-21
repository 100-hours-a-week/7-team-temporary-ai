import unittest
import asyncio
import os
import sys
from dotenv import load_dotenv

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.llm.gemini_client import get_gemini_client
from app.llm.runpod_client import get_runpod_client

# Load env if available (mainly for local testing)
load_dotenv()

class TestConnectivity(unittest.IsolatedAsyncioTestCase):
    """
    클라우드 환경 연결 테스트
    - 목적: 코드 로직이 아니라, '네트워크'와 '자격 증명(Key)'이 유효한지 확인
    - DB에 쓰기(Write) 작업을 하지 않음
    """

    async def test_gemini_connection(self):
        """Gemini API 연결 확인 (Ping)"""
        print("\n>>> [Connectivity] Gemini API 연결 테스트 시작")
        
        api_key = settings.gemini_api_key
        if not api_key:
            self.fail("[ERROR] GEMINI_API_KEY가 설정되지 않았습니다.")

        try:
            client = get_gemini_client()
            # 가장 가벼운 모델로 가장 짧은 토큰 생성 요청
            response = await client.generate(
                system="You are a ping bot. Reply with 'Pong'.",
                user="Ping"
            )
            print(f"[SUCCESS] Gemini 응답: {response}")
            self.assertTrue(response, "Gemini 응답이 비어있습니다.")
            
        except Exception as e:
            print(f"[FAIL] Gemini 연결 실패: {e}")
            self.fail(f"Gemini API 연결 실패 (방화벽/키 확인 필요): {e}")

    async def test_runpod_connection(self):
        """RunPod vLLM API 연결 확인 (텍스트 응답 생성)"""
        print("\n>>> [Connectivity] RunPod vLLM API 연결 테스트 시작")

        if not settings.runpod_base_url:
            self.skipTest("RUNPOD_BASE_URL이 설정되지 않았습니다.")

        try:
            client = get_runpod_client()
            response = await client.generate_text(
                system="You are a helpful assistant. Answer in Korean. Keep it short.",
                user="한국의 수도는 어디인가요? 한 문장으로 답해주세요."
            )
            print(f"[SUCCESS] RunPod 텍스트 응답: {response}")
            self.assertTrue(response, "RunPod 응답이 비어있습니다.")
            self.assertIn("서울", response, "응답에 '서울'이 포함되어야 합니다.")

        except Exception as e:
            print(f"[FAIL] RunPod 연결 실패: {e}")
            self.fail(f"RunPod vLLM API 연결 실패 (Pod 상태/URL/키 확인 필요): {e}")

    async def test_runpod_json_generation(self):
        """RunPod vLLM API JSON 응답 생성 확인"""
        print("\n>>> [Connectivity] RunPod JSON 생성 테스트 시작")

        if not settings.runpod_base_url:
            self.skipTest("RUNPOD_BASE_URL이 설정되지 않았습니다.")

        try:
            client = get_runpod_client()
            response = await client.generate(
                system="Always respond in valid JSON with keys: answer, confidence.",
                user="한국의 수도는 어디인가요?"
            )
            print(f"[SUCCESS] RunPod JSON 응답: {response}")
            self.assertIsInstance(response, dict, "응답이 dict 형식이어야 합니다.")
            self.assertIn("answer", response, "응답에 'answer' 키가 있어야 합니다.")

        except Exception as e:
            print(f"[FAIL] RunPod JSON 생성 실패: {e}")
            self.fail(f"RunPod JSON 생성 실패: {e}")

    async def test_runpod_fallback_to_gemini(self):
        """RunPod 실패 시 Gemini 폴백 동작 확인"""
        print("\n>>> [Connectivity] RunPod -> Gemini 폴백 테스트 시작")

        if not settings.gemini_api_key:
            self.skipTest("GEMINI_API_KEY가 설정되지 않았습니다.")

        try:
            from app.llm.runpod_client import RunPodClient

            # 잘못된 URL로 RunPod 클라이언트를 생성하여 강제 실패 유도
            import app.llm.runpod_client as rc_module
            original = rc_module._runpod_client
            rc_module._runpod_client = None

            original_url = settings.runpod_base_url
            settings.runpod_base_url = "https://invalid-runpod-url.example.com/v1"
            settings.runpod_api_key = "invalid_key"

            try:
                client = RunPodClient()

                # generate() 폴백 테스트
                response = await client.generate(
                    system="Always respond in valid JSON with keys: answer, confidence.",
                    user="한국의 수도는 어디인가요?"
                )
                print(f"[SUCCESS] Fallback generate() 응답: {response}")
                self.assertIsInstance(response, dict, "폴백 응답이 dict여야 합니다.")

                # generate_text() 폴백 테스트
                text_response = await client.generate_text(
                    system="You are a helpful assistant. Answer in Korean. Keep it short.",
                    user="한국의 수도는 어디인가요? 한 문장으로 답해주세요."
                )
                print(f"[SUCCESS] Fallback generate_text() 응답: {text_response}")
                self.assertTrue(text_response, "폴백 텍스트 응답이 비어있습니다.")

            finally:
                # 원래 설정 복원
                settings.runpod_base_url = original_url
                rc_module._runpod_client = original

        except Exception as e:
            print(f"[FAIL] 폴백 테스트 실패: {e}")
            self.fail(f"RunPod -> Gemini 폴백 실패: {e}")

    async def test_database_connection(self):
        """Database (PostgreSQL) 연결 확인 (Select 1)"""
        print("\n>>> [Connectivity] Database 연결 테스트 시작 (SQLAlchemy)")
        
        if not settings.database_url:
             print("[WARNING] DATABASE_URL 설정이 없습니다. 테스트를 건너뜜.")
             return

        try:
            from sqlalchemy import text
            from app.db.session import engine
            
            async with engine.connect() as conn:
                # 'SELECT 1' is the most basic health check
                result = await conn.execute(text("SELECT 1"))
                value = result.scalar()
                
                self.assertEqual(value, 1, "DB Select 1 결과가 올바르지 않음")
                print(f"[SUCCESS] Database 연결 성공 (result: {value})")

        except Exception as e:
            print(f"[FAIL] Database 연결 실패: {e}")
            self.fail(f"Database 연결 실패 (URL/방화벽 확인 필요): {e}")

if __name__ == '__main__':
    unittest.main()
