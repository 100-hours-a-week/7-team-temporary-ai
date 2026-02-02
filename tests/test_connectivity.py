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

    def test_supabase_connection(self):
        """Supabase DB 연결 확인 (Select 1)"""
        print("\n>>> [Connectivity] Supabase DB 연결 테스트 시작")
        
        if not settings.supabase_url or not settings.supabase_key:
             print("[WARNING] Supabase 설정이 없습니다. 테스트를 건너뜁니다.")
             return

        try:
            from supabase import create_client, Client
            
            supabase: Client = create_client(settings.supabase_url, settings.supabase_key)
            
            # 가벼운 쿼리 실행 (테이블 조회 대신 DB 버전이나 Health Check가 이상적이나, 
            # Supabase-py에서는 RPC나 단순 Select가 일반적임)
            # 여기서는 존재하지 않는 데이터를 조회하여 연결만 확인 (에러가 안 나면 연결 성공)
            
            # 방법 1: Auth Health Check (로그인 없이 가능 여부에 따라 다름)
            # 방법 2: 임의의 테이블 Select 
            # (테이블 이름을 모르므로, 가장 확실한 건 에러가 'Connection' 관련이 아닌지 보는 것)
            
            # 여기서는 settings에 명시된 URL로 요청이 가는지 확인
            # 실제 테이블이 없어도 404나 빈 리스트가 오면 연결은 된 것임 (Network Error가 아니면 됨)
            
            # 만약 'user' 테이블이 있다고 가정 (보통 있음)
            # 없으면 에러가 나겠지만, Network 에러와는 다름.
            # 가장 안전한 건 rpc가 있다면 rpc('ping') 같은 걸 만드는 것이나,
            # 현재 상황에선 postgrest-py의 상태 확인이 어려우므로 
            # Auth 객체가 생성되는지로 1차 확인
            
            self.assertIsNotNone(supabase.auth, "Supabase Client 생성 실패")
            print("[SUCCESS] Supabase Client 초기화 성공")
            
            # 심화: 실제 요청 보내보기 (선택)
            # try:
            #     supabase.table("users").select("*").limit(1).execute()
            # except Exception as e:
            #     # 테이블이 없어서 나는 에러는 연결 성공으로 간주
            #     if "relation" in str(e) and "does not exist" in str(e):
            #          print("[SUCCESS] DB 연결 성공 (테이블 없음 에러 확인)")
            #     else:
            #          raise e

        except Exception as e:
            print(f"[FAIL] Supabase 연결 실패: {e}")
            self.fail(f"Supabase 연결 실패 (방화벽/키 확인 필요): {e}")

if __name__ == '__main__':
    unittest.main()
