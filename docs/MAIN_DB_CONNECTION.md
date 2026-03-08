# 메인 데이터베이스 (AWS RDS) 접속 가이드

이 문서는 보안 네트워크 내에 있는 메인 데이터베이스(AWS RDS)에 **Bastion Server(징검다리 서버)**를 통해 접속하는 방법을 설명합니다.

## 📌 접속 구조
`내 컴퓨터` -(SSH)-> `Bastion Server (EC2)` -(PostgreSQL)-> `Main DB (RDS)`

---

## 🔑 사전 준비
- 접속용 키 파일: `molip-key.pem`
- 위치: 프로젝트 루트 디렉토리 (`/Users/swoo64/Desktop/MOLIP-AI`)

---

## 🏃 접속 단계

### 1. 키 파일 권한 설정
보안을 위해 키 파일의 권한을 소유자 읽기 전용으로 제한해야 합니다.
```bash
chmod 400 "molip-key.pem"
```

### 2. Bastion Server 접속 (SSH)
외부 인터넷에서 접속 가능한 징검다리 서버로 먼저 로그인합니다.
```bash
ssh -i "molip-key.pem" ubuntu@ec2-43-201-5-188.ap-northeast-2.compute.amazonaws.com
```

### 3. 실제 DB 접속 (psql)
서버에 접속된 상태(`ubuntu@ip-...:~$`)에서 실제 RDS 데이터베이스에 접속합니다.
```bash
psql \
-h ai-postgresql-vector-db.cpwk6q8qg95v.ap-northeast-2.rds.amazonaws.com \
-U molip \
-d postgres \
-p 5432
```
- **Password**: `molip1234` 입력

---

## 🚪 종료 방법 (나가기)

### 1. DB 접속 종료
`postgres=>` 상태에서 아래를 입력합니다.
```sql
\q
```

### 2. Bastion Server 접속 종료
`ubuntu@ip-...:~$` 상태에서 아래를 입력합니다.
```bash
exit
```

---

## 💻 로컬에서 메인 DB 접속/테스트 (SSH 터널링)

보안망 안에 있는 RDS에 로컬 컴퓨터의 API 서버나 테스트 코드가 직접 접속해야 할 경우, **SSH 터널링**을 사용합니다.

### 1. SSH 터널 열기 (터미널 1)
로컬 터미널에서 아래 명령어를 실행하여 내 컴퓨터의 `5433` 포트를 RDS의 `5432` 포트로 연결합니다. 이 터미널은 테스트가 끝날 때까지 유지해야 합니다.
```bash
ssh -i "molip-key.pem" -L 5433:ai-postgresql-vector-db.cpwk6q8qg95v.ap-northeast-2.rds.amazonaws.com:5432 ubuntu@ec2-43-201-5-188.ap-northeast-2.compute.amazonaws.com
```

### 2. 로컬 .env 설정 (터미널 2)
내 컴퓨터의 코드가 로컬 포트(`5433`)를 통해 RDS에 접속하도록 설정합니다.
```env
# .env 파일 수정
DATABASE_URL=postgresql+asyncpg://molip:molip1234@localhost:5433/postgres
```

### 3. 테스트 및 실행
이제 로컬에서 서버를 실행하거나 테스트를 돌리면 실제 메인 DB와 통신합니다.
```bash
# 연결 테스트
python -m pytest tests/test_connectivity.py

# 서버 실행
uvicorn app.main:app --reload
```

---

## ⚠️ 주의사항
- `molip-key.pem` 파일은 절대 외부로 유출되거나 Git에 업로드되지 않도록 주의하십시오. (현재 `.gitignore`에 등록됨)
- 메인 서버(EC2)에서 실행되는 코드는 위 과정 없이 `.env`의 `DATABASE_URL`을 통해 내부망으로 직접 접속합니다. (RDS 엔드포인트:5432 사용)
- **로컬에서 터널링 사용 시 반드시 `localhost:5433` 주소를 사용해야 하며, 실제 메인 망 배포 시에는 다시 RDS 엔드 포인트 주소로 되돌려야 합니다.**
