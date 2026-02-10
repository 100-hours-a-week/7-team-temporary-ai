# RunPod 관리 스크립트

이 디렉토리는 RunPod 인스턴스를 관리하기 위한 Python 스크립트를 포함하고 있습니다.

## 사전 요구 사항

1. **Python 패키지 설치**
   
   상위 디렉토리의 `requirements.txt`에 명시된 `runpod` 및 `python-dotenv` 패키지가 설치되어 있어야 합니다.
   ```bash
   pip install -r requirements.txt
   ```

2. **환경 변수 설정**

   `.env` 파일에 `RUNPOD_API_KEY`와 선택적으로 `RUNPOD_POD_ID`가 설정되어 있어야 합니다.
   ```env
   RUNPOD_API_KEY=your_runpod_api_key_here
   RUNPOD_POD_ID=your_runpod_pod_id_here
   ```

## 사용 방법

### Pod 시작

중지된 Pod을 다시 시작합니다.


- **.env 설정 사용:** (환경 변수 `RUNPOD_POD_ID` 필요)
```bash
python runpod/start.py
```

### Pod 중지

실행 중인 Pod을 중지(Halt)합니다.
- **.env 설정 사용:** (환경 변수 `RUNPOD_POD_ID` 필요)
```bash
python runpod/stop.py
```

### Pod ID 확인 방법

1. RunPod 콘솔(https://www.runpod.io/console/pods)에 접속합니다.
2. 'My Pods' 섹션에서 관리하려는 Pod을 찾습니다.
3. Pod 카드의 상단에 표시된 ID(예: `abc123xyz`)를 복사하여 사용합니다.

## 파일 설명

- `start.py`: 지정된 Pod ID의 인스턴스를 시작합니다.
- `stop.py`: 지정된 Pod ID의 인스턴스를 중지합니다.
