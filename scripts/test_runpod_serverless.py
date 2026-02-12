import os
import sys
import runpod
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 환경 변수 설정
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")
RUNPOD_TEMPLATE_ID = os.getenv("RUNPOD_TEMPLATE_ID")

if not RUNPOD_API_KEY:
    print("Error: RUNPOD_API_KEY not found in .env")
    sys.exit(1)

# 추가 환경변수 로드 부분 삭제
runpod.api_key = RUNPOD_API_KEY

def create_endpoint():
    """RunPod Serverless 엔드포인트 생성"""
    if not RUNPOD_TEMPLATE_ID:
        print("Error: RUNPOD_TEMPLATE_ID not found in .env")
        return

    print(f"Creating endpoint with Template ID: {RUNPOD_TEMPLATE_ID}...")
    
    try:
        # https://docs.runpod.io/serverless/references/workers#create-endpoint
        endpoint = runpod.create_endpoint(
            name="MOLIP-AI-Test-Endpoint",
            template_id=RUNPOD_TEMPLATE_ID,
            gpu_ids="ADA_24", # RTX 4090 (24GB VRAM)
            # locations="EU", # 특정 지역 강제하지 않음 (가용성 우선)
            workers_min=1, # 항상 1개가 켜져있도록 설정 (Cold Start 방지)
            workers_max=1, # 최대 1개만 실행
            idle_timeout=300, # 테스트를 위해 짧게 설정 (5분)
            flashboot=False, # FlashBoot 끔 (호환성 문제 배제)
            # env={...} # 템플릿에 설정된 값 사용하도록 주석 처리 또는 삭제
        )
        print("✅ Endpoint Created Successfully!")
        print(f"Endpoint ID: {endpoint['id']}")
        print(f"Status: {endpoint.get('status', 'Unknown')}")
        
        print("\n⏳ Waiting for worker allocation (polling status for 10s)...")
        import time
        for _ in range(5):
            time.sleep(2)
            try:
                # 상태 조회 (SDK에 get_endpoint가 있다고 가정)
                ep_info = runpod.get_endpoint(endpoint['id'])
                print(f"Current Status: {ep_info.get('workers', 'N/A')}") 
            except:
                pass

        print("-" * 30)
        print(f"To terminate, run: python scripts/test_runpod_serverless.py terminate {endpoint['id']}")
        
    except Exception as e:
        print(f"❌ Failed to create endpoint: {e}")

def terminate_endpoint(endpoint_id):
    """RunPod Serverless 엔드포인트 삭제 (Terminate isn't exactly the same as pods, it's delete for serverless APIs usually, checking lib)"""
    # runpod 라이브러리의 구조상 serverless endpoint 관리는 create_endpoint / delete_endpoint 등이 있음.
    # 하지만 runpod sdk 문서를 보면 endpoint 관련 함수가 명확하지 않을 수 있어, requests로 fallback하거나 sdk 기능 확인 필요.
    # runpod-python SDK: create_endpoint returns info. To delete, use delete_endpoint(endpoint_id) if exists.
    
    print(f"Terminating (Deleting) Endpoint ID: {endpoint_id}...")
    
    try:
        # runpod 라이브러리(v1.8.1)에 delete_endpoint가 없는 것으로 확인됨.
        # GraphQL을 직접 호출하여 삭제 시도.
        query = f"""
        mutation {{
            deleteEndpoint(id: "{endpoint_id}")
        }}
        """
        # runpod.run_graphql_query는 top-level에 노출되지 않았을 수 있음
        # runpod.api.ctl_commands에서 가져와서 사용
        from runpod.api.ctl_commands import run_graphql_query
        result = run_graphql_query(query)
        
        # 결과 확인 (에러 시 run_graphql_query 내부에서 raise되거나 result에 error가 포함됨)
        # 삭제 성공 시 보통 None 또는 ID 반환
        print(f"Result: {result}")
        print("✅ Endpoint Termination Request Sent!")
        
    except Exception as e:
        print(f"❌ Failed to terminate endpoint: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scripts/test_runpod_serverless.py create")
        print("  python scripts/test_runpod_serverless.py terminate <ENDPOINT_ID>")
        sys.exit(1)

    command = sys.argv[1]

    if command == "create":
        create_endpoint()
    elif command == "terminate":
        if len(sys.argv) < 3:
            print("Error: Missing endpoint_id")
            print("Usage: python scripts/test_runpod_serverless.py terminate <ENDPOINT_ID>")
        else:
            terminate_endpoint(sys.argv[2])
    else:
        print(f"Unknown command: {command}")
