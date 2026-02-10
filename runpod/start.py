import runpod
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# RunPod API Key 설정
runpod.api_key = os.getenv("RUNPOD_API_KEY")

def start_runpod_pod(pod_id, gpu_count=1):
    """
    중지된 Pod을 다시 시작합니다.
    기본값으로 gpu_count=1을 사용합니다.
    """
    if not pod_id:
        return "Error: Pod ID not provided and RUNPOD_POD_ID not set in .env"

    try:
        # resume_pod requires gpu_count
        result = runpod.resume_pod(pod_id, gpu_count)
        return result
    except Exception as e:
        return f"Error starting pod: {str(e)}"

if __name__ == "__main__":
    pod_id = None
    gpu_count = 1
    
    if len(sys.argv) > 1:
        pod_id = sys.argv[1]
        if len(sys.argv) > 2:
            try:
                gpu_count = int(sys.argv[2])
            except ValueError:
                print("Warning: GPU count must be an integer. Using default value 1.")
    else:
        pod_id = os.getenv("RUNPOD_POD_ID")

    if pod_id:
        print(f"Starting pod: {pod_id} with {gpu_count} GPU(s)")
        print(start_runpod_pod(pod_id, gpu_count))
    else:
        print("Usage: python start.py <pod_id> [gpu_count]")
        print("Or set RUNPOD_POD_ID in .env file")
