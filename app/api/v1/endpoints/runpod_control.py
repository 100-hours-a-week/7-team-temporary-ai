import os
import runpod
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

router = APIRouter()

# RunPod API Key 설정 (환경 변수에서 로드됨을 가정)
# app/main.py에서 dotenv를 로드하므로 여기서도 유효합니다.
runpod.api_key = os.getenv("RUNPOD_API_KEY")

@router.post("/start", summary="Start RunPod Pod")
async def start_pod(
    pod_id: Optional[str] = Query(None, description="The ID of the pod to start. If not provided, uses RUNPOD_POD_ID env var."),
    gpu_count: int = Query(1, description="Number of GPUs to use.")
):
    """
    중지된 RunPod Pod을 다시 시작합니다.
    """
    target_pod_id = pod_id or os.getenv("RUNPOD_POD_ID")
    
    if not target_pod_id:
        raise HTTPException(status_code=400, detail="Pod ID not provided and RUNPOD_POD_ID not set in environment.")

    try:
        # runpod 라이브러리를 사용하여 pod 시작
        # resume_pod requires gpu_count
        result = runpod.resume_pod(target_pod_id, gpu_count)
        return {"status": "success", "data": result, "message": f"Pod {target_pod_id} starting with {gpu_count} GPU(s)."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting pod: {str(e)}")

@router.post("/stop", summary="Stop RunPod Pod")
async def stop_pod(
    pod_id: Optional[str] = Query(None, description="The ID of the pod to stop. If not provided, uses RUNPOD_POD_ID env var.")
):
    """
    실행 중인 RunPod Pod을 중지합니다.
    """
    target_pod_id = pod_id or os.getenv("RUNPOD_POD_ID")
    
    if not target_pod_id:
        raise HTTPException(status_code=400, detail="Pod ID not provided and RUNPOD_POD_ID not set in environment.")

    try:
        # runpod 라이브러리를 사용하여 pod 중지
        result = runpod.stop_pod(target_pod_id)
        return {"status": "success", "data": result, "message": f"Pod {target_pod_id} stopping."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping pod: {str(e)}")
