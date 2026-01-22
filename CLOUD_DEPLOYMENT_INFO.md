# 클라우드 배포 가이드 (클라우드팀 전달용)

## 개요
MOLIP AI 서버는 FastAPI 기반의 Python 애플리케이션입니다.

## 필수 요구사항
- **Python**: 3.8 이상 (권장: 3.13)
- **pip**: 최신 버전

## 배포할 파일
```
app/                # FastAPI 애플리케이션 소스 코드
requirements.txt    # Python 패키지 목록 (고정 버전)
.env.example        # 환경 변수 예시
Dockerfile          # Docker 이미지 빌드 파일
.dockerignore       # Docker 빌드 시 제외 파일 목록
```

## 환경 변수 설정

### 스테이징 서버
```env
ENVIRONMENT=staging
BACKEND_URL=https://stg.molip.today
ALLOWED_ORIGINS=https://stg.molip.today
DEBUG=False
LOG_LEVEL=INFO
GEMINI_API_KEY=실제_API_키_입력
```

### 프로덕션 서버
```env
ENVIRONMENT=production
BACKEND_URL=https://molip.today
ALLOWED_ORIGINS=https://molip.today
DEBUG=False
LOG_LEVEL=WARNING
GEMINI_API_KEY=실제_API_키_입력
```

### ⚠️ 필수 환경 변수: GEMINI_API_KEY

**이 서버는 Gemini API를 사용하므로 `GEMINI_API_KEY`가 반드시 설정되어야 합니다.**

API 키가 없으면 서버 시작은 되지만, `/ai/v1/planners` API 호출 시 500 에러가 발생합니다.

#### Gemini API 키 발급 방법

1. [Google AI Studio](https://aistudio.google.com/) 접속
2. Google 계정으로 로그인
3. 좌측 메뉴에서 "Get API key" 클릭
4. "Create API key" 버튼 클릭
5. 프로젝트 선택 또는 새 프로젝트 생성
6. 생성된 API 키 복사 (형식: `AIza...`)

#### API 키 보안 주의사항

- API 키는 절대 Git에 커밋하지 마세요
- `.env` 파일은 `.gitignore`에 포함되어 있습니다
- 프로덕션 환경에서는 클라우드 시크릿 매니저 사용 권장

### 환경 변수 설정 방법

**옵션 1: .env 파일**
```bash
vi .env
# 위 내용 입력 후 저장
```

**옵션 2: 클라우드 환경 변수**
- AWS: Systems Manager Parameter Store, Secrets Manager
- GCP: Secret Manager
- Azure: Key Vault
- Kubernetes: ConfigMap, Secret

## 배포 방법

### 1. 기본 배포 (개발/테스트용)
```bash
# 1. 가상환경 생성
python3 -m venv venv
source venv/bin/activate

# 2. 패키지 설치
pip install -r requirements.txt

# 3. 환경 변수 설정 (위 참고)

# 4. 서버 실행
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2. Docker 배포 (권장)

프로젝트에 `Dockerfile`과 `.dockerignore`가 포함되어 있습니다.

**빌드 및 실행:**
```bash
docker build -t molip-ai .
docker run -d \
  -p 8000:8000 \
  -e BACKEND_URL=https://molip.today \
  -e ALLOWED_ORIGINS=https://molip.today \
  -e ENVIRONMENT=production \
  -e DEBUG=False \
  -e LOG_LEVEL=WARNING \
  -e GEMINI_API_KEY=실제_API_키_입력 \
  --name molip-ai \
  molip-ai
```

### 3. systemd 배포 (Linux)
```ini
[Unit]
Description=MOLIP AI Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/molip-ai
Environment="PATH=/opt/molip-ai/venv/bin"
ExecStart=/opt/molip-ai/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

### 4. Gunicorn + Uvicorn Workers (프로덕션 권장)
```bash
# requirements.txt에 gunicorn 추가 필요
pip install gunicorn==23.0.0

# 실행 (워커 4개)
gunicorn app.main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

## Health Check

### 엔드포인트
```
GET http://서버주소:8000/health
```

### 정상 응답
```json
{
  "status": "healthy",
  "app": "MOLIP-AI-Planner",
  "version": "0.1.0 (TEST)",
  "debug": false
}
```

### 로드밸런서 설정
- **Path**: `/health`
- **Protocol**: HTTP
- **Port**: 8000
- **Interval**: 30초
- **Timeout**: 5초
- **Healthy threshold**: 2
- **Unhealthy threshold**: 3

## API 엔드포인트

### TEST API
```
POST http://서버주소:8000/ai/v1/planners
Content-Type: application/json
```

### Swagger UI (API 문서)
```
GET http://서버주소:8000/docs
```

## 포트
- **기본 포트**: 8000
- 변경 시: `PORT` 환경 변수 설정

## CORS
- `ALLOWED_ORIGINS` 환경 변수로 관리
- 스테이징: `https://stg.molip.today`
- 프로덕션: `https://molip.today`
- 여러 도메인: 쉼표로 구분 (예: `https://a.com,https://b.com`)

## 로그

### 로그 레벨 (`LOG_LEVEL` 환경 변수)
- `INFO`: 일반 정보 (스테이징 권장)
- `WARNING`: 경고 이상 (프로덕션 권장)
- `ERROR`: 에러만

### 로그 확인
```bash
# Docker
docker logs -f molip-ai

# systemd
journalctl -u molip-ai -f

# 직접 실행 시 표준 출력
```

## 트러블슈팅

### 서버가 시작되지 않음
```bash
# Python 버전 확인
python3 --version

# 패키지 설치 확인
pip list | grep fastapi

# 환경 변수 확인
env | grep BACKEND_URL

# 포트 사용 확인
lsof -i:8000
```

### CORS 에러
- `ALLOWED_ORIGINS` 환경 변수에 프론트엔드 도메인이 정확히 포함되어 있는지 확인
- 프로토콜(http/https) 포함 필수

## 보안 권장사항

1. **환경 변수**
   - `.env` 파일을 Git에 절대 올리지 마세요
   - 클라우드 시크릿 매니저 사용 권장

2. **프로덕션 설정**
   - `DEBUG=False` 필수
   - `LOG_LEVEL=WARNING` 권장

3. **방화벽**
   - 8000 포트는 로드밸런서/리버스 프록시에서만 접근 가능하도록 설정

## 참고
- **API 명세서**: `api명세서.md` 참고
- **환경 변수 예시**: `.env.example` 참고
