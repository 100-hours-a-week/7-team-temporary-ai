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

    async def test_postgresql_connection(self):
        """AWS RDS PostgreSQL DB 연결 확인 (Select 1)"""
        print("\n>>> [Connectivity] AWS RDS PostgreSQL DB 연결 테스트 시작")
        
        if not settings.database_url:
             print("[WARNING] Database URL 설정이 없습니다. 테스트를 건너뜁니다.")
             return

        try:
            from sqlalchemy import text
            from app.db.session import AsyncSessionLocal
            
            async with AsyncSessionLocal() as session:
                # 가벼운 쿼리 실행
                result = await session.execute(text("SELECT 1"))
                val = result.scalar()
                
                self.assertEqual(val, 1, "DB Select 1 실패")
                print("[SUCCESS] AWS RDS PostgreSQL 연결 및 'SELECT 1' 성공")
                
                # pgvector 확장팩 확인
                vector_check = await session.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'"))
                ext = vector_check.scalar()
                if ext == 'vector':
                    print("[SUCCESS] pgvector 확장팩 활성화 확인됨")
                else:
                    print("[WARNING] pgvector 확장팩이 보이지 않습니다. 스키마 확인 필요")

        except Exception as e:
            print(f"[FAIL] AWS RDS PostgreSQL 연결 실패: {e}")
            self.fail(f"DB 연결 실패: {e}")

if __name__ == '__main__':
    unittest.main()
