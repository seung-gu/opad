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
# JWT 인증 (필수!)
# 보안을 위해 강력한 랜덤 문자열 사용
# 생성 방법: openssl rand -hex 32
JWT_SECRET_KEY=your-secure-random-secret-key-here

# CORS 설정 (선택사항, 기본값: "*")
# 프로덕션에서는 반드시 명시적 도메인 설정 권장
# 예: CORS_ORIGINS=https://app.example.com,https://www.example.com
CORS_ORIGINS=*  # 개발 환경에서만 사용

# Redis 연결
REDIS_URL=redis://localhost:6379
# 또는 Railway Redis add-on
REDIS_URL=${{Redis.REDIS_URL}}

# MongoDB 연결 (Railway MongoDB add-on)
MONGO_URL=mongodb://localhost:27017/  # 로컬 개발
# Railway: MONGO_URL is automatically provided by MongoDB add-on
# Optional: MongoDB database name (default: 'opad')
MONGODB_DATABASE=opad

# R2 설정 (결과 저장용) - 이제 사용하지 않음 (MongoDB로 마이그레이션)
# R2_BUCKET_NAME=your-bucket
# R2_ACCOUNT_ID=your-account-id
# R2_ACCESS_KEY_ID=your-key-id
# R2_SECRET_ACCESS_KEY=your-secret-key

# OpenAI (CrewAI에서 사용)
OPENAI_API_KEY=your-key
SERPER_API_KEY=your-key

# Stanza NLP (자동 설정, 환경변수 불필요)
# German pipeline (~349MB)은 API startup 시 자동 다운로드
# 모델 캐시 위치: ~/stanza_resources/
```

### Worker 서비스
```bash
# Redis 연결 (API와 동일)
REDIS_URL=redis://localhost:6379

# MongoDB 연결 (API와 동일)
MONGO_URL=mongodb://localhost:27017/  # 로컬 개발
# Railway: MONGO_URL is automatically provided by MongoDB add-on
MONGODB_DATABASE=opad  # Optional

# R2 설정 - 이제 사용하지 않음 (MongoDB로 마이그레이션)
# R2_BUCKET_NAME=your-bucket
# R2_ACCOUNT_ID=your-account-id
# R2_ACCESS_KEY_ID=your-key-id
# R2_SECRET_ACCESS_KEY=your-secret-key

# OpenAI
OPENAI_API_KEY=your-key
SERPER_API_KEY=your-key
```

---

## 🚀 로컬 개발 환경 실행

### 1. Database Services 시작
```bash
# Docker Compose로 MongoDB + Redis 실행 (권장)
docker-compose -f docker-compose.local.yml up -d

# 또는 각각 실행:

# Redis 단독 실행
docker run -d -p 6379:6379 --name opad-redis redis:7-alpine

# MongoDB 단독 실행 (로컬 설치 필요)
mongod --dbpath /path/to/data
```

### 2. 환경변수 설정
```bash
# 프로젝트 루트에서
export REDIS_URL=redis://localhost:6379
export MONGO_URL=mongodb://localhost:27017/
export MONGODB_DATABASE=opad
export OPENAI_API_KEY=your-key
export SERPER_API_KEY=your-key
export JWT_SECRET_KEY=$(openssl rand -hex 32)  # Generate secure JWT secret
```

**MongoDB 환경변수:**
- `MONGO_URL`: MongoDB connection string (default: `mongodb://localhost:27017/`)
- `MONGODB_DATABASE`: Database name (default: 'opad')

### 3. Python 의존성 설치
```bash
# 프로젝트 루트에서
# uv를 사용하여 의존성 설치 (권장)
uv sync

# 또는 pip 사용 (uv가 없는 경우)
pip install -e .
```

**참고**: 이 프로젝트는 `uv`를 사용합니다. Python 명령어 실행 시 항상 `uv run`을 사용하세요:
- `uv run python -m unittest ...`
- `uv run python script.py`

**Stanza NLP 모델 다운로드** (자동):
- API 서비스 첫 실행 시 Stanza German pipeline (~349MB)이 자동으로 다운로드됩니다.
- 다운로드는 `server/api/main.py`의 `lifespan` 함수에서 `get_nlp_port().preload()`를 통해 실행됩니다 (NLPPort/StanzaAdapter).
- 이후 실행 시에는 캐시된 모델을 사용하므로 추가 다운로드가 필요하지 않습니다.
- 수동 다운로드: `uv run python -c "import stanza; stanza.download('de')"`

### 4. API 서비스 실행 (터미널 1)
```bash
cd /Users/seung-gu/projects/opad
PYTHONPATH=src uvicorn api.main:app --reload --port 8001
```

### 5. Worker 서비스 실행 (터미널 2)
```bash
cd /Users/seung-gu/projects/opad
PYTHONPATH=src uv run python -m worker.main
```

### 6. Web 서비스 실행 (터미널 3)
```bash
cd /Users/seung-gu/projects/opad/client/apps/web
npm install
API_BASE_URL=http://localhost:8001 npm run dev
```

### 7. 테스트 (Optional)
```bash
# Python 테스트 실행
uv run pytest server/api/tests/ -v
uv run pytest server/worker/tests/ -v

# 커버리지와 함께 실행
uv run pytest --cov=src --cov-report=term-missing
```

### 8. API 확인
- FastAPI Swagger UI: http://localhost:8001/docs
- API 엔드포인트 목록: http://localhost:8001/endpoints
- Web UI: http://localhost:8000

---

## 📦 Railway Deployment Setup

### ⚠️ Important: Environment Structure
**All 3 services must be in the same Railway environment/project.**
- ❌ **Wrong**: Create 3 separate environments, each with 1 service
- ✅ **Correct**: Create all 3 services (web/api/worker) within the same environment
- **Why**: Railway variable references (`${{ service.VAR }}`) only work within the same environment

### 1. Create Services
Create 3 services in the **same Railway project**:
- `web` (Next.js)
- `api` (FastAPI)
- `worker` (Python)

### 2. Configure Dockerfile Path
For each service: Settings → Build → Dockerfile Path:
- `web`: `Dockerfile.web`
- `api`: `Dockerfile.api`
- `worker`: `Dockerfile.worker`

### 3. Add Database Add-ons
- **Add MongoDB Add-on** to API service (or any service - Railway shares variables)
  - Railway automatically provides `MONGO_URL` environment variable
  - MongoDB is pre-configured with `--setParameter diagnosticDataCollectionEnabled=false`
  - Note: WiredTiger checkpoint logs may still appear (this is normal MongoDB behavior)
- **Add Redis Add-on** to API service
  - Worker service references API's Redis variables

### 4. Environment Variables

#### Web Service
```
API_BASE_URL=https://${{ api.RAILWAY_PUBLIC_DOMAIN }}
```

#### API Service
- **MongoDB Add-on** automatically provides `MONGO_URL` (no configuration needed)
- **Redis Add-on** automatically provides `REDIS_URL` (no configuration needed)
- Optional: `MONGODB_DATABASE=opad` (default is 'opad')

#### Worker Service
```
# Redis (from API service)
REDIS_URL=${{ api.REDIS_URL }}

# MongoDB (from API service or add-on directly)
MONGO_URL=${{ api.MONGO_URL }}  # or use MongoDB add-on variable
MONGODB_DATABASE=opad  # Optional (default: 'opad')

# R2 설정 - 더 이상 사용하지 않음 (MongoDB로 마이그레이션됨)
# R2_BUCKET_NAME=your-bucket
# R2_ACCOUNT_ID=your-account-id
# R2_ACCESS_KEY_ID=your-key-id
# R2_SECRET_ACCESS_KEY=your-secret-key

# OpenAI (CrewAI에서 사용)
OPENAI_API_KEY=your-key
SERPER_API_KEY=your-key
```

### 5. Public Networking Setup
- API service: Settings → Networking → Generate Domain
- Port: Railway auto-assigns (usually 8080)

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

---

## 📊 Redis Data Format

### Job Queue (`opad:jobs`)
```json
{
  "job_id": "uuid",
  "article_id": "uuid",
  "inputs": {
    "language": "German",
    "level": "B2",
    "length": "500",
    "topic": "AI"
  },
  "created_at": "2026-01-08T14:00:00"
}
```

### Job Status (`opad:job:{job_id}`)
```json
{
  "id": "uuid",
  "status": "queued|running|completed|failed",
  "progress": 0-100,
  "message": "Status message",
  "error": "Error message (if failed)",
  "updated_at": "2026-01-08T14:00:00"
}
```

**Job Status Flow (Redis, 24h TTL):**
- `queued` → `running` → `completed` / `failed`
- `progress`: 0 → 25 → 50 → 75 → 100

### Article Status (MongoDB)

**Article Status** (MongoDB, 영구 저장):
- `running`: Article 생성 시 초기 상태 (처리 중)
- `completed`: Article 생성 완료
- `failed`: Article 생성 실패
- `deleted`: Article 삭제 (soft delete)

**Article Status Flow:**
- 생성 시: `running`
- 완료 시: `completed`
- 실패 시: `failed`

**Note**: Article Status와 Job Status는 별도로 관리됩니다:
- **Article Status (MongoDB)**: Article의 최종 상태 (영구 저장)
- **Job Status (Redis)**: Job 처리의 실시간 상태 (24시간 후 자동 삭제)
