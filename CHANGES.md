# 변경 사항 요약: 이슈 #7

## ✅ 완료된 작업

### 1. FastAPI 서비스 생성 (`src/api/`)
- **목적**: Article/Job CRUD 및 Job enqueue 처리
- **주요 파일**:
  - `main.py`: FastAPI 앱 진입점
  - `models.py`: Pydantic 모델 (Article, Job)
  - `routes/articles.py`: Article 관련 엔드포인트
  - `routes/jobs.py`: Job 상태 조회 엔드포인트
  - `queue.py`: Redis 큐 관리

### 2. Worker 서비스 생성 (`src/worker/`)
- **목적**: Redis 큐에서 job consume → CrewAI 실행 → 결과 저장
- **주요 파일**:
  - `main.py`: Worker 진입점
  - `processor.py`: Job 처리 로직

### 3. Next.js 수정
- **`/api/generate`**: Python spawn 제거, FastAPI 호출로 변경
- **`/api/status`**: status.json 파일 읽기 제거, FastAPI 호출로 변경
- **`page.tsx`**: jobId 기반 폴링으로 변경

### 4. 의존성 추가 (`pyproject.toml`)
- `fastapi>=0.104.0`
- `uvicorn[standard]>=0.24.0`
- `redis>=5.0.0`
- `pydantic>=2.0.0`

---

## 🔄 변경 전후 비교

### Before (단일 서비스)
```
Next.js → spawn('python3', main.py) → CrewAI 실행
         ↓
    status.json 파일 쓰기
         ↓
    R2 업로드
```

### After (3-Service)
```
Next.js → FastAPI → Redis Queue
                    ↓
                 Worker → CrewAI 실행 → R2 업로드
```

---

## 📝 주요 개념 설명

### 1. **비동기 Job 처리**
- **문제**: CrewAI 실행은 2-5분 걸림 → HTTP 요청 타임아웃
- **해결**: Job Queue 패턴
  - 요청 즉시 `jobId` 반환
  - 실제 작업은 백그라운드에서 처리
  - 클라이언트는 `GET /jobs/:jobId`로 폴링

### 2. **Redis Queue**
- **역할**: Job 요청을 큐에 저장, Worker가 순차적으로 처리
- **구조**:
  - Queue: `opad:jobs` (List)
  - Status: `opad:job:{job_id}` (String, JSON)
- **작동 방식**:
  - API: `LPUSH`로 job 추가
  - Worker: `BRPOP`로 job 가져오기 (blocking)

### 3. **서비스 분리**
- **Web**: UI만 담당, Python 실행 없음
- **API**: CRUD + Job enqueue, 실제 실행 없음
- **Worker**: CrewAI 실행만 담당, HTTP 서버 없음

---

## 🚧 다음 단계 (이슈 #8, #9, #10)

### 이슈 #8: Postgres + Redis add-ons
- 현재: 메모리 저장 (임시)
- 목표: Postgres로 Article/Job 영구 저장

### 이슈 #9: Dockerfile 전략
- 현재: 단일 Dockerfile
- 목표: 3개 Dockerfile (web, api, worker)

### 이슈 #10: Health endpoint
- 현재: 기본 `/health` 엔드포인트
- 목표: Redis/DB 연결 상태 확인 추가

---

## 🔍 코드 변경 상세

### `web/app/api/generate/route.ts`
**Before:**
```typescript
const childProcess = spawn('python3', [pythonScript], {...})
```

**After:**
```typescript
// 1. Article 생성
const article = await fetch(`${apiBaseUrl}/articles`, {...})

// 2. Job enqueue
const job = await fetch(`${apiBaseUrl}/articles/${articleId}/generate`, {...})
```

### `web/app/api/status/route.ts`
**Before:**
```typescript
const content = await readFile(statusPath, 'utf-8')
```

**After:**
```typescript
const response = await fetch(`${apiBaseUrl}/jobs/${jobId}`, {...})
```

### `web/app/page.tsx`
**Before:**
- `status.json` 파일 기반 폴링

**After:**
- `jobId` 기반 폴링
- `GET /api/status?job_id=...` 호출

---

## 📚 학습 포인트

1. **Job Queue 패턴**: 장시간 작업을 비동기로 처리하는 표준 방법
2. **서비스 분리**: 단일 책임 원칙 (SRP) 적용
3. **Redis 활용**: 큐와 상태 저장소로 사용
4. **FastAPI**: Python 웹 프레임워크, 자동 API 문서 생성
5. **비동기 처리**: 클라이언트는 즉시 응답, 작업은 백그라운드에서
