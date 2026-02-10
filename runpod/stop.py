import runpod
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# RunPod API Key 설정
runpod.api_key = os.getenv("RUNPOD_API_KEY")

def stop_runpod_pod(pod_id):
    """
    특정 Pod을 중지(Halt)합니다.
    """
    if not pod_id:
        return "Error: Pod ID not provided and RUNPOD_POD_ID not set in .env"
        
    try:
        # stop_pod is confirmed to work by user
        result = runpod.stop_pod(pod_id)
        return result
    except Exception as e:
        return f"Error stopping pod: {str(e)}"

if __name__ == "__main__":
    pod_id = None
    if len(sys.argv) > 1:
        pod_id = sys.argv[1]
    else:
        pod_id = os.getenv("RUNPOD_POD_ID")

    if pod_id:
        print(f"Stopping pod: {pod_id}")
        print(stop_runpod_pod(pod_id))
    else:
        print("Usage: python stop.py <pod_id>")
        print("Or set RUNPOD_POD_ID in .env file")
