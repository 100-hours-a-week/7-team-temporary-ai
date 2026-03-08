import unittest
import asyncio
import os
import sys
from dotenv import load_dotenv

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.llm.gemini_client import get_gemini_client

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
