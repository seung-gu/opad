# 설정 가이드: 3-Service 아키텍처

## 🔧 환경변수 설정

### Web 서비스 (Next.js)
```bash
# FastAPI 서비스 URL
API_BASE_URL=http://api:8000  # Railway 내부 통신
# 또는
API_BASE_URL=https://your-api-service.railway.app  # 외부 URL
```

### API 서비스 (FastAPI)
```bash
# Redis 연결
REDIS_URL=redis://localhost:6379
# 또는 Railway Redis add-on
REDIS_URL=${{Redis.REDIS_URL}}

# R2 설정 (결과 저장용)
R2_BUCKET_NAME=your-bucket
R2_ACCOUNT_ID=your-account-id
R2_ACCESS_KEY_ID=your-key-id
R2_SECRET_ACCESS_KEY=your-secret-key

# OpenAI (CrewAI에서 사용)
OPENAI_API_KEY=your-key
SERPER_API_KEY=your-key
```

### Worker 서비스
```bash
# Redis 연결 (API와 동일)
REDIS_URL=redis://localhost:6379

# R2 설정
R2_BUCKET_NAME=your-bucket
R2_ACCOUNT_ID=your-account-id
R2_ACCESS_KEY_ID=your-key-id
R2_SECRET_ACCESS_KEY=your-secret-key

# OpenAI
OPENAI_API_KEY=your-key
SERPER_API_KEY=your-key
```

---

## 🚀 로컬 개발 환경 실행

### 1. Redis 시작
```bash
# Docker로 Redis 실행
docker run -d -p 6379:6379 --name opad-redis redis:7-alpine

# 또는 로컬 Redis 설치
redis-server
```

### 2. 환경변수 설정
```bash
# 프로젝트 루트에서
export REDIS_URL=redis://localhost:6379
export OPENAI_API_KEY=your-key
export SERPER_API_KEY=your-key
```

### 3. Python 의존성 설치
```bash
# 프로젝트 루트에서
pip install -e .
```

### 4. API 서비스 실행 (터미널 1)
```bash
cd /Users/seung-gu/projects/opad
PYTHONPATH=src uvicorn api.main:app --reload --port 8000
```

### 5. Worker 서비스 실행 (터미널 2)
```bash
cd /Users/seung-gu/projects/opad
PYTHONPATH=src python -m worker.main
```

### 6. Web 서비스 실행 (터미널 3)
```bash
cd /Users/seung-gu/projects/opad/src/web
npm install
API_BASE_URL=http://localhost:8000 npm run dev
```

---

## 📦 Railway 배포 설정

### 서비스별 Start Command

#### Web 서비스
```bash
cd web && npm install && npm run build && npx next start -p $PORT
```

#### API 서비스
```bash
pip install -e . && uvicorn api.main:app --host 0.0.0.0 --port $PORT
```

#### Worker 서비스
```bash
pip install -e . && python -m worker.main
```
(Worker는 HTTP 포트가 필요 없으므로 PORT 사용 안 함)

---

## 🔍 테스트 방법

### 1. API 서비스 테스트
```bash
# Health check
curl http://localhost:8000/health

# Article 생성
curl -X POST http://localhost:8000/articles \
  -H "Content-Type: application/json" \
  -d '{
    "language": "German",
    "level": "B2",
    "length": "500",
    "topic": "AI"
  }'

# Job enqueue (article_id는 위에서 받은 값)
curl -X POST http://localhost:8000/articles/{article_id}/generate \
  -H "Content-Type: application/json" \
  -d '{
    "language": "German",
    "level": "B2",
    "length": "500",
    "topic": "AI"
  }'

# Job 상태 조회 (job_id는 위에서 받은 값)
curl http://localhost:8000/jobs/{job_id}
```

### 2. Worker 테스트
- Worker가 실행 중이면 자동으로 큐에서 job을 consume
- 로그에서 "Processing job..." 메시지 확인

### 3. 통합 테스트
1. Web UI에서 "Generate New Article" 클릭
2. 브라우저 개발자 도구 Network 탭에서 `/api/generate` 확인
3. `job_id`가 반환되는지 확인
4. `/api/status?job_id=...` 폴링 확인
5. 완료되면 article이 표시되는지 확인

---

## 🐛 문제 해결

### Redis 연결 실패
- `REDIS_URL` 환경변수 확인
- Redis 서비스가 실행 중인지 확인
- Railway에서 Redis add-on이 연결되어 있는지 확인

### API 호출 실패 (Web → API)
- `API_BASE_URL` 환경변수 확인
- Railway 내부 통신: `http://api:8000` (서비스 이름 사용)
- 외부 통신: `https://your-api-service.railway.app`

### Worker가 job을 처리하지 않음
- Worker가 실행 중인지 확인
- Redis 큐에 job이 있는지 확인: `redis-cli LLEN opad:jobs`
- Worker 로그 확인

### Job 상태가 업데이트되지 않음
- Redis에 상태가 저장되는지 확인: `redis-cli GET opad:job:{job_id}`
- Worker 로그에서 에러 확인
